# ui/plot_widget.py
"""绘图区域 — 压力曲线 + 速率曲线"""
import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFileDialog, QMessageBox
from config import Config
from result_calculator import ResultCalculator

class PlotWidget(QWidget):
    sig_view_lock_changed = Signal(bool)

    def __init__(self, data_ctrl, parent=None):
        super().__init__(parent)
        self.setObjectName("plot_widget")
        self.data_ctrl = data_ctrl
        self.rate_visible = True
        self.view_locked = False
        self.measure_text_item = None
        self._setup_plot()
        self.widget.installEventFilter(self)

    def _setup_plot(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.widget = pg.PlotWidget()
        self.widget.setBackground(Config.COLORS['bg_chart'])
        self.widget.showGrid(x=True, y=True, alpha=0.15)
        self.widget.setLabel('bottom', '时间', units='s', color=Config.COLORS['fg_secondary'])
        self.widget.setLabel('left', '压力', units='mmHg', color=Config.COLORS['fg_highlight'])
        self.widget.setTitle('实时压力曲线', color=Config.COLORS['fg_text'], size='14pt')

        # 左轴
        left_axis = self.widget.getAxis('left')
        left_axis.setPen(pg.mkPen(Config.COLORS['border']))
        left_axis.setTextPen(pg.mkPen(Config.COLORS['fg_secondary']))

        # ViewBox
        self.viewbox = self.widget.getViewBox()
        self.viewbox.setRange(xRange=(0, 60), yRange=(0, 350))
        self.viewbox.setBackgroundColor(Config.COLORS['bg_chart'])

        # 压力曲线
        pen = pg.mkPen(Config.COLORS['pressure_curve'], width=2.5)
        self.curve_pressure = pg.PlotDataItem([], [], pen=pen, downsample=100,
                                              downsampleMethod='peak', autoDownsample=True)
        self.widget.addItem(self.curve_pressure)

        # 右轴（速率）
        self.widget.showAxis('right')
        self.right_axis = self.widget.getAxis('right')
        self.right_axis.setLabel('速率', units='mmHg/s', color=Config.COLORS['rate_curve'])
        self.right_axis.setPen(pg.mkPen(Config.COLORS['border']))
        self.right_axis.setTextPen(pg.mkPen(Config.COLORS['fg_secondary']))
        self.right_axis.setRange(0, 50)

        # 速率曲线
        pen_rate = pg.mkPen(Config.COLORS['rate_curve'], width=2.5)
        self.curve_rate = self.widget.plot([], [], pen=pen_rate, yAxis='right')

        layout.addWidget(self.widget)

    def update_plot(self, x_data, y_data):
        if not x_data:
            return
        self.curve_pressure.setData(x_data, y_data)

        rate = ResultCalculator.compute_rate_curve(np.array(x_data), np.array(y_data))
        self.curve_rate.setData(x_data, rate)
        self.curve_rate.setVisible(self.rate_visible)

        if not self.view_locked:
            max_time = max(x_data) + 2
            if max_time < 10:
                max_time = 10
            self.viewbox.setRange(xRange=(0, max_time))
            ymin = min(0, min(y_data) - 10)
            ymax = max(350, max(y_data) + 10)
            self.viewbox.setRange(yRange=(ymin, ymax))
            self._update_rate_axis(rate)

    def _update_rate_axis(self, rate):
        if len(rate) == 0:
            return
        peak = max(rate)
        rmax = max(25, peak + 5)
        step = 2 if rmax <= 50 else 5
        max_tick = int(np.ceil(rmax / step)) * step
        tick_values = np.arange(0, max_tick + step/2, step)
        ticks = [(v, str(int(v)) if step >= 1 else f"{v:.1f}") for v in tick_values]
        if len(ticks) > 15:
            step *= 2
            max_tick = int(np.ceil(rmax / step)) * step
            tick_values = np.arange(0, max_tick + step/2, step)
            ticks = [(v, str(int(v)) if step >= 1 else f"{v:.1f}") for v in tick_values]
        self.right_axis.setTicks([ticks])
        self.right_axis.setRange(0, rmax)

    def set_rate_visible(self, visible):
        self.rate_visible = visible
        self.curve_rate.setVisible(visible)

    def toggle_view_lock(self):
        self.view_locked = not self.view_locked
        self.sig_view_lock_changed.emit(self.view_locked)
        return self.view_locked

    def refresh_theme(self):
        """主题切换时刷新颜色"""
        self.widget.setBackground(Config.COLORS['bg_chart'])
        self.viewbox.setBackgroundColor(Config.COLORS['bg_chart'])
        self.widget.getAxis('left').setPen(pg.mkPen(Config.COLORS['border']))
        self.widget.getAxis('left').setTextPen(pg.mkPen(Config.COLORS['fg_secondary']))
        self.right_axis.setPen(pg.mkPen(Config.COLORS['border']))
        self.right_axis.setTextPen(pg.mkPen(Config.COLORS['fg_secondary']))
        self.curve_pressure.setPen(pg.mkPen(Config.COLORS['pressure_curve'], width=2.5))
        self.curve_rate.setPen(pg.mkPen(Config.COLORS['rate_curve'], width=2.5))

    def clear(self):
        self.curve_pressure.setData([], [])
        self.curve_rate.setData([], [])

    def reset_view(self):
        self.viewbox.setRange(xRange=(0, 60), yRange=(0, 350))
        self.right_axis.setRange(0, 50)
        self.view_locked = False

    def getViewBox(self):
        return self.viewbox

    def save_image(self, parent):
        fn, _ = QFileDialog.getSaveFileName(parent, "保存图片", "", "PNG (*.png);;JPEG (*.jpg)")
        if fn:
            pixmap = self.widget.grab()
            if not pixmap.isNull():
                pixmap.save(fn)
                logger.success(f"图片已保存至 {fn}")

    def eventFilter(self, obj, event):
        # Ctrl+滚轮横向缩放，Shift+滚轮纵向缩放
        if event.type() == event.Type.Wheel and obj is self.widget:
            delta = event.angleDelta().y()
            if delta == 0:
                return False
            xr = self.viewbox.viewRange()[0]
            yr = self.viewbox.viewRange()[1]
            cx = (xr[0] + xr[1]) / 2
            cy = (yr[0] + yr[1]) / 2
            scale = 1.1 if delta > 0 else 1 / 1.1
            if event.modifiers() & Qt.ControlModifier:
                new_x = (cx - (cx - xr[0]) * scale, cx + (xr[1] - cx) * scale)
                self.viewbox.setRange(xRange=new_x, yRange=yr, padding=0)
                return True
            elif event.modifiers() & Qt.ShiftModifier:
                new_y = (cy - (cy - yr[0]) * scale, cy + (yr[1] - cy) * scale)
                self.viewbox.setRange(xRange=xr, yRange=new_y, padding=0)
                return True
        return super().eventFilter(obj, event)