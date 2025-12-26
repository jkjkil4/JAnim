from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QIcon, QKeySequence, QLinearGradient,
                           QMouseEvent, QPainter, QPaintEvent, QPen, QShortcut)
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from janim.anims.timeline import Timeline
from janim.gui.handlers.select import BasicAttrs as SelectBasicAttrs
from janim.gui.handlers.select import get_fixed_camera_info
from janim.gui.handlers.utils import (HandlerPanel, SourceDiff,
                                      get_confirm_buttons, jump, parse_item)
from janim.items.item import Item
from janim.items.points import Points
from janim.locale.i18n import get_translator
from janim.utils.file_ops import get_gui_asset
from janim.utils.space_ops import normalize

if TYPE_CHECKING:
    from janim.gui.anim_viewer import AnimViewer

_ = get_translator('janim.gui.handlers.move')


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

        # setup ui

        label_tips = QLabel(
            _('Use mouse to drag items\n'
              '(Not implemented) Hold Shift: Lock horizontal/vertical/diagonal directions\n'
              'Hold Ctrl: Disable (Not implemented) auto-snapping'),
            self
        )

        self.diff = SourceDiff(command, self)

        self.btn_undo = QPushButton(self)
        self.btn_undo.setIcon(QIcon(get_gui_asset('undo.png')))
        self.btn_undo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_redo = QPushButton(self)
        self.btn_redo.setIcon(QIcon(get_gui_asset('redo.png')))
        self.btn_redo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.update_btn_state()

        sc_undo = QShortcut(QKeySequence('Ctrl+Z'), self)
        sc_undo.setContext(Qt.ShortcutContext.ApplicationShortcut)

        sc_redo = QShortcut(QKeySequence('Ctrl+Shift+Z'), self)
        sc_redo.setContext(Qt.ShortcutContext.ApplicationShortcut)

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

        self.btn_undo.clicked.connect(self.on_btn_undo_clicked)
        self.btn_redo.clicked.connect(self.on_btn_redo_clicked)
        sc_undo.activated.connect(self.on_btn_undo_clicked)
        sc_redo.activated.connect(self.on_btn_redo_clicked)

        btn_ok.clicked.connect(self.diff.submit)
        btn_cancel.clicked.connect(self.close)
        self.diff.submitted.connect(self.close_and_rebuild_timeline)

        # event filter

        self.viewer.installEventFilter(self)
        self.viewer.glw.installEventFilter(self)
        self.viewer.overlay.installEventFilter(self)

    def on_btn_undo_clicked(self) -> None:
        self.history.undo()
        self.update_btn_state()
        self.update_replacement()
        self.update_overlay()

    def on_btn_redo_clicked(self) -> None:
        self.history.redo()
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
            offset = np.round(hor * offx + ver * offy, 2)
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
        self.dragging_box.offset = self.offset_start + shift
        self.dragged = True

        self.viewer.overlay.update()

    def on_glw_mouse_release(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self.dragging_box is None:
            return

        if self.dragged:
            self.history.save(self.boxes.index(self.dragging_box), self.offset_start, self.dragging_box.offset.copy())
            self.update_btn_state()
            self.update_replacement()
        self.dragging_box = None

    def select_box_at_position(self, position: QPointF) -> ItemBox | None:
        glpos = self.viewer.glw.map_to_gl2d(position)
        x, y = glpos * self.camera_info.frame_radius

        for box in reversed(self.boxes):
            if box.contains(x, y):
                return box
        return None

    def on_overlay_paint(self, event: QPaintEvent) -> None:
        glw = self.viewer.glw

        p = QPainter(self.viewer.overlay)

        for box in self.boxes:
            # 转换坐标
            min_glpos = np.array([box.min_x + box.offset[0], box.min_y + box.offset[1]]) / self.camera_info.frame_radius
            max_glpos = np.array([box.max_x + box.offset[0], box.max_y + box.offset[1]]) / self.camera_info.frame_radius

            min_screen = glw.map_from_gl2d(*min_glpos)
            max_screen = glw.map_from_gl2d(*max_glpos)
            rect = QRectF(min_screen, max_screen).normalized()

            # 填充渐变
            fill_gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
            fill_gradient.setColorAt(0, QColor(255, 255, 255, 140))
            fill_gradient.setColorAt(1, QColor(0, 0, 0, 140))

            # 描边渐变
            border_gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
            border_gradient.setColorAt(0, QColor(80, 80, 80, 255))
            border_gradient.setColorAt(1, QColor(175, 175, 175, 255))

            # 绘制矩形
            p.setBrush(fill_gradient)
            p.setPen(QPen(border_gradient, 2))
            p.drawRect(rect)

            # 绘制文字
            p.setPen(QColor(255, 255, 255, 255))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, box.cls_name)


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
        self.cls_name = item.__class__.__name__

        cmpt = item.current(as_time=attrs.global_t)(Points).points
        if attrs.is_camera_axis_simple or item.is_fix_in_frame():
            points = cmpt.box.get_corners()
        else:
            points = cmpt.get_all()

        if item.is_fix_in_frame():
            mapped = get_fixed_camera_info().map_points(points)
        else:
            mapped = attrs.camera_info.map_points(points)

        self.min_x, self.min_y = np.nanmin(mapped, axis=0) * attrs.camera_info.frame_radius
        self.max_x, self.max_y = np.nanmax(mapped, axis=0) * attrs.camera_info.frame_radius

        # s - select
        self.min_sx, self.min_sy = (self.min_x, self.min_y) - attrs.tolerance
        self.max_sx, self.max_sy = (self.max_x, self.max_y) + attrs.tolerance

        self.offset = np.array([0, 0])

    def contains(self, x: float, y: float) -> bool:
        offx, offy = self.offset
        return self.min_sx <= x - offx <= self.max_sx and self.min_sy <= y - offy <= self.max_sy


class BasicAttrs(SelectBasicAttrs):
    def __init__(self, viewer: AnimViewer):
        super().__init__(viewer)
        # 让 tolerance 基于视野坐标
        self.tolerance *= self.camera_info.frame_size
