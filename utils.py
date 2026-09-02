# utils.py
"""通用工具函数"""
import re
import os
import math
from datetime import datetime
from typing import Optional

from config import Config

def get_timestamp() -> str:
    return datetime.now().strftime('%H:%M:%S')

def format_time(t: float) -> str:
    return f"{t:.3f}"

def create_directory(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path)

_DATA_PATTERN = re.compile(Config.DATA_PATTERN)

def parse_pressure_from_cuff(raw: str) -> Optional[float]:
    match = _DATA_PATTERN.match(raw.strip())
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None

def safe_rate_format(rate: float) -> str:
    if math.isinf(rate) or math.isnan(rate):
        return "--"
    if rate > Config.MAX_RATE_LIMIT:
        return f"{Config.MAX_RATE_LIMIT:.1f}"
    return f"{rate:.2f}"