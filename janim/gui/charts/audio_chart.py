from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen

from janim.anims.timeline import Timeline
from janim.gui.charts.base import ChartWidgetBase, make_ticks
from janim.locale import get_translator
from janim.utils.bezier import interpolate

_ = get_translator('janim.gui.charts.audio_chart')


class AudioChartWidget(ChartWidgetBase):
    left_margin = 48
    right_margin = 30
    top_margin = 34
    bottom_margin = 34

    waveform_color = QColor(85, 193, 167)
    fade_color = QColor(41, 171, 202)

    def __init__(self, info: Timeline.PlayAudioInfo, fps: int, near: float | None = None,
                 parent=None):
        """初始化音频图表并预计算显示区间与采样数据"""
        super().__init__(parent)
        self.setMinimumSize(350, 270)

        self.info = info
        self.fps = fps
        self.near = near

        self.clip_begin = info.clip_range.at
        self.clip_end = info.clip_range.end
        if near is not None:
            self.clip_begin = max(self.clip_begin, near + info.clip_range.at - 4)
            self.clip_end = min(self.clip_end, near + info.clip_range.at + 4)

        self.range_begin = info.range.at + (self.clip_begin - info.clip_range.at)
        self.range_end = self.range_begin + (self.clip_end - self.clip_begin)

        self.samples, self.times = self.prepare_samples()

    def prepare_samples(self) -> tuple[np.ndarray, np.ndarray]:
        """采样音频图数据"""
        audio = self.info.audio

        begin = int(self.clip_begin * audio.framerate)
        end = int(self.clip_end * audio.framerate)

        left_blank = max(0, -begin)
        right_blank = max(0, end - audio.sample_count())

        data = audio._samples.data[max(0, begin): min(end, audio.sample_count())]
        if data.ndim > 1:
            data = np.max(data, axis=1)

        if left_blank != 0 or right_blank != 0:
            data = np.concatenate([
                np.zeros(left_blank, dtype=np.int16),
                data,
                np.zeros(right_blank, dtype=np.int16),
            ])

        unit = max(1, audio.framerate // self.fps)
        usable = len(data) // unit * unit

        if usable == 0:
            samples = np.array([], dtype=float)
        else:
            samples = np.max(
                np.abs(
                    data[:usable].reshape(-1, unit)
                ),
                axis=1
            ) / np.iinfo(np.int16).max

        if len(samples) == 0:
            times = np.array([], dtype=float)
        else:
            times = np.linspace(self.range_begin, self.range_end, len(samples))

        return samples, times

    def paint_chart(self, p: QPainter, plot_rect: QRectF) -> None:
        """绘制音频图表坐标轴、渐变提示和波形线"""
        x_tick_count = max(2, 1 + int(math.ceil(self.range_end - self.range_begin)))
        x_ticks = make_ticks(self.range_begin, self.range_end, x_tick_count)
        top_ticks = make_ticks(self.clip_begin, self.clip_end, len(x_ticks))
        y_ticks = [0, 0.25, 0.5, 0.75, 1]

        self.draw_axes(
            p,
            plot_rect,
            x_ticks,
            y_ticks,
            (self.range_begin, self.range_end),
            (0, 1),
            bottom_title=_('Timeline Progress'),
            top_title=_('Audio Progress'),
            top_ticks=top_ticks,
            top_range=(self.clip_begin, self.clip_end),
        )

        p.save()

        if self.clip_begin != self.info.clip_range.at:
            self.draw_fade(
                p,
                plot_rect,
                self.clip_begin,
                interpolate(self.clip_begin, self.clip_end, 0.1),
                True,
            )

        if self.clip_end != self.info.clip_range.end:
            self.draw_fade(
                p,
                plot_rect,
                interpolate(self.clip_begin, self.clip_end, 0.9),
                self.clip_end,
                False,
            )

        if len(self.samples) >= 2:
            path = QPainterPath()
            points = [self.sample_point(index, plot_rect) for index in range(len(self.samples))]
            path.moveTo(points[0])
            for point in points[1:]:
                path.lineTo(point)
            p.setPen(QPen(self.waveform_color, 1.75))
            p.drawPath(path)

        p.restore()

    def draw_fade(self, p: QPainter, plot_rect: QRectF, begin: float, end: float, left: bool) -> None:
        """用于绘制左右边缘的渐变提示"""
        x1 = self.value_to_x(begin, self.clip_begin, self.clip_end, plot_rect)
        x2 = self.value_to_x(end, self.clip_begin, self.clip_end, plot_rect)
        rect = QRectF(QPointF(min(x1, x2), plot_rect.top()), QPointF(max(x1, x2), plot_rect.bottom()))
        gradient = QLinearGradient(rect.left(), 0, rect.right(), 0)
        if left:
            gradient.setColorAt(
                0.0,
                QColor(self.fade_color.red(), self.fade_color.green(), self.fade_color.blue(), 128),
            )
            gradient.setColorAt(1.0, QColor(self.fade_color.red(), self.fade_color.green(), self.fade_color.blue(), 0))
        else:
            gradient.setColorAt(0.0, QColor(self.fade_color.red(), self.fade_color.green(), self.fade_color.blue(), 0))
            gradient.setColorAt(
                1.0,
                QColor(self.fade_color.red(), self.fade_color.green(), self.fade_color.blue(), 128),
            )
        p.fillRect(rect, gradient)

    def sample_point(self, index: int, plot_rect: QRectF) -> QPointF:
        """将第 ``index`` 个采样点映射为绘制坐标"""
        x = self.value_to_x(self.times[index], self.range_begin, self.range_end, plot_rect)
        y = self.value_to_y(float(self.samples[index]), 0, 1, plot_rect)
        return QPointF(x, y)
