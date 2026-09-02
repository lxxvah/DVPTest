# serial_worker.py
import time
import threading
import logging
from typing import Optional
from PySide6.QtCore import QThread, Signal
import serial
from config import Config

logger = logging.getLogger("DVPTest")


class SerialWorker(QThread):
    sig_raw = Signal(str)
    sig_data = Signal(float, float)
    sig_error = Signal(str)

    HEARTBEAT = 0x09
    FRAME_HEADER = 0xAA
    FRAME_LEN = 8

    def __init__(self, port: str, baudrate: int, device_type: str = "unknown"):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.device_type = device_type
        self.mode: Optional[str] = None
        self.ser = None
        self.running = False
        self.start_time = None
        self.write_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._rx_buffer = bytearray()

    def run(self):
        try:
            logger.info(f"正在打开串口 {self.port} @ {self.baudrate}")
            self.ser = serial.Serial(self.port, self.baudrate, timeout=0.5, write_timeout=0.5)
            self.running = True
            self.start_time = time.perf_counter()

            self.mode = self._auto_detect_protocol()
            logger.info(f"协议检测完成: device_type={self.device_type}, mode={self.mode}")
            self.sig_raw.emit(f"[协议选择] device_type={self.device_type}, mode={self.mode}")

            if self.mode == "text":
                logger.info("进入文本模式")
                self._run_text_mode()
            else:
                logger.info("进入二进制模式")
                self._run_binary_mode()

        except Exception as e:
            logger.error(f"run() 异常: {e}")
            self.sig_error.emit(str(e))
        finally:
            self._close_serial()
            logger.info("run() 结束")

    def _auto_detect_protocol(self) -> str:
        if self.device_type in ("simulator", "nibp_simulator"):
            logger.debug("设备类型为 simulator，直接返回 binary")
            return "binary"
        if self.device_type == "test_board":
            logger.debug("设备类型为 test_board，返回 text")
            return "text"

        logger.debug("设备类型 unknown，开始嗅探")
        time.sleep(0.1)
        sniff_data = self._sniff_data()
        if sniff_data:
            logger.debug(f"嗅探到 {len(sniff_data)} 字节: {sniff_data[:32]}")
            if b'cuff=' in sniff_data and b'mmHg' in sniff_data:
                logger.debug("嗅探到文本协议特征")
                return "text"
            if self.FRAME_HEADER in sniff_data or self.HEARTBEAT in sniff_data:
                logger.debug("嗅探到二进制协议特征")
                self._rx_buffer = bytearray(sniff_data)
                return "binary"
            if self._has_binary_control_chars(sniff_data):
                logger.debug("嗅探到二进制控制字符")
                self._rx_buffer = bytearray(sniff_data)
                return "binary"

        logger.debug("嗅探无结果，默认文本")
        return "text"

    def _sniff_data(self) -> bytes:
        sniff_data = b""
        if self.ser and self.ser.is_open:
            end_time = time.time() + Config.DETECT_TIMEOUT
            while time.time() < end_time:
                if self.ser.in_waiting > 0:
                    sniff_data += self.ser.read(self.ser.in_waiting)
                    if b'\n' in sniff_data or len(sniff_data) >= 64:
                        break
                time.sleep(0.01)
        return sniff_data

    def _has_binary_control_chars(self, data: bytes) -> bool:
        return any(0 <= b < 0x20 and b not in (0x09, 0x0A, 0x0D) for b in data)

    def _run_text_mode(self):
        from utils import parse_pressure_from_cuff
        while self.running and self.ser.is_open and not self._stop_event.is_set():
            if self.ser.in_waiting > 0:
                line = self.ser.read_until(b'\n')
                if line:
                    raw = line.decode('utf-8', errors='ignore').strip()
                    pressure = parse_pressure_from_cuff(raw)
                    if pressure is not None:
                        t = time.perf_counter() - self.start_time
                        self._emit_data(t, pressure)
                        self.sig_raw.emit(raw)
            else:
                time.sleep(0.001)

    def _run_binary_mode(self):
        logger.info("二进制模式启动，发送压力表命令")
        self._send_pressure_table_command()

        if self._rx_buffer:
            logger.debug(f"处理残留嗅探数据 {len(self._rx_buffer)} 字节")
            self._process_binary_data(self._rx_buffer)
            self._rx_buffer = bytearray()

        while self.running and self.ser.is_open and not self._stop_event.is_set():
            if self.ser.in_waiting > 0:
                data = self.ser.read(self.ser.in_waiting)
                logger.debug(f"读取到 {len(data)} 字节原始数据")
                self._process_binary_data(data)
            else:
                time.sleep(0.001)

    def _process_binary_data(self, data: bytes):
        logger.debug(f"_process_binary_data 处理 {len(data)} 字节")
        self._rx_buffer.extend(data)
        idx = 0
        while idx < len(self._rx_buffer):
            byte = self._rx_buffer[idx]

            if byte == self.HEARTBEAT:
                logger.debug("检测到心跳，回复")
                self._reply_heartbeat()
                idx += 1
                continue

            if byte == self.FRAME_HEADER:
                if idx + self.FRAME_LEN > len(self._rx_buffer):
                    logger.debug(f"AA 帧不完整，等待更多数据 (需要 {idx+self.FRAME_LEN}, 现有 {len(self._rx_buffer)})")
                    break
                pressure = self._parse_pressure_from_frame(self._rx_buffer, idx)
                t = time.perf_counter() - self.start_time
                logger.debug(f"解析出压力: t={t:.3f}, p={pressure:.1f}")
                self._emit_data(t, pressure)
                self.sig_raw.emit(f"[压力] {pressure:.1f} mmHg")
                idx += self.FRAME_LEN
                continue

            logger.warning(f"未知字节 0x{byte:02X}，跳过")
            idx += 1

        if idx > 0:
            del self._rx_buffer[:idx]

    def _parse_pressure_from_frame(self, buffer: bytearray, idx: int) -> float:
        pressure_raw = (buffer[idx + 1] << 8) | buffer[idx + 2]
        pressure = pressure_raw * 0.01 - 10.0
        return pressure

    def _emit_data(self, t: float, p: float):
        logger.debug(f"发出 sig_data: t={t:.3f}, p={p:.2f}")
        self.sig_data.emit(t, p)

    def _reply_heartbeat(self):
        reply = bytes([self.HEARTBEAT, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        with self.write_lock:
            if self.ser and self.ser.is_open:
                try:
                    self.ser.write(reply)
                    self.ser.flush()
                except Exception:
                    pass

    def _send_pressure_table_command(self):
        cmd = bytes([0x03, 0x02, 0x00])
        with self.write_lock:
            if self.ser and self.ser.is_open:
                try:
                    self.ser.write(cmd)
                    self.ser.flush()
                    logger.debug("已发送压力表命令 0x03 0x02 0x00")
                except Exception as e:
                    logger.error(f"发送压力表命令失败: {e}")

    def send_command(self, cmd: str) -> bool:
        if self.mode == "text":
            return self._send_text_command(cmd)
        else:
            return self._send_binary_command(cmd)

    def _send_text_command(self, cmd: str) -> bool:
        with self.write_lock:
            if self.ser and self.ser.is_open:
                try:
                    self.ser.write((cmd + "\r\n").encode())
                    self.ser.flush()
                    return True
                except Exception:
                    return False
        return False

    def _send_binary_command(self, cmd: str) -> bool:
        with self.write_lock:
            if not self.ser or not self.ser.is_open:
                return False
            try:
                cmd_bytes = bytes.fromhex(cmd.replace(" ", "").upper())
                self.ser.write(cmd_bytes)
                self.ser.flush()
                return True
            except Exception:
                return False

    def send_bytes_command(self, cmd_bytes: bytes) -> bool:
        with self.write_lock:
            if self.ser and self.ser.is_open:
                try:
                    self.ser.write(cmd_bytes)
                    self.ser.flush()
                    return True
                except Exception:
                    return False
        return False

    def _close_serial(self):
        with self.write_lock:
            if self.ser and self.ser.is_open:
                try:
                    self.ser.close()
                except Exception:
                    pass

    def stop_reader(self):
        self.running = False
        self._stop_event.set()

    def reset_time_base(self):
        self.start_time = time.perf_counter()

    def flush_input_buffer(self):
        with self.write_lock:
            if self.ser and self.ser.is_open:
                try:
                    self.ser.reset_input_buffer()
                except Exception:
                    pass