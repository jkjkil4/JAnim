import itertools as it
import math
from bisect import bisect, bisect_left
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QPoint, QPointF, QRect, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QKeyEvent, QMouseEvent, QPainter,
                           QPaintEvent, QPen, QWheelEvent)
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from janim.anims.animation import FOREVER, Animation, TimeRange
from janim.anims.composition import AnimGroup
from janim.anims.timeline import BuiltTimeline, Timeline, TimelineItem
from janim.gui.label import (LABEL_DEFAULT_HEIGHT, LABEL_PIXEL_HEIGHT_PER_UNIT,
                             Label, LabelGroup, LazyLabelGroup, PixelRange)
from janim.items.item import Item
from janim.locale.i18n import get_local_strings
from janim.utils.bezier import interpolate
from janim.utils.rate_functions import linear
from janim.utils.simple_functions import clip

if TYPE_CHECKING:
    from PySide6.QtCharts import QAreaSeries, QChartView

_ = get_local_strings('timeline_view')

TIMELINE_VIEW_MIN_DURATION = 0.5
LABEL_OBJ_NAME = '__obj'
SUBTIMELINE_LABEL_GROUP_NAME = '__subtimeline_label_group'
SUBTIMELINE_CLASS_NAME = '__subtimeline_class'


class TimelineView(QWidget):
    '''
    窗口下方的进度条和动画区段指示器

    - **w** 键放大区段（使视野精确到一小段中）
    - **s** 键缩小区段（使视野扩展到一大段中）
    - **a** 和 **d** 左右移动区段
    - 使用鼠标滚轮纵向平移
    '''

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
    range_tip_height = 4
    play_space = 20

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.label_group: LabelGroup | None = None

        self.highlighting: LabelGroup | None = None
        self.highlight_hover_timer = QTimer(self)
        self.highlight_hover_timer.setSingleShot(True)
        self.highlight_hover_timer.timeout.connect(self.on_highlight_hover_timer_timeout)

        self.detail_hover_timer = QTimer(self)
        self.detail_hover_timer.setSingleShot(True)
        self.detail_hover_timer.timeout.connect(self.on_detail_hover_timer_timeout)

        self.drag_timer = QTimer(self)
        self.drag_timer.setSingleShot(True)
        self.drag_timer.timeout.connect(self.on_drag_timer_timeout)

        self.tooltip: QWidget | None = None

        self.key_timer = QTimer(self)
        self.key_timer.timeout.connect(self.on_key_timer_timeout)
        self.key_timer.start(1000 // 60)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setMinimumHeight(LABEL_DEFAULT_HEIGHT * LABEL_PIXEL_HEIGHT_PER_UNIT + self.range_tip_height + 10)

    def set_built(self, built: BuiltTimeline, pause_progresses: list[int]) -> None:
        # 记录先前展开的的 subtimeline labels
        has_prev = self.label_group is not None
        if has_prev:
            stored = self.LabelGroupExpandedInfo(self.label_group)

        # 设置属性
        self.range = TimeRange(0, min(20, built.duration))
        self.y_pixel_offset: float = 0
        self.built = built
        self._progress: int = 0
        self._maximum = round(built.duration * self.built.cfg.preview_fps)
        self.pause_progresses = pause_progresses
        self.inout_point: tuple[float, float] | None = None

        self.is_pressing = TimelineView.Pressing()

        # 初始化新的 labels
        self.init_label_group()

        # 还原先前展开的 subtimeline labels
        if has_prev:
            stored.restore(self.label_group)

        # 触发画面更新
        self.update()

    # region labels

    class LabelGroupExpandedInfo:
        # 语义：
        # 如果 self.expanded 为 None，则 subtimeline_label_group 就未展开或不存在
        # 如果 self.expanded 是 list，则 list 中的 subtimeline 已展开
        def __init__(self, label_group: LabelGroup | LazyLabelGroup):
            if label_group._collapse:
                self.expanded = None
                return

            subtimeline_label_group: LabelGroup | None = getattr(label_group, SUBTIMELINE_LABEL_GROUP_NAME)
            if subtimeline_label_group is None or subtimeline_label_group._collapse:
                self.expanded = None
                return

            self.expanded: list[tuple[int, str, TimelineView.LabelGroupExpandedInfo]] = []
            for i, sub in enumerate(subtimeline_label_group.labels):
                sub: LazyLabelGroup
                if sub._collapse:
                    continue
                name = getattr(sub, SUBTIMELINE_CLASS_NAME)
                self.expanded.append((i, name, TimelineView.LabelGroupExpandedInfo(sub)))

        def restore(self, label_group: LabelGroup | LazyLabelGroup):
            if self.expanded is None:
                return

            subtimeline_label_group: LabelGroup | None = getattr(label_group, SUBTIMELINE_LABEL_GROUP_NAME)
            if subtimeline_label_group is None:
                return

            if subtimeline_label_group._collapse:
                subtimeline_label_group.switch_collapse()
            labels = subtimeline_label_group.labels
            for i, name, sub_info in self.expanded:
                if i >= len(labels):
                    continue

                label: LazyLabelGroup = labels[i]
                if name != getattr(label, SUBTIMELINE_CLASS_NAME):
                    continue

                label.switch_collapse()
                sub_info.restore(label)

    def init_label_group(self) -> None:
        '''
        构建动画区段信息，以便操作与绘制
        '''
        self.debug_label_group = self.make_debug_label_group(self.built)
        self.audio_label_group = self.make_audio_label_group(self.built)
        self.anim_label_group = self.make_anim_label_group(self.built)

        self.subtimeline_label_group = self.make_subtimeline_label_group(self.built)

        self.label_group = LabelGroup(
            '',
            self.anim_label_group.t_range,
            *[
                label_group
                for label_group in (self.subtimeline_label_group, self.debug_label_group, self.audio_label_group)
                if label_group is not None
            ],
            self.anim_label_group,
            collapse=False,
            header=False,
        )
        setattr(self.label_group, SUBTIMELINE_LABEL_GROUP_NAME, self.subtimeline_label_group)

    @staticmethod
    def make_anim_label_group(built: BuiltTimeline) -> LabelGroup:
        def make_label_from_anim(anim: Animation, header: bool = True) -> Label | None:
            name = anim.name or anim.__class__.__name__
            color = QColor(*anim.label_color)
            if isinstance(anim, AnimGroup):
                labels = [
                    label
                    for subanim in anim.anims
                    if (label := make_label_from_anim(subanim)) is not None
                ]
                if not labels:
                    return None
                label = LabelGroup(
                    name,
                    TimeRange(      # 这里不直接使用 anim.t_range 是为了处理 FOREVER 的子动画
                        min(label.t_range.at for label in labels),
                        max(label.t_range.end for label in labels)
                    ),
                    *labels,
                    collapse=anim.collapse,
                    header=header,
                    brush=color,
                    highlight_pen=QPen(QColor(41, 171, 202), 3),
                    highlight_brush=QColor(41, 171, 202, 40),
                )
            else:
                label = Label(
                    name,

                    anim.t_range
                    if anim.t_range.end is not FOREVER
                    else TimeRange(anim.t_range.at, built.duration),

                    brush=color,
                )
            setattr(label, LABEL_OBJ_NAME, anim)
            return label

        return LabelGroup(
            '',
            TimeRange(0, built.duration),
            *[
                label
                for anim in built.timeline.anim_groups
                if (
                    label := make_label_from_anim(
                        anim,
                        len(anim.anims) != 1 or anim.rate_func is not linear
                    )
                ) is not None
            ],
            collapse=False,
            header=False,
        )

    @staticmethod
    def make_audio_label_group(built: BuiltTimeline) -> LabelGroup | None:
        if not built.timeline.has_audio():
            return None

        infos = built.timeline.audio_infos
        multiple = len(infos) != 1

        def make_audio_label(info: Timeline.PlayAudioInfo) -> Label:
            label = Label(info.audio.filename,
                          info.range,
                          pen=QColor(85, 193, 167),
                          brush=QColor(85, 193, 167, 160))
            setattr(label, LABEL_OBJ_NAME, info)
            return label

        audio_label_group = LabelGroup(
            'audio',
            TimeRange(
                0,
                max(built.duration, max(info.range.end for info in infos))
            ),
            *[make_audio_label(info) for info in infos],
            collapse=multiple,
            header=multiple,
            brush=QColor(85, 193, 167),
            skip_grouponly_query=True
        )
        # 只有在播放多个音频，并且音频有重叠区段的时候才折叠组
        # 因此这里判断如果没有重叠区段，就把折叠取消
        if multiple and audio_label_group.is_exclusive():
            audio_label_group._collapse = False
            audio_label_group._header = False

        return audio_label_group

    @staticmethod
    def make_debug_label_group(built: BuiltTimeline) -> LabelGroup | None:
        if not built.timeline.debug_list:
            return None

        built_t_range = TimeRange(0, built.duration)

        def make_debug_label(item: Item):
            return LabelGroup(
                repr(item),
                built_t_range,
                make_visibility_debug_label(item),
                make_anim_debug_label(item),
                brush=QColor(170, 148, 132),
                highlight_pen=QPen(QColor(41, 171, 202), 3),
                highlight_brush=QColor(41, 171, 202, 40),
                collapse=False,
                header=True
            )

        class VisibilityLabel(Label):
            def __init__(self, t_range: TimeRange):
                super().__init__('', t_range, brush=QColor(255, 255, 128, 200))

            @property
            def height(self) -> int:
                return 1

        def make_visibility_debug_label(item: Item):
            visibility = built.timeline.item_appearances[item].visibility
            if len(visibility) % 2 != 0:
                visibility.append(built.duration + 1)
            return LabelGroup(
                '',
                built_t_range,
                *[
                    VisibilityLabel(TimeRange(visibility[i * 2], visibility[i * 2 + 1]))
                    for i in range(len(visibility) // 2)
                ],
                collapse=False,
                header=False,
                skip_grouponly_query=True
            )

        def make_anim_debug_label(item: Item):
            colors = [
                [251, 180, 174], [179, 205, 227], [204, 235, 197],
                [222, 203, 228], [254, 217, 166], [255, 255, 204],
                [229, 216, 189], [253, 218, 236], [242, 242, 242]
            ]
            iter = it.cycle(colors)
            dct = {}

            def get_color(anim) -> QColor:
                color = dct.get(anim, None)
                if color is None:
                    color = dct[anim] = QColor(*next(iter))
                return color

            stack = built.timeline.item_appearances[item].stack
            return LabelGroup(
                '',
                built_t_range,
                *[
                    Label(
                        (
                            f'{anim.__class__.__name__} at 0x{id(anim):X}'
                            if anim._generate_by is None
                            else f'{anim.__class__.__name__} at 0x{id(anim):X} '
                            f'(from {anim._generate_by.__class__.__name__} at 0x{id(anim._generate_by):X})'
                        ),
                        TimeRange(t1, t2),
                        brush=get_color(anim)
                    )
                    for (t1, t2), anims in zip(
                        it.pairwise([*stack.times, built.duration + 1]),
                        stack.stacks
                    )
                    for anim in anims
                ],
                collapse=False,
                header=False,
                skip_grouponly_query=True
            )

        return LabelGroup(
            'debug',
            built_t_range,
            *[make_debug_label(item) for item in built.timeline.debug_list],
            brush=QColor(170, 148, 132),
            highlight_pen=QPen(QColor(41, 171, 202), 3),
            highlight_brush=QColor(41, 171, 202, 40),
            collapse=False,
            header=True
        )

    @staticmethod
    def make_subtimeline_label_group(built: BuiltTimeline) -> LabelGroup | None:
        items = built.timeline.subtimeline_items

        if not items:
            return None

        multiple = len(items) != 1

        def make_subtimeline_label(item: TimelineItem) -> LazyLabelGroup:
            def callback() -> list[LabelGroup]:
                debug_label_group = TimelineView.make_debug_label_group(item._built)
                audio_label_group = TimelineView.make_audio_label_group(item._built)
                anim_label_group = TimelineView.make_anim_label_group(item._built)

                subtimeline_label_group = TimelineView.make_subtimeline_label_group(item._built)
                setattr(group, SUBTIMELINE_LABEL_GROUP_NAME, subtimeline_label_group)

                lst = [
                    *[
                        label_group
                        for label_group in (subtimeline_label_group, debug_label_group, audio_label_group)
                        if label_group is not None
                    ],
                    anim_label_group
                ]
                for label_group in lst:
                    label_group.shift_time_range(group.t_range.at + item.first_frame_duration)
                return lst

            timeline = item._built.timeline

            group = LazyLabelGroup(
                f'{timeline.__class__.__name__} at 0x{id(timeline):X} (item at 0x{id(item):X})',
                TimeRange(item.at, item.end),
                callback,
                brush=QColor(177, 137, 198, 190),
                pen=QColor(177, 137, 198),
                highlight_pen=QPen(QColor(41, 171, 202), 3),
                highlight_brush=QColor(41, 171, 202, 40),
            )
            setattr(group, SUBTIMELINE_CLASS_NAME, timeline.__class__.__name__)
            return group

        subtimeline_label_group = LabelGroup(
            'sub-timeline',
            TimeRange(
                0,
                max(built.duration, max(item.end for item in items))
            ),
            *[make_subtimeline_label(item) for item in items],
            collapse=multiple,
            header=multiple,
            brush=QColor(177, 137, 198),
            skip_grouponly_query=True
        )
        # 只有在含有多个子 Timeline，并且有重叠区段的时候才折叠组
        # 因此这里判断如果没有重叠区段，就把折叠取消
        if multiple and subtimeline_label_group.is_exclusive():
            subtimeline_label_group._collapse = False
            subtimeline_label_group._header = False

        return subtimeline_label_group

    def query_label_at(self, pos: QPointF, policy: LabelGroup.QueryPolicy) -> Label | LabelGroup | None:
        return self.label_group.query_at(self.labels_rect, self.range, pos, self.y_pixel_offset, policy)

    # endregion

    # region hover

    def hover_at(self, pos: QPoint) -> None:
        label = self.query_label_at(pos, LabelGroup.QueryPolicy.HeaderAndLabel)
        obj = getattr(label, LABEL_OBJ_NAME, None)
        if obj is None:
            return

        if isinstance(obj, Animation):
            self.hover_at_anim(pos, obj)
        else:
            self.hover_at_audio(pos, obj)

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
            # 否则将其截短（保留前40个字符和最后40个字符）后，再作为 msg_lst 的一部分
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

        unit = audio.framerate // self.built.cfg.fps

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

        font = chart.font()
        font.setPointSize(7)

        x_axis = QValueAxis()
        x_axis.setRange(range_begin, range_end)
        x_axis.setTickCount(max(2, 1 + int(range_end - range_begin)))
        x_axis.setTitleText(_('Timeline Progress'))
        x_axis.setTitleFont(font)
        chart.addAxis(x_axis, Qt.AlignmentFlag.AlignBottom)

        y_axis = QValueAxis()
        y_axis.setRange(0, 1)
        chart.addAxis(y_axis, Qt.AlignmentFlag.AlignLeft)

        x_clip_axis = QValueAxis()
        x_clip_axis.setRange(clip_begin, clip_end)
        x_clip_axis.setTitleText(_('Audio Progress'))
        x_clip_axis.setTitleFont(font)
        chart.addAxis(x_clip_axis, Qt.AlignmentFlag.AlignTop)

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
        chart_view.setMinimumSize(350, 270)

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
            if last.parent is None:
                break
            parents.append(last.parent)

        is_forever = anim.t_range.end is FOREVER
        end = 'FOREVER' if is_forever else f'{round(anim.t_range.end, 2)}s'
        label1 = QLabel(f'{anim.__class__.__name__} '
                        f'{round(anim.t_range.at, 2)}s ~ {end}')

        if not is_forever:
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
        if not is_forever:
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

        count = min(500, int(anim.t_range.duration * self.built.cfg.fps))
        times = np.linspace(anim.t_range.at,
                            anim.t_range.end,
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

    def on_highlight_hover_timer_timeout(self) -> None:
        label = self.query_label_at(self.mapFromGlobal(self.cursor().pos()), LabelGroup.QueryPolicy.GroupOnly)
        if label is not self.highlighting:
            self.highlighting = label
            self.update()

    def on_detail_hover_timer_timeout(self) -> None:
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

    # region range

    def set_range(self, at: float, duration: float) -> None:
        duration = min(duration, self.built.duration)
        at = clip(at, 0, self.built.duration - duration)
        self.range = TimeRange(at, at + duration)
        self.update()

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

            factor = min(self.built.duration / self.range.duration, 1 / 0.97)
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

    def set_in_point(self) -> None:
        t = self.progress_to_time(self._progress)

        if self.inout_point is None:
            self.inout_point = (t, self.built.duration)
        else:
            if t >= self.inout_point[1]:
                self.inout_point = (t, self.built.duration)
            else:
                self.inout_point = (t, self.inout_point[1])

        self.update()

    def set_out_point(self) -> None:
        t = self.progress_to_time(self._progress)

        if self.inout_point is None:
            self.inout_point = (0, t)
        else:
            if t <= self.inout_point[0]:
                self.inout_point = (0, t)
            else:
                self.inout_point = (self.inout_point[0], t)

        self.update()

    def reset_inout_point(self) -> None:
        self.inout_point = None
        self.update()

    # endregion

    # region progress

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

    def set_progress_by_x(self, x: float) -> None:
        self.set_progress(self.pixel_to_progress(x))

        minimum = self.play_space
        maximum = self.width() - self.play_space

        if x < minimum or x > maximum:
            self.drag_timer.start(30)

    def progress(self) -> int:
        return self._progress

    def at_end(self) -> bool:
        return self._progress == self._maximum

    # endregion

    # region conversion

    def progress_to_time(self, progress: int) -> float:
        return progress / self.built.cfg.preview_fps

    def time_to_progress(self, time: float) -> int:
        return round(time * self.built.cfg.preview_fps)

    def time_to_pixel(self, time: float) -> float:
        # 假设 self.labels_rect 的左右与控件没有间隙
        return (time - self.range.at) / self.range.duration * self.width()

    def pixel_to_time(self, pixel: float) -> float:
        # 假设 self.labels_rect 的左右与控件没有间隙
        return pixel / self.width() * self.range.duration + self.range.at

    def progress_to_pixel(self, progress: int) -> float:
        return self.time_to_pixel(self.progress_to_time(progress))

    def pixel_to_progress(self, pixel: float) -> int:
        return self.time_to_progress(self.pixel_to_time(pixel))

    def time_range_to_pixel_range(self, range: TimeRange) -> PixelRange:
        left = (range.at - self.range.at) / self.range.duration * self.width()
        width = range.duration / self.range.duration * self.width()
        return PixelRange(left, width)

    # endregion

    # region events

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.press_at = event.position()
            self.try_to_switch_collapse = self.query_label_at(self.press_at, LabelGroup.QueryPolicy.HeaderOnly)

            if self.try_to_switch_collapse is None:
                self.set_progress_by_x(event.position().x())
                self.dragged.emit()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self.highlight_hover_timer.isActive():
            self.highlight_hover_timer.start(50)
        self.detail_hover_timer.start(500)
        self.hide_tooltip()

        if event.buttons() & Qt.MouseButton.LeftButton:
            if self.try_to_switch_collapse is not None:
                if abs(self.press_at.x() - event.x()) > 16 or abs(self.press_at.y() - event.y()) > 16:
                    self.try_to_switch_collapse = None

            if self.try_to_switch_collapse is None:
                self.set_progress_by_x(event.position().x())
                self.dragged.emit()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self.try_to_switch_collapse is not None:
                self.try_to_switch_collapse.switch_collapse()
                self.update()

            self.drag_timer.stop()

    def leaveEvent(self, _) -> None:
        self.highlighting = None
        self.highlight_hover_timer.stop()
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

        elif key == Qt.Key.Key_Left:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                progresses = self.pause_progresses
                idx = bisect(progresses, self._progress - 1)
                idx -= 1
                if idx < 0:
                    self.set_progress(0)
                else:
                    self.set_progress(progresses[idx])
            else:
                time = self.progress_to_time(self._progress)
                label = self.anim_label_group.find_before(time - 1e-2)
                if label is None:
                    self.set_progress(0)
                else:
                    self.set_progress(self.time_to_progress(label.t_range.at))

            self.dragged.emit()

        elif key == Qt.Key.Key_Right:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                progresses = self.pause_progresses
                idx = bisect(progresses, self._progress + 1)
                if idx < len(progresses):
                    self.set_progress(progresses[idx])
                else:
                    self.set_progress(self._maximum)
            else:
                time = self.progress_to_time(self._progress)
                label = self.anim_label_group.find_after(time + 1e-2)
                if label is None:
                    self.set_progress(self._maximum)
                else:
                    self.set_progress(self.time_to_progress(label.t_range.at))

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
        self.y_pixel_offset = clip(
            self.y_pixel_offset - event.angleDelta().y() / 120 * LABEL_PIXEL_HEIGHT_PER_UNIT,
            0,
            max(0, self.label_group.height - LABEL_DEFAULT_HEIGHT) * LABEL_PIXEL_HEIGHT_PER_UNIT
        )
        self.update()

    # endregion

    # region paint

    def paintEvent(self, _: QPaintEvent) -> None:
        p = QPainter(self)

        # 绘制 inout_point 区段
        if self.inout_point is not None:
            inp, outp = self.inout_point
            # 可见的时候才绘制
            if inp < self.range.end and outp > self.range.at:
                x1 = self.time_to_pixel(max(inp, self.range.at))
                x2 = self.time_to_pixel(min(outp, self.range.end))
                p.fillRect(x1, 0, x2 - x1, self.height(), QColor(17, 58, 81))

        # 绘制每次 forward 或 play 的时刻
        times_of_code = self.built.timeline.times_of_code
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

        # 绘制 labels（包括音频区段和动画区段）
        labels_rect = self.labels_rect
        params = Label.PaintParams(labels_rect, self.range, self.y_pixel_offset)
        p.setClipRect(labels_rect)
        self.label_group.paint(p, params)
        p.setClipping(False)

        if self.highlighting is not None:
            self.highlighting.paint_highlight(p, params)

        # 绘制当前进度指示
        p.setPen(QPen(Qt.GlobalColor.white, 2))
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.paint_line(p, self.progress_to_time(self._progress))
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # 绘制视野区域指示（底部的长条）
        left = self.range.at / self.built.duration * self.width()
        width = self.range.duration / self.built.duration * self.width()
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
    def labels_rect(self) -> QRect:
        return self.rect().adjusted(0, 0, 0, -self.range_tip_height)

    def paint_line(self, p: QPainter, time: float) -> None:
        pixel_at = self.time_to_pixel(time)
        p.drawLine(pixel_at, 0, pixel_at, self.height())

    # endregion
