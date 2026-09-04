# main.py
"""程序入口"""
import sys
from PySide6.QtWidgets import QApplication

from logger import setup_logging
setup_logging()

from ui_main import MainWindow
from ui_components import apply_theme

if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_theme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())