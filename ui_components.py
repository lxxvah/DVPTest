"""UI 模块：界面组件、窗口状态和应用主题入口。"""
import html
import logging
from collections import deque
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel,
    QComboBox, QLineEdit, QFrame, QGroupBox,
)

from config import Config

logger = logging.getLogger("DVPTest")


class UITheme:
    """所有界面资源；业务配置不应依赖这些内容。"""

    COLORS = {
        "bg_main": "#0d151c", "bg_panel": "#121d26", "bg_chart": "#0b1218",
        "border": "#304553", "fg_text": "#e6edf3", "fg_secondary": "#91a4b2",
        "fg_highlight": "#43d9c5", "pressure_curve": "#43d9c5",
        "rate_curve": "#f6bd60", "inflate_result": "#59d98e",
        "deflate_result": "#ff7b72", "instant_rate": "#f6bd60",
        "log_green": "#59d98e", "log_white": "#e6edf3",
        "log_yellow": "#f6bd60", "log_blue": "#43d9c5", "log_red": "#ff7b72",
    }

    BUTTON_TEXTS = {
        "refresh": ("刷新", "btn_action", False, False),
        "clear": ("清屏", "btn_action", False, False),
        "toggle_plot": ("暂停绘图", "btn_toggle_plot", False, False),
        "toggle_rate": ("速率曲线：开", "btn_action", True, True),
        "connect": ("连接", "btn_connect", False, False),
        "disconnect": ("断开", "btn_disconnect", False, False),
        "start": ("开始", "btn_start", False, False),
        "stop": ("结束", "btn_stop", False, False),
        "save_img": ("保存图片", "btn_action", False, False),
        "save_csv": ("保存CSV", "btn_action", False, False),
        "load_wave": ("加载波形", "btn_action", False, False),
        "cursor": ("光标测量", "btn_action", False, False),
    }

    _BUTTON_BASE = """
        QPushButton {{ background: {background}; color: #ffffff; border: 1px solid {border};
        border-radius: 4px; padding: 5px 12px; font-weight: bold; }}
        QPushButton:hover {{ background: {hover}; }}
        QPushButton:pressed {{ background: {pressed}; }}
        QPushButton:disabled {{ background: #263640; color: #718391; border: 1px solid #304553; }}
    """

    BUTTON_STYLES = {
        "action": _BUTTON_BASE.format(background="#456274", border="#59798b", hover="#587b8e", pressed="#304a59"),
        "connect": _BUTTON_BASE.format(background="#23866f", border="#43d9c5", hover="#2fa68b", pressed="#176352"),
        "disconnect": _BUTTON_BASE.format(background="#9b4c50", border="#ff7b72", hover="#bd5c60", pressed="#77363b"),
        "start": _BUTTON_BASE.format(background="#267e93", border="#43d9c5", hover="#309bb0", pressed="#1b5d70"),
        "stop": _BUTTON_BASE.format(background="#aa7130", border="#f6bd60", hover="#c6873b", pressed="#80511f"),
        "toggle_plot": _BUTTON_BASE.format(background="#286e5c", border="#59d98e", hover="#34866f", pressed="#1c4f42"),
        "rate_on": _BUTTON_BASE.format(background="#a47736", border="#f6bd60", hover="#bd9148", pressed="#795623"),
        "rate_off": _BUTTON_BASE.format(background="#456274", border="#59798b", hover="#587b8e", pressed="#304a59"),
        "lock_active": _BUTTON_BASE.format(background="#286e5c", border="#59d98e", hover="#34866f", pressed="#1c4f42"),
    }

    STYLESHEET = """
        * { margin: 0; padding: 0; }
        QMainWindow, QWidget { background-color: #0d151c; color: #e6edf3; }
        QLabel { color: #91a4b2; }
        QLineEdit, QComboBox { background: #16232d; color: #e6edf3; border: 1px solid #304553;
            border-radius: 4px; padding: 4px 6px; }
        QLineEdit:focus, QComboBox:focus { border: 1px solid #43d9c5; }
        QComboBox QAbstractItemView { background: #16232d; color: #e6edf3; selection-background-color: #1d8f88; }
        QGroupBox { color: #e6edf3; border: 1px solid #304553; border-radius: 5px;
            margin-top: 8px; padding-top: 8px; }
        QGroupBox::title { color: #43d9c5; padding: 0 5px; }
        QTextEdit { background: #0b1218; color: #dbe7ee; border: none; }
        QPushButton#logFilterButton { background: transparent; color: #91a4b2; border: none;
            border-radius: 3px; padding: 3px 7px; font-weight: normal; }
        QPushButton#logFilterButton:hover { color: #e6edf3; background: #1a2b36; }
        QPushButton#logFilterButton:checked { color: #43d9c5; background: #183a3e; }
    """


