"""
在 ``janim/gui/charts`` 中定义了若干自定义绘制的图表类

不使用 ``PySide6.QtCharts`` 的原因：

``PySide6`` 包分为两大部分：``PySide6-Essentials`` 和 ``PySide6-Addons`` ， ``janim`` 用到的其它 ``PySide6`` 的功能都包含在 ``Essentials`` 中，
如果只是为了 ``QtCharts`` 而引入 ``Addons`` 这么巨大的包太不划算了
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QWidget


def format_number(value: float) -> str:
    """将数值格式化为紧凑字符串，用于坐标轴标签"""
    rounded = round(value)
    if math.isclose(value, rounded, abs_tol=1e-9):
        return str(int(rounded))
    return f'{value:.2f}'.rstrip('0').rstrip('.')


def make_ticks(begin: float, end: float, count: int) -> list[float]:
    """在给定区间内生成等间距刻度值"""
    if count <= 1 or math.isclose(begin, end):
        return [begin]
    if count == 2:
        return [begin, end]
    step = (end - begin) / (count - 1)
    return [begin + step * index for index in range(count)]


class ChartWidgetBase(QWidget):
    left_margin = 48
    right_margin = 12
    top_margin = 28
    bottom_margin = 34

    background_color = QColor(250, 250, 250)
    border_color = QColor(165, 165, 165)
    grid_color = QColor(232, 232, 232)
    axis_color = QColor(120, 120, 120)
    label_color = QColor(70, 70, 70)

    def __init__(self, parent: QWidget | None = None):
        """初始化图表基类并统一设置字体大小。"""
        super().__init__(parent)
        font = self.font()
        font.setPointSize(7)
        self.setFont(font)

    def content_rect(self) -> QRectF:
        """返回扣除四周边距，即图表内容的绘制区域"""
        rect = self.rect().adjusted(
            self.left_margin,
            self.top_margin,
            -self.right_margin,
            -self.bottom_margin,
        )
        return QRectF(rect)

    def paintEvent(self, _: object) -> None:
        """设置绘制参数，并调用子类绘制逻辑"""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        p.fillRect(self.rect(), self.background_color)

        self.paint_chart(p, self.content_rect())

    def paint_chart(self, p: QPainter, plot_rect: QRectF) -> None:
        """子类绘制逻辑"""
        raise NotImplementedError()

    def draw_frame(self, p: QPainter, plot_rect: QRectF) -> None:
        """绘制图表边框"""
        p.setPen(QPen(self.border_color, 1))
        p.drawRect(plot_rect)

    def value_to_x(self, value: float, begin: float, end: float, plot_rect: QRectF) -> float:
        """将数据值映射为横坐标像素"""
        if math.isclose(begin, end):
            return plot_rect.left()
        return plot_rect.left() + (value - begin) / (end - begin) * plot_rect.width()

    def value_to_y(self, value: float, begin: float, end: float, plot_rect: QRectF) -> float:
        """将数据值映射为纵坐标像素（向上增大）"""
        if math.isclose(begin, end):
            return plot_rect.bottom()
        return plot_rect.bottom() - (value - begin) / (end - begin) * plot_rect.height()

    def draw_grid(
        self,
        p: QPainter,
        plot_rect: QRectF,
        x_ticks: list[float],
        y_ticks: list[float],
        x_range: tuple[float, float],
        y_range: tuple[float, float]
    ) -> None:
        """绘制网格线"""
        p.save()
        p.setPen(QPen(self.grid_color, 1))

        x_begin, x_end = x_range
        y_begin, y_end = y_range

        for value in x_ticks:
            x = self.value_to_x(value, x_begin, x_end, plot_rect)
            p.drawLine(QPointF(x, plot_rect.top()), QPointF(x, plot_rect.bottom()))

        for value in y_ticks:
            y = self.value_to_y(value, y_begin, y_end, plot_rect)
            p.drawLine(QPointF(plot_rect.left(), y), QPointF(plot_rect.right(), y))

        p.restore()

    def draw_axes(
        self, p: QPainter, plot_rect: QRectF,
        x_ticks: list[float], y_ticks: list[float],
        x_range: tuple[float, float], y_range: tuple[float, float],
        *,
        bottom_title: str | None = None,
        top_title: str | None = None,
        top_ticks: list[float] | None = None,
        top_range: tuple[float, float] | None = None
    ) -> None:
        """绘制坐标轴、刻度与标题文字"""
        self.draw_frame(p, plot_rect)
        self.draw_grid(p, plot_rect, x_ticks, y_ticks, x_range, y_range)

        p.save()
        p.setPen(QPen(self.axis_color, 1))
        font_metrics = QFontMetrics(self.font())

        # bottom axis
        bottom_label_top = int(plot_rect.bottom()) + 2
        bottom_label_height = self.bottom_margin - 6
        for value in x_ticks:
            x = self.value_to_x(value, *x_range, plot_rect)
            p.drawLine(QPointF(x, plot_rect.bottom()), QPointF(x, plot_rect.bottom() + 4))
            label_rect = QRectF(x - 20, bottom_label_top, 40, bottom_label_height)
            p.setPen(self.label_color)
            p.drawText(
                label_rect,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                format_number(value),
            )
            p.setPen(QPen(self.axis_color, 1))

        if bottom_title:
            title_rect = QRectF(plot_rect.left(), plot_rect.bottom() + 14, plot_rect.width(), 14)
            p.setPen(self.label_color)
            p.drawText(title_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, bottom_title)
            p.setPen(QPen(self.axis_color, 1))

        # top axis
        if top_ticks is not None and top_range is not None:
            top_label_bottom = int(plot_rect.top()) - 2
            top_label_height = self.top_margin - 6
            for value in top_ticks:
                x = self.value_to_x(value, *top_range, plot_rect)
                p.drawLine(QPointF(x, plot_rect.top()), QPointF(x, plot_rect.top() - 4))
                label_rect = QRectF(x - 20, top_label_bottom - top_label_height, 40, top_label_height)
                p.setPen(self.label_color)
                p.drawText(
                    label_rect,
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                    format_number(value),
                )
                p.setPen(QPen(self.axis_color, 1))

        if top_title:
            title_rect = QRectF(plot_rect.left(), 5, plot_rect.width(), 14)
            p.setPen(self.label_color)
            p.drawText(title_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, top_title)
            p.setPen(QPen(self.axis_color, 1))

        # left axis
        left_label_width = self.left_margin - 6
        for value in y_ticks:
            y = self.value_to_y(value, *y_range, plot_rect)
            p.drawLine(QPointF(plot_rect.left() - 4, y), QPointF(plot_rect.left(), y))
            label_rect = QRectF(2, y - font_metrics.height() / 2 - 1, left_label_width, font_metrics.height() + 2)
            p.setPen(self.label_color)
            p.drawText(
                label_rect,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                format_number(value),
            )
            p.setPen(QPen(self.axis_color, 1))

        p.restore()
