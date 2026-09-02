# logger.py
"""数据记录器（CSV） + 全局日志配置 + Qt桥接"""
import csv
import threading
import logging
import os
from datetime import datetime

from PySide6.QtCore import QObject, Signal

from utils import create_directory, format_time

# ============================================================
# 1. 自定义日志级别
# ============================================================
SUCCESS_LEVEL = 25          # 介于 INFO (20) 和 WARNING (30) 之间
CMD_LEVEL    = 26

logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")
logging.addLevelName(CMD_LEVEL, "CMD")

def success(self, msg, *args, **kwargs):
    if self.isEnabledFor(SUCCESS_LEVEL):
        self._log(SUCCESS_LEVEL, msg, args, **kwargs)

def cmd(self, msg, *args, **kwargs):
    if self.isEnabledFor(CMD_LEVEL):
        self._log(CMD_LEVEL, msg, args, **kwargs)

# 动态注入到 Logger 类
logging.Logger.success = success
logging.Logger.cmd = cmd

# ============================================================
# 2. Qt 桥接（将日志发送到 UI）
# ============================================================
class LogBridge(QObject):
    """单例，负责将日志记录通过信号发送到 UI 线程"""
    sig_log = Signal(str, str)   # msg, level_str

    def __init__(self):
        super().__init__()
        self._level_map = {
            logging.DEBUG: 'debug',
            logging.INFO: 'info',
            SUCCESS_LEVEL: 'success',
            logging.WARNING: 'warning',
            logging.ERROR: 'error',
            CMD_LEVEL: 'cmd',
        }

    def emit(self, msg: str, levelno: int):
        level_str = self._level_map.get(levelno, 'info')
        self.sig_log.emit(msg, level_str)

# 全局桥接实例（供 UI 连接）
_bridge = LogBridge()

class QtLogHandler(logging.Handler):
    """自定义 Handler，将日志记录转发到 LogBridge 的信号"""
    def emit(self, record: logging.LogRecord):
        msg = self.format(record)
        _bridge.emit(msg, record.levelno)

# ============================================================
# 3. 全局日志配置函数
# ============================================================
def setup_logging(log_dir: str = "./logs/debug", level: int = logging.DEBUG) -> str:
    """
    配置全局日志系统（供所有模块调用）

    Args:
        log_dir: 日志文件存放目录
        level: 日志级别

    Returns:
        创建的日志文件完整路径
    """
    # 创建日志目录
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 生成带时间戳的文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(log_dir, f"debug_{timestamp}.log")

    # 获取 DVPTest 日志记录器
    logger = logging.getLogger("DVPTest")
    logger.setLevel(level)

    # 清除已有的 handlers（防止重复添加）
    if logger.handlers:
        logger.handlers.clear()

    # 文件 handler
    fh = logging.FileHandler(log_filename, encoding="utf-8")
    fh.setLevel(level)

    # 控制台 handler
    ch = logging.StreamHandler()
    ch.setLevel(level)

    # Qt 桥接 handler
    qt_handler = QtLogHandler()
    qt_handler.setLevel(level)

    # 统一格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    qt_handler.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.addHandler(qt_handler)
    logger.propagate = False

    # 控制台输出提示
    print(f"[日志] 日志文件: {log_filename}")
    return log_filename

# ============================================================
# 4. CSV 数据记录器（原有，未改动）
# ============================================================
class DataLogger:
    def __init__(self, base_dir: str = "./logs/csv"):
        self.base_dir = base_dir
        self.file = None
        self.writer = None
        self.is_logging = False
        self.lock = threading.Lock()
        self.filename = None

    def start(self) -> str:
        with self.lock:
            if self.is_logging:
                return self.filename
            create_directory(self.base_dir)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.filename = os.path.join(self.base_dir, f"pressure_data_{timestamp}.csv")
            try:
                self.file = open(self.filename, 'w', newline='', encoding='utf-8-sig')
            except Exception as e:
                raise RuntimeError(f"无法创建日志文件 {self.filename}: {e}")
            self.writer = csv.writer(self.file)
            self.writer.writerow(['时间(s)', '压力(mmHg)'])
            self.is_logging = True
        return self.filename

    def write(self, t: float, p: float):
        if self.is_logging and self.writer:
            with self.lock:
                self.writer.writerow([format_time(t), f"{p:.2f}"])
                self.file.flush()

    def stop(self):
        with self.lock:
            if self.is_logging:
                self.is_logging = False
                if self.file:
                    try:
                        self.file.close()
                    except Exception:
                        pass
                    self.file = None
                    self.writer = None

    def is_active(self) -> bool:
        return self.is_logging