# test_managers.py
"""
第三层：状态机（完全解耦 + InflectionDetector 版）
核心逻辑：
...
"""
import logging
from enum import Enum
from typing import Callable, Optional

from inflection_detector import InflectionDetector

logger = logging.getLogger("DVPTest")


class TestPhase(Enum):
    IDLE = "IDLE"
    INFLATING = "INFLATING"
    DEFLATING = "DEFLATING"
    DONE = "DONE"


class TestManager:
    # [LOG] 移除 on_log 参数
    def __init__(self, on_result: Callable):
        self.on_result = on_result
        # [LOG] 不再需要 on_log，内部直接用 logger
        logger.debug("=== test_managers.py 已加载（新版本）===")
        # ==================== 充气参数 ====================
        self.inflate_start_val = 5.0
        self.inflate_mid_val = 200.0
        self.inflate_target_val = 300.0

        # ==================== 泄气参数 ====================
        self.deflate_start_val = 300.0
        self.deflate_mid_val = 200.0
        self.deflate_target_val = 5.0

        # ==================== 阶段标记 ====================
        self.phase = TestPhase.IDLE
        self.rate_threshold = 0.1

        # ============================================================
        # ★ 充气数据包
        # ============================================================
        self._inflate_packet = self._create_empty_packet("inflate")
        self._inflate_peak: Optional[float] = None
        self._inflate_peak_time: Optional[float] = None
        self._inflate_result_sent = False

        # ============================================================
        # ★ 泄气数据包
        # ============================================================
        self._deflate_packet = self._create_empty_packet("deflate")
        self._deflate_peak: Optional[float] = None
        self._deflate_peak_time: Optional[float] = None
        self._deflate_result_sent = False

        self._deflate_counter = 0
        self._deflate_threshold = 3
        self._deflate_drop_threshold = 5.0

        # ============================================================
        # ★ 拐点检测器
        # ============================================================
        self._inflection_detector = InflectionDetector()

        # ============================================================
        # ★ 充气监测状态
        # ============================================================
        self._inflate_start_recorded = False
        self._inflate_mid_recorded = False
        self._inflate_target_recorded = False

        # ============================================================
        # ★ 泄气监测状态
        # ============================================================
        self._was_above_start = False
        self._was_above_mid = False
        self._was_above_target = False

        logger.debug("[TestManager] 初始化完成（完全解耦 + InflectionDetector 版）")

    # ==================== 辅助：创建空数据包 ====================
    def _create_empty_packet(self, ptype: str) -> dict:
        if ptype == "inflate":
            return {
                'state': 'IDLE',
                'start': {'value': self.inflate_start_val, 'time': None, 'reached': False},
                'mid': {'value': self.inflate_mid_val, 'time': None, 'reached': False},
                'target': {'value': self.inflate_target_val, 'time': None, 'reached': False},
                'peak': {'value': None, 'time': None}
            }
        else:
            return {
                'state': 'IDLE',
                'start': {'value': self.deflate_start_val, 'time': None, 'reached': False},
                'mid': {'value': self.deflate_mid_val, 'time': None, 'reached': False},
                'target': {'value': self.deflate_target_val, 'time': None, 'reached': False},
                'peak': {'value': None, 'time': None},
                'inflection': {'value': None, 'time': None, 'rate': None, 'method': None}
            }

    # ==================== 参数更新 ====================
    def update_inflate_params(self, start: float, mid: float, target: float) -> bool:
        if not (start < mid < target):
            return False
        self.inflate_start_val = start
        self.inflate_mid_val = mid
        self.inflate_target_val = target
        self._inflate_packet = self._create_empty_packet("inflate")
        self._inflate_peak = None
        self._inflate_peak_time = None
        self._inflate_result_sent = False
        self.reset()
        logger.debug(f"充气参数更新: start={start}, mid={mid}, target={target}")
        return True

    def update_deflate_params(self, start: float, mid: float, target: float) -> bool:
        if not (start > mid > target):
            return False
        self.deflate_start_val = start
        self.deflate_mid_val = mid
        self.deflate_target_val = target
        self._deflate_packet = self._create_empty_packet("deflate")
        self._deflate_peak = None
        self._deflate_peak_time = None
        self._deflate_result_sent = False
        self.reset()
        logger.debug(f"泄气参数更新: start={start}, mid={mid}, target={target}")
        return True

    def update_params(self, start: float, mid: float, target: float) -> bool:
        return self.update_inflate_params(start, mid, target)

    def reset(self):
        self.phase = TestPhase.IDLE
        self._inflate_packet = self._create_empty_packet("inflate")
        self._inflate_peak = None
        self._inflate_peak_time = None
        self._inflate_result_sent = False

        self._deflate_packet = self._create_empty_packet("deflate")
        self._deflate_peak = None
        self._deflate_peak_time = None
        self._deflate_result_sent = False
        self._deflate_counter = 0

        self._inflection_detector.reset()

        self._inflate_start_recorded = False
        self._inflate_mid_recorded = False
        self._inflate_target_recorded = False

        self._was_above_start = False
        self._was_above_mid = False
        self._was_above_target = False

        logger.debug("[TestManager] reset 完成")

    # ==================== ★ 核心：数据入口 ====================
    def process_data(self, t: float, p: float, signed_rate: float, acceleration: float):
        if self.phase == TestPhase.DONE:
            logger.debug(f"阶段 DONE，忽略新数据 t={t:.2f}")
            return

        # ============================================================
        # ★ 第1步：充气峰值跟踪
        # ============================================================
        if self._inflate_peak is None or p > self._inflate_peak:
            self._inflate_peak = p
            self._inflate_peak_time = t
            self._inflate_packet['peak']['value'] = p
            self._inflate_packet['peak']['time'] = t
            logger.debug(f"充气峰值更新: {p:.1f} @ {t:.2f}s")

        # ============================================================
        # ★ 第2步：充气监测
        # ============================================================
        self._monitor_inflate(t, p)

        # ============================================================
        # ★ 第3步：泄气监测
        # ============================================================
        self._monitor_deflate(t, p)

        # ============================================================
        # ★ 第4步：拐点检测
        # ============================================================
        inflection = self._inflection_detector.process(t, p, signed_rate, acceleration)
        if inflection:
            t_inf, p_inf, rate_inf, method = inflection

            self._deflate_peak = p_inf
            self._deflate_peak_time = t_inf
            self._deflate_packet['peak']['value'] = p_inf
            self._deflate_packet['peak']['time'] = t_inf
            self._deflate_packet['inflection']['value'] = p_inf
            self._deflate_packet['inflection']['time'] = t_inf
            self._deflate_packet['inflection']['rate'] = rate_inf
            self._deflate_packet['inflection']['method'] = method

            logger.success(f"★ 泄气拐点确认 [{method}]: p={p_inf:.2f} @ t={t_inf:.3f}s, rate={rate_inf:.2f}")

            if not self._inflate_result_sent:
                self._inflate_result_sent = True
                self._inflate_packet['state'] = 'DONE'
                logger.info("充气结果已生成（由泄气拐点触发）")
                logger.success("★ 充气结果已触发（拐点）")
                self.on_result('inflate', self._inflate_packet.copy())

        # ============================================================
        # ★ 第5步：物理分类
        # ============================================================
        phase = self._determine_phase(signed_rate)
        logger.debug(f"物理分类结果: {phase}")

        # ============================================================
        # ★ 第6步：阶段切换
        # ============================================================
        self._update_phase(phase, t, p)

    def _determine_phase(self, signed_rate: float) -> str:
        abs_rate = abs(signed_rate)
        if abs_rate < self.rate_threshold:
            return "STABLE"
        if signed_rate > 0:
            return "INFLATING"
        return "DEFLATING"

    # ==================== ★ 阶段更新 ====================
    def _update_phase(self, phase: str, t: float, p: float):
        # ---------- IDLE → INFLATING ----------
        if self.phase == TestPhase.IDLE:
            if phase == "INFLATING" and p >= self.inflate_start_val:
                self.phase = TestPhase.INFLATING
                self._inflate_packet['state'] = 'INFLATING'
                msg = f"IDLE → INFLATING @ {t:.2f}s, p={p:.1f}"
                logger.info(msg)

        # ---------- INFLATING → DEFLATING（保底切换） ----------
        elif self.phase == TestPhase.INFLATING:
            if phase == "DEFLATING":
                if self._inflate_peak is not None and (self._inflate_peak - p) >= self._deflate_drop_threshold:
                    self._deflate_counter += 1
                    logger.debug(f"有效泄气迹象，下降 {self._inflate_peak - p:.1f} mmHg，计数 {self._deflate_counter}/{self._deflate_threshold}")
                else:
                    if self._deflate_counter > 0:
                        logger.debug(f"泄气幅度不足，重置计数器（之前={self._deflate_counter}）")
                        self._deflate_counter = 0

                if self._deflate_counter >= self._deflate_threshold:
                    self.phase = TestPhase.DEFLATING
                    self._deflate_packet['state'] = 'DEFLATING'

                    if not self._inflection_detector.is_detected():
                        self._deflate_peak = p
                        self._deflate_peak_time = t
                        self._deflate_packet['peak']['value'] = p
                        self._deflate_packet['peak']['time'] = t
                        self._deflate_packet['inflection']['value'] = p
                        self._deflate_packet['inflection']['time'] = t
                        self._deflate_packet['inflection']['rate'] = None
                        self._deflate_packet['inflection']['method'] = "保底"
                        logger.debug(f"保底泄气峰值: {p:.1f} @ {t:.2f}s")

                    if not self._inflate_result_sent:
                        self._inflate_result_sent = True
                        self._inflate_packet['state'] = 'DONE'
                        logger.info("充气结果已生成（状态切换保底触发）")
                        logger.warning("★ 充气结果已触发（保底）")
                        self.on_result('inflate', self._inflate_packet.copy())

                    msg = f"INFLATING → DEFLATING（保底），泄气开始，当前压力 {p:.1f} @ {t:.2f}s"
                    logger.warning(msg)
                    self._deflate_counter = 0
            else:
                if self._deflate_counter > 0:
                    self._deflate_counter = 0

        # ---------- DEFLATING → DONE ----------
        elif self.phase == TestPhase.DEFLATING:
            if phase == "STABLE" and self._deflate_packet['target']['reached']:
                self.phase = TestPhase.DONE
                self._deflate_packet['state'] = 'DONE'
                logger.info("DEFLATING → DONE，泄气完成")

    # ============================================================
    # ★ 充气监测
    # ============================================================
    def _monitor_inflate(self, t: float, p: float):
        if self._inflate_start_recorded and self._inflate_mid_recorded and self._inflate_target_recorded:
            return

        if not self._inflate_start_recorded and p >= self.inflate_start_val:
            self._inflate_start_recorded = True
            self._inflate_packet['start']['time'] = t
            self._inflate_packet['start']['reached'] = True
            logger.debug(f"充气起始值 {self.inflate_start_val} mmHg 到达 @ {t:.2f}s")

        if not self._inflate_mid_recorded and p >= self.inflate_mid_val:
            self._inflate_mid_recorded = True
            self._inflate_packet['mid']['time'] = t
            self._inflate_packet['mid']['reached'] = True
            logger.debug(f"充气中间值 {self.inflate_mid_val} mmHg 到达 @ {t:.2f}s")

        if not self._inflate_target_recorded and p >= self.inflate_target_val:
            self._inflate_target_recorded = True
            self._inflate_packet['target']['time'] = t
            self._inflate_packet['target']['reached'] = True
            logger.debug(f"充气目标值 {self.inflate_target_val} mmHg 到达 @ {t:.2f}s")

    # ============================================================
    # ★ 泄气监测
    # ============================================================
    def _monitor_deflate(self, t: float, p: float):
        if (self._deflate_packet['start']['reached'] and
            self._deflate_packet['mid']['reached'] and
            self._deflate_packet['target']['reached']):
            return

        if p > self.deflate_start_val:
            self._was_above_start = True
        if p > self.deflate_mid_val:
            self._was_above_mid = True
        if p > self.deflate_target_val:
            self._was_above_target = True

        if not self._deflate_packet['start']['reached'] and self._was_above_start and p <= self.deflate_start_val:
            self._deflate_packet['start']['time'] = t
            self._deflate_packet['start']['reached'] = True
            self._was_above_start = False
            logger.success(f"★ 泄气起始值 {self.deflate_start_val} mmHg 真实穿越 @ {t:.2f}s")

        if not self._deflate_packet['mid']['reached'] and self._was_above_mid and p <= self.deflate_mid_val:
            self._deflate_packet['mid']['time'] = t
            self._deflate_packet['mid']['reached'] = True
            self._was_above_mid = False
            logger.success(f"★ 泄气中间值 {self.deflate_mid_val} mmHg 真实穿越 @ {t:.2f}s")

        if not self._deflate_packet['target']['reached'] and self._was_above_target and p <= self.deflate_target_val:
            self._deflate_packet['target']['time'] = t
            self._deflate_packet['target']['reached'] = True
            self._was_above_target = False
            logger.success(f"★ 泄气目标值 {self.deflate_target_val} mmHg 真实穿越 @ {t:.2f}s")

            if not self._deflate_result_sent:
                self._deflate_result_sent = True
                self._deflate_packet['state'] = 'DONE'
                logger.info("泄气结果已生成（由目标值到达触发）")
                logger.success("★ 泄气结果已触发（目标到达）")
                self.on_result('deflate', self._deflate_packet.copy())

    # ==================== 查询接口 ====================
    def get_inflate_data(self) -> dict:
        return self._inflate_packet.copy()

    def get_deflate_data(self) -> dict:
        return self._deflate_packet.copy()

    def get_stage(self) -> TestPhase:
        return self.phase

    # ==================== 强制结束 ====================
    def force_complete_inflate(self):
        if self.phase == TestPhase.INFLATING:
            if not self._inflate_result_sent:
                self._inflate_result_sent = True
                self._inflate_packet['state'] = 'DONE'
                self.on_result('inflate', self._inflate_packet.copy())
            self.phase = TestPhase.DONE
            logger.warning("充气强制结束")

    def force_complete_deflate(self):
        if self.phase == TestPhase.DEFLATING:
            if not self._deflate_result_sent:
                self._deflate_result_sent = True
                self._deflate_packet['state'] = 'DONE'
                self.on_result('deflate', self._deflate_packet.copy())
            self.phase = TestPhase.DONE
            logger.warning("泄气强制结束")