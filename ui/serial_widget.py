# ui/serial_widget.py
"""串口工具栏 — 端口选择、波特率、连接/断开"""
from PySide6.QtCore import Signal, QSettings, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QComboBox, QPushButton, QLineEdit
import serial.tools.list_ports
from config import Config

class SerialWidget(QFrame):
    sig_connect = Signal()
    sig_disconnect = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("toolbar")
        self._setup_ui()
        self._refresh_ports()

    def _setup_ui(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 2, 10, 2)
        lay.setSpacing(8)

        lay.addWidget(QLabel("串口:"))
        self.combo_port = QComboBox()
        self.combo_port.setFixedWidth(80)
        lay.addWidget(self.combo_port)

        btn_refresh = QPushButton("刷新")
        btn_refresh.setObjectName("btn_action")
        btn_refresh.clicked.connect(self._refresh_ports)
        lay.addWidget(btn_refresh)

        lay.addWidget(QLabel("波特率:"))
        self.combo_baud = QComboBox()
        self.combo_baud.addItems(Config.BAUDRATES)
        self.combo_baud.setCurrentText(Config.DEFAULT_BAUD)
        self.combo_baud.setFixedWidth(80)
        lay.addWidget(self.combo_baud)

        self.btn_connect = QPushButton("连接")
        self.btn_connect.setObjectName("btn_connect")
        self.btn_connect.clicked.connect(self._do_connect)
        lay.addWidget(self.btn_connect)

        self.btn_disconnect = QPushButton("断开")
        self.btn_disconnect.setObjectName("btn_disconnect")
        self.btn_disconnect.setEnabled(False)
        self.btn_disconnect.clicked.connect(self._do_disconnect)
        lay.addWidget(self.btn_disconnect)

        # 清屏按钮
        self.btn_clear = QPushButton("清屏")
        self.btn_clear.setObjectName("btn_action")
        lay.addWidget(self.btn_clear)

        # 停止阈值
        lay.addWidget(QLabel("停止阈值:"))
        self.threshold_edit = QLineEdit(str(Config.PLOT_STOP_THRESHOLD))
        self.threshold_edit.setFixedWidth(40)
        self.threshold_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.threshold_edit.textChanged.connect(self._on_threshold_changed)
        lay.addWidget(self.threshold_edit)
        lay.addWidget(QLabel("mmHg"))

        # 速率曲线开关
        self.btn_toggle_rate = QPushButton("速率曲线：开")
        self.btn_toggle_rate.setObjectName("btn_action")
        self.btn_toggle_rate.setCheckable(True)
        self.btn_toggle_rate.setChecked(True)
        lay.addWidget(self.btn_toggle_rate)

        lay.addStretch()
        self.label_status = QLabel("● 未连接")
        self.label_status.setStyleSheet("color: #86868b; font-size: 13px;")
        lay.addWidget(self.label_status)

    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.combo_port.clear()
        self.combo_port.addItems(ports)
        settings = QSettings("YourCompany", "PressureTest")
        stored = settings.value("serial/port", Config.DEFAULT_PORT)
        if stored in ports:
            self.combo_port.setCurrentText(stored)

    def _on_threshold_changed(self, text):
        try:
            val = float(text)
            if val >= 0:
                Config.PLOT_STOP_THRESHOLD = val
        except ValueError:
            pass

    def load_settings(self):
        settings = QSettings("YourCompany", "PressureTest")
        port = settings.value("serial/port", Config.DEFAULT_PORT)
        baud = settings.value("serial/baud", Config.DEFAULT_BAUD)
        idx = self.combo_port.findText(port)
        if idx >= 0:
            self.combo_port.setCurrentIndex(idx)
        idx = self.combo_baud.findText(baud)
        if idx >= 0:
            self.combo_baud.setCurrentIndex(idx)

    def save_settings(self):
        settings = QSettings("YourCompany", "PressureTest")
        settings.setValue("serial/port", self.combo_port.currentText())
        settings.setValue("serial/baud", self.combo_baud.currentText())

    def _do_connect(self):
        if not self.combo_port.currentText():
            return
        self.sig_connect.emit()

    def _do_disconnect(self):
        self.sig_disconnect.emit()

    def set_connected_state(self, connected):
        self.btn_connect.setEnabled(not connected)
        self.btn_disconnect.setEnabled(connected)
        if connected:
            self.label_status.setText("● 已连接")
            self.label_status.setStyleSheet("color: #34c759; font-size: 13px;")
        else:
            self.label_status.setText("● 未连接")
            self.label_status.setStyleSheet("color: #86868b; font-size: 13px;")

    def set_status(self, text, color):
        self.label_status.setText(f"● {text}")
        self.label_status.setStyleSheet(f"color: {color}; font-size: 13px;")

    def refresh_theme(self):
        from config import Config
        if self.btn_connect.isEnabled():
            self.label_status.setStyleSheet(f"color: {Config.COLORS['fg_secondary']}; font-size: 13px;")