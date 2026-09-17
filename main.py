# main.py
"""程序入口"""
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen, QBrush, QColor, QPolygonF
from PySide6.QtCore import Qt, QPointF, QRectF

from logger import setup_logging
setup_logging()

from ui_main import MainWindow
from ui_components import apply_theme


def _draw_valve_icon(size: int = 64) -> QIcon:
    """用 QPainter 直接画阀门图标，不依赖外部文件"""
    LINE = QColor("#2c3440")   # 深色外框
    TEAL = QColor("#00d4aa")   # 亮青绿主色
    BG   = QColor("#ffffff")   # 白底

    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)

    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)

    # 坐标缩放：按 64 设计，实际尺寸自适应
    s = size / 64.0
    p.scale(s, s)

    # 白底圆角矩形
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(BG))
    p.drawRoundedRect(QRectF(0, 0, 64, 64), 10, 10)

    # 外框
    pen = QPen(LINE, 4)
    pen.setJoinStyle(Qt.MiterJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(6, 6, 52, 52), 8, 8)

    # 水平气路管道
    p.drawLine(QPointF(10, 32), QPointF(54, 32))

    # 阀芯外圈
    p.drawEllipse(QPointF(32, 32), 10, 10)

    # 阀芯内芯
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(TEAL))
    p.drawEllipse(QPointF(32, 32), 8, 8)

    # 左侧充气口
    p.drawEllipse(QRectF(11, 28, 8, 8))

    # 右侧泄气箭头
    p.drawLine(QPointF(44, 32), QPointF(59, 32))
    arrow = QPolygonF([
        QPointF(59, 32),
        QPointF(53, 26),
        QPointF(53, 38),
    ])
    p.drawPolygon(arrow)

    p.end()
    return QIcon(pm)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_theme(app)

    icon = _draw_valve_icon(64)
    app.setWindowIcon(icon)

    window = MainWindow()
    window.setWindowIcon(icon)
    window.show()
    sys.exit(app.exec())