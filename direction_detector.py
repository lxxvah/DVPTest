# direction_detector.py
"""
压力变化方向判断模块（独立、无外部依赖、全自适应）

输入：t（时间）、p（压力）—— 只用这两个
输出：DirectionResult，含方向、斜率、峰值回落、采样率、噪声估计、置信度

自适应三件事：
  1. 采样率 fs     ← 从相邻帧 Δt 的 EMA
  2. 压力噪声 σ_p  ← 从"最平静窗口"的中位数估计（抗趋势污染）
  3. 斜率噪声 σ_s  ← 由 σ_p 和回归窗口帧数解析推导

所有阈值均由 σ_p、σ_s、峰值自动推导：
  - 斜率符号门限 = 3 × σ_s
  - 进入 FALLING 的斜率门限 = 8 × σ_s
  - 峰值回落绝对门限 = max(5 × σ_p, 峰值的 0.5%)

这样无论设备是 2 Hz 还是 100 Hz、充气/泄气是 5 还是 500 mmHg/s，
逻辑都成立，不需要手工调阈值。
"""
import math
import statistics
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple, List


class Direction(Enum):
    RISING = "RISING"
    FALLING = "FALLING"
    STABLE = "STABLE"


@dataclass
class DirectionResult:
    direction: Direction
    slope: float             # 回归斜率 (mmHg/s)
    slope_ema: float         # EMA 平滑后的斜率
    peak_drop: float         # 从峰值回落 (mmHg)
    peak_drop_ratio: float   # 从峰值回落比例
    sample_rate: float       # 估算采样率 (Hz)
    sigma_p: float           # 估算压力噪声 (mmHg)
    sigma_slope: float       # 估算斜率噪声 (mmHg/s)
    confidence: float
    reason: str

    def __repr__(self):
        return (f"DirectionResult({self.direction.value:7s}, "
                f"slope_ema={self.slope_ema:8.2f}, "
                f"drop={self.peak_drop:6.2f}({self.peak_drop_ratio*100:4.1f}%), "
                f"fs={self.sample_rate:5.1f}Hz, σp={self.sigma_p:.3f}, "
                f"σs={self.sigma_slope:.1f}, conf={self.confidence:.2f})")


