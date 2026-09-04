# ui/cursor_manager.py
"""光标测量管理 — 两组独立光标（C1/C2, B1/B2）"""
import math
import logging
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import pyqtgraph as pg
from config import Config

logger = logging.getLogger("DVPTest")

class CursorManager:
    def __init__(self, plot_widget):
        self.plot = plot_widget
        self.enabled = False
        self.items = []

        self.groups = {
            'group1': {'colors': ['#34c759', '#ff3b30'], 'labels': ['C1', 'C2']},
            'group2': {'colors': ['#a371f7', '#3fb9b9'], 'labels': ['B1', 'B2']}
        }
        self.group1_measure = None
        self.group2_measure = None

        self.plot.widget.scene().sigMouseClicked.connect(self._on_click)

    def enable(self):
        self.enabled = True
        self.plot.widget.setCursor(Qt.CrossCursor)
        logger.info("光标测量已启用（C1/C2一组，B1/B2一组，各独立测量）")

    def disable(self):
        self.enabled = False
        self.plot.widget.setCursor(Qt.ArrowCursor)
        self.clear_all()
        logger.info("光标测量已关闭")

    def _on_click(self, event):
        if not self.enabled:
            return
        pos = event.scenePos()
        if not self.plot.widget.sceneBoundingRect().contains(pos):
            return
        vb = self.plot.widget.getViewBox()
        data_pos = vb.mapSceneToView(pos)
        x, y = data_pos.x(), data_pos.y()

        if len(self.items) >= 4:
            self.clear_all()

        idx = len(self.items)
        if idx < 2:
            color = self.groups['group1']['colors'][idx]
            label = self.groups['group1']['labels'][idx]
        else:
            color = self.groups['group2']['colors'][idx - 2]
            label = self.groups['group2']['labels'][idx - 2]

        self._add_cursor(x, y, color, label)
        self._update_measurements()

    def _add_cursor(self, x, y, color, label):
        pen_color = pg.mkColor(color)
        pen_color.setAlpha(150)
        pen = pg.mkPen(pen_color, width=1.2, style=Qt.DashLine)
        pen.setDashPattern([6, 6])

        v_line = pg.InfiniteLine(pos=x, angle=90, movable=True, pen=pen)
        h_line = pg.InfiniteLine(pos=y, angle=0, movable=True, pen=pen)
        dot = pg.ScatterPlotItem([x], [y], pen=pg.mkPen(color, width=1.2),
                                brush=pg.mkBrush(color), size=9)
        text = pg.TextItem(f"{label} ({x:.2f}, {y:.2f})", color=color, anchor=(0, 1))
        text.setPos(x, y)
        text.setFont(QFont("Consolas", 10))

        self.plot.widget.addItem(v_line)
        self.plot.widget.addItem(h_line)
        self.plot.widget.addItem(dot)
        self.plot.widget.addItem(text)

        item = {'v': v_line, 'h': h_line, 'dot': dot, 'text': text, 'x': x, 'y': y}
        self.items.append(item)
        v_line.sigPositionChanged.connect(self._on_moved)
        h_line.sigPositionChanged.connect(self._on_moved)
        logger.info(f"光标 {label} 已添加 (x={x:.2f}, y={y:.2f})")

    def _on_moved(self):
        self._update_measurements()

    def _update_measurements(self):
        for i, item in enumerate(self.items):
            x = item['v'].value()
            y = item['h'].value()
            label = self.groups['group1']['labels'][i] if i < 2 else self.groups['group2']['labels'][i-2]
            item['text'].setText(f"{label} ({x:.2f}, {y:.2f})")
            item['text'].setPos(x, y)
            item['dot'].setData([x], [y])

        if len(self.items) >= 2:
            self._calc_group(0, 1, 'group1')
        else:
            self._remove_measure_item('group1')

        if len(self.items) >= 4:
            self._calc_group(2, 3, 'group2')
        else:
            self._remove_measure_item('group2')

    def _calc_group(self, idx1, idx2, group_name):
        item1, item2 = self.items[idx1], self.items[idx2]
        x1, y1 = item1['v'].value(), item1['h'].value()
        x2, y2 = item2['v'].value(), item2['h'].value()

        dt = abs(x2 - x1)
        dp = abs(y2 - y1)
        rate = dp / dt if dt > 1e-9 else 0.0
        rate = min(rate, Config.MAX_RATE_LIMIT)

        text = (f'<span style="color:{Config.COLORS["fg_text"]};">Δt = {dt:.3f}s<br>'
                f'ΔP = {dp:.1f}mmHg<br>速率 = {rate:.2f}mmHg/s</span>')

        if group_name == 'group1':
            if self.group1_measure is None:
                self.group1_measure = pg.TextItem("", color=Config.COLORS['fg_text'], anchor=(0, 1))
                self.group1_measure.setFont(QFont("Consolas", 10))
                self.plot.widget.addItem(self.group1_measure)
            self.group1_measure.setPos(x2 + 1, y2 + 25)
            self.group1_measure.setHtml(text)
            # 更新左侧速率显示
            if self.plot.parent() and hasattr(self.plot.parent(), 'left_panel'):
                self.plot.parent().left_panel.update_rate(f"{rate:.2f}")
        else:
            if self.group2_measure is None:
                self.group2_measure = pg.TextItem("", color=Config.COLORS['fg_text'], anchor=(1, 1))
                self.group2_measure.setFont(QFont("Consolas", 10))
                self.plot.widget.addItem(self.group2_measure)
            self.group2_measure.setPos(x2 - 1, y2 + 15)
            self.group2_measure.setHtml(text)

    def _remove_measure_item(self, group_name):
        attr = 'group1_measure' if group_name == 'group1' else 'group2_measure'
        if getattr(self, attr) is not None:
            self.plot.widget.removeItem(getattr(self, attr))
            setattr(self, attr, None)

    def clear_all(self):
        for item in self.items:
            self.plot.widget.removeItem(item['v'])
            self.plot.widget.removeItem(item['h'])
            self.plot.widget.removeItem(item['dot'])
            self.plot.widget.removeItem(item['text'])
        self.items.clear()
        self._remove_measure_item('group1')
        self._remove_measure_item('group2')
        # 重置左侧速率显示
        if self.plot.parent() and hasattr(self.plot.parent(), 'left_panel'):
            self.plot.parent().left_panel.update_rate("--")