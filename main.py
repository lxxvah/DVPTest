# main.py
"""程序入口"""
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from logger import setup_logging
setup_logging()

from ui_main import MainWindow
from config import Config

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 全局样式表用于非按钮控件（QLineEdit、QGroupBox等）
    app.setStyleSheet(Config.STYLESHEET)
    app.setFont(QFont("Segoe UI", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())