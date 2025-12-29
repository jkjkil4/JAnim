from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout

from janim.anims.timeline import Timeline
from janim.constants import (LARGE_BUFF, MED_LARGE_BUFF, MED_SMALL_BUFF,
                             SMALL_BUFF)
from janim.gui.handlers.select import BasicAttrs as SelectBasicAttrs
from janim.gui.handlers.select import get_fixed_camera_info
from janim.gui.handlers.utils import (HandlerPanel, SourceDiff,
                                      get_confirm_buttons,
                                      get_undo_redo_buttons, jump, parse_item)
from janim.items.item import Item
from janim.items.points import Points
from janim.locale.i18n import get_translator
from janim.utils.space_ops import normalize

if TYPE_CHECKING:
    from janim.gui.anim_viewer import AnimViewer

_ = get_translator('janim.gui.handlers.move')

SNAP_TOLERANCE = 0.04


def handler(viewer: AnimViewer, command: Timeline.GuiCommand) -> None:
    scripts = [script.strip() for script in command.body.split(',')]
    items = [
        parse_item(script, command.locals)
        for script in scripts
    ]

    jump(viewer, command)
    widget = MovePanel(viewer, command, scripts, items)
    widget.show()


class MovePanel(HandlerPanel):
    def __init__(self, viewer: AnimViewer, command: Timeline.GuiCommand, scripts: list[str], items: list[Item]):
        super().__init__(viewer, command)
        self.scripts = scripts
        self.items = items

        attrs = BasicAttrs(viewer)
        self.camera_info = attrs.camera_info

        self.boxes = [ItemBox(item, attrs) for item in items]
        self.history = History(self.boxes)

        self.x_snap: SnapMatch | None = None
        self.y_snap: SnapMatch | None = None

        rgb_avg = np.average(viewer.built.cfg.background_color.get_rgb())
        is_background_dark = rgb_avg < 0.5
        self.rect_brush_rgb = (255, 255, 255) if is_background_dark else (0, 0, 0)
        self.rect_inner_color = Qt.GlobalColor.black if is_background_dark else Qt.GlobalColor.white
        self.text_color = Qt.GlobalColor.black if is_background_dark else Qt.GlobalColor.white

        # setup ui

        label_tips = QLabel(
            _('Use mouse to drag items\n'
              'Hold Shift: Lock horizontal/vertical/diagonal directions\n'
              'Hold Ctrl: Disable auto-snapping'),
            self
        )

        self.diff = SourceDiff(command, self)

        self.btn_undo, self.btn_redo = get_undo_redo_buttons(self, self.on_undo, self.on_redo)
        self.update_btn_state()

        btn_box, btn_ok, btn_cancel = get_confirm_buttons(self)

        hlayout_bottom = QHBoxLayout()
        hlayout_bottom.addWidget(self.btn_undo)
        hlayout_bottom.addWidget(self.btn_redo)
        hlayout_bottom.addStretch()
        hlayout_bottom.addWidget(btn_box)

        vlayout = QVBoxLayout(self)
        vlayout.addWidget(label_tips)
        vlayout.addWidget(self.diff)
        vlayout.addStretch()
        vlayout.addLayout(hlayout_bottom)

        # setup slots

        btn_ok.clicked.connect(self.diff.submit)
        btn_cancel.clicked.connect(self.close)
        self.diff.submitted.connect(self.close_and_rebuild_timeline)

        # event filter

        self.dragging_box: ItemBox | None = None

        self.viewer.installEventFilter(self)
        self.viewer.glw.installEventFilter(self)
        self.viewer.overlay.installEventFilter(self)

    def on_undo(self) -> None:
        self.history.undo()
        self.handle_history_change()

    def on_redo(self) -> None:
        self.history.redo()
        self.handle_history_change()

    def handle_history_change(self) -> None:
        self.update_btn_state()
        self.update_replacement()
        self.update_overlay()

    def update_btn_state(self) -> None:
        self.btn_undo.setEnabled(self.history.undoable())
        self.btn_redo.setEnabled(self.history.redoable())

    def update_replacement(self) -> None:
        def get_line(script: str, item: Item, box: ItemBox) -> str:
            offx, offy = box.offset
            if item.is_fix_in_frame():
                return f'{script}.points.shift([{round(offx, 2)}, {round(offy, 2)}, 0])'
            hor = normalize(self.camera_info.horizontal_vect)
            ver = normalize(self.camera_info.vertical_vect)
            offset = (hor * offx + ver * offy) * box.distance_scale
            offset = np.round(offset.astype(np.float64), 2)
            return f'{script}.points.shift([{offset[0]}, {offset[1]}, {offset[2]}])'

        lines = [
            get_line(script, item, box)
            for script, item, box in zip(self.scripts, self.items, self.boxes)
            if np.any(box.offset != 0)
        ]
        self.diff.set_replacement('\n'.join(lines))

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.viewer.glw:
            if event.type() == QEvent.Type.MouseButtonPress:
                self.on_glw_mouse_press(event)
            if event.type() == QEvent.Type.MouseMove:
                self.on_glw_mouse_move(event)
            if event.type() == QEvent.Type.MouseButtonRelease:
                self.on_glw_mouse_release(event)

        if watched is self.viewer.overlay:
            if event.type() == QEvent.Type.Paint:
                self.on_overlay_paint(event)

        return super().eventFilter(watched, event)

    def on_glw_mouse_press(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        self.drag_start = event.position()
        self.dragging_box = self.select_box_at_position(self.drag_start)
        if self.dragging_box is None:
            return
        self.offset_start = self.dragging_box.offset.copy()
        self.dragged = False

    def on_glw_mouse_move(self, event: QMouseEvent) -> None:
        if event.buttons() != Qt.MouseButton.LeftButton:
            return
        if self.dragging_box is None:
            return

        glw = self.viewer.glw

        glpos = np.array(glw.map_to_gl2d(event.position())) - glw.map_to_gl2d(self.drag_start)
        shift = glpos * self.camera_info.frame_radius

        # 当按住 Shift 键时，锁定水平/垂直/对角线方向
        lock_direction = event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        if lock_direction:
            shift = compute_lock_directions_shift(shift)

        self.dragging_box.offset = self.offset_start + shift

        # 自动吸附
        if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            shift = self.auto_snapping(shift, lock_direction)

        self.dragged = True

        self.update_overlay()

    def on_glw_mouse_release(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self.dragging_box is None:
            return

        if self.dragged:
            self.history.save(self.boxes.index(self.dragging_box), self.offset_start, self.dragging_box.offset.copy())
            self.handle_history_change()
        self.dragging_box = None
        self.x_snap = None
        self.y_snap = None

    def select_box_at_position(self, position: QPointF) -> ItemBox | None:
        glpos = self.viewer.glw.map_to_gl2d(position)
        x, y = glpos * self.camera_info.frame_radius

        for box in reversed(self.boxes):
            if box.contains(x, y):
                return box
        return None

    def auto_snapping(self, shift: np.ndarray, lock_direction: bool) -> None:
        self.x_snap = None
        self.y_snap = None

        # 在 lock_direction 的时候，只允许 x,y 方向上同倍率拉伸，即可保持 lock_direction 效果
        if lock_direction:
            for box in self.boxes:
                if box is self.dragging_box:
                    continue
                match_x = self.dragging_box.snap_x_to(box)
                match_y = self.dragging_box.snap_y_to(box)
                factor_x = match_x.additional_factor(shift[0]) if match_x else None
                factor_y = match_y.additional_factor(shift[1]) if match_y else None
                # 如果两个都是 None，则说明完全没有匹配
                if factor_x is None and factor_y is None:
                    continue
                # 如果两个都匹配，则选择偏移量最小的那个，即，将偏移量更大的那个设置为 None
                if factor_x is not None and factor_y is not None:
                    if abs(match_x.delta) > abs(match_y.delta):
                        match_x = None
                    else:
                        match_y = None

                if match_x:
                    self.x_snap = match_x
                    factor = factor_x
                else:
                    self.y_snap = match_y
                    factor = factor_y

                self.dragging_box.offset += factor * shift
                break

        # 对于不是 lock_direction，可以在 x,y 方向上分别偏移
        else:
            for box in self.boxes:
                if box is self.dragging_box:
                    continue
                match = self.dragging_box.snap_x_to(box)
                if match is not None:
                    self.x_snap = match
                    self.dragging_box.offset[0] += match.delta
                    break

            for box in self.boxes:
                if box is self.dragging_box:
                    continue
                match = self.dragging_box.snap_y_to(box)
                if match is not None:
                    self.y_snap = match
                    self.dragging_box.offset[1] += match.delta
                    break

    def on_overlay_paint(self, event: QPaintEvent) -> None:
        p = QPainter(self.viewer.overlay)

        for script, box in zip(self.scripts, self.boxes):
            # ### 这部分是绘制当前正在拖动的框的原位置，用于参考

            if box is self.dragging_box:
                rect = self.get_screen_rect_of_box(box, offset=self.offset_start)

                # 绘制虚线边框
                self.set_dashed_pen(p, QColor(150, 150, 150, 200))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRect(rect)

            # ### 这部分是绘制各个框

            rect = self.get_screen_rect_of_box(box)

            # 绘制矩形
            p.setBrush(QColor(*self.rect_brush_rgb, 90))
            p.setPen(QPen(QColor(*self.rect_brush_rgb), 2))
            p.drawRect(rect)

            rect.adjust(1, 1, -1, -1)

            # 绘制内边框
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(self.rect_inner_color)
            p.drawRect(rect)

            rect.adjust(1, 1, -1, -1)

            # 计算文字的大小并绘制文字背景矩形
            text_bg_rect = p.fontMetrics().boundingRect(script)
            text_bg_rect.moveTo(int(rect.left()), int(rect.top()))
            text_bg_rect.adjust(-2, -2, 5, 3)

            p.setBrush(QColor(*self.rect_brush_rgb))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(text_bg_rect)

            # 绘制文字
            p.setPen(self.text_color)
            p.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, script)

        # 绘制 snap 标识线
        glw = self.viewer.glw
        frame_radius = self.camera_info.frame_radius

        if self.x_snap:
            x1 = glw.map_from_glx(self.x_snap.target / frame_radius[0])
            x2 = glw.map_from_glx(self.x_snap.target_base / frame_radius[0])

            self.set_dashed_pen(p, QColor(0, 255, 100))
            p.drawLine(x1, 0, x1, glw.height())

            self.set_dashed_pen(p, QColor(100, 200, 255))
            p.drawLine(x2, 0, x2, glw.height())

        if self.y_snap:
            y1 = glw.map_from_gly(self.y_snap.target / frame_radius[1])
            y2 = glw.map_from_gly(self.y_snap.target_base / frame_radius[1])

            self.set_dashed_pen(p, QColor(0, 255, 100))
            p.drawLine(0, y1, glw.width(), y1)

            self.set_dashed_pen(p, QColor(100, 200, 255))
            p.drawLine(0, y2, glw.width(), y2)

    def get_screen_rect_of_box(self, box: ItemBox, offset: np.ndarray | None = None) -> QRectF:
        if offset is None:
            offset = box.offset

        min_glpos, max_glpos = box.min_max_glpos(offset)

        glw = self.viewer.glw
        min_screen = glw.map_from_gl2d(*min_glpos)
        max_screen = glw.map_from_gl2d(*max_glpos)
        return QRectF(min_screen, max_screen).normalized()

    @staticmethod
    def set_dashed_pen(p: QPainter, color: QColor, pen_width: int = 2) -> None:
        pen = QPen(color, pen_width)
        pen.setStyle(Qt.PenStyle.CustomDashLine)
        pen.setDashPattern([2, 3])  # 6个单位实线，2个单位空白，增加占空比
        p.setPen(pen)


class History:
    def __init__(self, boxes: list[ItemBox]):
        self.boxes = boxes

        self.records: list[tuple[int, np.ndarray, np.ndarray]] = []
        self.ptr = 0

    def save(self, idx: int, old_offset: np.ndarray, new_offset: np.ndarray) -> None:
        record = (idx, old_offset, new_offset)
        if self.ptr == len(self.records):
            self.records.append(record)
        else:
            self.records[self.ptr] = record
        self.ptr += 1

    def undoable(self) -> bool:
        return self.ptr > 0

    def undo(self) -> None:
        if self.ptr > 0:
            self.ptr -= 1
            idx, old_offset, _ = self.records[self.ptr]
            self.boxes[idx].offset = old_offset

    def redoable(self) -> bool:
        return self.ptr < len(self.records)

    def redo(self) -> None:
        if self.ptr < len(self.records):
            idx, _, new_offset = self.records[self.ptr]
            self.boxes[idx].offset = new_offset
            self.ptr += 1


class ItemBox:
    """
    物件及其在视野坐标下的可选中范围
    """
    def __init__(self, item: Item, attrs: BasicAttrs):
        info = attrs.camera_info
        self.frame_radius = info.frame_radius

        # self.cls_name = item.__class__.__name__

        cmpt = item.current(as_time=attrs.global_t)(Points).points
        if attrs.is_camera_axis_simple or item.is_fix_in_frame():
            points = cmpt.box.get_corners()
        else:
            points = cmpt.get_all()

        if item.is_fix_in_frame():
            mapped = get_fixed_camera_info().map_points(points)
        else:
            mapped = info.map_points(points)

        self.min_x, self.min_y = np.nanmin(mapped, axis=0) * info.frame_radius
        self.max_x, self.max_y = np.nanmax(mapped, axis=0) * info.frame_radius

        # s - select
        self.min_sx, self.min_sy = (self.min_x, self.min_y) - attrs.tolerance
        self.max_sx, self.max_sy = (self.max_x, self.max_y) + attrs.tolerance

        # 由鼠标拖动导致的偏移量
        self.offset = np.array([0, 0])

        # 最终应用的时候需要考虑的向量缩放
        camera_direction = -normalize(info.camera_axis)
        self.distance_scale = np.dot(points[0] - info.camera_location, camera_direction) / info.distance_from_plane

    def contains(self, x: float, y: float) -> bool:
        offx, offy = self.offset
        return self.min_sx <= x - offx <= self.max_sx and self.min_sy <= y - offy <= self.max_sy

    @property
    def real_min_x(self) -> float:
        return self.min_x + self.offset[0]

    @property
    def real_max_x(self) -> float:
        return self.max_x + self.offset[0]

    @property
    def real_min_y(self) -> float:
        return self.min_y + self.offset[1]

    @property
    def real_max_y(self) -> float:
        return self.max_y + self.offset[1]

    def min_max_framepos(self, offset: np.ndarray | None) -> tuple[np.ndarray, np.ndarray]:
        if offset is None:
            offset = self.offset
        min_framepos = np.array([self.real_min_x, self.real_min_y])
        max_framepos = np.array([self.real_max_x, self.real_max_y])
        return (min_framepos, max_framepos)

    def min_max_glpos(self, offset: np.ndarray | None) -> tuple[np.ndarray, np.ndarray]:
        min_framepos, max_framepos = self.min_max_framepos(offset)
        min_glpos = min_framepos / self.frame_radius
        max_glpos = max_framepos / self.frame_radius
        return (min_glpos, max_glpos)

    def snap_x_to(self, other: ItemBox) -> SnapMatch:
        if (match := self._snap_min_mid_max(self.real_min_x, self.real_max_x, other.real_min_x, other.real_max_x)):
            return match
        if (match := self._snap_buff(self.real_min_x, other.real_max_x, 1)):
            return match
        if (match := self._snap_buff(self.real_max_x, other.real_min_x, -1)):
            return match

    def snap_y_to(self, other: ItemBox) -> SnapMatch:
        if (match := self._snap_min_mid_max(self.real_min_y, self.real_max_y, other.real_min_y, other.real_max_y)):
            return match
        if (match := self._snap_buff(self.real_min_y, other.real_max_y, 1)):
            return match
        if (match := self._snap_buff(self.real_max_y, other.real_min_y, -1)):
            return match

    @staticmethod
    def _snap_min_mid_max(self_min: float, self_max: float, other_min: float, other_max: float) -> SnapMatch | None:
        self_mid = (self_min + self_max) / 2
        other_mid = (other_min + other_max) / 2
        if abs(other_mid - self_mid) <= SNAP_TOLERANCE:
            return SnapMatch(self_mid, other_mid, other_mid)
        if abs(other_min - self_min) <= SNAP_TOLERANCE:
            return SnapMatch(self_min, other_min, other_min)
        if abs(other_max - self_max) <= SNAP_TOLERANCE:
            return SnapMatch(self_max, other_max, other_max)
        return None

    @staticmethod
    def _snap_buff(self_v: float, other_base: float, other_buff_sign: int) -> SnapMatch | None:
        for buff in (0, SMALL_BUFF, MED_SMALL_BUFF, MED_LARGE_BUFF, LARGE_BUFF):
            other_v = other_base + other_buff_sign * buff
            if abs(other_v - self_v) <= SNAP_TOLERANCE:
                return SnapMatch(self_v, other_v, other_base)
        return None


@dataclass
class SnapMatch:
    source: float
    target: float
    target_base: float

    @property
    def delta(self) -> float:
        return self.target - self.source

    def additional_factor(self, applied_delta: float) -> float | None:
        if np.isclose(applied_delta, 0):
            return None
        return self.delta / applied_delta


class BasicAttrs(SelectBasicAttrs):
    def __init__(self, viewer: AnimViewer):
        super().__init__(viewer)
        # 让 tolerance 基于视野坐标
        self.tolerance *= self.camera_info.frame_size


def compute_lock_directions_shift(shift: np.ndarray) -> np.ndarray:
    """
    计算锁定水平/垂直/对角线情况下的 ``shift``
    """
    x, y = shift
    # 以度为单位的角度
    angle = np.degrees(np.arctan2(abs(y), abs(x)))

    # 根据角度判断锁定方向
    # 0-22.5°: 水平, 22.5-67.5°: 对角线, 67.5-90°: 垂直
    if angle < 22.5:
        shift = np.array([x, 0.0])
    elif angle < 67.5:
        avg = (abs(x) + abs(y)) / 2
        shift = np.array([np.sign(x) * avg, np.sign(y) * avg])
    else:
        shift = np.array([0.0, y])

    return shift
