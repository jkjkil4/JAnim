from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QEvent, QObject, QPointF, Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout

from janim.anims.timeline import Timeline
from janim.camera.camera import Camera
from janim.constants import DEGREES, PI, RIGHT, TAU
from janim.exception import GuiCommandError
from janim.gui.handlers.utils import (HandlerPanel, SourceDiff,
                                      get_confirm_buttons,
                                      get_undo_redo_buttons, jump, parse_item)
from janim.locale.i18n import get_translator

if TYPE_CHECKING:
    from janim.gui.anim_viewer import AnimViewer

_ = get_translator('janim.gui.handlers.camera')

# 每像素对应 0.4 度
DELTA_TO_RADIAN_RATIO = 0.4 * DEGREES


def handler(viewer: AnimViewer, command: Timeline.GuiCommand) -> None:
    if command.body:
        camera = parse_item(command.body, command.locals)
        if not isinstance(camera, Camera):
            raise GuiCommandError(
                _('The item from "{script}" is not a Camera, found {type}')
                .format(script=command.body, type=camera.__class__.__name__)
            )
    else:
        camera = viewer.built.timeline.camera

    jump(viewer, command)
    widget = CameraPanel(viewer, command, camera)
    widget.show()


class CameraPanel(HandlerPanel):
    def __init__(self, viewer: AnimViewer, command: Timeline.GuiCommand, camera: Camera):
        super().__init__(viewer, command)
        self.camera = camera.store()
        self.active_camera = self.camera.store()
        self.history = History(self.camera)

        self.viewer.glw.inject_camera = self.active_camera

        # setup ui

        label_tips = QLabel(
            _('Drag the mouse in the viewport to adjust the camera angle\n'
              'Hold Ctrl: Rotate in place'),
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

        self.setLayout(vlayout)

        # setup slots

        btn_ok.clicked.connect(self.diff.submit)
        btn_cancel.clicked.connect(self.close)
        self.diff.submitted.connect(self.close_and_rebuild_timeline)

        # throttle re-render

        self.throttle_timer = QTimer(self, singleShot=True, interval=1000 // viewer.built.cfg.preview_fps)
        self.throttle_timer.timeout.connect(self.update_glw)

        # event filter

        self.viewer.glw.installEventFilter(self)

    def on_undo(self) -> None:
        self.history.undo()
        self.active_camera.restore(self.camera)
        self.handle_history_change()

    def on_redo(self) -> None:
        self.history.redo()
        self.active_camera.restore(self.camera)
        self.handle_history_change()

    def handle_history_change(self) -> None:
        self.update_btn_state()
        self.update_replacement()
        self.throttle_update_glw()

    def update_btn_state(self) -> None:
        self.btn_undo.setEnabled(self.history.undoable())
        self.btn_redo.setEnabled(self.history.redoable())

    def update_replacement(self) -> None:
        target = self.command.body or 'self.camera'

        elements = self.active_camera.points.orientation.elements
        params = ', '.join(map(str, np.round(elements, 2)))

        self.diff.set_replacement(f'{target}.points.set(orientation=Quaternion({params}))')

    def throttle_update_glw(self) -> None:
        if not self.throttle_timer.isActive():
            self.throttle_timer.start()

    def closeEvent(self, event):
        super().closeEvent(event)

        self.viewer.glw.inject_camera = None

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.viewer.glw:
            match event.type():
                case QEvent.Type.MouseButtonPress:
                    self.on_glw_mouse_press(event)
                case QEvent.Type.MouseMove:
                    self.on_glw_mouse_move(event)
                case QEvent.Type.MouseButtonRelease:
                    self.on_glw_mouse_release(event)

        return super().eventFilter(watched, event)

    def on_glw_mouse_press(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        self.drag_start_pos = event.position()
        self.drag_start_angle = self.get_angle_on_position(event.position())

    def on_glw_mouse_move(self, event: QMouseEvent) -> None:
        if event.buttons() != Qt.MouseButton.LeftButton:
            return

        self.active_camera.restore(self.camera)
        self.apply_change_on_camera(self.active_camera, event)

        self.throttle_update_glw()

    def on_glw_mouse_release(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self.drag_start_pos == event.position():
            return

        self.apply_change_on_camera(self.camera, event)
        self.history.save(self.camera.store())
        self.handle_history_change()

    def get_angle_on_position(self, position: QPointF) -> float:
        center = self.viewer.glw.rect().center()
        return math.atan2(position.y() - center.y(), position.x() - center.x())

    def apply_change_on_camera(self, camera: Camera, event: QMouseEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            angle = self.get_angle_on_position(event.position())
            delta = simplify_angle_delta(angle, self.drag_start_angle)
            rotate_camera_in_place(camera, delta)
        else:
            rotate_camera_by_shift(camera, event.position() - self.drag_start_pos)


class History:
    def __init__(self, camera: Camera):
        self.camera = camera

        self.records: list[Camera] = [camera.store()]
        self.ptr = 1

    def save(self, state: Camera) -> None:
        if self.ptr == len(self.records):
            self.records.append(state)
        else:
            self.records[self.ptr] = state
        self.ptr += 1

    def undoable(self) -> bool:
        return self.ptr > 1

    def undo(self) -> None:
        if self.ptr > 1:
            self.ptr -= 1
            state = self.records[self.ptr - 1]
            self.camera.restore(state)

    def redoable(self) -> bool:
        return self.ptr < len(self.records)

    def redo(self) -> None:
        if self.ptr < len(self.records):
            state = self.records[self.ptr]
            self.camera.restore(state)
            self.ptr += 1


def rotate_camera_by_shift(camera: Camera, shift: QPointF) -> None:
    x, y = get_radian_by_shift(shift)
    camera.points.rotate(-y, axis=RIGHT, absolute=False)
    camera.points.rotate(-x)


def get_radian_by_shift(delta: QPointF) -> tuple[float, float]:
    radian = delta * DELTA_TO_RADIAN_RATIO
    return (round(radian.x(), 2), round(radian.y(), 2))


def rotate_camera_in_place(camera: Camera, angle: float) -> None:
    camera.points.rotate(-angle, absolute=False)


def simplify_angle_delta(angle1: float, angle2: float) -> float:
    """
    简化两角 ``delta`` 的数值
    """
    if angle2 > angle1 + PI:
        angle2 -= TAU
    elif angle2 < angle1 - PI:
        angle2 += TAU
    return round(angle2 - angle1, 2)