def apply_theme(app):
    """应用统一的桌面主题；业务模块不需要知道样式表来源。"""
    from PySide6.QtGui import QFont

    app.setStyleSheet(UITheme.STYLESHEET)
    app.setFont(QFont("Microsoft YaHei UI", 10))


class UITestState(IntEnum):
    IDLE = 0
    RUNNING = 1
    FINISHED = 2


@dataclass
class UIState:
    plot_widget: Optional[pg.PlotWidget] = None
    curve_pressure: Optional[pg.PlotDataItem] = None
    curve_rate: Optional[pg.PlotDataItem] = None
    label_status: Optional[QLabel] = None
    label_rate: Optional[QLabel] = None
    label_inflate: Optional[QLabel] = None
    label_deflate: Optional[QLabel] = None
    btn_connect: Optional[QPushButton] = None
    btn_disconnect: Optional[QPushButton] = None
    btn_start: Optional[QPushButton] = None
    btn_stop: Optional[QPushButton] = None
    btn_toggle_rate: Optional[QPushButton] = None
    btn_toggle_plot: Optional[QPushButton] = None
    btn_lock_view: Optional[QPushButton] = None
    combo_port: Optional[QComboBox] = None
    combo_baud: Optional[QComboBox] = None
    inflate_start_edit: Optional[QLineEdit] = None
    inflate_mid_edit: Optional[QLineEdit] = None
    inflate_target_edit: Optional[QLineEdit] = None
    deflate_start_edit: Optional[QLineEdit] = None
    deflate_mid_edit: Optional[QLineEdit] = None
    deflate_target_edit: Optional[QLineEdit] = None
    threshold_edit: Optional[QLineEdit] = None
    test_state: UITestState = UITestState.IDLE
    cursor_enabled: bool = True
    rate_visible: bool = True
    view_locked: bool = False
    btn_pc_mode: Optional[QPushButton] = None
    btn_pressure_test: Optional[QPushButton] = None


