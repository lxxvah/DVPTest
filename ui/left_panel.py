# ui/left_panel.py
"""左侧面板 — 参数输入、控制按钮、实时压力显示"""
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QGroupBox, QFrame
)
from config import Config

class LeftPanel(QWidget):
    # 信号
    sig_start = Signal()
    sig_stop = Signal()
    sig_clear = Signal()
    sig_toggle_plot = Signal(bool)
    sig_toggle_rate = Signal(bool)
    sig_save_image = Signal()
    sig_save_csv = Signal()
    sig_load_wave = Signal()
    sig_toggle_cursor = Signal(bool)
    sig_pc_mode = Signal()
    sig_pressure_test = Signal()
    sig_param_changed = Signal(str)
    sig_lock_view = Signal()

    def __init__(self, data_ctrl, parent=None):
        super().__init__(parent)
        self.setObjectName("left_panel")
        self.data_ctrl = data_ctrl
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(18)

        layout.addWidget(self._build_param_group())
        layout.addWidget(self._build_control_group())
        layout.addWidget(self._build_rate_display())
        layout.addStretch()

    def _build_param_group(self):
        group = QWidget()
        param_layout = QVBoxLayout(group)
        param_layout.setContentsMargins(0, 0, 0, 0)
        param_layout.setSpacing(8)

        # 充气参数
        grp_inf = QGroupBox("充气测试")
        grp_inf.setFlat(True)
        g_lay = QHBoxLayout(grp_inf)
        g_lay.setSpacing(4)
        g_lay.setContentsMargins(6, 6, 6, 6)
        self._add_input(g_lay, "起始", "inflate_start", str(Config.INFLATE_DEFAULT[0]), "inflate")
        self._add_input(g_lay, "中间", "inflate_mid", str(Config.INFLATE_DEFAULT[1]), "inflate")
        self._add_input(g_lay, "目标", "inflate_target", str(Config.INFLATE_DEFAULT[2]), "inflate")
        g_lay.addStretch()
        param_layout.addWidget(grp_inf)

        # 泄气参数
        grp_def = QGroupBox("泄气测试")
        grp_def.setFlat(True)
        g_lay2 = QHBoxLayout(grp_def)
        g_lay2.setSpacing(4)
        g_lay2.setContentsMargins(6, 6, 6, 6)
        self._add_input(g_lay2, "起始", "deflate_start", str(Config.DEFLATE_DEFAULT[0]), "deflate")
        self._add_input(g_lay2, "中间", "deflate_mid", str(Config.DEFLATE_DEFAULT[1]), "deflate")
        self._add_input(g_lay2, "目标", "deflate_target", str(Config.DEFLATE_DEFAULT[2]), "deflate")
        g_lay2.addStretch()
        param_layout.addWidget(grp_def)

        return group

    def _add_input(self, layout, label_text, attr_name, default_text, test_key):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(2)
        h.addWidget(QLabel(label_text))
        edit = QLineEdit(default_text)
        edit.setFixedWidth(44)
        edit.textChanged.connect(lambda: self.sig_param_changed.emit(test_key))
        setattr(self, attr_name, edit)
        h.addWidget(edit)
        layout.addWidget(w)

    def _build_control_group(self):
        group = QWidget()
        ctrl_layout = QVBoxLayout(group)
        ctrl_layout.setContentsMargins(0, 0, 0, 0)
        ctrl_layout.setSpacing(10)

        # 模拟器
        lbl_simulator = QLabel("无创血压模拟器")
        ctrl_layout.addWidget(lbl_simulator)

        row_pc = QHBoxLayout()
        row_pc.setSpacing(6)
        self.btn_pc_mode = QPushButton("进入PC界面")
        self.btn_pc_mode.setObjectName("btn_action")
        self.btn_pc_mode.clicked.connect(self.sig_pc_mode.emit)
        row_pc.addWidget(self.btn_pc_mode)

        self.btn_pressure_test = QPushButton("压力表测试")
        self.btn_pressure_test.setObjectName("btn_start")
        self.btn_pressure_test.clicked.connect(self.sig_pressure_test.emit)
        row_pc.addWidget(self.btn_pressure_test)
        row_pc.addStretch()
        ctrl_layout.addLayout(row_pc)

        # 测试板
        lbl_board = QLabel("测试板压力传感器")
        ctrl_layout.addWidget(lbl_board)

        row_start = QHBoxLayout()
        row_start.setSpacing(6)
        self.btn_start = QPushButton("开始 AT#AG")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.clicked.connect(self.sig_start.emit)
        row_start.addWidget(self.btn_start)

        self.btn_stop = QPushButton("结束 AT#AH")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.sig_stop.emit)
        row_start.addWidget(self.btn_stop)
        row_start.addStretch()
        ctrl_layout.addLayout(row_start)

        # 保存/加载
        row_save = QHBoxLayout()
        row_save.setSpacing(6)
        btn_img = QPushButton("保存图片")
        btn_img.setObjectName("btn_action")
        btn_img.clicked.connect(self.sig_save_image.emit)
        row_save.addWidget(btn_img)

        btn_csv = QPushButton("保存CSV")
        btn_csv.setObjectName("btn_action")
        btn_csv.clicked.connect(self.sig_save_csv.emit)
        row_save.addWidget(btn_csv)
        row_save.addStretch()
        ctrl_layout.addLayout(row_save)

        row_load = QHBoxLayout()
        row_load.setSpacing(6)
        btn_load = QPushButton("加载波形")
        btn_load.setObjectName("btn_action")
        btn_load.clicked.connect(self.sig_load_wave.emit)
        row_load.addWidget(btn_load)

        self.btn_cursor = QPushButton("光标测量")
        self.btn_cursor.setObjectName("btn_action")
        self.btn_cursor.setCheckable(True)
        self.btn_cursor.clicked.connect(self._toggle_cursor)
        row_load.addWidget(self.btn_cursor)
        row_load.addStretch()
        ctrl_layout.addLayout(row_load)

        # 锁定视图 + 主题切换
        row_lock = QHBoxLayout()
        row_lock.setSpacing(6)
        self.btn_lock_view = QPushButton("锁定视图：关")
        self.btn_lock_view.setObjectName("btn_action")
        self.btn_lock_view.setCheckable(True)
        self.btn_lock_view.clicked.connect(self.sig_lock_view.emit)
        row_lock.addWidget(self.btn_lock_view)

        self.btn_toggle_plot = QPushButton("暂停绘图")
        self.btn_toggle_plot.setObjectName("btn_toggle_plot")
        self.btn_toggle_plot.clicked.connect(lambda: self.sig_toggle_plot.emit(True))
        row_lock.addWidget(self.btn_toggle_plot)

        row_lock.addStretch()
        ctrl_layout.addLayout(row_lock)

        # 主题切换
        row_theme = QHBoxLayout()
        row_theme.setSpacing(6)
        self.btn_theme = QPushButton("🌙 深色")
        self.btn_theme.setObjectName("btn_action")
        row_theme.addWidget(self.btn_theme)
        row_theme.addStretch()
        ctrl_layout.addLayout(row_theme)

        return group

    def _toggle_cursor(self):
        self.sig_toggle_cursor.emit(self.btn_cursor.isChecked())

    def _build_rate_display(self):
        group = QWidget()
        rate_layout = QVBoxLayout(group)
        rate_layout.setContentsMargins(0, 0, 0, 0)
        rate_layout.setSpacing(4)

        # 瞬时速率
        frame = QFrame()
        frame.setObjectName("rate_frame")
        h = QHBoxLayout(frame)
        h.setContentsMargins(6, 2, 6, 2)
        h.addWidget(QLabel("瞬时速率:"))
        self.label_rate = QLabel("--")
        self.label_rate.setStyleSheet(
            f"color: {Config.COLORS['instant_rate']}; font-weight: bold; font-size: 14px;"
        )
        h.addWidget(self.label_rate)
        h.addStretch()
        rate_layout.addWidget(frame)

        # 实时压力
        self.label_pressure = QLabel("--")
        self.label_pressure.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_pressure.setStyleSheet(
            f"color: {Config.COLORS['fg_highlight']}; font-size: 64px; font-weight: 600;"
        )
        rate_layout.addWidget(self.label_pressure)

        # 充气/泄气结果
        frame_result = QFrame()
        frame_result.setObjectName("result_frame")
        v = QVBoxLayout(frame_result)
        v.setContentsMargins(6, 2, 6, 2)

        h_inf = QHBoxLayout()
        h_inf.addWidget(QLabel("充气结果:"))
        self.label_inflate = QLabel("--")
        self.label_inflate.setStyleSheet(
            f"color: {Config.COLORS['inflate_result']}; font-weight: bold; font-size: 14px;"
        )
        h_inf.addWidget(self.label_inflate)
        h_inf.addStretch()
        v.addLayout(h_inf)

        h_def = QHBoxLayout()
        h_def.addWidget(QLabel("泄气结果:"))
        self.label_deflate = QLabel("--")
        self.label_deflate.setStyleSheet(
            f"color: {Config.COLORS['deflate_result']}; font-weight: bold; font-size: 14px;"
        )
        h_def.addWidget(self.label_deflate)
        h_def.addStretch()
        v.addLayout(h_def)

        rate_layout.addWidget(frame_result)

        return group

    # ===================== 公共更新方法 =====================
    def update_button_state(self, connected=False, running=False):
        self.btn_start.setEnabled(connected and not running)
        self.btn_stop.setEnabled(connected and running)

    def update_pc_mode(self, is_pc):
        self.btn_pc_mode.setText("退出PC界面" if is_pc else "进入PC界面")

    def update_pressure(self, pressure):
        if pressure is not None and pressure >= 0:
            self.label_pressure.setText(
                f'<span style="font-size:64px;color:{Config.COLORS["fg_highlight"]};font-weight:600;">{pressure:.1f}</span>'
                f'<span style="font-size:25px;color:{Config.COLORS["fg_secondary"]};"> mmHg</span>'
            )
        else:
            self.label_pressure.setText("--")

    def update_rate(self, rate):
        self.label_rate.setText(f"{rate} mmHg/s")

    def update_result(self, key, text):
        if key == "inflate":
            self.label_inflate.setText(text)
        elif key == "deflate":
            self.label_deflate.setText(text)

    def set_view_locked(self, locked):
        self.btn_lock_view.setText("锁定视图：开" if locked else "锁定视图：关")
        self.btn_lock_view.setChecked(locked)

    def set_cursor_state(self, enabled):
        self.btn_cursor.setChecked(enabled)

    def clear_results(self):
        self.label_rate.setText("--")
        self.label_inflate.setText("--")
        self.label_deflate.setText("--")

    def refresh_theme(self):
        """主题切换时刷新颜色"""
        self.label_rate.setStyleSheet(
            f"color: {Config.COLORS['instant_rate']}; font-weight: bold; font-size: 14px;"
        )
        self.label_inflate.setStyleSheet(
            f"color: {Config.COLORS['inflate_result']}; font-weight: bold; font-size: 14px;"
        )
        self.label_deflate.setStyleSheet(
            f"color: {Config.COLORS['deflate_result']}; font-weight: bold; font-size: 14px;"
        )
        self.label_pressure.setStyleSheet(
            f"color: {Config.COLORS['fg_highlight']}; font-size: 64px; font-weight: 600;"
        )