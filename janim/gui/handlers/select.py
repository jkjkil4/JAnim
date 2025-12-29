from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import QLabel, QVBoxLayout

from janim.anims.timeline import Timeline
from janim.camera.camera_info import CameraInfo
from janim.constants import OUT
from janim.gui.handlers.utils import (HandlerPanel, SourceDiff,
                                      get_confirm_buttons, jump, parse_item)
from janim.items.item import Item
from janim.items.points import Points
from janim.locale.i18n import get_translator
from janim.utils.space_ops import normalize

if TYPE_CHECKING:
    from janim.gui.anim_viewer import AnimViewer

_ = get_translator('janim.gui.handlers.select')


def handler(viewer: AnimViewer, command: Timeline.GuiCommand) -> None:
    item = parse_item(command.body, command.locals)

    jump(viewer, command)
    widget = SelectPanel(viewer, command, item)
    widget.show()


class SelectPanel(HandlerPanel):
    def __init__(self, viewer: AnimViewer, command: Timeline.GuiCommand, item: Item):
        super().__init__(viewer, command)
        self.item = item

        # setup ui

        label_tips = QLabel(
            _('Left Click: Select Child Item\n'
              'Right Click: Deselect Child Item'),
            self
        )

        self.diff = SourceDiff(command, self)
        btn_box, btn_ok, btn_cancel = get_confirm_buttons(self)

        vlayout = QVBoxLayout(self)
        vlayout.addWidget(label_tips)
        vlayout.addWidget(self.diff)
        vlayout.addStretch()
        vlayout.addWidget(btn_box, 0, Qt.AlignmentFlag.AlignRight)

        self.setLayout(vlayout)

        # setup slots

        btn_ok.clicked.connect(self.diff.submit)
        btn_cancel.clicked.connect(self.close)
        self.diff.submitted.connect(self.close_and_rebuild_timeline)

        # update

        debounce_timer = QTimer(self, singleShot=True, interval=200)
        debounce_timer.timeout.connect(self.compute_boxes)
        self.viewer.timeline_view.value_changed.connect(debounce_timer.start)

        self.selected_indices: list[int] = []
        self.compute_boxes()
        self.update_replacement()

        # event filter

        self.viewer.glw.installEventFilter(self)
        self.viewer.overlay.installEventFilter(self)

    def compute_boxes(self) -> None:
        self.item_box = compute_box_of_item(self.viewer, self.item)
        self.children_boxes = compute_boxes_of_children(self.viewer, self.item)
        self.update_overlay()

    def update_replacement(self) -> None:
        ranges: list[tuple[float, float]] = []
        range_start = None
        range_end = None

        for i in range(len(self.children_boxes)):
            if i in self.selected_indices:
                if range_start is None:
                    range_start = i
                    range_end = i + 1
                    continue

                if i == range_end:
                    range_end += 1
                else:
                    ranges.append((range_start, range_end))
                    range_start = i
                    range_end = i + 1
        if range_start is not None:
            ranges.append((range_start, range_end))

        if not ranges:
            self.diff.set_replacement('Group()')
            return

        replacements = [self.get_range_replacement(range) for range in ranges]
        if len(replacements) == 1:
            self.diff.set_replacement(replacements[0])
            return

        inner_parts = ', '.join(replacements)
        self.diff.set_replacement(f'Group({inner_parts})')

    def get_range_replacement(self, range: tuple[float, float]) -> str:
        start, end = range
        if start == end - 1:
            return f'{self.command.body}[{start}]'

        start_or_none = '' if start == 0 else start
        end_or_none = '' if end == len(self.children_boxes) else end
        return f'{self.command.body}[{start_or_none}:{end_or_none}]'

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.viewer.glw:
            if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick):
                self.on_glw_mouse_press(event)
            if event.type() == QEvent.Type.MouseMove:
                self.on_glw_mouse_move(event)

        if watched is self.viewer.overlay:
            if event.type() == QEvent.Type.Paint:
                self.on_overlay_paint(event)

        return super().eventFilter(watched, event)

    def on_glw_mouse_press(self, event: QMouseEvent) -> None:
        match event.button():
            case Qt.MouseButton.LeftButton:
                self.select_child_item(event)
            case Qt.MouseButton.RightButton:
                self.remove_child_item(event)

    def on_glw_mouse_move(self, event: QMouseEvent) -> None:
        match event.buttons():
            case Qt.MouseButton.LeftButton:
                self.select_child_item(event)
            case Qt.MouseButton.RightButton:
                self.remove_child_item(event)

    def select_child_item(self, event: QMouseEvent) -> None:
        glx, gly = self.viewer.glw.map_to_gl2d(event.position())

        for i, box in enumerate(self.children_boxes):
            if i in self.selected_indices:
                continue
            if not box.contains(glx, gly):
                continue
            self.selected_indices.append(i)

        self.update_replacement()
        self.update_overlay()

    def remove_child_item(self, event: QMouseEvent) -> None:
        glx, gly = self.viewer.glw.map_to_gl2d(event.position())

        for i in self.selected_indices:
            box = self.children_boxes[i]
            if not box.contains(glx, gly):
                continue
            self.selected_indices.remove(i)

        self.update_replacement()
        self.update_overlay()

    def on_overlay_paint(self, event: QPaintEvent) -> None:
        glw = self.viewer.glw

        p = QPainter(self.viewer.overlay)

        # 绘制父物件
        p.setBrush(QColor(195, 131, 19, 32))
        p.setPen(QColor(195, 131, 19))
        p.drawRect(
            QRectF(
                glw.map_from_gl2d(self.item_box.min_glx, self.item_box.min_gly),
                glw.map_from_gl2d(self.item_box.max_glx, self.item_box.max_gly)
            )
        )

        # 绘制选中的子物件
        p.setBrush(QColor(194, 102, 219, 64))
        p.setPen(QColor(194, 102, 219))
        for i in self.selected_indices:
            box = self.children_boxes[i]
            p.drawRect(
                QRectF(
                    glw.map_from_gl2d(box.min_glx, box.min_gly),
                    glw.map_from_gl2d(box.max_glx, box.max_gly)
                )
            )


