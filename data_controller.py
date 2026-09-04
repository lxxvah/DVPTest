# data_controller.py
"""
第二层：数据中枢
职责：接收 (t, p)，存储数据、计算速率、驱动状态机、触发绘图
输入：sig_data(t, p)
输出：(t, p, signed_rate, acceleration) → test_manager.process_data()
      sig_plot.emit(x_data, y_data) → UI 波形
      sig_result_text.emit(result) → UI 结果（格式化后）
"""
import time
import threading
import math
import os
import logging
from typing import List, Tuple, Optional
from PySide6.QtCore import QObject, Signal

from config import Config
from logger import DataLogger
from serial_worker import SerialWorker
from result_calculator import ResultCalculator
from test_managers import TestManager
from result_formatter import ResultFormatter

logger = logging.getLogger("DVPTest")


class DataController(QObject):
    # [LOG] 删除了 sig_log 信号
    sig_plot = Signal(list, list)
    sig_result_text = Signal(dict)   # 发送格式化结果：{'key': key, 'text': text}
    sig_raw = Signal(str)
    sig_rate = Signal(float)

    def __init__(self):
        super().__init__()
        # ---- 串口 ----
        self.worker: Optional[SerialWorker] = None
        self.is_connected = False
        self.device_type = "test_board"
        self.is_pc_mode = False

        # ---- 数据存储 ----
        self.x_data: List[float] = []
        self.y_data: List[float] = []
        self.display_y: List[float] = []
        self.lock = threading.RLock()
        self._max_points = Config.MAX_DATA_POINTS

        # ---- 速率 ----
        self.signed_rate = 0.0
        self.current_rate = 0.0
        self.acceleration = 0.0

        # ---- 绘图控制 ----
        self.last_plot_time = 0.0
        self.plot_interval_ms = Config.PLOT_INTERVAL_MS
        self.plot_paused = False

        # ---- 日志 ----
        self.logger = DataLogger()

        # ---- 状态机 ----  [LOG] 移除 on_log 参数
        self.test_manager = TestManager(self._on_test_result)

        # ---- 时间基准 ----
        self.base_time = time.perf_counter()

        # ---- ★ 新增：运动学计算历史状态 ----
        self._prev_t = None
        self._prev_p = None
        self._prev_v = None

    # [LOG] 删除 _log 方法，所有调用替换为 logger.xxx

    # ---------- 设备识别 ----------
    def _identify_device(self, port: str) -> str:
        import serial.tools.list_ports
        try:
            for info in serial.tools.list_ports.comports():
                if info.device == port:
                    if info.vid == Config.SIMULATOR_VID and info.pid == Config.SIMULATOR_PID:
                        return "simulator"
            return "unknown"
        except Exception:
            return "unknown"

    # ---------- 连接管理 ----------
    def connect_serial(self, port: str, baudrate: int) -> bool:
        if self.is_connected:
            logger.info("已经连接，请先断开")
            return False

        self.device_type = self._identify_device(port)
        logger.data(f"串口设备: {port}, 类型: {self.device_type}")

        try:
            self.worker = SerialWorker(port, baudrate, device_type=self.device_type)
            self.worker.sig_raw.connect(self.sig_raw)
            self.worker.sig_data.connect(self._on_data_received)
            self.worker.sig_error.connect(lambda e: logger.error(f"串口错误: {e}"))
            self.worker.start()

            self.is_connected = True
            self.is_pc_mode = False
            with self.lock:
                self.base_time = time.perf_counter()
                self.last_plot_time = 0.0

            logger.success(f"已连接到串口 {port} @ {baudrate} bps")
            return True

        except Exception as e:
            logger.error(f"连接串口失败: {e}")
            return False

    def disconnect_serial(self):
        if self.worker:
            self.worker.stop_reader()
            if not self.worker.wait(Config.AUTO_CONNECT_INTERVAL_MS):
                logger.warning("串口线程未能正常结束，强制终止")
                self.worker.terminate()
                self.worker.wait()
            self.worker = None

        self.is_connected = False
        self.is_pc_mode = False
        self.reset_all()
        logger.success("已断开串口")

    # ---------- ★ 智能断开 ----------
    def smart_disconnect(self, is_running: bool = False) -> bool:
        if not self.is_connected:
            return True

        try:
            if self.device_type == "simulator":
                if self.is_pc_mode:
                    logger.info("退出程序：退出PC界面...")
                    if not self.exit_pc_mode():
                        logger.warning("退出PC界面失败，强制断开")
                    else:
                        time.sleep(Config.DISCONNECT_DELAY)
                else:
                    logger.info("退出程序：未处于PC模式，直接断开")
            else:
                if is_running:
                    logger.info("退出程序：结束测试...")
                    if not self.send_command("AT#AH"):
                        logger.warning("发送结束命令失败，强制断开")
                    else:
                        time.sleep(Config.DISCONNECT_DELAY)
                else:
                    logger.info("退出程序：测试未运行，直接断开")
        finally:
            self.disconnect_serial()
        return True

    # ---------- 绘图控制 ----------
    def toggle_plot_pause(self):
        with self.lock:
            self.plot_paused = not self.plot_paused
            if not self.plot_paused:
                self.last_plot_time = 0.0
                x_copy = self.x_data.copy()
                y_copy = self.display_y.copy()
                self.sig_plot.emit(x_copy, y_copy)
            logger.info(f"绘图已{'暂停' if self.plot_paused else '恢复'}")

    def reset_all(self):
        with self.lock:
            self.x_data.clear()
            self.y_data.clear()
            self.display_y.clear()
            self.test_manager.reset()
            self.plot_paused = False
            if self.worker:
                self.worker.reset_time_base()
                self.worker.flush_input_buffer()
            self.base_time = time.perf_counter()
            self.last_plot_time = 0.0

            self._prev_t = None
            self._prev_p = None
            self._prev_v = None
            self.acceleration = 0.0

        logger.info("数据已重置，绘图恢复")

    # ---------- ★ 核心：数据接收 ----------
    def _on_data_received(self, t_from_worker: float, p: float):
        try:
            t = t_from_worker
            
            # ============================================================
            # 阶段 1：锁内（仅保护共享数据的最小操作）
            # ============================================================
            with self.lock:
                # 1. 运动学计算（使用传入数据）
                curr_t, curr_p, v, a = ResultCalculator.compute_kinematics(
                    curr_t=t,
                    curr_p=p,
                    prev_t=self._prev_t,
                    prev_p=self._prev_p,
                    prev_v=self._prev_v
                )

                # 2. 更新历史状态（必须保护）
                self._prev_t = curr_t
                self._prev_p = curr_p
                self._prev_v = v

                # 3. 更新速率（必须保护）
                self.signed_rate = v
                self.acceleration = a
                self.current_rate = abs(v)

                # 4. 追加数据到列表（必须保护）
                self.x_data.append(curr_t)
                self.y_data.append(curr_p)
                self.display_y.append(curr_p)
                if len(self.x_data) > self._max_points:
                    self.x_data = self.x_data[-self._max_points:]
                    self.y_data = self.y_data[-self._max_points:]
                    self.display_y = self.display_y[-self._max_points:]

                # 5. 准备绘图触发数据（在锁内取引用，锁外复制）
                current_time_ms = time.perf_counter() * 1000
                if not self.plot_paused and (current_time_ms - self.last_plot_time) >= self.plot_interval_ms:
                    self.last_plot_time = current_time_ms
                    should_emit = True
                    # ★ 在锁内获取列表引用（复制操作放到锁外）
                    x_ref = self.x_data
                    y_ref = self.display_y
                else:
                    should_emit = False
                    x_ref = None
                    y_ref = None

            # ============================================================
            # 阶段 2：锁外（耗时/非共享操作）
            # ============================================================

            # ★ 移出：发射速率信号（不需要锁保护）
            self.sig_rate.emit(min(self.current_rate, Config.MAX_RATE_LIMIT))

            # ★ 移出：文件 I/O（DataLogger 有自己的内部锁）
            if self.logger.is_active():
                self.logger.write(curr_t, curr_p)

            # ★ 移出：状态机调用（不碰 x_data/y_data）
            self.test_manager.process_data(curr_t, curr_p, v, a)

            # ★ 移出：绘图触发（在锁内只取了引用，锁外执行复制）
            if should_emit:
                x_copy = x_ref.copy() if x_ref is not None else []
                y_copy = y_ref.copy() if y_ref is not None else []
                self.sig_plot.emit(x_copy, y_copy)

            # ★ 移出：自动暂停检测（不碰 x_data/y_data）
            if not self.plot_paused:
                deflate_data = self.test_manager.get_deflate_data()
                target = deflate_data.get('target', {})
                target_time = target.get('time')
                if target_time is not None and curr_p <= Config.PLOT_STOP_THRESHOLD:
                    self.plot_paused = True
                    logger.info(f"泄气目标已到达，且压力达到 {Config.PLOT_STOP_THRESHOLD} mmHg，暂停绘图更新")

        except Exception as e:
            logger.error(f"数据处理错误: {type(e).__name__}: {e}", exc_info=True)

    def _check_plot_trigger(self):
        current_time = time.perf_counter() * 1000
        if not self.plot_paused and (current_time - self.last_plot_time) >= self.plot_interval_ms:
            self.last_plot_time = current_time
            return True, self.x_data.copy(), self.display_y.copy()
        return False, [], []

    # ---------- 结果回调 ----------
    def _on_test_result(self, key: str, packet: dict):
        result = ResultFormatter.format_result(key, packet)
        self.sig_result_text.emit(result)

    # ---------- 参数更新 ----------
    def update_inflate_params(self, start: float, mid: float, target: float) -> bool:
        return self.test_manager.update_inflate_params(start, mid, target)

    def update_deflate_params(self, start: float, mid: float, target: float) -> bool:
        return self.test_manager.update_deflate_params(start, mid, target)

    def update_test_params(self, start: float, mid: float, target: float) -> bool:
        return self.update_inflate_params(start, mid, target)

    # ---------- 日志控制 ----------
    def start_logging(self) -> str:
        try:
            filename = self.logger.start()
            logger.success(f"开始记录数据，文件: {filename}")
            return filename
        except Exception as e:
            logger.error(f"启动日志失败: {e}")
            return ""

    def stop_logging(self):
        self.logger.stop()
        logger.info("停止记录数据")

    def is_logging(self) -> bool:
        return self.logger.is_active()

    # ---------- CSV 操作 ----------
    def save_data_to_csv(self, filename: str):
        try:
            with self.lock:
                if not self.x_data:
                    raise ValueError("没有数据可保存")
                import csv
                with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(['时间(s)', '压力(mmHg)'])
                    from utils import format_time
                    for t, p in zip(self.x_data, self.y_data):
                        writer.writerow([format_time(t), f"{p:.2f}"])
            logger.success(f"数据已保存至 {filename}")
        except Exception as e:
            logger.error(f"保存CSV失败: {e}")
            raise

    def load_data_from_csv(self, filename: str):
        try:
            import csv
            x, y = [], []
            with open(filename, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 2:
                        try:
                            x.append(float(row[0]))
                            y.append(float(row[1]))
                        except ValueError:
                            continue
            if not x:
                raise ValueError("CSV文件无有效数据")
            pairs = sorted(zip(x, y), key=lambda t: t[0])
            x, y = zip(*pairs)
            x, y = list(x), list(y)

            with self.lock:
                self.x_data = x
                self.y_data = y
                self.display_y = y.copy()
                self.test_manager.reset()
                self.plot_paused = False
                self.last_plot_time = 0.0
            self.sig_plot.emit(self.x_data.copy(), self.display_y.copy())
            logger.success(f"已加载波形: {os.path.basename(filename)}")
            self._replay_data_for_results() # ★ 新增：加载后自动分析生成结果
            return x, y
        except Exception as e:
            raise ValueError(f"加载失败: {e}")

    # ---------- 命令发送 ----------
    def send_command(self, cmd: str) -> bool:
        if self.worker:
            try:
                return self.worker.send_command(cmd)
            except Exception as e:
                logger.error(f"发送失败: {e}")
                return False
        return False

    def send_bytes_command(self, cmd_bytes: bytes) -> bool:
        if self.worker:
            try:
                return self.worker.send_bytes_command(cmd_bytes)
            except Exception as e:
                logger.error(f"发送二进制命令失败: {e}")
                return False
        return False

    # ---------- PC 模式 ----------
    def enter_pc_mode(self) -> bool:
        if not self.is_connected:
            logger.warning("未连接串口")
            return False
        cmd = bytes(Config.BINARY_COMMANDS["enter_pc"])
        if self.send_bytes_command(cmd):
            self.is_pc_mode = True
            logger.success("已进入PC界面")
            return True
        return False

    def exit_pc_mode(self) -> bool:
        if not self.is_connected:
            logger.warning("未连接串口")
            return False
        cmd = bytes(Config.BINARY_COMMANDS["exit_pc"])
        if self.send_bytes_command(cmd):
            self.is_pc_mode = False
            logger.info("已退出PC界面")
            return True
        return False

        # ==================== 离线分析：重放数据生成结果 ====================
    def _replay_data_for_results(self):
        """
        重放已加载的数据，驱动状态机生成充气和泄气结果
        此方法不触发任何 UI 绘图/速率信号，仅用于离线分析
        """
        with self.lock:
            if len(self.x_data) < 2:
                return
            x_copy = self.x_data.copy()
            y_copy = self.y_data.copy()

        # 重置状态机（从零开始分析）
        self.test_manager.reset()

        # 运动学计算的局部历史状态
        prev_t = None
        prev_p = None
        prev_v = None

        for t, p in zip(x_copy, y_copy):
            curr_t, curr_p, v, a = ResultCalculator.compute_kinematics(
                curr_t=t,
                curr_p=p,
                prev_t=prev_t,
                prev_p=prev_p,
                prev_v=prev_v
            )
            prev_t, prev_p, prev_v = curr_t, curr_p, v
            self.test_manager.process_data(curr_t, curr_p, v, a)

        # 提取并发送结果
        inflate_packet = self.test_manager.get_inflate_data()
        deflate_packet = self.test_manager.get_deflate_data()

        if inflate_packet.get('state') == 'DONE':
            self._on_test_result('inflate', inflate_packet)
        if deflate_packet.get('state') == 'DONE':
            self._on_test_result('deflate', deflate_packet)
            
    def get_data(self):
        with self.lock:
            return self.x_data.copy(), self.display_y.copy()