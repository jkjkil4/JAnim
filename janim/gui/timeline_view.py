import math
from bisect import bisect, bisect_left
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QPoint, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QBrush, QColor, QKeyEvent, QMouseEvent, QPainter,
                           QPaintEvent, QPen, QWheelEvent)
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from janim.anims.animation import Animation, TimeRange
from janim.anims.timeline import SEGMENT_DURATION, Timeline, TimelineAnim
from janim.locale.i18n import get_local_strings
from janim.utils.bezier import interpolate
from janim.utils.simple_functions import clip

if TYPE_CHECKING:
    from PySide6.QtCharts import QAreaSeries, QChartView

_ = get_local_strings('timeline_view')

TIMELINE_VIEW_MIN_DURATION = 0.5


class TimelineView(QWidget):
    '''
    窗口下方的进度条和动画区段指示器

    - **w** 键放大区段（使视野精确到一小段中）
    - **s** 键缩小区段（使视野扩展到一大段中）
    - **a** 和 **d** 左右移动区段
    '''
    @dataclass
    class LabelInfo:
        '''
        动画区段被渲染到第几行的标记
        '''
        anim: Animation
        row: int
        segment_left: int  # 为了优化性能使用的

    @dataclass
    class PixelRange:
        left: float
        width: float

        @property
        def right(self) -> float:
            return self.left + self.width

    @dataclass
    class Pressing:
        '''
        记录按键状态
        '''
        w: bool = False
        a: bool = False
        s: bool = False
        d: bool = False

    value_changed = Signal(float)
    dragged = Signal()

    space_pressed = Signal()

    # px
    audio_height = 20
    label_height = 24
    range_tip_height = 4
    play_space = 20

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self.on_hover_timer_timeout)

        self.drag_timer = QTimer(self)
        self.drag_timer.setSingleShot(True)
        self.drag_timer.timeout.connect(self.on_drag_timer_timeout)

        self.tooltip: QWidget | None = None

        self.key_timer = QTimer(self)
        self.key_timer.timeout.connect(self.on_key_timer_timeout)
        self.key_timer.start(1000 // 60)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setMinimumHeight(self.label_height + self.range_tip_height + 10)

    def set_anim(self, anim: TimelineAnim, pause_progresses: list[int]) -> None:
        self.range = TimeRange(0, min(20, anim.global_range.duration))
        self.y_offset = 0
        self.anim = anim
        self._progress = 0
        self._maximum = round(anim.global_range.end * self.anim.cfg.preview_fps)
        self.pause_progresses = pause_progresses

        self.is_pressing = TimelineView.Pressing()

        self.init_label_info()
        self.update()

    def init_label_info(self) -> None:
        '''
        计算各个动画区段应当被渲染到第几行，以叠放式进行显示
        '''
        segment_count = math.ceil(self.anim.global_range.duration / SEGMENT_DURATION) + 1
        self.labels_info_segments: list[list[TimelineView.LabelInfo]] = [[] for _ in range(segment_count)]
        self.max_row = 0

        self.flatten = self.anim.user_anim.flatten()[1:]
        self.sorted_anims = sorted(self.flatten, key=lambda x: x.global_range.at)

        stack: list[Animation] = []
        for anim in self.sorted_anims:
            # 可能会因为浮点误差导致 <= 中的相等判断错误，所以 +1e-5
            while stack and stack[-1].global_range.end <= anim.global_range.at + 1e-5:
                stack.pop()

            left = math.floor(anim.global_range.at / SEGMENT_DURATION)
            right = math.ceil(anim.global_range.end / SEGMENT_DURATION)

            info = TimelineView.LabelInfo(anim, len(stack), left)
            for idx in range(left, right):
                self.labels_info_segments[idx].append(info)

            self.max_row = max(self.max_row, len(stack))
            stack.append(anim)

    def set_range(self, at: float, duration: float) -> None:
        duration = min(duration, self.anim.global_range.duration)
        at = clip(at, 0, self.anim.global_range.duration - duration)
        self.range = TimeRange(at, duration)
        self.update()

    # region hover

    def hover_at(self, pos: QPoint) -> None:
        audio_rect = self.audio_rect
        bottom_rect = self.bottom_rect

        # 因为后出现的音频在绘制时会覆盖前面的音频，所以这里用 reversed，就会得到最上层的
        for info in reversed(self.anim.timeline.audio_infos):
            range = self.time_range_to_pixel_range(info.range)
            if QRectF(range.left, audio_rect.y(), range.width, self.audio_height).contains(pos):
                self.hover_at_audio(pos, info)
                return

        idx = math.floor(self.pixel_to_time(pos.x()) / SEGMENT_DURATION)
        if idx >= len(self.labels_info_segments):
            return

        for info in self.labels_info_segments[idx]:
            range = self.time_range_to_pixel_range(info.anim.global_range)
            if QRectF(range.left,
                      bottom_rect.y() + self.label_y(info.row),
                      range.width,
                      self.label_height).contains(pos):
                self.hover_at_anim(pos, info.anim)
                return

    def hover_at_audio(self, pos: QPoint, info: Timeline.PlayAudioInfo) -> None:
        msg_lst = [
            f'{round(info.range.at, 2)}s ~ {round(info.range.end, 2)}s',
            info.audio.file_path
        ]
        if info.clip_range != TimeRange(0, info.audio.duration()):
            msg_lst.append(_('Clip') + f': {round(info.clip_range.at, 2)}s ~ {round(info.clip_range.end, 2)}s')

        # 只有在这区间内的“建议裁剪区段”才能够被显示
        visible_clip_begin = info.clip_range.at - 4
        visible_clip_end = info.clip_range.end + 4

        recommended_ranges = list(info.audio.recommended_ranges())

        def is_visible(start: float, end: float) -> bool:
            return visible_clip_begin < start < visible_clip_end or visible_clip_begin < end < visible_clip_end

        clips = ', '.join(
            f'{math.floor(start * 10) / 10}s ~ {math.ceil(end * 10) / 10}s'
            for start, end in recommended_ranges
            if is_visible(start, end)
        )
        if clips:
            # 如果 recommended_ranges 的前（后）是被忽略了的，那么在前（后）加上省略号
            clips = ''.join([
                '' if is_visible(*recommended_ranges[0]) else '... ',
                clips,
                '' if is_visible(*recommended_ranges[-1]) else ' ...'
            ])

            # 当 clips 不太长的时候（正常情况下），就直接将其作为 msg_lst 的一部分
            # 否则将其截短（保留前25个字符和最后25个字符）后，再作为 msg_lst 的一部分
            if len(clips) < 80:
                msg_lst.append(_('Recommended clip') + f': {clips}')
            else:
                msg_lst.append(_('Recommended clip') + f': {clips[:40]} ... {clips[-40:]}')
                msg_lst.append('    ' + _('(Too many! Unable to display all ranges.)'))

        label = QLabel('\n'.join(msg_lst))
        chart_view = self.create_audio_chart(info, near=round(self.pixel_to_time(pos.x())))

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(chart_view)

        self.tooltip = QWidget()
        self.tooltip.setWindowFlag(Qt.WindowType.ToolTip)
        self.tooltip.setLayout(layout)
        self.tooltip.adjustSize()

        self.place_tooltip(self.tooltip, pos)
        self.tooltip.show()

    def create_audio_chart(self, info: Timeline.PlayAudioInfo, near: float | None = None) -> 'QChartView':
        from PySide6.QtCharts import (QChart, QChartView, QLineSeries,
                                      QValueAxis)

        audio = info.audio

        clip_begin = info.clip_range.at
        clip_end = info.clip_range.end
        if near is not None:
            clip_begin = max(clip_begin, near - info.range.at + info.clip_range.at - 4)
            clip_end = min(clip_end, near - info.range.at + info.clip_range.at + 4)

        range_begin = info.range.at + (clip_begin - info.clip_range.at)
        range_end = range_begin + (clip_end - clip_begin)

        begin = int(clip_begin * audio.framerate)
        end = int(clip_end * audio.framerate)

        left_blank = max(0, -begin)
        right_blank = max(0, end - audio.sample_count())

        data = audio._samples.data[max(0, begin): min(end, audio.sample_count())]
        if data.ndim > 1:
            data = np.max(data, axis=1)

        if left_blank != 0 or right_blank != 0:
            data = np.concatenate([
                np.zeros(left_blank, dtype=np.int16),
                data,
                np.zeros(right_blank, dtype=np.int16)
            ])

        unit = audio.framerate // self.anim.cfg.fps

        data: np.ndarray = np.max(
            np.abs(
                data[:len(data) // unit * unit].reshape(-1, unit)
            ),
            axis=1
        ) / np.iinfo(np.int16).max

        times = np.linspace(range_begin,
                            range_end,
                            len(data))

        chart = QChart()

        x_axis = QValueAxis()
        x_axis.setRange(range_begin, range_end)
        x_axis.setTickCount(max(2, 1 + int(range_end - range_begin)))
        chart.addAxis(x_axis, Qt.AlignmentFlag.AlignBottom)

        y_axis = QValueAxis()
        y_axis.setRange(0, 1)
        chart.addAxis(y_axis, Qt.AlignmentFlag.AlignLeft)

        x_clip_axis = QValueAxis()
        x_clip_axis.setRange(clip_begin, clip_end)
        chart.addAxis(x_clip_axis, Qt.AlignmentFlag.AlignBottom)

        series = QLineSeries()
        for t, y in zip(times, data):
            series.append(t, y)
        chart.addSeries(series)
        series.attachAxis(x_axis)
        series.attachAxis(y_axis)

        if clip_begin != info.clip_range.at:
            area = self.create_axvspan(clip_begin, interpolate(clip_begin, clip_end, 0.1),
                                       QColor(41, 171, 202, 128), QColor(41, 171, 202, 0))
            chart.addSeries(area)
            area.attachAxis(x_clip_axis)
            area.attachAxis(y_axis)

        if clip_end != info.clip_range.end:
            area = self.create_axvspan(interpolate(clip_begin, clip_end, 0.9), clip_end,
                                       QColor(41, 171, 202, 0), QColor(41, 171, 202, 128))
            chart.addSeries(area)
            area.attachAxis(x_clip_axis)
            area.attachAxis(y_axis)

        chart.legend().setVisible(False)

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setMinimumSize(350, 200)

        return chart_view

    @staticmethod
    def create_axvspan(x1: float, x2: float, c1: QColor, c2: QColor) -> 'QAreaSeries':
        from PySide6.QtCharts import QAreaSeries, QLineSeries
        from PySide6.QtGui import QGradient, QLinearGradient

        upper_series = QLineSeries()
        upper_series.append(x1, 1.)
        upper_series.append(x2, 1.)

        lower_series = QLineSeries()
        lower_series.append(x1, 0.)
        lower_series.append(x2, 0.)

        area = QAreaSeries(upper_series, lower_series)
        upper_series.setParent(area)
        lower_series.setParent(area)

        grandient = QLinearGradient(QPoint(0, 0), QPoint(1, 0))
        grandient.setColorAt(0.0, c1)
        grandient.setColorAt(1.0, c2)
        grandient.setCoordinateMode(QGradient.CoordinateMode.ObjectBoundingMode)
        area.setBrush(grandient)
        area.setPen(Qt.PenStyle.NoPen)

        return area

    def hover_at_anim(self, pos: QPoint, anim: Animation) -> None:
        parents = [anim]
        while True:
            last = parents[-1]
            if last.parent is None or last.parent is self.anim.user_anim:
                break
            parents.append(last.parent)

        label1 = QLabel(f'{anim.__class__.__name__} '
                        f'{round(anim.global_range.at, 2)}s ~ {round(anim.global_range.end, 2)}s')
        chart_view = self.create_anim_chart(anim)

        def getname(rate_func) -> str:
            try:
                return rate_func.__name__
            except AttributeError:
                return '[unknown]'

        label2 = QLabel(
            '\n↑\n'.join(
                f'{getname(anim.rate_func)} ({anim.__class__.__name__})'
                for anim in parents
            )
        )

        layout = QVBoxLayout()
        layout.addWidget(label1)
        layout.addWidget(chart_view)
        layout.addWidget(label2)

        self.tooltip = QWidget()
        self.tooltip.setWindowFlag(Qt.WindowType.ToolTip)
        self.tooltip.setLayout(layout)
        self.tooltip.adjustSize()

        self.place_tooltip(self.tooltip, pos)
        self.tooltip.show()

    def create_anim_chart(self, anim: Animation) -> 'QChartView':
        from PySide6.QtCharts import QChart, QChartView, QScatterSeries

        count = min(500, int(anim.global_range.duration * self.anim.cfg.fps))
        times = np.linspace(anim.global_range.at,
                            anim.global_range.end,
                            count)

        series = QScatterSeries()
        series.setMarkerSize(3)
        series.setPen(Qt.PenStyle.NoPen)
        for t in times:
            series.append(t, anim.get_alpha_on_global_t(t))

        chart = QChart()
        chart.addSeries(series)
        chart.createDefaultAxes()
        chart.legend().setVisible(False)

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setMinimumSize(250, 200)

        return chart_view

    def place_tooltip(self, tooltip: QWidget, pos: QPoint) -> None:
        rect = tooltip.screen().availableGeometry()
        global_pos = self.mapToGlobal(pos)
        to = QPoint(global_pos) + QPoint(2, 2)
        if to.x() + tooltip.width() > rect.right():
            to.setX(global_pos.x() - tooltip.width() - 2)
        if to.y() + tooltip.height() > rect.bottom():
            to.setY(global_pos.y() - tooltip.height() - 2)

        tooltip.move(to)

    def hide_tooltip(self) -> None:
        if self.tooltip is not None:
            self.tooltip = None

    def on_hover_timer_timeout(self) -> None:
        pos = self.mapFromGlobal(self.cursor().pos())
        if self.rect().contains(pos):
            self.hover_at(pos)

    def on_drag_timer_timeout(self) -> None:
        minimum = self.play_space
        maximum = self.width() - self.play_space

        x = self.mapFromGlobal(self.cursor().pos()).x()

        if x < minimum or x > maximum:
            self.set_progress_by_x(x)

    # endregion

    def on_key_timer_timeout(self) -> None:
        if self.is_pressing.w:
            cursor_time = self.pixel_to_time(self.mapFromGlobal(self.cursor().pos()).x())

            factor = max(TIMELINE_VIEW_MIN_DURATION / self.range.duration, 0.97)
            self.set_range(
                factor * (self.range.at - cursor_time) + cursor_time,
                self.range.duration * factor
            )

        elif self.is_pressing.s:
            cursor_time = self.pixel_to_time(self.mapFromGlobal(self.cursor().pos()).x())

            factor = min(self.anim.global_range.duration / self.range.duration, 1 / 0.97)
            self.set_range(
                factor * (self.range.at - cursor_time) + cursor_time,
                self.range.duration * factor
            )

        if self.is_pressing.a or self.is_pressing.d:
            shift = self.range.duration * 0.05 * (self.is_pressing.d - self.is_pressing.a)
            self.set_range(
                self.range.at + shift,
                self.range.duration
            )

            self.update()

    def set_progress(self, progress: int) -> None:
        progress = clip(progress, 0, self._maximum)
        if progress != self._progress:
            self._progress = progress

            pixel_at = self.progress_to_pixel(progress)
            minimum = self.play_space
            maximum = self.width() - self.play_space
            if pixel_at < minimum:
                self.set_range(
                    self.pixel_to_time(pixel_at - minimum),
                    self.range.duration
                )
            if pixel_at > maximum:
                self.set_range(
                    self.pixel_to_time(pixel_at - maximum),
                    self.range.duration
                )

            self.value_changed.emit(progress)
            self.update()

    def progress(self) -> int:
        return self._progress

    def at_end(self) -> bool:
        return self._progress == self._maximum

    def progress_to_time(self, progress: int) -> float:
        return progress / self.anim.cfg.preview_fps

    def time_to_progress(self, time: float) -> int:
        return round(time * self.anim.cfg.preview_fps)

    def time_to_pixel(self, time: float) -> float:
        return (time - self.range.at) / self.range.duration * self.width()

    def pixel_to_time(self, pixel: float) -> float:
        return pixel / self.width() * self.range.duration + self.range.at

    def progress_to_pixel(self, progress: int) -> float:
        return self.time_to_pixel(self.progress_to_time(progress))

    def pixel_to_progress(self, pixel: float) -> int:
        return self.time_to_progress(self.pixel_to_time(pixel))

    def time_range_to_pixel_range(self, range: TimeRange) -> PixelRange:
        left = (range.at - self.range.at) / self.range.duration * self.width()
        width = range.duration / self.range.duration * self.width()
        return TimelineView.PixelRange(left, width)

    def set_progress_by_x(self, x: float) -> None:
        self.set_progress(self.pixel_to_progress(x))

        minimum = self.play_space
        maximum = self.width() - self.play_space

        if x < minimum or x > maximum:
            self.drag_timer.start(30)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_progress_by_x(event.position().x())
            self.dragged.emit()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self.hover_timer.start(500)
        self.hide_tooltip()

        if event.buttons() & Qt.MouseButton.LeftButton:
            self.set_progress_by_x(event.position().x())
            self.dragged.emit()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_timer.stop()

    def leaveEvent(self, _) -> None:
        self.hide_tooltip()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()

        if key == Qt.Key.Key_Space:
            self.space_pressed.emit()

        elif key == Qt.Key.Key_W:
            self.is_pressing.w = True
        elif key == Qt.Key.Key_A:
            self.is_pressing.a = True
        elif key == Qt.Key.Key_S:
            self.is_pressing.s = True
        elif key == Qt.Key.Key_D:
            self.is_pressing.d = True

        elif key == Qt.Key.Key_Z:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                progresses = self.pause_progresses
                idx = bisect(progresses, self._progress - 1)
                idx -= 1
                if idx < 0:
                    self.set_progress(0)
                else:
                    self.set_progress(progresses[idx])
            else:
                anims = self.sorted_anims
                time = self.progress_to_time(self._progress)
                idx = bisect(anims, time - 1e-2, key=lambda x: x.global_range.at)
                idx -= 1
                if idx < 0:
                    self.set_progress(0)
                else:
                    self.set_progress(self.time_to_progress(anims[idx].global_range.at))

            self.dragged.emit()

        elif key == Qt.Key.Key_C:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                progresses = self.pause_progresses
                idx = bisect(progresses, self._progress + 1)
                if idx < len(progresses):
                    self.set_progress(progresses[idx])
                else:
                    self.set_progress(self._maximum)
            else:
                anims = self.sorted_anims
                time = self.progress_to_time(self._progress)
                idx = bisect(anims, time + 1e-2, key=lambda x: x.global_range.at)
                if idx < len(anims):
                    self.set_progress(self.time_to_progress(anims[idx].global_range.at))
                else:
                    self.set_progress(self._maximum)

            self.dragged.emit()

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        key = event.key()

        if key == Qt.Key.Key_W:
            self.is_pressing.w = False
        elif key == Qt.Key.Key_A:
            self.is_pressing.a = False
        elif key == Qt.Key.Key_S:
            self.is_pressing.s = False
        elif key == Qt.Key.Key_D:
            self.is_pressing.d = False

    def wheelEvent(self, event: QWheelEvent) -> None:
        self.y_offset = clip(self.y_offset - event.angleDelta().y() / 240 * self.label_height,
                             0,
                             self.max_row * self.label_height)
        self.update()

    def paintEvent(self, _: QPaintEvent) -> None:
        p = QPainter(self)
        orig_font = p.font()

        # 绘制每次 forward 或 play 的时刻
        times_of_code = self.anim.timeline.times_of_code
        left = bisect_left(times_of_code, self.range.at, key=lambda x: x.time)
        right = bisect(times_of_code, self.range.end, key=lambda x: x.time)

        p.setPen(QPen(QColor(74, 48, 80), 2))
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for i in range(left, right):
            self.paint_line(p, times_of_code[i].time)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # 绘制 pause_progresses
        if self.pause_progresses:
            p.setPen(QPen(QColor(88, 196, 221), 2))
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            progress_begin = self.time_to_progress(self.range.at)
            progress_end = self.time_to_progress(self.range.end)
            left = bisect_left(self.pause_progresses, progress_begin)
            right = bisect(self.pause_progresses, progress_end)
            for i in range(left, right):
                self.paint_line(p, self.progress_to_time(self.pause_progresses[i]))
            p.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # 绘制音频区段
        if self.anim.timeline.has_audio():
            audio_rect = self.audio_rect

            font = p.font()
            font.setPointSize(8)
            p.setFont(font)

            for info in self.anim.timeline.audio_infos:
                if info.range.end <= self.range.at or info.range.at >= self.range.end:
                    continue

                self.paint_label(p,
                                 info.range,
                                 audio_rect.y(),
                                 self.audio_height,
                                 info.audio.filename,
                                 QColor(152, 255, 191),
                                 QColor(152, 255, 191, 128),
                                 False)

            p.setFont(orig_font)

        # 绘制动画区段
        bottom_rect = self.bottom_rect
        p.setClipRect(bottom_rect)

        range_at = self.range.at
        range_end = self.range.end

        segment_left = math.floor(range_at / SEGMENT_DURATION)
        segment_right = math.ceil(range_end / SEGMENT_DURATION)
        for idx in range(segment_left, min(segment_right, len(self.labels_info_segments))):
            labels_info = self.labels_info_segments[idx]
            for info in labels_info:
                if info.segment_left == idx or (info.segment_left < segment_left and idx == segment_left):
                    if info.anim.global_range.end <= range_at or info.anim.global_range.at >= range_end:
                        continue
                    self.paint_label(p,
                                     info.anim.global_range,
                                     bottom_rect.y() + self.label_y(info.row),
                                     self.label_height,
                                     info.anim.__class__.__name__,
                                     Qt.PenStyle.NoPen,
                                     QColor(*info.anim.label_color).lighter(),
                                     True)

        p.setClipping(False)

        # 绘制当前进度指示
        p.setPen(QPen(Qt.GlobalColor.white, 2))
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.paint_line(p, self.progress_to_time(self._progress))
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # 绘制视野区域指示（底部的长条）
        left = self.range.at / self.anim.global_range.duration * self.width()
        width = self.range.duration / self.anim.global_range.duration * self.width()
        width = max(width, self.range_tip_height)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(77, 102, 132))
        p.drawRoundedRect(
            left,
            self.height() - self.range_tip_height,
            width,
            self.range_tip_height,
            self.range_tip_height / 2,
            self.range_tip_height / 2
        )

    @property
    def audio_rect(self) -> QRect:
        if not self.anim.timeline.has_audio():
            return QRect(0, 0, self.width(), 0)
        return QRect(0, 0, self.width(), self.audio_height)

    @property
    def bottom_rect(self) -> QRect:
        return self.rect().adjusted(0,
                                    self.audio_height if self.anim.timeline.has_audio() else 0,
                                    0,
                                    -self.range_tip_height)

    def label_y(self, row: int) -> float:
        return -self.y_offset + row * self.label_height

    def paint_label(
        self,
        p: QPainter,
        time_range: TimeRange,
        y: float,
        height: float,
        txt: str,
        stroke: QPen | QColor,
        fill: QBrush | QColor,
        is_anim_lable: bool
    ) -> None:
        range = self.time_range_to_pixel_range(time_range)
        rect = QRectF(range.left, y, range.width, height)

        # 标记是否应当绘制文字
        out_of_boundary = False

        if is_anim_lable:
            # 使得超出底端的区段也能看到一条边
            max_y = self.height() - self.range_tip_height - 4
            if rect.y() > max_y:
                rect.moveTop(max_y)
                rect.setHeight(4)
                out_of_boundary = True

            # 使得超出顶端的区段也能看到一条边
            top_margin = self.audio_height if self.anim.timeline.has_audio() else 0
            min_bottom = top_margin + 4
            if rect.bottom() < min_bottom:
                rect.moveTop(top_margin)
                rect.setHeight(4)
                out_of_boundary = True

        # 这里的判断使得区段过窄时也能看得见
        if rect.width() > 5:
            x_adjust = 2
        elif rect.width() > 1:
            x_adjust = (rect.width() - 1) / 2
        else:
            x_adjust = 0

        # 绘制背景部分
        if not out_of_boundary:
            rect.adjust(x_adjust, 2, -x_adjust, -2)
        p.setPen(stroke)
        p.setBrush(fill)
        p.drawRect(rect)

        # 使得在区段的左侧有一部分在显示区域外时，
        # 文字仍然对齐到屏幕的左端，而不是跑到屏幕外面去
        if rect.x() < 0:
            rect.setX(0)

        # 绘制文字
        if not out_of_boundary:
            rect.adjust(1, 1, -1, -1)
            p.setPen(Qt.GlobalColor.black)
            p.drawText(
                rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                txt
            )

    def paint_line(self, p: QPainter, time: float) -> None:
        pixel_at = self.time_to_pixel(time)
        p.drawLine(pixel_at, 0, pixel_at, self.height())
