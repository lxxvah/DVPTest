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

    HEARTBEAT = Config.HEARTBEAT_CMD
    FRAME_HEADER = Config.BINARY_FRAME_HEADER
    FRAME_LEN = Config.BINARY_FRAME_LENGTH

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
            logger.data(f"串口配置: {self.port} @ {self.baudrate}")
            self.ser = serial.Serial(
                self.port,
                self.baudrate,
                timeout=Config.SERIAL_READ_TIMEOUT,
                write_timeout=Config.SERIAL_WRITE_TIMEOUT,
            )
            self.running = True
            self.start_time = time.perf_counter()

            self.mode = self._auto_detect_protocol()
            logger.data(f"串口协议: {self.mode}")
            self.sig_raw.emit(f"[协议选择] device_type={self.device_type}, mode={self.mode}")

            if self.mode == "text":
                logger.debug("进入文本模式")
                self._run_text_mode()
            else:
                logger.debug("进入二进制模式")
                self._run_binary_mode()

        except Exception as e:
            logger.error(f"run() 异常: {e}")
            self.sig_error.emit(str(e))
        finally:
            self._close_serial()
            logger.debug("run() 结束")

    def _auto_detect_protocol(self) -> str:
        if self.device_type in ("simulator", "nibp_simulator"):
            logger.debug("设备类型为 simulator，直接返回 binary")
            return "binary"
        if self.device_type == "test_board":
            logger.debug("设备类型为 test_board，返回 text")
            return "text"

        logger.debug("设备类型 unknown，开始嗅探")
        time.sleep(Config.PROTOCOL_DETECT_DELAY)
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
                    if b'\n' in sniff_data or len(sniff_data) >= Config.PROTOCOL_SNIFF_MAX_BYTES:
                        break
                time.sleep(Config.PROTOCOL_SNIFF_INTERVAL)
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
                        logger.data(f"测试板 串口: {raw}")
                        t = time.perf_counter() - self.start_time
                        self._emit_data(t, pressure)
                        self.sig_raw.emit(raw)
            else:
                time.sleep(Config.SERIAL_IDLE_INTERVAL)

    def _run_binary_mode(self):
        logger.debug("二进制模式启动，发送压力表命令")
        self._send_pressure_table_command()

        if self._rx_buffer:
            logger.debug(f"处理残留嗅探数据 {len(self._rx_buffer)} 字节")
            self._process_binary_data(self._rx_buffer)
            self._rx_buffer = bytearray()

        while self.running and self.ser.is_open and not self._stop_event.is_set():
            if self.ser.in_waiting > 0:
                data = self.ser.read(self.ser.in_waiting)
                self._process_binary_data(data)
            else:
                time.sleep(Config.SERIAL_IDLE_INTERVAL)

    def _process_binary_data(self, data: bytes):
        self._rx_buffer.extend(data)
        idx = 0
        while idx < len(self._rx_buffer):
            byte = self._rx_buffer[idx]

            if byte == self.HEARTBEAT:
                self._reply_heartbeat()
                idx += 1
                continue

            if byte == self.FRAME_HEADER:
                if idx + self.FRAME_LEN > len(self._rx_buffer):
                    logger.debug(f"AA 帧不完整，等待更多数据 (需要 {idx+self.FRAME_LEN}, 现有 {len(self._rx_buffer)})")
                    break
                pressure = self._parse_pressure_from_frame(self._rx_buffer, idx)
                t = time.perf_counter() - self.start_time
                logger.data(f"模拟器 压力={pressure:.1f} mmHg")
                self._emit_data(t, pressure)
                idx += self.FRAME_LEN
                continue

            logger.warning(f"未知字节 0x{byte:02X}，跳过")
            idx += 1

        if idx > 0:
            del self._rx_buffer[:idx]

    def _parse_pressure_from_frame(self, buffer: bytearray, idx: int) -> float:
        pressure_raw = (buffer[idx + 1] << 8) | buffer[idx + 2]
        pressure = pressure_raw * Config.PRESSURE_SCALE + Config.PRESSURE_OFFSET
        return pressure

    def _emit_data(self, t: float, p: float):
        self.sig_data.emit(t, p)

    def _reply_heartbeat(self):
        reply = bytes([self.HEARTBEAT] + [0x00] * (Config.HEARTBEAT_REPLY_LENGTH - 1))
        with self.write_lock:
            if self.ser and self.ser.is_open:
                try:
                    self.ser.write(reply)
                    self.ser.flush()
                except Exception:
                    pass

    def _send_pressure_table_command(self):
        cmd = bytes(Config.PRESSURE_TABLE_COMMAND)
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