class ItemBox:
    """
    物件及其在 GL 坐标下的可选中范围，四周留有余量
    """
    def __init__(self, item: Item, attrs: BasicAttrs):
        self.item = item

        cmpt = item.current(as_time=attrs.global_t)(Points).points
        if attrs.is_camera_axis_simple or item.is_fix_in_frame():
            points = cmpt.box.get_corners()
        else:
            points = cmpt.get_all()

        if item.is_fix_in_frame():
            mapped = get_fixed_camera_info().map_points(points)
        else:
            mapped = attrs.camera_info.map_points(points)

        self.min_glx, self.min_gly = np.nanmin(mapped, axis=0) - attrs.tolerance
        self.max_glx, self.max_gly = np.nanmax(mapped, axis=0) + attrs.tolerance

    def contains(self, glx: float, gly: float) -> bool:
        return self.min_glx <= glx <= self.max_glx and self.min_gly <= gly <= self.max_gly

    def __eq__(self, other: ItemBox) -> bool:
        return self.item is other.item


def select_next_item_at_position(
    viewer: AnimViewer,
    position: QPointF,
    current: ItemBox | None
) -> ItemBox | None:
    """
    选取指定位置的下一个物件

    所谓“下一个物件”，即对于每次发现可选取物件的列表，如果原先的物件 ``current`` 在列表中，则选取列表中的后一项
    """
    glx, gly = viewer.glw.map_to_gl2d(position)

    attrs = BasicAttrs(viewer)

    found: list[ItemBox] = []

    for item, appr in viewer.built.visible_item_segments.get(attrs.global_t):
        if not appr.is_visible_at(attrs.global_t):
            continue
        item_box = ItemBox(item, attrs)
        if not item_box.contains(glx, gly):
            continue
        found.append(item_box)

    if not found:
        return None

    if current is None or current not in found:
        return found[0]

    idx = found.index(current)
    return found[(idx + 1) % len(found)]


def compute_box_of_item(viewer: AnimViewer, item: Item) -> ItemBox:
    """
    计算 ``item`` 的 :class:`ItemBox`
    """
    return ItemBox(item, BasicAttrs(viewer))


def compute_boxes_of_children(viewer: AnimViewer, item: Item) -> list[ItemBox]:
    """
    遍历 ``item`` 的子物件，计算每个子物件的 :class:`ItemBox`
    """
    return [
        ItemBox(sub, BasicAttrs(viewer))
        for sub in item.get_children()
    ]


class BasicAttrs:
    def __init__(self, viewer: AnimViewer):
        tlview = viewer.timeline_view

        self.global_t = tlview.progress_to_time(tlview.progress())
        self.camera_info = viewer.built.current_camera_info()
        # 选取框往四周预留的余量，有余量方便选中极细或极小的物件，基于 GL 坐标
        self.tolerance = np.array([4 / viewer.glw.width(), 4 / viewer.glw.height()])

        # 检查 camera_axis 是否只有单个分量
        vec = np.sort(np.abs(normalize(self.camera_info.camera_axis)))  # 这一串只为了：归一化、绝对值、尽可能单个分量挪到最后
        self.is_camera_axis_simple = np.isclose(vec, OUT).all()


@lru_cache
def get_fixed_camera_info() -> CameraInfo:
    """
    返回值用于辅助计算 fixed-in-frame 物件的 bounding
    """
    from janim.camera.camera import Camera
    return Camera().points.info
