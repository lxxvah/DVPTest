# result_calculator.py
"""速率计算与运动学分析模块"""
import math
import numpy as np
from typing import List, Optional, Tuple
from config import Config


class ResultCalculator:
    # ==================== 原有函数（保持不变） ====================

    @staticmethod
    def compute_instant_rate(x_data: List[float], y_data: List[float], idx: int = -1) -> float:
        """原始瞬时速率（无滤波）"""
        if len(x_data) < 2:
            return 0.0
        if idx < 0:
            idx = len(x_data) - 1
        if idx < 1 or idx >= len(x_data):
            return 0.0
        dt = x_data[idx] - x_data[idx - 1]
        dp = y_data[idx] - y_data[idx - 1]
        if abs(dt) < Config.TIME_DELTA_EPSILON:
            return 0.0
        rate = dp / dt
        if math.isinf(rate) or math.isnan(rate):
            return 0.0
        return max(-Config.MAX_RATE_LIMIT, min(Config.MAX_RATE_LIMIT, rate))

    @staticmethod
    def compute_signed_rate_filtered(
        x_data: List[float],
        y_data: List[float],
        idx: int = -1,
        window: int = Config.RATE_FILTER_WINDOW,
        sigma: float = Config.RATE_FILTER_SIGMA
    ) -> float:
        """带中值滤波的速率（抗噪声）"""
        if len(x_data) < 3:
            if len(x_data) < 2:
                return 0.0
            if idx < 0:
                idx = len(x_data) - 1
            if idx < 1 or idx >= len(x_data):
                return 0.0
            dt = x_data[idx] - x_data[idx - 1]
            dp = y_data[idx] - y_data[idx - 1]
            if abs(dt) < Config.TIME_DELTA_EPSILON:
                return 0.0
            rate = dp / dt
            if math.isinf(rate) or math.isnan(rate):
                return 0.0
            return max(-Config.MAX_RATE_LIMIT, min(Config.MAX_RATE_LIMIT, rate))

        if idx < 0:
            idx = len(x_data) - 1
        if idx < 1 or idx >= len(x_data):
            return 0.0

        start = max(0, idx - window)
        end = min(len(x_data), idx + window + 1)
        win_y = y_data[start:end]
        win_x = x_data[start:end]

        median = np.median(win_y)
        std = np.std(win_y)
        if std == 0:
            dt = x_data[idx] - x_data[idx - 1]
            dp = y_data[idx] - y_data[idx - 1]
            if abs(dt) < Config.TIME_DELTA_EPSILON:
                return 0.0
            rate = dp / dt
            if math.isinf(rate) or math.isnan(rate):
                return 0.0
            return max(-Config.MAX_RATE_LIMIT, min(Config.MAX_RATE_LIMIT, rate))

        current_p = y_data[idx]
        if abs(current_p - median) > sigma * std:
            # 异常值：使用窗口整体斜率
            dt = win_x[-1] - win_x[0]
            dp = win_y[-1] - win_y[0]
            if abs(dt) < Config.TIME_DELTA_EPSILON:
                return 0.0
            rate = dp / dt
            if math.isinf(rate) or math.isnan(rate):
                return 0.0
            return max(-Config.MAX_RATE_LIMIT, min(Config.MAX_RATE_LIMIT, rate))
        else:
            # 正常值：使用瞬时差分
            dt = x_data[idx] - x_data[idx - 1]
            dp = y_data[idx] - y_data[idx - 1]
            if abs(dt) < Config.TIME_DELTA_EPSILON:
                return 0.0
            rate = dp / dt
            if math.isinf(rate) or math.isnan(rate):
                return 0.0
            return max(-Config.MAX_RATE_LIMIT, min(Config.MAX_RATE_LIMIT, rate))

    @staticmethod
    def compute_rate_curve(x_data: List[float], y_data: List[float]) -> np.ndarray:
        """计算绝对值速率曲线（用于绘图）"""
        if len(x_data) < 2:
            return np.array([0.0])
        dt = np.diff(x_data)
        dp = np.diff(y_data)
        dt = np.where(np.abs(dt) < Config.TIME_DELTA_EPSILON, Config.ZERO_TIME_DELTA, dt)
        rate = dp / dt
        rate = np.nan_to_num(rate, nan=0.0, posinf=0.0, neginf=0.0)
        rate = np.clip(rate, -Config.MAX_RATE_LIMIT, Config.MAX_RATE_LIMIT)
        rate = np.abs(rate)
        rate = np.clip(rate, 0, Config.RATE_CURVE_MAX)
        return np.concatenate(([0], rate))

    # ==================== ★ 新增：统一运动学计算 ====================

    @staticmethod
    def compute_kinematics(
        curr_t: float,
        curr_p: float,
        prev_t: Optional[float],
        prev_p: Optional[float],
        prev_v: Optional[float],
        rate_limit: float = Config.MAX_RATE_LIMIT,
        accel_limit: float = Config.MAX_ACCELERATION_LIMIT
    ) -> Tuple[float, float, float, float]:
        """
        统一的运动学计算：根据当前时刻数据和历史状态，计算速度（一阶导）和加速度（二阶导）

        Args:
            curr_t:     当前时刻 (s)
            curr_p:     当前压力 (mmHg)
            prev_t:     上一时刻 (s)，首次调用传入 None
            prev_p:     上一时刻压力 (mmHg)，首次调用传入 None
            prev_v:     上一时刻速度 (mmHg/s)，首次调用传入 None
            rate_limit: 速度限幅（防止传感器尖峰，默认 Config.MAX_RATE_LIMIT）
            accel_limit: 加速度限幅（防止极端值，默认 10000 mmHg/s²）

        Returns:
            Tuple[float, float, float, float]: (curr_t, curr_p, velocity, acceleration)
                - velocity:   带符号速度，正值=充气，负值=泄气
                - acceleration: 带符号加速度，负值=加速泄气/减速充气，正值=减速泄气/加速充气
        """
        # ---- 1. 处理首次调用（无历史数据） ----
        if prev_t is None or prev_p is None:
            return curr_t, curr_p, 0.0, 0.0

        # ---- 2. 计算时间差（防止除零） ----
        dt = curr_t - prev_t
        if abs(dt) < Config.TIME_DELTA_EPSILON:
            # 时间没有前进，无法计算有效速度/加速度
            return curr_t, curr_p, 0.0, 0.0

        # ---- 3. 计算速度（一阶导）并限幅 ----
        v_raw = (curr_p - prev_p) / dt

        # 处理 inf/nan
        if math.isinf(v_raw) or math.isnan(v_raw):
            v = 0.0
        else:
            v = max(-rate_limit, min(rate_limit, v_raw))

        # ---- 4. 计算加速度（二阶导）并限幅 ----
        if prev_v is None:
            # 没有上一时刻速度，无法计算加速度
            a = 0.0
        else:
            a_raw = (v - prev_v) / dt
            if math.isinf(a_raw) or math.isnan(a_raw):
                a = 0.0
            else:
                a = max(-accel_limit, min(accel_limit, a_raw))

        # ---- 5. 返回结果 ----
        return curr_t, curr_p, v, a