class LogWidget(QWidget):
    """带级别筛选的轻量日志面板。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.log_entries = deque(maxlen=Config.MAX_LOG_ENTRIES)
        self.filter_level = "全部"
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        filter_bar = QHBoxLayout()
        filter_bar.setContentsMargins(8, 4, 8, 4)
        filter_bar.setSpacing(4)
        self.filter_btns = []
        for label in ["全部", "info", "success", "warning", "error", "cmd"]:
            btn = QPushButton(label)
            btn.setObjectName("logFilterButton")
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.clicked.connect(lambda checked, level=label: self._on_filter_clicked(level))
            filter_bar.addWidget(btn)
            self.filter_btns.append(btn)
        self.filter_btns[0].setChecked(True)
        filter_bar.addStretch()
        layout.addLayout(filter_bar)
        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)
        layout.addWidget(self.text_log)

    def _on_filter_clicked(self, text: str):
        self.filter_level = text
        self._refresh_display()

    def append_log(self, msg: str, level: str = "info"):
        display_level = "connect" if level == "info" and (
            msg.startswith("已连接到") or msg.startswith("已断开")
        ) else level
        self.log_entries.append((msg, level, display_level))
        if self._should_show(level):
            self._append_one(msg, display_level)

    def _should_show(self, level: str) -> bool:
        return self.filter_level == "全部" or self.filter_level == level

    def _refresh_display(self):
        self.text_log.clear()
        for msg, level, display_level in self.log_entries:
            if self._should_show(level):
                self._append_one(msg, display_level)

    def _append_one(self, msg: str, display_level: str):
        from utils import get_timestamp
        level_labels = {
            "info": "[info]", "success": "[success]", "warning": "[warning]",
            "error": "[error]", "cmd": "[cmd]", "debug": "[debug]",
            "connect": "[连接]",
        }
        colors = {
            "info": "#c9d1d9", "success": "#3fb950", "warning": "#d29922",
            "error": "#f85149", "cmd": "#58a6ff", "debug": "#8b949e",
            "connect": "#c9d1d9",
        }
        label = level_labels.get(display_level, f"[{display_level}]")
        color = colors.get(display_level, "#c9d1d9")
        html_text = (
            f'<span style="color:#8b949e;">[{get_timestamp()}]</span> '
            f'<span style="color:{color};">{label} {html.escape(msg)}</span>'
        )
        self.text_log.append(html_text)


class MainWindowUiMixin:
    """负责创建主窗口控件，不处理串口和测试业务。"""

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        toolbar = self._build_toolbar()
        toolbar.setFixedHeight(Config.UI_TOOLBAR_HEIGHT)
        main_layout.addWidget(toolbar)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        left_panel = self._build_left_panel()
        left_panel.setFixedWidth(Config.UI_LEFT_PANEL_WIDTH)
        body_layout.addWidget(left_panel)
        body_layout.addWidget(self._build_right_panel(), stretch=1)
        main_layout.addWidget(body, stretch=1)

        log_area = self._build_log_area()
        log_area.setFixedHeight(Config.UI_LOG_HEIGHT)
        main_layout.addWidget(log_area)
        status_bar = self._build_status_bar()
        status_bar.setFixedHeight(Config.UI_STATUS_BAR_HEIGHT)
        main_layout.addWidget(status_bar)

    def _build_toolbar(self):
        bar = QFrame()
        bar.setStyleSheet("background: #0d151c; border-bottom: 1px solid #304553;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 2, 10, 2)
        layout.setSpacing(8)

        layout.addWidget(QLabel("串口:"))
        self.state.combo_port = QComboBox()
        self.state.combo_port.setFixedWidth(Config.UI_PORT_WIDTH)
        layout.addWidget(self.state.combo_port)
        text, _, _, _ = UITheme.BUTTON_TEXTS["refresh"]
        refresh = QPushButton(text)
        refresh.setStyleSheet(UITheme.BUTTON_STYLES["action"])
        refresh.clicked.connect(self._refresh_ports)
        layout.addWidget(refresh)

        layout.addWidget(QLabel("波特率:"))
        self.state.combo_baud = QComboBox()
        self.state.combo_baud.addItems(Config.BAUDRATES)
        self.state.combo_baud.setCurrentText(Config.DEFAULT_BAUD)
        self.state.combo_baud.setFixedWidth(Config.UI_BAUD_WIDTH)
        layout.addWidget(self.state.combo_baud)

        text, _, _, _ = UITheme.BUTTON_TEXTS["connect"]
        self.state.btn_connect = QPushButton(text)
        self.state.btn_connect.setStyleSheet(UITheme.BUTTON_STYLES["connect"])
        self.state.btn_connect.clicked.connect(self._connect)
        layout.addWidget(self.state.btn_connect)

        text, _, _, _ = UITheme.BUTTON_TEXTS["disconnect"]
        self.state.btn_disconnect = QPushButton(text)
        self.state.btn_disconnect.setStyleSheet(UITheme.BUTTON_STYLES["disconnect"])
        self.state.btn_disconnect.setEnabled(False)
        self.state.btn_disconnect.clicked.connect(self._disconnect)
        layout.addWidget(self.state.btn_disconnect)

        text, _, _, _ = UITheme.BUTTON_TEXTS["clear"]
        clear = QPushButton(text)
        clear.setStyleSheet(UITheme.BUTTON_STYLES["action"])
        clear.clicked.connect(self._clear_screen)
        layout.addWidget(clear)

        text, _, _, _ = UITheme.BUTTON_TEXTS["toggle_plot"]
        self.state.btn_toggle_plot = QPushButton(text)
        self.state.btn_toggle_plot.setStyleSheet(UITheme.BUTTON_STYLES["toggle_plot"])
        self.state.btn_toggle_plot.clicked.connect(self._toggle_plot_pause)
        layout.addWidget(self.state.btn_toggle_plot)

        layout.addWidget(QLabel("停止阈值:"))
        self.state.threshold_edit = QLineEdit(str(Config.PLOT_STOP_THRESHOLD))
        self.state.threshold_edit.setFixedWidth(Config.UI_THRESHOLD_WIDTH)
        self.state.threshold_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state.threshold_edit.textChanged.connect(self._on_threshold_changed)
        layout.addWidget(self.state.threshold_edit)
        layout.addWidget(QLabel("mmHg"))

        text, _, checkable, checked = UITheme.BUTTON_TEXTS["toggle_rate"]
        self.state.btn_toggle_rate = QPushButton(text)
        self.state.btn_toggle_rate.setStyleSheet(UITheme.BUTTON_STYLES["rate_on"])
        self.state.btn_toggle_rate.setCheckable(checkable)
        self.state.btn_toggle_rate.setChecked(checked)
        self.state.btn_toggle_rate.clicked.connect(self._toggle_rate_curve)
        layout.addWidget(self.state.btn_toggle_rate)

        self.state.btn_lock_view = QPushButton("锁定视图：关")
        self.state.btn_lock_view.setStyleSheet(UITheme.BUTTON_STYLES["action"])
        self.state.btn_lock_view.setCheckable(True)
        self.state.btn_lock_view.clicked.connect(self._toggle_view_lock)
        layout.addWidget(self.state.btn_lock_view)
        layout.addStretch()

        self.state.label_status = QLabel("● 未连接")
        self.state.label_status.setStyleSheet("color: #91a4b2; font-size: 13px;")
        layout.addWidget(self.state.label_status)
        return bar

    def _build_left_panel(self):
        panel = QWidget()
        panel.setStyleSheet("background: #0d151c; border-right: 1px solid #304553;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(18)
        layout.addWidget(self._build_param_group())
        layout.addWidget(self._build_control_group())
        layout.addWidget(self._build_rate_display())
        layout.addStretch()
        return panel

    def _build_param_group(self):
        group = QWidget()
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        inflate = QGroupBox("充气测试")
        inflate_layout = QHBoxLayout(inflate)
        inflate_layout.setContentsMargins(6, 6, 6, 6)
        inflate_layout.setSpacing(4)
        for label, attr, value in zip(("起始", "中间", "目标"),
                                      ("inflate_start_edit", "inflate_mid_edit", "inflate_target_edit"),
                                      Config.INFLATE_DEFAULT):
            self._add_param_input(inflate_layout, label, attr, str(value), "inflate")
        layout.addWidget(inflate)

        deflate = QGroupBox("泄气测试")
        deflate_layout = QHBoxLayout(deflate)
        deflate_layout.setContentsMargins(6, 6, 6, 6)
        deflate_layout.setSpacing(4)
        for label, attr, value in zip(("起始", "中间", "目标"),
                                      ("deflate_start_edit", "deflate_mid_edit", "deflate_target_edit"),
                                      Config.DEFLATE_DEFAULT):
            self._add_param_input(deflate_layout, label, attr, str(value), "deflate")
        layout.addWidget(deflate)
        return group

    def _add_param_input(self, layout, label_text, attr_name, default_text, test_key):
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(2)
        row.addWidget(QLabel(label_text))
        edit = QLineEdit(default_text)
        edit.setFixedWidth(Config.UI_PARAM_WIDTH)
        edit.textChanged.connect(lambda: self._on_param_change(test_key))
        setattr(self.state, attr_name, edit)
        row.addWidget(edit)
        layout.addWidget(widget)

    def _build_control_group(self):
        group = QWidget()
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        simulator = QLabel("无创血压模拟器")
        simulator.setStyleSheet("color: #91a4b2; font-size: 12px; font-weight: bold;")
        layout.addWidget(simulator)
        row = QHBoxLayout()
        self.state.btn_pc_mode = QPushButton("进入PC界面")
        self.state.btn_pc_mode.setStyleSheet(UITheme.BUTTON_STYLES["action"])
        self.state.btn_pc_mode.clicked.connect(self._toggle_pc_mode)
        row.addWidget(self.state.btn_pc_mode)
        self.state.btn_pressure_test = QPushButton("压力表测试")
        self.state.btn_pressure_test.setStyleSheet(UITheme.BUTTON_STYLES["start"])
        self.state.btn_pressure_test.clicked.connect(self._on_pressure_test)
        row.addWidget(self.state.btn_pressure_test)
        row.addStretch()
        layout.addLayout(row)

        board = QLabel("测试板压力传感器")
        board.setStyleSheet("color: #91a4b2; font-size: 12px; font-weight: bold;")
        layout.addWidget(board)
        row = QHBoxLayout()
        text, _, _, _ = UITheme.BUTTON_TEXTS["start"]
        self.state.btn_start = QPushButton(text)
        self.state.btn_start.setStyleSheet(UITheme.BUTTON_STYLES["start"])
        self.state.btn_start.clicked.connect(self._on_start)
        row.addWidget(self.state.btn_start)
        text, _, _, _ = UITheme.BUTTON_TEXTS["stop"]
        self.state.btn_stop = QPushButton(text)
        self.state.btn_stop.setStyleSheet(UITheme.BUTTON_STYLES["stop"])
        self.state.btn_stop.setEnabled(False)
        self.state.btn_stop.clicked.connect(self._on_stop)
        row.addWidget(self.state.btn_stop)
        row.addStretch()
        layout.addLayout(row)

        for names, callbacks in ((("save_img", "save_csv"), (self._save_image, self._save_csv)),
                                 (("load_wave", "cursor"), (self._load_waveform, self._toggle_cursor))):
            row = QHBoxLayout()
            for name, callback in zip(names, callbacks):
                text, _, _, _ = UITheme.BUTTON_TEXTS[name]
                button = QPushButton(text)
                button.setStyleSheet(UITheme.BUTTON_STYLES["action"])
                button.clicked.connect(callback)
                row.addWidget(button)
            row.addStretch()
            layout.addLayout(row)
        return group

    def _build_rate_display(self):
        group = QWidget()
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        frame = QFrame()
        row = QHBoxLayout(frame)
        row.setContentsMargins(6, 2, 6, 2)
        row.addWidget(QLabel("瞬时速率:"))
        self.state.label_rate = QLabel("--")
        self.state.label_rate.setStyleSheet(
            f"color: {UITheme.COLORS['instant_rate']}; font-weight: bold; font-size: 14px; font-family: Consolas;"
        )
        row.addWidget(self.state.label_rate)
        row.addStretch()
        layout.addWidget(frame)
        self.label_pressure = QLabel("--")
        self.label_pressure.setStyleSheet(
            "color: #43d9c5; font-size: 64px; font-weight: bold; font-family: Consolas; padding: 4px 0px;"
        )
        self.label_pressure.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label_pressure)
        return group

    def _build_right_panel(self):
        right = QWidget()
        layout = QVBoxLayout(right)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_plot_area(), stretch=1)
        info = self._build_info_row()
        info.setFixedHeight(Config.UI_INFO_HEIGHT)
        layout.addWidget(info)
        return right

    def _build_plot_area(self):
        plot = pg.PlotWidget()
        plot.setBackground(UITheme.COLORS["bg_chart"])
        plot.showGrid(x=True, y=True, alpha=0.15)
        plot.setLabel("bottom", "时间", units="s", color=UITheme.COLORS["fg_secondary"])
        plot.setLabel("left", "压力", units="mmHg", color=UITheme.COLORS["pressure_curve"])
        plot.setTitle("实时压力曲线", color=UITheme.COLORS["fg_text"], size="14pt")
        plot.getAxis("bottom").setStyle(tickFont=None, tickTextOffset=4)
        left_axis = plot.getAxis("left")
        left_axis.setPen(pg.mkPen(UITheme.COLORS["pressure_curve"]))
        left_axis.setTextPen(pg.mkPen(UITheme.COLORS["pressure_curve"]))
        left_axis.setStyle(tickFont=None, tickTextOffset=4)
        viewbox = plot.getViewBox()
        viewbox.setRange(
            xRange=Config.PLOT_INITIAL_X_RANGE,
            yRange=Config.PLOT_INITIAL_Y_RANGE,
        )
        viewbox.setBackgroundColor(UITheme.COLORS["bg_chart"])
        self.state.curve_pressure = pg.PlotDataItem(
            [], [], pen=pg.mkPen(UITheme.COLORS["pressure_curve"], width=2.5),
            downsample=100, downsampleMethod="peak", autoDownsample=True,
        )
        plot.addItem(self.state.curve_pressure)
        plot.showAxis("right")
        right_axis = plot.getAxis("right")
        right_axis.setLabel("速率", units="mmHg/s", color=UITheme.COLORS["rate_curve"])
        right_axis.setPen(pg.mkPen(UITheme.COLORS["rate_curve"]))
        right_axis.setTextPen(pg.mkPen(UITheme.COLORS["rate_curve"]))
        right_axis.setStyle(tickFont=None, tickTextOffset=4)
        self.state.curve_rate = plot.plot(
            [], [], pen=pg.mkPen(UITheme.COLORS["rate_curve"], width=2.5), yAxis="right"
        )
        right_axis.setRange(*Config.PLOT_INITIAL_RATE_RANGE)
        self.state.plot_widget = plot
        plot.scene().sigMouseClicked.connect(self._on_plot_clicked)
        plot.setCursor(Qt.CrossCursor)
        plot.installEventFilter(self)
        return plot

    def _build_info_row(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(5)
        for title, attr, color in (("充气结果:", "label_inflate", UITheme.COLORS["inflate_result"]),
                                   ("泄气结果:", "label_deflate", UITheme.COLORS["deflate_result"])):
            frame = QFrame()
            row = QHBoxLayout(frame)
            row.setContentsMargins(6, 2, 6, 2)
            row.addWidget(QLabel(title))
            label = QLabel("--")
            label.setStyleSheet(
                f"color: {color}; font-weight: bold; font-size: 14px; font-family: Consolas;"
            )
            setattr(self.state, attr, label)
            row.addWidget(label)
            row.addStretch()
            layout.addWidget(frame)
        return container

    def _build_log_area(self):
        self.log_widget = LogWidget()
        self.log_widget.setStyleSheet("border-top: 1px solid #304553;")
        return self.log_widget

    def _build_status_bar(self):
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.addWidget(QLabel("⚙ Ctrl+滚轮横向缩放  Shift+滚轮纵向缩放  清屏重置时间轴"))
        layout.addStretch()
        return bar
