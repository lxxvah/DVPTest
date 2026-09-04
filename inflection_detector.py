# inflection_detector.py
"""
拐点检测模块
职责：从实时数据流中检测泄气拐点（压力从稳定转为下降的转折点）
输入：(t, p, signed_rate, acceleration)
输出：拐点 (t, p, rate) 或 None

使用方式：
    detector = InflectionDetector()
    
    # 在 process_data 中逐点调用
    inflection = detector.process(t, p, signed_rate, acceleration)
    if inflection:
        # 检测到拐点，处理逻辑
        pass
"""

import logging
from typing import Optional, Tuple, Dict, List
from config import Config

logger = logging.getLogger("DVPTest")


class InflectionDetector:
    """
    多场景自适应拐点检测器
    支持：快速泄气、中速泄气、缓慢泄气、微变泄气、漏气背景下的主动泄气
    """
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """重置所有状态"""
        self._inflection_detected = False
        
        # 历史数据（最近10个点）
        self._p: List[float] = []
        self._t: List[float] = []
        self._rate: List[float] = []
        self._accel: List[float] = []
        
        # 峰值跟踪
        self._peak_p: float = 0.0
        self._peak_t: float = 0.0
        self._peak_set: bool = False
        
        # 漏气检测
        self._slow_leak_detected: bool = False
        self._slow_leak_start: Optional[Tuple[float, float]] = None  # (t, p)
        self._slow_leak_duration: float = 0.0
        self._leak_rate_avg: float = 0.0
        
        # 候选拐点
        self._candidate: Optional[Tuple[float, float, float]] = None  # (t, p, rate)
        self._candidate_count: int = 0
        
        # 主动泄气开始检测
        self._active_start: Optional[Tuple[float, float]] = None
        self._active_count: int = 0
    
    def process(self, t: float, p: float, signed_rate: float, acceleration: float) -> Optional[Tuple[float, float, float, str]]:
        """
        处理单点数据，返回拐点信息
        
        Args:
            t: 时间 (s)
            p: 压力 (mmHg)
            signed_rate: 带符号速率 (mmHg/s)
            acceleration: 加速度 (mmHg/s²)
        
        Returns:
            None: 未检测到拐点
            Tuple[float, float, float, str]: (拐点时间, 拐点压力, 拐点速率, 检测方法)
        """
        if self._inflection_detected:
            return None
        
        # ---- 1. 更新峰值 ----
        if not self._peak_set or p > self._peak_p:
            self._peak_p = p
            self._peak_t = t
            self._peak_set = True
        
        # ---- 2. 更新历史数据 ----
        self._p.append(p)
        self._t.append(t)
        self._rate.append(signed_rate)
        self._accel.append(acceleration)
        
        if len(self._p) > Config.INFLECTION_HISTORY_SIZE:
            self._p.pop(0)
            self._t.pop(0)
            self._rate.pop(0)
            self._accel.pop(0)
        
        # 至少需要4个点做趋势判断
        if len(self._p) < Config.INFLECTION_MIN_POINTS:
            return None
        
        # ---- 3. 计算趋势指标 ----
        p0, p1, p2, p3 = self._p[-4], self._p[-3], self._p[-2], self._p[-1]
        t0, t1, t2, t3 = self._t[-4], self._t[-3], self._t[-2], self._t[-1]
        
        if t3 - t0 > Config.INFLECTION_MIN_TIME_DELTA:
            slope_4 = (p3 - p0) / (t3 - t0)
        else:
            slope_4 = 0.0
        
        if t3 - t1 > Config.INFLECTION_MIN_TIME_DELTA:
            slope_3 = (p3 - p1) / (t3 - t1)
        else:
            slope_3 = 0.0
        
        current_rate = self._rate[-1]
        current_accel = self._accel[-1]
        distance_to_peak = self._peak_p - p
        
        # ---- 4. 执行各策略检测 ----
        result = None
        
        # ---- 4.1 漏气检测（抑制误触发） ----
        if (distance_to_peak < Config.INFLECTION_LEAK_PEAK_DISTANCE
            and Config.INFLECTION_SLOW_LEAK_RATE_MIN < current_rate
            < Config.INFLECTION_SLOW_LEAK_RATE_MAX):
            if not self._slow_leak_detected:
                self._slow_leak_detected = True
                self._slow_leak_start = (t, p)
                self._slow_leak_duration = 0.0
                self._leak_rate_avg = current_rate
                logger.debug(f"[漏气] 检测到缓慢漏气 @ {t:.2f}s, rate={current_rate:.2f}")
            else:
                start_t, _ = self._slow_leak_start
                self._slow_leak_duration = t - start_t
                self._leak_rate_avg = (
                    self._leak_rate_avg * Config.INFLECTION_LEAK_AVERAGE_WEIGHT
                    + current_rate * Config.INFLECTION_LEAK_CURRENT_WEIGHT
                )
            
            # 漏气期间重置候选
            self._candidate = None
            self._candidate_count = 0
            self._active_start = None
            self._active_count = 0
            return None
        
        # ---- 4.2 从漏气状态转换到主动泄气 ----
        if self._slow_leak_detected and current_rate < Config.INFLECTION_ACTIVE_FROM_LEAK_RATE:
            logger.debug(f"[主动泄气] 从漏气状态转换 @ {t:.2f}s, rate={current_rate:.2f}")
            result = self._confirm(t, p, current_rate, "主动泄气(漏气后)")
        
        # ---- 4.3 正常主动泄气检测（速率+加速度） ----
        if (result is None and current_rate < Config.INFLECTION_ACTIVE_RATE
            and current_accel < Config.INFLECTION_ACTIVE_ACCELERATION
            and distance_to_peak > Config.INFLECTION_ACTIVE_PEAK_DISTANCE):
            if self._candidate is None:
                self._candidate = (t, p, current_rate)
                self._candidate_count = 1
            else:
                cand_t, cand_p, cand_rate = self._candidate
                if p < cand_p and current_rate < cand_rate:
                    self._candidate_count += 1
                else:
                    self._candidate = (t, p, current_rate)
                    self._candidate_count = 1
            
            if self._candidate_count >= Config.INFLECTION_CANDIDATE_COUNT:
                cand_t, cand_p, cand_rate = self._candidate
                result = self._confirm(cand_t, cand_p, cand_rate, "速率+加速度")
        
        # ---- 4.4 仅速率持续下降（加速度不明显） ----
        if (result is None and current_rate < Config.INFLECTION_CONTINUOUS_RATE
            and distance_to_peak > Config.INFLECTION_ACTIVE_PEAK_DISTANCE):
            if self._active_start is None:
                self._active_start = (t, p)
                self._active_count = 1
            else:
                start_t, start_p = self._active_start
                if p < start_p:
                    self._active_count += 1
                    if ((start_p - p) > Config.INFLECTION_CONTINUOUS_DROP
                            or self._active_count >= Config.INFLECTION_ACTIVE_COUNT):
                        result = self._confirm(
                            start_t, start_p,
                            (p - start_p) / (t - start_t),
                            "持续下降"
                        )
                else:
                    self._active_start = (t, p)
                    self._active_count = 1
        
        # ---- 4.5 连续3点下降（最灵敏） ----
        if result is None and len(self._p) >= Config.INFLECTION_MIN_POINTS:
            if p1 < p0 and p2 < p1 and p3 < p2:
                total_drop = p0 - p3
                if (total_drop > Config.INFLECTION_TOTAL_DROP
                    and distance_to_peak > Config.INFLECTION_CONTINUOUS_PEAK_DISTANCE):
                    result = self._confirm(
                        t1, p1,
                        (p3 - p0) / (t3 - t0),
                        "连续下降"
                    )
        
        # ---- 5. 重置机制 ----
        if current_rate > Config.INFLECTION_RISING_RATE:
            self._candidate = None
            self._candidate_count = 0
            self._active_start = None
            self._active_count = 0
            
            if (distance_to_peak < Config.INFLECTION_RESET_PEAK_DISTANCE
                    and current_rate > Config.INFLECTION_RATE_EPSILON):
                self._slow_leak_detected = False
                self._slow_leak_start = None
        
        return result
    
    def _confirm(self, t: float, p: float, rate: float, method: str) -> Tuple[float, float, float, str]:
        """确认拐点，返回结果"""
        if self._inflection_detected:
            return None
        
        self._inflection_detected = True
        
        # 重置所有状态
        self._slow_leak_detected = False
        self._slow_leak_start = None
        self._candidate = None
        self._candidate_count = 0
        self._active_start = None
        self._active_count = 0
        
        logger.info(f"★ 泄气拐点确认 [{method}]: p={p:.2f} @ t={t:.3f}s, rate={rate:.2f}")
        
        return (t, p, rate, method)
    
    def is_detected(self) -> bool:
        """是否已检测到拐点"""
        return self._inflection_detected
    
    def get_peak(self) -> Tuple[float, float]:
        """获取当前峰值 (t, p)"""
        return (self._peak_t, self._peak_p) if self._peak_set else (None, None)