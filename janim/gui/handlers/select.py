from __future__ import annotations

from typing import TYPE_CHECKING
from functools import lru_cache

import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QVBoxLayout

from janim.camera.camera_info import CameraInfo
from janim.anims.timeline import Timeline
from janim.gui.handlers.utils import (HandlerPanel, SourceDiff,
                                      get_confirm_buttons, jump)
from janim.items.item import Item
from janim.items.points import Points

if TYPE_CHECKING:
    from janim.gui.anim_viewer import AnimViewer


def handler(viewer: AnimViewer, command: Timeline.GuiCommand) -> None:
    jump(viewer, command)
    widget = SelectPanel(viewer, command)
    widget.show()


class SelectPanel(HandlerPanel):
    def __init__(self, viewer: AnimViewer, command: Timeline.GuiCommand):
        super().__init__(viewer, command)

        # setup ui

        diff = SourceDiff(command, self)
        btn_box, btn_ok, btn_cancel = get_confirm_buttons(self)

        vlayout = QVBoxLayout(self)
        vlayout.addWidget(diff)
        vlayout.addStretch()
        vlayout.addWidget(btn_box, 0, Qt.AlignmentFlag.AlignRight)

        self.setLayout(vlayout)

        # setup slots

        btn_ok.clicked.connect(diff.submit)
        btn_cancel.clicked.connect(self.close)
        diff.submitted.connect(self.close_and_rebuild_timeline)


class ItemBox:
    """
    物件及其可选中范围
    """
    def __init__(self, item: Item, as_time: float, camera_info: CameraInfo, tolerance: np.ndarray):
        self.item = item

        box = item.current(as_time=as_time)(Points).points.box
        if item.is_fix_in_frame():
            mapped = get_fixed_camera_info().map_points(box.get_corners())
        else:
            mapped = camera_info.map_points(box.get_corners())

        self.min_glx, self.min_gly = mapped.min(axis=0) - tolerance
        self.max_glx, self.max_gly = mapped.max(axis=0) + tolerance

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

    global_t = viewer.built._time
    camera_info = viewer.built.current_camera_info()
    tolerance = get_tolerance(viewer)

    found: list[ItemBox] = []

    for item, appr in viewer.built.visible_item_segments.get(global_t):
        if not appr.is_visible_at(global_t):
            continue
        item_box = ItemBox(item, global_t, camera_info, tolerance)
        if not item_box.contains(glx, gly):
            continue
        found.append(item_box)

    if not found:
        return None

    if current is None or current not in found:
        return found[0]

    idx = found.index(current)
    return found[(idx + 1) % len(found)]


def compute_boxes_of_children(viewer: AnimViewer, item: Item) -> list[ItemBox]:
    """
    遍历 ``item`` 的子物件，计算每个子物件的 :class:`ItemBox`
    """
    global_t = viewer.built._time
    camera_info = viewer.built.current_camera_info()
    tolerance = get_tolerance(viewer)

    return [
        ItemBox(sub, global_t, camera_info, tolerance)
        for sub in item.get_children()
    ]


def get_tolerance(viewer: AnimViewer) -> np.ndarray:
    """
    得到选取框往四周预留的余量

    有余量方便选中极细以及极小的物件
    """
    return np.array([6 / viewer.glw.width(), 6 / viewer.glw.height()])


@lru_cache
def get_fixed_camera_info() -> CameraInfo:
    """
    用于辅助计算 fixed-in-frame 物件的 bounding
    """
    from janim.camera.camera import Camera
    return Camera().points.info
