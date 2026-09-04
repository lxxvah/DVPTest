# ui/theme_manager.py
"""主题管理 — 切换浅色/深色，刷新全局样式"""
import logging
from PySide6.QtCore import QSettings
from config import Config

logger = logging.getLogger("DVPTest")

class ThemeManager:
    def __init__(self):
        self.current_theme = 'light'
        self._main_window = None

    def attach(self, main_window):
        """绑定主窗口"""
        self._main_window = main_window

    def apply_theme(self, theme: str):
        """应用指定主题"""
        Config.update_colors(theme)
        self.current_theme = theme

        if self._main_window:
            # 刷新全局样式表
            self._main_window.setStyleSheet(Config.get_stylesheet())
            # 刷新各个子模块
            self._refresh_children()

        logger.info(f"主题切换为: {theme}")

    def toggle(self):
        """切换主题"""
        new_theme = 'dark' if self.current_theme == 'light' else 'light'
        self.apply_theme(new_theme)
        settings = QSettings("YourCompany", "PressureTest")
        settings.setValue("theme", new_theme)
        # 更新主题按钮文字
        if self._main_window and hasattr(self._main_window, 'left_panel'):
            self._main_window.left_panel.btn_theme.setText(
                "☀️ 浅色" if new_theme == 'dark' else "🌙 深色"
            )
        return new_theme

    def _refresh_children(self):
        """刷新所有子模块的颜色"""
        mw = self._main_window
        if not mw:
            return

        # 刷新绘图
        if hasattr(mw, 'plot_widget'):
            mw.plot_widget.refresh_theme()

        # 刷新左侧面板
        if hasattr(mw, 'left_panel'):
            mw.left_panel.refresh_theme()

        # 刷新串口工具栏状态标签
        if hasattr(mw, 'serial_widget'):
            mw.serial_widget.refresh_theme()