# ui_main.py
"""主窗口及UI组件（集成日志，统一写入 debug.log）"""
import sys
import os
import math
import logging

from PySide6.QtCore import (
    QObject, Signal, Slot, QThread, Qt, QRectF, QEvent, QTimer, QSettings,
    QSignalBlocker
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QLineEdit, QTextEdit,
    QFrame, QFileDialog, QMessageBox, QGroupBox, QSizePolicy
)
from PySide6.QtGui import QFont, QPainter, QPixmap, QWheelEvent

import pyqtgraph as pg
import numpy as np
import serial.tools.list_ports

from config import Config
from data_controller import DataController
from result_calculator import ResultCalculator
from test_managers import TestPhase
from logger import _bridge   # 导入全局桥接
from ui_components import LogWidget, UIState, UITestState, UITheme, MainWindowUiMixin

# ---------- 日志记录器 ----------
logger = logging.getLogger("DVPTest")

# ---------- 主窗口 ----------
class MainWindow(QMainWindow, MainWindowUiMixin):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("泄气充气压力性能测试 作者：得鹿梦鱼  「莫道桑榆晚，为霞尚满天」")
        self.setMinimumSize(1200, 720)

        self.state = UIState()
        self.data_ctrl = DataController()

        # ★ 先构建 UI，创建 log_widget
        self._build_ui()

        # ★ 日志连接：改为连接全局桥接（此时 log_widget 已存在）
        _bridge.sig_log.connect(self.log_widget.append_log)

        self.data_ctrl.sig_plot.connect(self._on_plot_update)
        self.data_ctrl.sig_result_text.connect(self._on_result_text)
        self.data_ctrl.sig_rate.connect(self._on_rate_update)

        self._refresh_ports()
        self._load_serial_settings()
        self._load_test_settings()
        self._update_buttons()

        # ★ 光标系统（两组独立测量）
        self.cursor_items = []
        self.cursor_groups = {
            'group1': {'indices': [0, 1], 'colors': ['#3fb950', '#f85149'], 'labels': ['C1', 'C2']},
            'group2': {'indices': [2, 3], 'colors': ['#a371f7', '#3fb9b9'], 'labels': ['B1', 'B2']}
        }
        self.group1_measure_item = None
        self.group2_measure_item = None
        self.measure_text_item = None

        if self.state.plot_widget is not None:
            self.state.plot_widget.installEventFilter(self)

        # 热插拔自动连接定时器
        self._auto_connect_timer = QTimer(self)
        self._auto_connect_timer.timeout.connect(self._auto_connect_timer_cb)
        self._auto_connect_timer.start(Config.AUTO_CONNECT_INTERVAL_MS)
        self._auto_connect_enabled = True
        self.ensurePolished()
        logger.debug("[UI] MainWindow 初始化完成")

    # ---------- 自动连接定时器回调 ----------
    def _auto_connect_timer_cb(self):
        if not self._auto_connect_enabled:
            return
        if self.data_ctrl.is_connected:
            return
        import serial.tools.list_ports
        target_vid = Config.SIMULATOR_VID
        target_pid = Config.SIMULATOR_PID
        for port in serial.tools.list_ports.comports():
            if port.vid == target_vid and port.pid == target_pid:
                self.state.combo_port.setCurrentText(port.device)
                logger.info(f"检测到无创模拟器/测试板 ({port.device})，自动连接中...")
                self._connect()
                return

    # ---------- UI 构建 ----------
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

        right_panel = self._build_right_panel()
        body_layout.addWidget(right_panel, stretch=1)

        main_layout.addWidget(body, stretch=1)

        log_area = self._build_log_area()
        log_area.setFixedHeight(Config.UI_LOG_HEIGHT)
        main_layout.addWidget(log_area)

        status_bar = self._build_status_bar()
        status_bar.setFixedHeight(Config.UI_STATUS_BAR_HEIGHT)
        main_layout.addWidget(status_bar)

    def _build_toolbar(self):
        bar = QFrame()
        bar.setStyleSheet(f"background-color: #0d1117; border-bottom: 1px solid #21262d;")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 2, 10, 2)
        lay.setSpacing(8)

        lay.addWidget(QLabel("串口:"))
        self.state.combo_port = QComboBox()
        self.state.combo_port.setFixedWidth(Config.UI_PORT_WIDTH)
        lay.addWidget(self.state.combo_port)

        text, obj_name, _, _ = UITheme.BUTTON_TEXTS["refresh"]
        btn_refresh = QPushButton(text)
        btn_refresh.setStyleSheet(UITheme.BUTTON_STYLES["action"])
        btn_refresh.clicked.connect(self._refresh_ports)
        lay.addWidget(btn_refresh)

        lay.addWidget(QLabel("波特率:"))
        self.state.combo_baud = QComboBox()
        self.state.combo_baud.addItems(Config.BAUDRATES)
        self.state.combo_baud.setCurrentText(Config.DEFAULT_BAUD)
        self.state.combo_baud.setFixedWidth(Config.UI_BAUD_WIDTH)
        lay.addWidget(self.state.combo_baud)

        text, obj_name, _, _ = UITheme.BUTTON_TEXTS["connect"]
        self.state.btn_connect = QPushButton(text)
        self.state.btn_connect.setStyleSheet(UITheme.BUTTON_STYLES["connect"])
        self.state.btn_connect.clicked.connect(self._connect)
        lay.addWidget(self.state.btn_connect)

        text, obj_name, _, _ = UITheme.BUTTON_TEXTS["disconnect"]
        self.state.btn_disconnect = QPushButton(text)
        self.state.btn_disconnect.setStyleSheet(UITheme.BUTTON_STYLES["disconnect"])
        self.state.btn_disconnect.setEnabled(False)
        self.state.btn_disconnect.clicked.connect(self._disconnect)
        lay.addWidget(self.state.btn_disconnect)

        text, obj_name, _, _ = UITheme.BUTTON_TEXTS["clear"]
        clear_btn = QPushButton(text)
        clear_btn.setStyleSheet(UITheme.BUTTON_STYLES["action"])
        clear_btn.clicked.connect(self._clear_screen)
        lay.addWidget(clear_btn)

        text, obj_name, _, _ = UITheme.BUTTON_TEXTS["toggle_plot"]
        self.state.btn_toggle_plot = QPushButton(text)
        self.state.btn_toggle_plot.setStyleSheet(UITheme.BUTTON_STYLES["toggle_plot"])
        self.state.btn_toggle_plot.clicked.connect(self._toggle_plot_pause)
        lay.addWidget(self.state.btn_toggle_plot)

        lay.addWidget(QLabel("停止阈值:"))
        self.state.threshold_edit = QLineEdit(str(Config.PLOT_STOP_THRESHOLD))
        self.state.threshold_edit.setFixedWidth(Config.UI_THRESHOLD_WIDTH)
        self.state.threshold_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state.threshold_edit.textChanged.connect(self._on_threshold_changed)
        lay.addWidget(self.state.threshold_edit)
        lay.addWidget(QLabel("mmHg"))

        text, obj_name, checkable, checked = UITheme.BUTTON_TEXTS["toggle_rate"]
        self.state.btn_toggle_rate = QPushButton(text)
        if checked:
            self.state.btn_toggle_rate.setStyleSheet(UITheme.BUTTON_STYLES["rate_on"])
        else:
            self.state.btn_toggle_rate.setStyleSheet(UITheme.BUTTON_STYLES["rate_off"])
        self.state.btn_toggle_rate.setCheckable(checkable)
        self.state.btn_toggle_rate.setChecked(checked)
        self.state.btn_toggle_rate.clicked.connect(self._toggle_rate_curve)
        lay.addWidget(self.state.btn_toggle_rate)

        self.state.btn_lock_view = QPushButton("锁定视图：关")
        self.state.btn_lock_view.setStyleSheet(UITheme.BUTTON_STYLES["action"])
        self.state.btn_lock_view.setCheckable(True)
        self.state.btn_lock_view.setChecked(False)
        self.state.btn_lock_view.clicked.connect(self._toggle_view_lock)
        lay.addWidget(self.state.btn_lock_view)

        lay.addStretch()
        self.state.label_status = QLabel("● 未连接")
        self.state.label_status.setStyleSheet("color: #8b949e; font-size: 13px;")
        lay.addWidget(self.state.label_status)
        return bar

    def _on_threshold_changed(self, text: str):
        try:
            val = float(text)
            if val >= 0:
                Config.PLOT_STOP_THRESHOLD = val
                logger.info(f"停止绘图阈值已更新为 {val} mmHg")
        except ValueError:
            pass

    def _toggle_plot_pause(self):
        self.data_ctrl.toggle_plot_pause()
        self._update_plot_button_state()

    def _update_plot_button_state(self):
        if self.state.btn_toggle_plot:
            if self.data_ctrl.plot_paused:
                self.state.btn_toggle_plot.setText("恢复绘图")
            else:
                self.state.btn_toggle_plot.setText("暂停绘图")

    def _toggle_rate_curve(self):
        self.state.rate_visible = not self.state.rate_visible
        if self.state.rate_visible:
            self.state.btn_toggle_rate.setText("速率曲线：开")
            self.state.btn_toggle_rate.setStyleSheet(UITheme.BUTTON_STYLES["rate_on"])
        else:
            self.state.btn_toggle_rate.setText("速率曲线：关")
            self.state.btn_toggle_rate.setStyleSheet(UITheme.BUTTON_STYLES["rate_off"])
        if self.state.curve_rate is not None:
            self.state.curve_rate.setVisible(self.state.rate_visible)

    def _toggle_view_lock(self):
        self.state.view_locked = not self.state.view_locked
        if self.state.view_locked:
            self.state.btn_lock_view.setText("锁定视图：开")
            self.state.btn_lock_view.setStyleSheet(UITheme.BUTTON_STYLES["lock_active"])
            self.state.btn_lock_view.style().unpolish(self.state.btn_lock_view)
            self.state.btn_lock_view.style().polish(self.state.btn_lock_view)
            logger.info("视图已锁定，不再自动适配缩放")
        else:
            self.state.btn_lock_view.setText("锁定视图：关")
            self.state.btn_lock_view.setStyleSheet(UITheme.BUTTON_STYLES["action"])
            self.state.btn_lock_view.style().unpolish(self.state.btn_lock_view)
            self.state.btn_lock_view.style().polish(self.state.btn_lock_view)
            x, y = self.data_ctrl.get_data()
            if x:
                self._refresh_plot(x, y)
            logger.info("视图已解锁，恢复自动适配")

    def _build_left_panel(self):
        panel = QWidget()
        panel.setStyleSheet("background-color: #0d1117; border-right: 1px solid #21262d;")
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
        param_layout = QVBoxLayout(group)
        param_layout.setContentsMargins(0, 0, 0, 0)
        param_layout.setSpacing(8)

        grp_inf = QGroupBox("充气测试")
        grp_inf.setFlat(True)
        g_lay = QHBoxLayout(grp_inf)
        g_lay.setSpacing(4)
        g_lay.setContentsMargins(6, 6, 6, 6)
        self._add_param_input(g_lay, "起始", "inflate_start_edit", str(Config.INFLATE_DEFAULT[0]), "inflate")
        self._add_param_input(g_lay, "中间", "inflate_mid_edit", str(Config.INFLATE_DEFAULT[1]), "inflate")
        self._add_param_input(g_lay, "目标", "inflate_target_edit", str(Config.INFLATE_DEFAULT[2]), "inflate")
        g_lay.addStretch()
        param_layout.addWidget(grp_inf)

        grp_def = QGroupBox("泄气测试")
        grp_def.setFlat(True)
        g_lay2 = QHBoxLayout(grp_def)
        g_lay2.setSpacing(4)
        g_lay2.setContentsMargins(6, 6, 6, 6)
        self._add_param_input(g_lay2, "起始", "deflate_start_edit", str(Config.DEFLATE_DEFAULT[0]), "deflate")
        self._add_param_input(g_lay2, "中间", "deflate_mid_edit", str(Config.DEFLATE_DEFAULT[1]), "deflate")
        self._add_param_input(g_lay2, "目标", "deflate_target_edit", str(Config.DEFLATE_DEFAULT[2]), "deflate")
        g_lay2.addStretch()
        param_layout.addWidget(grp_def)

        return group

    def _add_param_input(self, layout, label_text, attr_name, default_text, test_key):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(2)
        h.addWidget(QLabel(label_text))
        edit = QLineEdit(default_text)
        edit.setFixedWidth(Config.UI_PARAM_WIDTH)
        edit.textChanged.connect(lambda: self._on_param_change(test_key))
        setattr(self.state, attr_name, edit)
        h.addWidget(edit)
        layout.addWidget(w)

    def _build_control_group(self):
        group = QWidget()
        ctrl_layout = QVBoxLayout(group)
        ctrl_layout.setContentsMargins(0, 0, 0, 0)
        ctrl_layout.setSpacing(10)

        lbl_simulator = QLabel("无创血压模拟器")
        lbl_simulator.setStyleSheet("color: #8b949e; font-size: 12px; font-weight: bold;")
        ctrl_layout.addWidget(lbl_simulator)

        row_pc = QHBoxLayout()
        row_pc.setSpacing(6)
        self.state.btn_pc_mode = QPushButton("进入PC界面")
        self.state.btn_pc_mode.setStyleSheet(UITheme.BUTTON_STYLES["action"])
        self.state.btn_pc_mode.clicked.connect(self._toggle_pc_mode)
        row_pc.addWidget(self.state.btn_pc_mode)

        self.state.btn_pressure_test = QPushButton("压力表测试")
        self.state.btn_pressure_test.setStyleSheet(UITheme.BUTTON_STYLES["start"])
        self.state.btn_pressure_test.clicked.connect(self._on_pressure_test)
        row_pc.addWidget(self.state.btn_pressure_test)
        row_pc.addStretch()
        ctrl_layout.addLayout(row_pc)

        lbl_board = QLabel("测试板压力传感器")
        lbl_board.setStyleSheet("color: #8b949e; font-size: 12px; font-weight: bold;")
        ctrl_layout.addWidget(lbl_board)

        row_start = QHBoxLayout()
        row_start.setSpacing(6)
        text, obj_name, _, _ = UITheme.BUTTON_TEXTS["start"]
        self.state.btn_start = QPushButton(text)
        self.state.btn_start.setStyleSheet(UITheme.BUTTON_STYLES["start"])
        self.state.btn_start.clicked.connect(self._on_start)
        row_start.addWidget(self.state.btn_start)

        text, obj_name, _, _ = UITheme.BUTTON_TEXTS["stop"]
        self.state.btn_stop = QPushButton(text)
        self.state.btn_stop.setStyleSheet(UITheme.BUTTON_STYLES["stop"])
        self.state.btn_stop.setEnabled(False)
        self.state.btn_stop.clicked.connect(self._on_stop)
        row_start.addWidget(self.state.btn_stop)
        row_start.addStretch()
        ctrl_layout.addLayout(row_start)

        row_save = QHBoxLayout()
        row_save.setSpacing(6)
        text, obj_name, _, _ = UITheme.BUTTON_TEXTS["save_img"]
        btn_save_img = QPushButton(text)
        btn_save_img.setStyleSheet(UITheme.BUTTON_STYLES["action"])
        btn_save_img.clicked.connect(self._save_image)
        row_save.addWidget(btn_save_img)

        text, obj_name, _, _ = UITheme.BUTTON_TEXTS["save_csv"]
        btn_save_csv = QPushButton(text)
        btn_save_csv.setStyleSheet(UITheme.BUTTON_STYLES["action"])
        btn_save_csv.clicked.connect(self._save_csv)
        row_save.addWidget(btn_save_csv)
        row_save.addStretch()
        ctrl_layout.addLayout(row_save)

        row_load = QHBoxLayout()
        row_load.setSpacing(6)
        text, obj_name, _, _ = UITheme.BUTTON_TEXTS["load_wave"]
        btn_load = QPushButton(text)
        btn_load.setStyleSheet(UITheme.BUTTON_STYLES["action"])
        btn_load.clicked.connect(self._load_waveform)
        row_load.addWidget(btn_load)

        text, obj_name, _, _ = UITheme.BUTTON_TEXTS["cursor"]
        btn_cursor = QPushButton(text)
        btn_cursor.setStyleSheet(UITheme.BUTTON_STYLES["action"])
        btn_cursor.clicked.connect(self._toggle_cursor)
        row_load.addWidget(btn_cursor)
        row_load.addStretch()
        ctrl_layout.addLayout(row_load)

        return group

    def _build_rate_display(self):
        group = QWidget()
        rate_layout = QVBoxLayout(group)
        rate_layout.setContentsMargins(0, 0, 0, 0)
        rate_layout.setSpacing(4)

        frame_rate = QFrame()
        frame_rate.setStyleSheet("background-color: #0d1117; border: none;")
        h_rate = QHBoxLayout(frame_rate)
        h_rate.setContentsMargins(6, 2, 6, 2)
        lbl_rate = QLabel("瞬时速率:")
        lbl_rate.setStyleSheet("color: #8b949e; font-size: 13px;")
        self.state.label_rate = QLabel("--")
        self.state.label_rate.setStyleSheet(
            f"color: {UITheme.COLORS['instant_rate']}; font-weight: bold; font-size: 14px; font-family: Consolas;"
        )
        h_rate.addWidget(lbl_rate)
        h_rate.addWidget(self.state.label_rate)
        h_rate.addStretch()
        rate_layout.addWidget(frame_rate)

        # ★ 实时压力显示（无背景框，超大字体，单位右下角）
        self.label_pressure = QLabel("--")
        self.label_pressure.setStyleSheet("""
            color: #58a6ff;
            font-size: 64px;
            font-weight: bold;
            font-family: Consolas;
            background-color: transparent;
            padding: 4px 0px;
        """)
        self.label_pressure.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rate_layout.addWidget(self.label_pressure)

        return group

    def _build_right_panel(self):
        right = QWidget()
        right.setStyleSheet("background-color: #0d1117;")
        layout = QVBoxLayout(right)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        plot_widget = self._build_plot_area()
        layout.addWidget(plot_widget, stretch=1)
        info_widget = self._build_info_row()
        info_widget.setFixedHeight(Config.UI_INFO_HEIGHT)
        layout.addWidget(info_widget)
        return right

    def _build_plot_area(self):
        plot_widget = pg.PlotWidget()
        plot_widget.setBackground(UITheme.COLORS['bg_chart'])
        plot_widget.showGrid(x=True, y=True, alpha=0.15)
        plot_widget.setLabel('bottom', '时间', units='s', color='#8b949e')
        plot_widget.setLabel('left', '压力', units='mmHg', color=UITheme.COLORS['pressure_curve'])
        plot_widget.setTitle('实时压力曲线', color='#c9d1d9', size='14pt')
        plot_widget.getAxis('bottom').setStyle(tickFont=None, tickTextOffset=4)

        left_axis = plot_widget.getAxis('left')
        left_axis.setPen(pg.mkPen(UITheme.COLORS['pressure_curve']))
        left_axis.setTextPen(pg.mkPen(UITheme.COLORS['pressure_curve']))
        left_axis.setStyle(tickFont=None, tickTextOffset=4)

        viewbox = plot_widget.getViewBox()
        viewbox.setRange(xRange=Config.PLOT_INITIAL_X_RANGE, yRange=Config.PLOT_INITIAL_Y_RANGE)
        viewbox.setBackgroundColor('#0d1117')

        pen = pg.mkPen(UITheme.COLORS['pressure_curve'], width=2.5)
        self.state.curve_pressure = pg.PlotDataItem([], [], pen=pen, downsample=100,
                                                    downsampleMethod='peak', autoDownsample=True)
        plot_widget.addItem(self.state.curve_pressure)

        plot_widget.showAxis('right')
        right_axis = plot_widget.getAxis('right')
        right_axis.setLabel('速率', units='mmHg/s', color=UITheme.COLORS['rate_curve'])
        right_axis.setPen(pg.mkPen(UITheme.COLORS['rate_curve']))
        right_axis.setTextPen(pg.mkPen(UITheme.COLORS['rate_curve']))
        right_axis.setStyle(tickFont=None, tickTextOffset=4)

        pen_rate = pg.mkPen(UITheme.COLORS['rate_curve'], width=2.5)
        self.state.curve_rate = plot_widget.plot([], [], pen=pen_rate, yAxis='right')
        self.state.curve_rate.setVisible(True)
        right_axis.setRange(*Config.PLOT_INITIAL_RATE_RANGE)

        self.state.plot_widget = plot_widget
        plot_widget.scene().sigMouseClicked.connect(self._on_plot_clicked)
        plot_widget.setCursor(Qt.CrossCursor)
        plot_widget.installEventFilter(self)
        return plot_widget

    def _refresh_plot(self, x_data, y_data):
        if not x_data:
            return

        self.state.curve_pressure.setData(x_data, y_data)
        rate = ResultCalculator.compute_rate_curve(np.array(x_data), np.array(y_data))
        self.state.curve_rate.setData(x_data, rate)
        self.state.curve_rate.setVisible(self.state.rate_visible)

        if not self.state.view_locked:
            viewbox = self.state.plot_widget.getViewBox()
            max_time = max(x_data) + Config.PLOT_AUTO_TIME_PADDING
            if max_time < Config.PLOT_AUTO_MIN_TIME:
                max_time = Config.PLOT_AUTO_MIN_TIME
            viewbox.setRange(xRange=(0, max_time))
            ymin = min(0, min(y_data) - Config.PLOT_AUTO_PRESSURE_PADDING)
            ymax = max(Config.PLOT_INITIAL_Y_RANGE[1], max(y_data) + Config.PLOT_AUTO_PRESSURE_PADDING)
            viewbox.setRange(yRange=(ymin, ymax))
            self._update_rate_axis(rate)

        if self.measure_text_item is not None:
            vb = self.state.plot_widget.getViewBox()
            x_range = vb.viewRange()[0]
            y_range = vb.viewRange()[1]
            self.measure_text_item.setPos(x_range[1] * 0.65, y_range[1] * 0.65)

    def _update_rate_axis(self, rate: np.ndarray):
        if len(rate) == 0:
            return
        current_rate = rate[-1]
        peak_rate = max(rate)
        if current_rate <= Config.PLOT_RATE_CURRENT_THRESHOLD:
            rmax = Config.PLOT_RATE_LOW_MAX
            step = Config.PLOT_RATE_LOW_STEP
        else:
            rmax = peak_rate + Config.PLOT_RATE_HIGH_PADDING
            if rmax <= Config.PLOT_RATE_MEDIUM_MAX:
                step = Config.PLOT_RATE_MEDIUM_STEP
            else:
                step = Config.PLOT_RATE_HIGH_STEP
        if rmax < 1:
            rmax = 1
        max_tick = int(np.ceil(rmax / step)) * step
        tick_values = np.arange(0, max_tick + step/2, step)
        if step < 1:
            tick_labels = [f"{v:.1f}" for v in tick_values]
        else:
            tick_labels = [f"{int(v)}" for v in tick_values]
        ticks = list(zip(tick_values, tick_labels))
        if len(ticks) > Config.PLOT_MAX_TICK_COUNT:
            step *= 2
            max_tick = int(np.ceil(rmax / step)) * step
            tick_values = np.arange(0, max_tick + step/2, step)
            tick_labels = [f"{int(v)}" if step >= 1 else f"{v:.1f}" for v in tick_values]
            ticks = list(zip(tick_values, tick_labels))
        right_axis = self.state.plot_widget.getAxis('right')
        right_axis.setTicks([ticks])
        right_axis.setRange(0, rmax)

    def _build_info_row(self):
        container = QWidget()
        container.setStyleSheet("background-color: #0d1117; border-top: 2px solid #21262d;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(5)

        frame_inf = QFrame()
        frame_inf.setStyleSheet("background-color: #0d1117; border: 2px solid #21262d;")
        h_inf = QHBoxLayout(frame_inf)
        h_inf.setContentsMargins(6, 2, 6, 2)
        lbl_inf = QLabel("充气结果:")
        lbl_inf.setStyleSheet("color: #8b949e; font-size: 16px;")
        self.state.label_inflate = QLabel("--")
        self.state.label_inflate.setStyleSheet(
            f"color: {UITheme.COLORS['inflate_result']}; font-weight: bold; font-size: 14px; font-family: Consolas;"
        )
        h_inf.addWidget(lbl_inf)
        h_inf.addWidget(self.state.label_inflate)
        h_inf.addStretch()
        layout.addWidget(frame_inf)

        frame_def = QFrame()
        frame_def.setStyleSheet("background-color: #0d1117; border: 2px solid #21262d;")
        h_def = QHBoxLayout(frame_def)
        h_def.setContentsMargins(6, 2, 6, 2)
        lbl_def = QLabel("泄气结果:")
        lbl_def.setStyleSheet("color: #8b949e; font-size: 16px;")
        self.state.label_deflate = QLabel("--")
        self.state.label_deflate.setStyleSheet(
            f"color: {UITheme.COLORS['deflate_result']}; font-weight: bold; font-size: 14px; font-family: Consolas;"
        )
        h_def.addWidget(lbl_def)
        h_def.addWidget(self.state.label_deflate)
        h_def.addStretch()
        layout.addWidget(frame_def)

        return container

    def _build_log_area(self):
        self.log_widget = LogWidget()
        self.log_widget.setStyleSheet("border-top: 1px solid #21262d;")
        return self.log_widget

    def _build_status_bar(self):
        bar = QWidget()
        bar.setStyleSheet("background-color: #0d1117; border-top: 1px solid #21262d;")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 0, 10, 0)
        lbl = QLabel("⚙ Ctrl+滚轮横向缩放  Shift+滚轮纵向缩放  清屏重置时间轴", bar)
        lbl.setStyleSheet("color: #8b949e; font-size: 11pt;")
        lay.addWidget(lbl)
        lay.addStretch()
        return bar

    # ---------- 事件过滤器 ----------
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel and obj is self.state.plot_widget:
            wheel_event: QWheelEvent = event
            modifiers = wheel_event.modifiers()
            delta = wheel_event.angleDelta().y()
            if delta == 0:
                return False
            viewbox = self.state.plot_widget.getViewBox()
            x_range = viewbox.viewRange()[0]
            y_range = viewbox.viewRange()[1]
            x_center = (x_range[0] + x_range[1]) / 2
            y_center = (y_range[0] + y_range[1]) / 2
            scale_factor = Config.PLOT_ZOOM_FACTOR if delta > 0 else 1 / Config.PLOT_ZOOM_FACTOR
            if modifiers & Qt.KeyboardModifier.ControlModifier:
                new_x_range = (x_center - (x_center - x_range[0]) * scale_factor,
                               x_center + (x_range[1] - x_center) * scale_factor)
                viewbox.setRange(xRange=new_x_range, yRange=y_range, padding=0)
                event.accept()
                return True
            elif modifiers & Qt.KeyboardModifier.ShiftModifier:
                new_y_range = (y_center - (y_center - y_range[0]) * scale_factor,
                               y_center + (y_range[1] - y_center) * scale_factor)
                viewbox.setRange(xRange=x_range, yRange=new_y_range, padding=0)
                event.accept()
                return True
            else:
                return False
        return super().eventFilter(obj, event)

    # ---------- 数据回调 ----------
    # 注意：原来的 _on_log 方法已删除，所有日志通过 logger 发送
    @Slot(list, list)
    def _on_plot_update(self, x_data, y_data):
        logger.debug(f"[UI] _on_plot_update 收到 {len(x_data)} 个数据点")
        self._refresh_plot(x_data, y_data)
        self._update_plot_button_state()

        if y_data:
            pressure = y_data[-1]
            if pressure >= Config.MIN_DISPLAY_PRESSURE:
                self.label_pressure.setText(
                    f'<span style="font-size:64px;color:#58a6ff;font-weight:bold;font-family:Consolas;">{pressure:.1f}</span>'
                    f'<span style="font-size:25px;color:#8b949e;vertical-align:sub;"> mmHg</span>'
                )
            else:
                self.label_pressure.setText("--")
        else:
            self.label_pressure.setText("--")

    @Slot(dict)
    def _on_result_text(self, result: dict):
        key = result.get('key')
        text = result.get('text')
        logger.debug(f"[UI] _on_result_text: key={key}, text={text}")
        if key == "inflate":
            self.state.label_inflate.setText(text)
        elif key == "deflate":
            self.state.label_deflate.setText(text)

    @Slot(float)
    def _on_rate_update(self, rate: float):
        if math.isinf(rate) or math.isnan(rate) or rate > Config.MAX_RATE_LIMIT:
            display = f">{int(Config.MAX_RATE_LIMIT)}"
        else:
            display = f"{rate:.2f}"
        self.state.label_rate.setText(f"{display} mmHg/s")

        x_data, y_data = self.data_ctrl.get_data()
        if y_data:
            pressure = y_data[-1]
            if pressure >= Config.MIN_DISPLAY_PRESSURE:
                self.label_pressure.setText(
                    f'<span style="font-size:64px;color:#58a6ff;font-weight:bold;font-family:Consolas;">{pressure:.1f}</span>'
                    f'<span style="font-size:25px;color:#8b949e;vertical-align:sub;"> mmHg</span>'
                )
            else:
                self.label_pressure.setText("--")
        else:
            self.label_pressure.setText("--")

    # ---------- 按钮状态 ----------
    def _update_buttons(self):
        connected = self.data_ctrl.is_connected
        self.state.btn_connect.setEnabled(not connected)
        self.state.btn_disconnect.setEnabled(connected)
        st = self.state.test_state

        self.state.btn_start.setEnabled(connected and (st == UITestState.IDLE or st == UITestState.FINISHED))
        self.state.btn_stop.setEnabled(st == UITestState.RUNNING)
        self.state.btn_toggle_plot.setEnabled(connected)

        if connected:
            is_pc = self.data_ctrl.is_pc_mode
            self.state.btn_pc_mode.setText("退出PC界面" if is_pc else "进入PC界面")
            self.state.btn_pc_mode.setEnabled(True)
            self.state.btn_pressure_test.setEnabled(True)
        else:
            self.state.btn_pc_mode.setText("进入PC界面")
            self.state.btn_pc_mode.setEnabled(False)
            self.state.btn_pressure_test.setEnabled(False)

    def set_status(self, text: str, color: str = None):
        if color:
            self.state.label_status.setText(f"● {text}")
            self.state.label_status.setStyleSheet(f"color: {color}; font-size: 13px;")
        else:
            self.state.label_status.setText(f"● {text}")

    # ---------- 串口记忆 ----------
    def _test_settings(self):
        return QSettings("YourCompany", "PressureTest")

    def _load_test_settings(self):
        settings = self._test_settings()
        defaults = {
            "inflate/start": Config.INFLATE_DEFAULT[0],
            "inflate/mid": Config.INFLATE_DEFAULT[1],
            "inflate/target": Config.INFLATE_DEFAULT[2],
            "deflate/start": Config.DEFLATE_DEFAULT[0],
            "deflate/mid": Config.DEFLATE_DEFAULT[1],
            "deflate/target": Config.DEFLATE_DEFAULT[2],
        }
        edits = {
            "inflate/start": self.state.inflate_start_edit,
            "inflate/mid": self.state.inflate_mid_edit,
            "inflate/target": self.state.inflate_target_edit,
            "deflate/start": self.state.deflate_start_edit,
            "deflate/mid": self.state.deflate_mid_edit,
            "deflate/target": self.state.deflate_target_edit,
        }
        blockers = [QSignalBlocker(edit) for edit in edits.values()]
        for key, edit in edits.items():
            edit.setText(str(settings.value(f"test/{key}", defaults[key])))
        del blockers
        self._read_params_to_ctrl()

    def _save_test_settings(self):
        settings = self._test_settings()
        values = {
            "inflate/start": self.state.inflate_start_edit.text(),
            "inflate/mid": self.state.inflate_mid_edit.text(),
            "inflate/target": self.state.inflate_target_edit.text(),
            "deflate/start": self.state.deflate_start_edit.text(),
            "deflate/mid": self.state.deflate_mid_edit.text(),
            "deflate/target": self.state.deflate_target_edit.text(),
        }
        for key, value in values.items():
            settings.setValue(f"test/{key}", value)

    def _load_serial_settings(self):
        settings = QSettings("YourCompany", "PressureTest")
        port = settings.value("serial/port", Config.DEFAULT_PORT)
        baud = settings.value("serial/baud", Config.DEFAULT_BAUD)
        if port:
            idx = self.state.combo_port.findText(port)
            if idx >= 0:
                self.state.combo_port.setCurrentIndex(idx)
        if baud:
            idx = self.state.combo_baud.findText(baud)
            if idx >= 0:
                self.state.combo_baud.setCurrentIndex(idx)

    def _save_serial_settings(self):
        settings = QSettings("YourCompany", "PressureTest")
        settings.setValue("serial/port", self.state.combo_port.currentText())
        settings.setValue("serial/baud", self.state.combo_baud.currentText())

    # ---------- 事件 ----------
    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.state.combo_port.clear()
        self.state.combo_port.addItems(ports)
        settings = QSettings("YourCompany", "PressureTest")
        stored_port = settings.value("serial/port", Config.DEFAULT_PORT)
        if stored_port in ports:
            self.state.combo_port.setCurrentText(stored_port)
        elif ports:
            self.state.combo_port.setCurrentIndex(0)

    def _connect(self):
        if self.data_ctrl.is_connected:
            return
        port = self.state.combo_port.currentText()
        if not port:
            QMessageBox.warning(self, "错误", "请选择串口")
            return
        baud = int(self.state.combo_baud.currentText())
        if self.data_ctrl.connect_serial(port, baud):
            self._save_serial_settings()
            self.state.btn_connect.setEnabled(False)
            self.state.btn_disconnect.setEnabled(True)
            self.set_status("监听中", UITheme.COLORS['inflate_result'])
            self.data_ctrl.start_logging()
            try:
                self._read_params_to_ctrl()
            except Exception as e:
                logger.warning(f"读取参数异常: {e}")
            self.state.test_state = UITestState.IDLE
            self._update_buttons()
            self._update_plot_button_state()
            self.data_ctrl.is_pc_mode = False
            self._auto_connect_enabled = True
            logger.debug("[UI] _connect 完成")

            # 重置锁定视图状态
            self.state.view_locked = False
            self.state.btn_lock_view.setText("锁定视图：关")
            self.state.btn_lock_view.setStyleSheet(UITheme.BUTTON_STYLES["action"])
            self.state.btn_lock_view.setChecked(False)
        else:
            self.set_status("连接失败", UITheme.COLORS['deflate_result'])
        self._update_buttons()

    def _disconnect(self):
        if self.data_ctrl.is_connected:
            is_running = (self.state.test_state == UITestState.RUNNING)
            self.data_ctrl.smart_disconnect(is_running)

        self.state.btn_connect.setEnabled(True)
        self.state.btn_disconnect.setEnabled(False)
        if self.data_ctrl.is_logging():
            self.data_ctrl.stop_logging()
        self.set_status("已断开", UITheme.COLORS['fg_secondary'])
        self.state.test_state = UITestState.IDLE
        self._update_buttons()
        self._clear_cursors()
        self._reset_plot_view()
        self._update_plot_button_state()
        self._auto_connect_enabled = False
        self.data_ctrl.is_pc_mode = False
        logger.info("已断开连接，自动连接已暂停（如需重新启用，请手动连接一次）")
        logger.debug("[UI] _disconnect 完成")

        # 重置锁定视图状态
        self.state.view_locked = False
        self.state.btn_lock_view.setText("锁定视图：关")
        self.state.btn_lock_view.setChecked(False)
        self.state.btn_lock_view.setStyleSheet(UITheme.BUTTON_STYLES["action"])

    def _read_params_to_ctrl(self):
        valid = True
        try:
            start = float(self.state.inflate_start_edit.text())
            mid = float(self.state.inflate_mid_edit.text())
            target = float(self.state.inflate_target_edit.text())
            if not self.data_ctrl.update_inflate_params(start, mid, target):
                logger.warning("充气参数不满足: 起始 < 中间 < 目标，请检查")
                valid = False
        except ValueError:
            logger.warning("充气参数含有非法数字，请检查输入")
            valid = False

        try:
            start = float(self.state.deflate_start_edit.text())
            mid = float(self.state.deflate_mid_edit.text())
            target = float(self.state.deflate_target_edit.text())
            if not self.data_ctrl.update_deflate_params(start, mid, target):
                logger.warning("泄气参数不满足: 起始 > 中间 > 目标，请检查")
                valid = False
        except ValueError:
            logger.warning("泄气参数含有非法数字，请检查输入")
            valid = False

        if valid:
            logger.data(
                "测试配置: 充气="
                f"{self.state.inflate_start_edit.text()}→{self.state.inflate_mid_edit.text()}→"
                f"{self.state.inflate_target_edit.text()}, 泄气="
                f"{self.state.deflate_start_edit.text()}→{self.state.deflate_mid_edit.text()}→"
                f"{self.state.deflate_target_edit.text()}"
            )
            self._save_test_settings()
        return valid

    def _on_param_change(self, test_key: str):
        if self.state.test_state == UITestState.FINISHED:
            self.state.test_state = UITestState.IDLE
            self._update_buttons()
        if self.state.test_state == UITestState.RUNNING:
            logger.warning("测试进行中，禁止修改参数")
            return

        try:
            if test_key == "inflate":
                start = float(self.state.inflate_start_edit.text())
                mid = float(self.state.inflate_mid_edit.text())
                target = float(self.state.inflate_target_edit.text())
                if self.data_ctrl.update_inflate_params(start, mid, target):
                    self._save_test_settings()
                    logger.data(f"充气参数: {start}→{mid}→{target}")
                else:
                    logger.warning("充气参数不合法（必须 起始<中间<目标）")
            else:  # deflate
                start = float(self.state.deflate_start_edit.text())
                mid = float(self.state.deflate_mid_edit.text())
                target = float(self.state.deflate_target_edit.text())
                if self.data_ctrl.update_deflate_params(start, mid, target):
                    self._save_test_settings()
                    logger.data(f"泄气参数: {start}→{mid}→{target}")
                else:
                    logger.warning("泄气参数不合法（必须 起始>中间>目标）")
        except ValueError:
            logger.warning("参数含有非法数字，请检查输入")

    def _on_start(self):
        if not self.data_ctrl.is_connected:
            logger.warning("请先连接串口")
            return
        if self.state.test_state == UITestState.RUNNING:
            logger.warning("测试正在进行中，请勿重复开始")
            return
        if not self._read_params_to_ctrl():
            logger.warning("测试参数无效，已取消启动")
            return
        self.data_ctrl.reset_all()
        if self.data_ctrl.send_command("AT#AG"):
            self.state.test_state = UITestState.RUNNING
            self._update_buttons()
            self.set_status("测量中...", UITheme.COLORS['log_yellow'])
            logger.cmd("发送命令: AT#AG")
            self._update_plot_button_state()
        else:
            logger.error("AT#AG 发送失败")

    def _on_stop(self):
        if self.state.test_state != UITestState.RUNNING:
            logger.info("测试未开始或已结束")
            return
        if self.data_ctrl.send_command("AT#AH"):
            self.state.test_state = UITestState.FINISHED
            self._update_buttons()
            self.set_status("测试结束", UITheme.COLORS['log_blue'])
            logger.cmd("发送命令: AT#AH")
            phase = self.data_ctrl.test_manager.get_stage()
            if phase == TestPhase.INFLATING:
                self.data_ctrl.test_manager.force_complete_inflate()
            elif phase == TestPhase.DEFLATING:
                self.data_ctrl.test_manager.force_complete_deflate()
        else:
            logger.error("AT#AH 发送失败")

    # ---------- PC模式切换 ----------
    def _toggle_pc_mode(self):
        if not self.data_ctrl.is_connected:
            logger.warning("请先连接串口")
            return

        if self.data_ctrl.is_pc_mode:
            if self.data_ctrl.exit_pc_mode():
                self._update_buttons()
                logger.info("退出PC界面成功")
        else:
            if self.data_ctrl.enter_pc_mode():
                self._update_buttons()
                logger.success("进入PC界面成功")

    # ---------- 压力表测试 ----------
    def _on_pressure_test(self):
        if not self.data_ctrl.is_connected:
            logger.warning("请先连接串口")
            return

        if not self.data_ctrl.is_pc_mode:
            logger.info("尝试进入 PC 模式...")
            if not self.data_ctrl.enter_pc_mode():
                logger.error("进入 PC 模式失败，压力表测试无法继续")
                return
            else:
                self._update_buttons()
                import time
                time.sleep(Config.PC_MODE_SWITCH_DELAY)

        cmd = bytes(Config.BINARY_COMMANDS["pressure_test"])
        if self.data_ctrl.send_bytes_command(cmd):
            logger.cmd("发送压力表测试命令")
            self._clear_screen()
        else:
            logger.error("发送压力表测试命令失败")

    # ---------- 其他功能 ----------
    def _save_image(self):
        if self.state.plot_widget is None:
            QMessageBox.warning(self, "警告", "绘图区域未初始化")
            return
        fn, _ = QFileDialog.getSaveFileName(self, "保存图片", "", "PNG (*.png);;JPEG (*.jpg)")
        if fn:
            try:
                pixmap = self.state.plot_widget.grab()
                if pixmap.isNull():
                    QMessageBox.warning(self, "警告", "截图失败，请重试")
                    return
                pixmap.save(fn)
                logger.success(f"图片已保存至 {fn}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存图片失败: {e}")

    def _save_csv(self):
        x, y = self.data_ctrl.get_data()
        if not x:
            QMessageBox.warning(self, "警告", "没有数据")
            return
        fn, _ = QFileDialog.getSaveFileName(self, "保存CSV", "", "CSV (*.csv)")
        if fn:
            try:
                self.data_ctrl.save_data_to_csv(fn)
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def _load_waveform(self):
        fn, _ = QFileDialog.getOpenFileName(self, "加载波形", "", "CSV (*.csv)")
        if fn:
            try:
                self.data_ctrl.load_data_from_csv(fn)
                self.state.test_state = UITestState.IDLE
                self._update_buttons()
                self.set_status("离线查看", UITheme.COLORS['log_blue'])
                logger.success(f"已加载波形: {os.path.basename(fn)}")
                self._update_plot_button_state()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def _clear_screen(self):
        self.data_ctrl.reset_all()
        self.state.curve_pressure.setData([], [])
        self.state.curve_rate.setData([], [])
        self._clear_cursors()
        self.clear_results()
        self._reset_plot_view()
        self._update_buttons()
        self._update_plot_button_state()
        logger.info("数据已清空，波形已清屏（时间轴已归零）")
        self.label_pressure.setText("--")

    def _reset_plot_view(self):
        vb = self.state.plot_widget.getViewBox()
        vb.setRange(xRange=Config.PLOT_INITIAL_X_RANGE, yRange=Config.PLOT_INITIAL_Y_RANGE)
        self.state.plot_widget.getAxis('right').setRange(*Config.PLOT_INITIAL_RATE_RANGE)

    def clear_results(self):
        self.state.label_rate.setText("--")
        self.state.label_inflate.setText("--")
        self.state.label_deflate.setText("--")

    # ---------- 双光标测量（两组独立） ----------
    def _toggle_cursor(self):
        self.state.cursor_enabled = not self.state.cursor_enabled
        if self.state.cursor_enabled:
            self.state.plot_widget.setCursor(Qt.CrossCursor)
            logger.info("光标测量已启用（C1/C2一组，B1/B2一组，各独立测量）")
        else:
            self.state.plot_widget.setCursor(Qt.ArrowCursor)
            self._clear_cursors()
            logger.info("光标测量已关闭")

    def _on_plot_clicked(self, event):
        if not self.state.cursor_enabled:
            return
        pos = event.scenePos()
        if not self.state.plot_widget.sceneBoundingRect().contains(pos):
            return
        vb = self.state.plot_widget.getViewBox()
        data_pos = vb.mapSceneToView(pos)
        x, y = data_pos.x(), data_pos.y()

        if len(self.cursor_items) >= 4:
            self._clear_cursors()

        idx = len(self.cursor_items)
        if idx < 2:
            color = self.cursor_groups['group1']['colors'][idx]
            label = self.cursor_groups['group1']['labels'][idx]
        else:
            color = self.cursor_groups['group2']['colors'][idx - 2]
            label = self.cursor_groups['group2']['labels'][idx - 2]

        self._add_cursor_item(x, y, color, label)
        self._update_all_measurements()

    def _add_cursor_item(self, x: float, y: float, color: str, label: str):
        pen_color = pg.mkColor(color)
        pen_color.setAlpha(150)
        pen = pg.mkPen(pen_color, width=1.2, style=Qt.DashLine)
        pen.setDashPattern([6, 6])

        v_line = pg.InfiniteLine(pos=x, angle=90, movable=True, pen=pen)
        h_line = pg.InfiniteLine(pos=y, angle=0, movable=True, pen=pen)

        dot = pg.ScatterPlotItem([x], [y], pen=pg.mkPen(color, width=1.2),
                                brush=pg.mkBrush(color), size=9)
        text_item = pg.TextItem(f"{label} ({x:.2f}, {y:.2f})", color=color,
                                anchor=(0, 1))
        text_item.setPos(x, y)
        text_item.setFont(QFont("Consolas", 10))
        self.state.plot_widget.addItem(v_line)
        self.state.plot_widget.addItem(h_line)
        self.state.plot_widget.addItem(dot)
        self.state.plot_widget.addItem(text_item)
        self.cursor_items.append({'v_line': v_line, 'h_line': h_line,
                                'dot': dot, 'text': text_item, 'x': x, 'y': y})
        v_line.sigPositionChanged.connect(self._on_cursor_moved)
        h_line.sigPositionChanged.connect(self._on_cursor_moved)
        logger.info(f"光标 {label} 已添加 (x={x:.2f}, y={y:.2f})")

    def _on_cursor_moved(self):
        self._update_all_measurements()

    def _update_all_measurements(self):
        for i, item in enumerate(self.cursor_items):
            x = item['v_line'].value()
            y = item['h_line'].value()
            if i < 2:
                label = self.cursor_groups['group1']['labels'][i]
            else:
                label = self.cursor_groups['group2']['labels'][i - 2]
            item['text'].setText(f"{label} ({x:.2f}, {y:.2f})")
            item['text'].setPos(x, y)
            item['dot'].setData([x], [y])
            item['x'] = x
            item['y'] = y

        if len(self.cursor_items) >= 2:
            self._update_group_measurement(0, 1, 'group1')
        else:
            if self.group1_measure_item is not None:
                self.state.plot_widget.removeItem(self.group1_measure_item)
                self.group1_measure_item = None
            self.state.label_rate.setText("--")

        if len(self.cursor_items) >= 4:
            self._update_group_measurement(2, 3, 'group2')
        else:
            if self.group2_measure_item is not None:
                self.state.plot_widget.removeItem(self.group2_measure_item)
                self.group2_measure_item = None

    def _update_cursor_labels(self):
        for i, item in enumerate(self.cursor_items):
            x = item['v_line'].value()
            y = item['h_line'].value()
            if i < 2:
                label = self.cursor_groups['group1']['labels'][i]
            else:
                label = self.cursor_groups['group2']['labels'][i - 2]
            item['text'].setText(f"{label} ({x:.2f}, {y:.2f})")
            item['text'].setPos(x, y)
            item['dot'].setData([x], [y])
            item['x'] = x
            item['y'] = y

    def _update_group_measurement(self, idx1: int, idx2: int, group_name: str):
        if len(self.cursor_items) <= idx2:
            return

        item1 = self.cursor_items[idx1]
        item2 = self.cursor_items[idx2]

        x1 = item1['v_line'].value()
        y1 = item1['h_line'].value()
        x2 = item2['v_line'].value()
        y2 = item2['h_line'].value()

        dt = abs(x2 - x1)
        dp = abs(y2 - y1)
        if dt < Config.TIME_DELTA_EPSILON:
            rate = 0.0
        else:
            rate = dp / dt
        if math.isinf(rate) or math.isnan(rate):
            rate = 0.0
        rate = min(rate, Config.MAX_RATE_LIMIT)

        label1 = self.cursor_groups[group_name]['labels'][0]
        label2 = self.cursor_groups[group_name]['labels'][1]
        color1 = self.cursor_groups[group_name]['colors'][0]
        color2 = self.cursor_groups[group_name]['colors'][1]

        result_text = (
            f'<span style="color:#ffffff; font-size:12px;">Δt = {dt:.3f}s</span><br>'
            f'<span style="color:#ffffff; font-size:12px;">ΔP = {dp:.1f}mmHg</span><br>'
            f'<span style="color:#ffffff; font-size:12px;">速率 = {rate:.2f}mmHg/s</span>'
        )

        if group_name == 'group1':
            self.state.label_rate.setText(f"{rate:.2f} mmHg/s")
            self.state.label_rate.setStyleSheet(
                f"color: {UITheme.COLORS['instant_rate']}; font-weight: bold; font-size: 14px; font-family: Consolas;"
            )
            if self.group1_measure_item is None:
                self.group1_measure_item = pg.TextItem(
                    "", color='#c9d1d9', anchor=(0, 1),
                )
                self.group1_measure_item.setFont(QFont("Consolas", 10))
                self.state.plot_widget.addItem(self.group1_measure_item)
            self.group1_measure_item.setPos(x2 + 1, y2 + 25)
            self.group1_measure_item.setHtml(result_text)

        else:  # group2
            if self.group2_measure_item is None:
                self.group2_measure_item = pg.TextItem(
                    "", color='#c9d1d9', anchor=(1, 1),
                )
                self.group2_measure_item.setFont(QFont("Consolas", 10))
                self.state.plot_widget.addItem(self.group2_measure_item)
            self.group2_measure_item.setPos(x2 - 1, y2 + 15)
            self.group2_measure_item.setHtml(result_text)

    def _clear_cursors(self):
        for item in self.cursor_items:
            self.state.plot_widget.removeItem(item['v_line'])
            self.state.plot_widget.removeItem(item['h_line'])
            self.state.plot_widget.removeItem(item['dot'])
            self.state.plot_widget.removeItem(item['text'])
        self.cursor_items.clear()

        if self.group1_measure_item:
            self.state.plot_widget.removeItem(self.group1_measure_item)
            self.group1_measure_item = None
        if self.group2_measure_item:
            self.state.plot_widget.removeItem(self.group2_measure_item)
            self.group2_measure_item = None

        if self.measure_text_item:
            self.state.plot_widget.removeItem(self.measure_text_item)
            self.measure_text_item = None

        self.state.label_rate.setText("--")
        self.state.label_rate.setStyleSheet(
            f"color: {UITheme.COLORS['instant_rate']}; font-weight: bold; font-size: 14px; font-family: Consolas;"
        )

    # ---------- 关闭事件 ----------
    def closeEvent(self, event):
        try:
            self._clear_cursors()
            if self.data_ctrl.is_connected:
                is_running = (self.state.test_state == UITestState.RUNNING)
                self.data_ctrl.smart_disconnect(is_running)
        except Exception as e:
            logger.error(f"closeEvent 异常: {e}")
            try:
                if self.data_ctrl.is_logging():
                    self.data_ctrl.stop_logging()
            except Exception:
                pass
        finally:
            event.accept()


# 布局实现集中在 ui_components.py；主窗口类保留交互和业务行为。
for _ui_method in (
    "_build_ui", "_build_toolbar", "_build_left_panel", "_build_param_group",
    "_add_param_input", "_build_control_group", "_build_rate_display",
    "_build_right_panel", "_build_plot_area", "_build_info_row",
    "_build_log_area", "_build_status_bar",
):
    setattr(MainWindow, _ui_method, getattr(MainWindowUiMixin, _ui_method))