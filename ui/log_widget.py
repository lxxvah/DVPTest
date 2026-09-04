# ui/log_widget.py
"""日志显示组件 — 带过滤和颜色"""
import html
from collections import deque
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit
from config import Config
from utils import get_timestamp

class LogWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("log_widget")
        self.log_entries = deque(maxlen=Config.MAX_LOG_ENTRIES)
        self.filter_level = "全部"
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 过滤栏
        filter_bar = QHBoxLayout()
        filter_bar.setContentsMargins(4, 2, 4, 2)
        filter_bar.setSpacing(4)
        self.filter_btns = []
        for label in ["全部", "info", "success", "warning", "error", "cmd"]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.clicked.connect(lambda _, l=label: self._on_filter(l))
            filter_bar.addWidget(btn)
            self.filter_btns.append(btn)
        self.filter_btns[0].setChecked(True)
        filter_bar.addStretch()
        layout.addLayout(filter_bar)

        # 文本显示
        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)
        layout.addWidget(self.text_log)

    def _on_filter(self, level):
        self.filter_level = level
        self._refresh()

    def append_log(self, msg: str, level: str = "info"):
        display_level = "connect" if level == "info" and ("已连接" in msg or "已断开" in msg) else level
        self.log_entries.append((msg, level, display_level))
        if self._should_show(level):
            self._append_one(msg, display_level)

    def _should_show(self, level):
        return self.filter_level == "全部" or self.filter_level == level

    def _refresh(self):
        self.text_log.clear()
        for msg, level, display_level in self.log_entries:
            if self._should_show(level):
                self._append_one(msg, display_level)

    def _append_one(self, msg, display_level):
        labels = {'info':'[info]','success':'[success]','warning':'[warning]',
                  'error':'[error]','cmd':'[cmd]','debug':'[debug]','connect':'[连接]'}
        label = labels.get(display_level, f'[{display_level}]')
        colors = {
            'info': Config.COLORS['fg_text'],
            'success': Config.COLORS['log_green'],
            'warning': Config.COLORS['log_yellow'],
            'error': Config.COLORS['log_red'],
            'cmd': Config.COLORS['log_blue'],
            'debug': Config.COLORS['fg_secondary'],
            'connect': Config.COLORS['fg_text'],
        }
        color = colors.get(display_level, Config.COLORS['fg_text'])
        safe_msg = html.escape(msg)
        html_text = (f'<span style="color:{Config.COLORS["fg_secondary"]};">[{get_timestamp()}]</span> '
                     f'<span style="color:{color};">{label} {safe_msg}</span>')
        self.text_log.append(html_text)