class DirectionDetector:
    # ==================== 采样率估计 ====================
    DT_EMA_ALPHA = 0.3
    MIN_VALID_DT = 0.005
    MAX_VALID_DT = 2.0
    INIT_DT      = 0.02

    # ==================== 回归窗口（按秒自适应） ====================
    TARGET_WINDOW_SEC = 1.0
    MIN_FRAMES        = 3
    MAX_FRAMES        = 24

    # ==================== 噪声估计 ====================
    NOISE_HISTORY = 40          # 最近 N 帧用于估计噪声
    NOISE_MIN_FRAMES = 6        # 至少需要这么多帧才开始估计
    NOISE_FLOOR = 0.01          # σ_p 下限，防止除零/过敏感

    # ==================== 自适应阈值系数 ====================
    K_SIGN   = 3.0              # 斜率符号门限 = K_SIGN × σ_slope
    K_ENTER  = 8.0              # 进入 FALLING = K_ENTER × σ_slope
    K_DROP_ABS = 5.0            # 峰值回落绝对门限 = K_DROP_ABS × σ_p
    DROP_RATIO_ENTER = 0.005    # 或峰值的 0.5%

    # ==================== 迟滞（退出阈值 = 进入的 40%） ====================
    HYSTERESIS = 0.4

    # ==================== 置信度 ====================
    SLOPE_EMA_ALPHA = 0.4

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
        self.reset()

    # ============================================================
    def reset(self):
        self._t_hist = deque(maxlen=self.MAX_FRAMES)
        self._p_hist = deque(maxlen=self.MAX_FRAMES)

        # 采样率
        self._sample_dt: Optional[float] = None
        self._sample_rate = 1.0 / self.INIT_DT
        self._dt_samples = 0

        # 噪声（滑动窗口）
        self._noise_buf = deque(maxlen=self.NOISE_HISTORY)
        self._sigma_p = self.NOISE_FLOOR

        # 状态
        self._slope_ema = 0.0
        self._current = Direction.STABLE
        self._peak_p: Optional[float] = None
        self._peak_t: Optional[float] = None
        self._frame_count = 0

    # ============================================================
    def process(self, t, p, signed_rate=0.0, acceleration=0.0) -> DirectionResult:
        if (math.isnan(t) or math.isnan(p)
                or math.isinf(t) or math.isinf(p)):
            return self._make_result(0.0, 0.0, "输入异常", 0.0)

        self._frame_count += 1

        # ---------- 1. 更新采样率 ----------
        self._update_sample_rate(t)

        # ---------- 2. 入队 ----------
        self._t_hist.append(float(t))
        self._p_hist.append(float(p))

        # ---------- 3. 更新峰值 ----------
        if self._peak_p is None or p > self._peak_p:
            self._peak_p = float(p)
            self._peak_t = float(t)

        peak_drop = (self._peak_p - p) if self._peak_p is not None else 0.0
        peak_drop_ratio = (peak_drop / self._peak_p) if (self._peak_p or 0) > 1.0 else 0.0

        # ---------- 4. 更新噪声估计 ----------
        self._update_noise(p)

        # ---------- 5. 回归斜率 ----------
        slope = self._compute_slope()
        self._slope_ema = (self.SLOPE_EMA_ALPHA * slope
                           + (1.0 - self.SLOPE_EMA_ALPHA) * self._slope_ema)

        # ---------- 6. 由噪声推导当前阈值 ----------
        sigma_slope = self._sigma_slope()
        thr_sign  = self.K_SIGN  * sigma_slope
        thr_enter = self.K_ENTER * sigma_slope
        thr_drop_abs = max(self.K_DROP_ABS * self._sigma_p,
                           (self._peak_p or 0.0) * self.DROP_RATIO_ENTER)

        # ---------- 7. 决策 ----------
        direction, reason = self._decide(
            self._slope_ema, peak_drop, peak_drop_ratio,
            thr_sign, thr_enter, thr_drop_abs
        )
        self._current = direction

        conf = self._compute_confidence(peak_drop_ratio, self._slope_ema,
                                        thr_enter, thr_drop_abs)
        return self._make_result(slope, peak_drop, reason,
                                 peak_drop_ratio, conf, sigma_slope)

    # ============================================================
    # 采样率
    # ============================================================
    def _update_sample_rate(self, t):
        if len(self._t_hist) == 0:
            return
        dt = float(t) - self._t_hist[-1]
        if not (self.MIN_VALID_DT < dt < self.MAX_VALID_DT):
            return
        if self._sample_dt is None:
            self._sample_dt = dt
        else:
            a = self.DT_EMA_ALPHA
            self._sample_dt = (1 - a) * self._sample_dt + a * dt
        self._sample_rate = 1.0 / self._sample_dt
        self._dt_samples += 1

    # ============================================================
    # 噪声估计
    # ------------------------------------------------------------
    # 用相邻帧差分的稳健估计：
    #     diff = p[i] - p[i-1]
    #     MAD  = median(|diff - median(diff)|)
    #     σ_p ≈ 1.4826 * MAD / √2
    # 这种估计不会被斜坡趋势污染（斜坡的差分是常数，中位数减法消掉）
    # ============================================================
    def _update_noise(self, p):
        n = len(self._p_hist)
        if n < 2:
            return
        diff = float(p) - self._p_hist[-2]
        self._noise_buf.append(diff)

        if len(self._noise_buf) < self.NOISE_MIN_FRAMES:
            return

        diffs = list(self._noise_buf)
        med = statistics.median(diffs)
        mad = statistics.median([abs(d - med) for d in diffs])
        sigma = 1.4826 * mad / math.sqrt(2.0)
        self._sigma_p = max(sigma, self.NOISE_FLOOR)

    # ============================================================
    # 从 σ_p 推导 σ_slope
    # ------------------------------------------------------------
    # 对 n 点等间隔最小二乘回归：
    #     Var(slope) = σ_p² / Σ(tᵢ - t̄)²
    # 令 Δt = 1/fs，n 点等间隔：
    #     Σ(tᵢ - t̄)² = Δt² · n(n²-1)/12
    #     因此 σ_slope = σ_p / (Δt · √(n(n²-1)/12))
    # ============================================================
    def _sigma_slope(self) -> float:
        n = self._effective_window()
        if n < self.MIN_FRAMES:
            return 0.0
        dt = self._sample_dt if self._sample_dt else self.INIT_DT
        denom = dt * math.sqrt(n * (n * n - 1) / 12.0)
        if denom < 1e-12:
            return 0.0
        return self._sigma_p / denom

    def _effective_window(self) -> int:
        n = len(self._t_hist)
        if n < self.MIN_FRAMES:
            return n
        if self._sample_dt is None:
            return min(n, 6)
        target = int(self.TARGET_WINDOW_SEC / self._sample_dt) + 1
        return max(self.MIN_FRAMES, min(target, self.MAX_FRAMES, n))

    # ============================================================
    def _compute_slope(self) -> float:
        n = self._effective_window()
        if n < self.MIN_FRAMES:
            return 0.0
        ts = list(self._t_hist)[-n:]
        ps = list(self._p_hist)[-n:]
        t_mean = sum(ts) / n
        p_mean = sum(ps) / n
        num = den = 0.0
        for i in range(n):
            dt = ts[i] - t_mean
            num += dt * (ps[i] - p_mean)
            den += dt * dt
        if den < 1e-12:
            return 0.0
        s = num / den
        return 0.0 if (math.isinf(s) or math.isnan(s)) else s

    # ============================================================
    def _decide(self, slope_ema, peak_drop, peak_drop_ratio,
                thr_sign, thr_enter, thr_drop_abs):
        # 峰值判据（进入 / 退出用迟滞）
        left_peak_enter = peak_drop >= thr_drop_abs
        left_peak_exit  = peak_drop >= thr_drop_abs * self.HYSTERESIS

        # 斜率符号
        if slope_ema > thr_sign:
            sign = "up"
        elif slope_ema < -thr_sign:
            sign = "down"
        else:
            sign = "flat"

        # ---- 当前 FALLING ----
        if self._current == Direction.FALLING:
            if not left_peak_exit:
                return Direction.STABLE, f"回到峰值附近 drop={peak_drop:.2f}"
            if sign == "up":
                return Direction.STABLE, "斜率转正"
            return Direction.FALLING, f"离开峰值 {peak_drop:.1f}"

        # ---- 进入 FALLING：两个条件同时满足 ----
        if left_peak_enter and slope_ema < -thr_enter:
            return Direction.FALLING, (f"drop={peak_drop:.1f} ≥ {thr_drop_abs:.1f} "
                                       f"且 slope={slope_ema:.1f} < {-thr_enter:.1f}")

        # ---- 其他 ----
        if sign == "up":
            return Direction.RISING, f"slope={slope_ema:.1f}"
        if sign == "down" and not left_peak_enter:
            return Direction.STABLE, f"峰值附近抖动 drop={peak_drop:.2f}"
        return Direction.STABLE, f"slope={slope_ema:.1f}"

    # ============================================================
    def _compute_confidence(self, ratio, slope_ema, thr_enter, thr_drop_abs):
        if ratio <= 0:
            return 0.0
        drop_score = min(1.0, ratio / 0.05)                     # 5% 满
        slope_score = min(1.0, abs(slope_ema) / max(thr_enter * 4, 1e-6))
        return min(1.0, 0.6 * drop_score + 0.4 * slope_score)

    # ============================================================
    def _make_result(self, slope, peak_drop, reason,
                     peak_drop_ratio=0.0, conf=0.0, sigma_slope=0.0):
        return DirectionResult(
            direction=self._current,
            slope=slope,
            slope_ema=self._slope_ema,
            peak_drop=peak_drop,
            peak_drop_ratio=peak_drop_ratio,
            sample_rate=self._sample_rate,
            sigma_p=self._sigma_p,
            sigma_slope=sigma_slope,
            confidence=conf,
            reason=reason,
        )

    # ============================================================
    # 查询接口
    # ============================================================
    def get_current(self) -> Direction:
        return self._current

    def get_peak(self) -> Tuple[Optional[float], Optional[float]]:
        return self._peak_t, self._peak_p

    def get_sample_rate(self) -> float:
        return self._sample_rate

    def get_sigma_p(self) -> float:
        return self._sigma_p

    def get_sigma_slope(self) -> float:
        return self._sigma_slope()

    def is_ready(self) -> bool:
        return (len(self._t_hist) >= self.MIN_FRAMES
                and self._dt_samples >= 2
                and len(self._noise_buf) >= self.NOISE_MIN_FRAMES)