# ui/main_window.py
"""主窗口 — 组装所有UI模块，包含所有业务逻辑"""
import os
import math
import logging
from PySide6.QtCore import QTimer, QSettings, Qt, Slot
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QMessageBox, QFileDialog

import serial.tools.list_ports
from config import Config
from data_controller import DataController
from test_managers import TestPhase
from logger import _bridge

from ui.log_widget import LogWidget
from ui.theme_manager import ThemeManager
from ui.cursor_manager import CursorManager
from ui.serial_widget import SerialWidget
from ui.plot_widget import PlotWidget
from ui.left_panel import LeftPanel

logger = logging.getLogger("DVPTest")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("泄气阀压力测试上位机 作者：刘欣  「莫道桑榆晚，为霞尚满天」")
        self.setMinimumSize(1200, 720)

        self.data_ctrl = DataController()
        self.theme_mgr = ThemeManager()
        self.cursor_mgr = None
        self.measure_text_item = None

        self._build_ui()
        self._connect_signals()
        self._restore_state()

        # 自动连接定时器
        self._auto_connect_timer = QTimer(self)
        self._auto_connect_timer.timeout.connect(self._auto_connect_cb)
        self._auto_connect_timer.start(2000)
        self._auto_connect_enabled = True

        self.ensurePolished()
        logger.debug("[MainWindow] 初始化完成")

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 串口工具栏
        self.serial_widget = SerialWidget()
        main_layout.addWidget(self.serial_widget)

        # 主区域（左右分割）
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # 左侧面板
        self.left_panel = LeftPanel(self.data_ctrl)
        self.left_panel.setMinimumWidth(180)
        self.left_panel.setMaximumWidth(500)

        # 右侧绘图
        self.plot_widget = PlotWidget(self.data_ctrl)
        self.cursor_mgr = CursorManager(self.plot_widget)

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.addWidget(self.left_panel)
        self.main_splitter.addWidget(self.plot_widget)
        self.main_splitter.setSizes([260, 1000])

        body_layout.addWidget(self.main_splitter)
        main_layout.addWidget(body, stretch=1)

        # 日志
        self.log_widget = LogWidget()
        self.log_widget.setFixedHeight(140)
        main_layout.addWidget(self.log_widget)

        # 状态栏
        status_bar = self._build_status_bar()
        status_bar.setFixedHeight(24)
        main_layout.addWidget(status_bar)

        # 给主题管理器绑定主窗口
        self.theme_mgr.attach(self)

    def _build_status_bar(self):
        from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
        bar = QWidget()
        bar.setObjectName("status_bar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 0, 10, 0)
        lbl = QLabel("⚙ Ctrl+滚轮横向缩放  Shift+滚轮纵向缩放  清屏重置时间轴", bar)
        lay.addWidget(lbl)
        lay.addStretch()
        return bar

    def _connect_signals(self):
        """连接所有信号槽"""
        # 日志桥接
        _bridge.sig_log.connect(self.log_widget.append_log)

        # 数据回调
        self.data_ctrl.sig_plot.connect(self._on_plot_update)
        self.data_ctrl.sig_result_text.connect(self._on_result_text)
        self.data_ctrl.sig_rate.connect(self._on_rate_update)
        self.data_ctrl.sig_raw.connect(lambda s: logger.info(f"[串口] {s}"))

        # 串口工具栏
        self.serial_widget.sig_connect.connect(self._connect)
        self.serial_widget.sig_disconnect.connect(self._disconnect)
        self.serial_widget.btn_clear.clicked.connect(self._clear_screen)
        self.serial_widget.btn_toggle_rate.clicked.connect(self._toggle_rate_curve)

        # 左侧面板信号
        self.left_panel.sig_start.connect(self._on_start)
        self.left_panel.sig_stop.connect(self._on_stop)
        self.left_panel.sig_clear.connect(self._clear_screen)
        self.left_panel.sig_toggle_plot.connect(self._toggle_plot_pause)
        self.left_panel.sig_toggle_rate.connect(self._toggle_rate_curve)
        self.left_panel.sig_save_image.connect(self._save_image)
        self.left_panel.sig_save_csv.connect(self._save_csv)
        self.left_panel.sig_load_wave.connect(self._load_waveform)
        self.left_panel.sig_toggle_cursor.connect(self._toggle_cursor)
        self.left_panel.sig_pc_mode.connect(self._toggle_pc_mode)
        self.left_panel.sig_pressure_test.connect(self._on_pressure_test)
        self.left_panel.sig_param_changed.connect(self._on_param_change)
        self.left_panel.sig_lock_view.connect(self._toggle_view_lock)
        self.left_panel.btn_theme.clicked.connect(self.theme_mgr.toggle)

    def _restore_state(self):
        """恢复主题、串口、分割器"""
        settings = QSettings("YourCompany", "PressureTest")
        saved_theme = settings.value("theme", "light")
        self.theme_mgr.apply_theme(saved_theme)
        self.serial_widget.load_settings()

        # 恢复分割器
        state = settings.value("splitter/state")
        if state is not None:
            try:
                self.main_splitter.restoreState(state)
            except Exception:
                pass

    # ===================== 自动连接 =====================
    def _auto_connect_cb(self):
        if not self._auto_connect_enabled or self.data_ctrl.is_connected:
            return
        for port in serial.tools.list_ports.comports():
            if port.vid == Config.SIMULATOR_VID and port.pid == Config.SIMULATOR_PID:
                self.serial_widget.combo_port.setCurrentText(port.device)
                logger.info(f"检测到无创模拟器/测试板 ({port.device})，自动连接中...")
                self._connect()
                return

    # ===================== 串口连接/断开 =====================
    def _connect(self):
        if self.data_ctrl.is_connected:
            return
        port = self.serial_widget.combo_port.currentText()
        if not port:
            QMessageBox.warning(self, "错误", "请选择串口")
            return
        baud = int(self.serial_widget.combo_baud.currentText())
        if self.data_ctrl.connect_serial(port, baud):
            self.serial_widget.save_settings()
            self.serial_widget.set_connected_state(True)
            self.left_panel.update_button_state(connected=True)
            self.data_ctrl.start_logging()
            try:
                self._read_params_to_ctrl()
            except Exception as e:
                logger.warning(f"读取参数异常: {e}")
            self._auto_connect_enabled = True
            self.left_panel.set_view_locked(False)
            logger.debug("[UI] _connect 完成")
        else:
            self.serial_widget.set_status("连接失败", Config.COLORS['deflate_result'])

    def _disconnect(self):
        if self.data_ctrl.is_connected:
            is_running = (self.data_ctrl.test_state == 1)
            self.data_ctrl.smart_disconnect(is_running)
        self.serial_widget.set_connected_state(False)
        if self.data_ctrl.is_logging():
            self.data_ctrl.stop_logging()
        self.serial_widget.set_status("已断开", Config.COLORS['fg_secondary'])
        self.cursor_mgr.clear_all()
        self.plot_widget.reset_view()
        self._auto_connect_enabled = False
        self.left_panel.set_view_locked(False)
        self.left_panel.update_button_state(connected=False)
        self.left_panel.update_pressure(None)
        logger.info("已断开连接，自动连接已暂停")

    # ===================== 参数读取 =====================
    def _read_params_to_ctrl(self):
        try:
            start = float(self.left_panel.inflate_start.text())
            mid = float(self.left_panel.inflate_mid.text())
            target = float(self.left_panel.inflate_target.text())
            if not self.data_ctrl.update_inflate_params(start, mid, target):
                logger.warning("充气参数不满足: 起始 < 中间 < 目标，请检查")
        except ValueError:
            logger.warning("充气参数含有非法数字，请检查输入")

    def _on_param_change(self, test_key: str):
        if self.data_ctrl.test_state == 1:  # RUNNING
            logger.warning("测试进行中，禁止修改参数")
            return
        try:
            if test_key == "inflate":
                start = float(self.left_panel.inflate_start.text())
                mid = float(self.left_panel.inflate_mid.text())
                target = float(self.left_panel.inflate_target.text())
                if self.data_ctrl.update_inflate_params(start, mid, target):
                    logger.info(f"充气参数已更新: {start}→{mid}→{target}")
                else:
                    logger.warning("充气参数不合法（必须 起始<中间<目标）")
            else:
                start = float(self.left_panel.deflate_start.text())
                mid = float(self.left_panel.deflate_mid.text())
                target = float(self.left_panel.deflate_target.text())
                if self.data_ctrl.update_deflate_params(start, mid, target):
                    logger.info(f"泄气参数已更新: {start}→{mid}→{target}")
                else:
                    logger.warning("泄气参数不合法（必须 起始>中间>目标）")
        except ValueError:
            logger.warning("参数含有非法数字，请检查输入")

    # ===================== 测试控制 =====================
    def _on_start(self):
        if not self.data_ctrl.is_connected:
            logger.warning("请先连接串口")
            return
        if self.data_ctrl.test_state == 1:
            logger.warning("测试正在进行中，请勿重复开始")
            return
        self._read_params_to_ctrl()
        self.data_ctrl.reset_all()
        if self.data_ctrl.send_command("AT#AG"):
            self.data_ctrl.test_state = 1
            self.left_panel.update_button_state(connected=True, running=True)
            self.serial_widget.set_status("测量中...", Config.COLORS['log_yellow'])
            logger.cmd("发送命令: AT#AG")
            self._update_plot_button_state()
        else:
            logger.error("AT#AG 发送失败")

    def _on_stop(self):
        if self.data_ctrl.test_state != 1:
            logger.info("测试未开始或已结束")
            return
        if self.data_ctrl.send_command("AT#AH"):
            self.data_ctrl.test_state = 2
            self.left_panel.update_button_state(connected=True, running=False)
            self.serial_widget.set_status("测试结束", Config.COLORS['log_blue'])
            logger.cmd("发送命令: AT#AH")
            phase = self.data_ctrl.test_manager.get_stage()
            if phase == TestPhase.INFLATING:
                self.data_ctrl.test_manager.force_complete_inflate()
            elif phase == TestPhase.DEFLATING:
                self.data_ctrl.test_manager.force_complete_deflate()
        else:
            logger.error("AT#AH 发送失败")

    # ===================== PC 模式 =====================
    def _toggle_pc_mode(self):
        if not self.data_ctrl.is_connected:
            logger.warning("请先连接串口")
            return
        if self.data_ctrl.is_pc_mode:
            if self.data_ctrl.exit_pc_mode():
                self.left_panel.update_pc_mode(False)
                logger.info("退出PC界面成功")
        else:
            if self.data_ctrl.enter_pc_mode():
                self.left_panel.update_pc_mode(True)
                logger.success("进入PC界面成功")

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
                self.left_panel.update_pc_mode(True)
                import time
                time.sleep(0.2)
        cmd = bytes(Config.BINARY_COMMANDS["pressure_test"])
        if self.data_ctrl.send_bytes_command(cmd):
            logger.cmd("发送压力表测试命令")
            self._clear_screen()
        else:
            logger.error("发送压力表测试命令失败")

    # ===================== 绘图控制 =====================
    def _toggle_plot_pause(self):
        self.data_ctrl.toggle_plot_pause()
        self._update_plot_button_state()

    def _update_plot_button_state(self):
        if self.data_ctrl.plot_paused:
            self.left_panel.btn_toggle_plot.setText("恢复绘图")
        else:
            self.left_panel.btn_toggle_plot.setText("暂停绘图")

    def _toggle_rate_curve(self, checked):
        self.plot_widget.set_rate_visible(checked)
        self.serial_widget.btn_toggle_rate.setText("速率曲线：开" if checked else "速率曲线：关")

    def _toggle_view_lock(self):
        self.plot_widget.toggle_view_lock()
        self.left_panel.set_view_locked(self.plot_widget.view_locked)

    # ===================== 数据回调 =====================
    @Slot(list, list)
    def _on_plot_update(self, x_data, y_data):
        logger.debug(f"[UI] _on_plot_update 收到 {len(x_data)} 个数据点")
        self.plot_widget.update_plot(x_data, y_data)
        self._update_plot_button_state()

        if y_data:
            pressure = y_data[-1]
            if pressure >= 0:
                self.left_panel.update_pressure(pressure)
            else:
                self.left_panel.update_pressure(None)
        else:
            self.left_panel.update_pressure(None)

    @Slot(dict)
    def _on_result_text(self, result: dict):
        key = result.get('key')
        text = result.get('text')
        self.left_panel.update_result(key, text)

    @Slot(float)
    def _on_rate_update(self, rate: float):
        if math.isinf(rate) or math.isnan(rate) or rate > Config.MAX_RATE_LIMIT:
            display = ">2000"
        else:
            display = f"{rate:.2f}"
        self.left_panel.update_rate(display)

        x_data, y_data = self.data_ctrl.get_data()
        if y_data:
            pressure = y_data[-1]
            if pressure >= 0:
                self.left_panel.update_pressure(pressure)
            else:
                self.left_panel.update_pressure(None)

    # ===================== 文件操作 =====================
    def _save_image(self):
        self.plot_widget.save_image(self)

    def _save_csv(self):
        x, y = self.data_ctrl.get_data()
        if not x:
            QMessageBox.warning(self, "警告", "没有数据")
            return
        fn, _ = QFileDialog.getSaveFileName(self, "保存CSV", "", "CSV (*.csv)")
        if fn:
            try:
                self.data_ctrl.save_data_to_csv(fn)
                logger.success(f"CSV已保存至 {fn}")
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def _load_waveform(self):
        fn, _ = QFileDialog.getOpenFileName(self, "加载波形", "", "CSV (*.csv)")
        if fn:
            try:
                self.data_ctrl.load_data_from_csv(fn)
                self.data_ctrl.test_state = 0
                self.left_panel.update_button_state(connected=self.data_ctrl.is_connected, running=False)
                self.serial_widget.set_status("离线查看", Config.COLORS['log_blue'])
                logger.success(f"已加载波形: {os.path.basename(fn)}")
                self._update_plot_button_state()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    # ===================== 清屏 =====================
    def _clear_screen(self):
        self.data_ctrl.reset_all()
        self.plot_widget.clear()
        self.cursor_mgr.clear_all()
        self.left_panel.clear_results()
        self.plot_widget.reset_view()
        self.left_panel.update_button_state(connected=self.data_ctrl.is_connected, running=False)
        self._update_plot_button_state()
        logger.info("数据已清空，波形已清屏（时间轴已归零）")
        self.left_panel.update_pressure(None)

    # ===================== 光标测量 =====================
    def _toggle_cursor(self, enabled):
        if enabled:
            self.cursor_mgr.enable()
        else:
            self.cursor_mgr.disable()
        self.left_panel.set_cursor_state(enabled)

    # ===================== 关闭事件 =====================
    def closeEvent(self, event):
        try:
            self.cursor_mgr.clear_all()
            if self.data_ctrl.is_connected:
                is_running = (self.data_ctrl.test_state == 1)
                self.data_ctrl.smart_disconnect(is_running)
        except Exception as e:
            logger.error(f"closeEvent 异常: {e}")
        # 保存分割器状态
        settings = QSettings("YourCompany", "PressureTest")
        try:
            settings.setValue("splitter/state", self.main_splitter.saveState())
        except Exception:
            pass
        event.accept()