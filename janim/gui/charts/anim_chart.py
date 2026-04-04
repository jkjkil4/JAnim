from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter

from janim.anims.animation import Animation
from janim.gui.charts.base import ChartWidgetBase, make_ticks


class AnimChartWidget(ChartWidgetBase):
    left_margin = 42
    right_margin = 30
    top_margin = 18
    bottom_margin = 30

    point_color = QColor(85, 193, 167)

    def __init__(self, anim: Animation, fps: int, parent=None):
        """初始化动画图表并预采样 alpha 曲线"""
        super().__init__(parent)
        self.setMinimumSize(250, 200)
        self.anim = anim
        self.fps = fps

        self.count = max(2, min(500, max(2, int(anim.t_range.duration * fps))))
        self.times = np.linspace(anim.t_range.at, anim.t_range.end, self.count)
        self.values = np.array([anim.get_alpha_on_global_t(time) for time in self.times], dtype=float)

    def paint_chart(self, p: QPainter, plot_rect: QRectF) -> None:
        """绘制缓动函数 alpha 散点图"""
        x_tick_count = max(2, min(6, int(math.ceil(self.anim.t_range.duration)) + 1))
        x_ticks = make_ticks(self.anim.t_range.at, self.anim.t_range.end, x_tick_count)
        y_ticks = [0, 0.25, 0.5, 0.75, 1]

        self.draw_axes(
            p,
            plot_rect,
            x_ticks,
            y_ticks,
            (self.anim.t_range.at, self.anim.t_range.end),
            (0, 1),
            bottom_title='Timeline Progress',
        )

        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.point_color)

        for time, value in zip(self.times, self.values):
            x = self.value_to_x(float(time), self.anim.t_range.at, self.anim.t_range.end, plot_rect)
            y = self.value_to_y(float(value), 0, 1, plot_rect)
            p.drawEllipse(QPointF(x, y), 1.5, 1.5)

        p.restore()
