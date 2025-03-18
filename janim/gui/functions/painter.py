from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QEvent, QObject, QPointF, Qt
from PySide6.QtGui import (QColor, QMouseEvent, QPainter, QPainterPath,
                           QPaintEvent, QPen)
from PySide6.QtWidgets import (QGroupBox, QHBoxLayout, QLabel, QRadioButton,
                               QScrollArea, QSlider, QTabWidget, QVBoxLayout,
                               QWidget)

from janim.camera.camera_info import CameraInfo
from janim.constants import DOWN, LEFT, RIGHT, UP
from janim.gui.functions.text_edit import TextEdit
from janim.locale.i18n import get_local_strings
from janim.utils.bezier import approx_smooth_quadratic_bezier_handles
from janim.utils.iterables import resize_preserving_head_and_tail

if TYPE_CHECKING:
    from janim.gui.anim_viewer import AnimViewer

_ = get_local_strings('painter')

POS_PER_LINE = 5


class Painter(QWidget):
    def __init__(self, parent: AnimViewer):
        super().__init__(parent)
        self.viewer = parent

        self.setup_ui()
        self.viewer.glw.installEventFilter(self)
        self.viewer.overlay.installEventFilter(self)

        self.tabs.currentChanged.connect(self.on_current_changed)
        self.tabs.tabCloseRequested.connect(self.on_close_requested)

        self.constructing: Painter.Widget | None = None

    def setup_ui(self) -> None:
        layout = QVBoxLayout()

        note = QLabel(_('Note: This is used to determine the position on the screen. '
                        'To actually add the drawn content, you need to manually add the corresponding code.'))
        note.setWordWrap(True)
        layout.addWidget(note)

        box = self.setup_box()
        layout.addWidget(box)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        layout.addWidget(self.tabs, 1)

        self.setLayout(layout)
        self.setStyleSheet('QScrollArea#itemWidget { border: none; }')
        self.setWindowTitle(_('Draw'))
        self.resize(650, 300)

    def setup_box(self) -> QGroupBox:
        layout = QHBoxLayout()
        layout.setSpacing(10)

        self.rdb_none = QRadioButton(_('None'))
        self.rdb_none.setChecked(True)

        self.rdb_dot = QRadioButton('Dot')
        self.rdb_rect = QRadioButton('Rect')
        self.rdb_path = QRadioButton('VItem' + _('(freehand-path)'))

        for w in (self.rdb_none, self.rdb_dot, self.rdb_rect, self.rdb_path):
            layout.addWidget(w)
        layout.addStretch()

        box = QGroupBox(_('Type'))
        box.setLayout(layout)
        return box

    def on_current_changed(self, index: int) -> None:
        self.viewer.overlay.update()

    def on_close_requested(self, index: int) -> None:
        self.tabs.removeTab(index)
        self.viewer.overlay.update()

    def is_none(self) -> bool:
        return self.rdb_none.isChecked()

    def compute_pos(self, point: QPointF) -> np.ndarray:
        glx, gly = self.viewer.glw.map_to_gl2d(point)
        info = self.viewer.built.current_camera_info()

        center = info.center
        hvec_half = info.horizontal_vect / 2
        vvec_half = info.vertical_vect / 2

        pos = center + hvec_half * glx + vvec_half * gly
        return pos

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.viewer.glw:
            match event.type():
                case QEvent.Type.MouseButtonPress:
                    self.on_glw_mouse_press(event)
                case QEvent.Type.MouseMove:
                    self.on_glw_mouse_move(event)
                case QEvent.Type.MouseButtonRelease:
                    self.on_glw_mouse_release(event)

        if watched is self.viewer.overlay:
            if event.type() is QEvent.Type.Paint:
                self.on_overlay_paint(event)

        return super().eventFilter(watched, event)

    def on_glw_mouse_press(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        pos = self.compute_pos(event.position())

        if self.is_none():
            widget: Painter.Widget = self.tabs.currentWidget()
            if widget is not None:
                widget.pressed(pos)
                self.viewer.overlay.update()
            return

        if self.rdb_dot.isChecked():
            self.constructing = self.PDot(self.viewer)
        elif self.rdb_rect.isChecked():
            self.constructing = self.PRect(self.viewer)
        elif self.rdb_path.isChecked():
            self.constructing = self.PVItem(self.viewer)
        else:
            assert False

        self.constructing.start(pos)
        self.viewer.overlay.update()

    def on_glw_mouse_move(self, event: QMouseEvent) -> None:
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return

        pos = self.compute_pos(event.position())

        if self.constructing is None:
            assert self.is_none()
            widget: Painter.Widget = self.tabs.currentWidget()
            if widget is not None:
                widget.moved(pos)
        else:
            self.constructing.append(pos)

        self.viewer.overlay.update()

    def on_glw_mouse_release(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self.constructing is None:
            assert self.is_none()
            widget: Painter.Widget = self.tabs.currentWidget()
            if widget is not None:
                widget.released()
        else:
            self.constructing.finish()

            self.rdb_none.setChecked(True)
            self.tabs.addTab(self.constructing, self.constructing.__class__.__name__.lstrip('P'))
            self.tabs.setCurrentWidget(self.constructing)
            self.constructing = None

        self.viewer.overlay.update()

    def on_overlay_paint(self, event: QPaintEvent) -> None:
        p = QPainter(self.viewer.overlay)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        info = self.viewer.built.current_camera_info()

        if self.constructing is not None:
            self.constructing.paint(p, info, True)

        current_widget = self.tabs.currentWidget()

        for i in range(self.tabs.count()):
            widget: Painter.Widget = self.tabs.widget(i)
            widget.paint(p, info, widget is current_widget)

    class Widget(QScrollArea):
        def __init__(self, viewer: AnimViewer):
            super().__init__()
            self.setWidgetResizable(True)
            self.setObjectName('itemWidget')
            self.viewer = viewer

        def start(self, pos: np.ndarray) -> None: ...
        def append(self, pos: np.ndarray) -> None: ...
        def finish(self) -> None: ...

        def pressed(self, pos: np.ndarray) -> None: ...
        def moved(self, pos: np.ndarray) -> None: ...
        def released(self) -> None: ...

        def paint(self, p: QPainter, info: CameraInfo, is_active: bool) -> None: ...

    class PDot(Widget):
        def start(self, pos: np.ndarray) -> None:
            self.moved(pos)

        def append(self, pos: np.ndarray) -> None:
            self.moved(pos)

        def finish(self) -> None:
            self.code = TextEdit()
            self.code.setLineWrapMode(TextEdit.LineWrapMode.NoWrap)

            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.code)
            self.setLayout(layout)

            self.update_code()

        def update_code(self) -> None:
            self.code.setPlainText(f'Dot({_glpos_to_str(self.glpos)})')

        def pressed(self, pos: np.ndarray) -> None:
            self.moved(pos)

        def moved(self, pos: np.ndarray) -> None:
            self.glpos = pos

        def released(self) -> None:
            self.update_code()

        def paint(self, p: QPainter, info: CameraInfo, is_active: bool) -> None:
            p.setPen(Qt.PenStyle.NoPen)
            if is_active:
                p.setBrush(Qt.GlobalColor.yellow)
            else:
                p.setBrush(QColor(255, 255, 255, 128))

            p.drawEllipse(self.viewer.glw.map_to_widget(*info.map_points([self.glpos])[0]),
                          3, 3)

    # TODO: 3d
    class PRect(Widget):
        def start(self, pos: np.ndarray) -> None:
            self.pos1 = self.pos2 = pos

        def append(self, pos: np.ndarray) -> None:
            self.pos2 = pos

        def finish(self) -> None:
            self.center = (self.pos1 + self.pos2) / 2

            self.code = TextEdit()
            self.code.setLineWrapMode(TextEdit.LineWrapMode.NoWrap)

            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.code)
            self.setLayout(layout)

            self.update_code()

        def pressed(self, pos: np.ndarray) -> None:
            self.moved(pos)

        def moved(self, pos: np.ndarray) -> None:
            offset = pos - self.center
            self.pos1 += offset
            self.pos2 += offset
            self.center = pos

        def released(self) -> None:
            self.update_code()

        def update_code(self) -> None:
            self.code.setPlainText(f'Rect({_glpos_to_str(self.pos1)}, {_glpos_to_str(self.pos2)})')

        def paint(self, p: QPainter, info: CameraInfo, is_active: bool) -> None:
            p.setPen(Qt.PenStyle.NoPen)
            if is_active:
                p.setBrush(QColor(255, 255, 0, 180))
            else:
                p.setBrush(QColor(255, 255, 255, 128))

            ul = np.array([min(v1, v2) for v1, v2 in zip(self.pos1, self.pos2)])
            dr = np.array([max(v1, v2) for v1, v2 in zip(self.pos1, self.pos2)])
            w_half, h_half = (dr - ul)[:2] / 2
            center = (ul + dr) / 2

            points = [
                center + x * w_half + y * h_half
                for x in (LEFT, RIGHT)
                for y in (DOWN, UP)
            ]
            points = [self.viewer.glw.map_to_widget(x, y) for x, y in info.map_points(points)]

            path = QPainterPath()
            path.moveTo(points[0])
            path.lineTo(points[1])
            path.lineTo(points[3])
            path.lineTo(points[2])
            path.closeSubpath()

            p.drawPath(path)

    class PVItem(Widget):
        def __init__(self, viewer: AnimViewer):
            super().__init__(viewer)
            self.path: list[np.ndarray] = []
            self.orig_array: np.ndarray | None = None

        def start(self, pos: np.ndarray) -> None:
            self.append(pos)

        def append(self, pos: np.ndarray) -> None:
            self.path.append(pos)
            self.update_array()

        def finish(self) -> None:
            if len(self.path) < 3:
                self.deleteLater()
                return

            if len(self.path) % 2 == 0:
                self.path.append(self.path[-1])
            self.orig_array = np.array(self.path)
            mins = np.min(self.orig_array, axis=0)
            maxs = np.max(self.orig_array, axis=0)
            self.center = (mins + maxs) / 2

            self.name = QLabel(_('Count'))
            self.label = QLabel()

            self.sd_count = QSlider(Qt.Orientation.Horizontal)
            self.sd_count.setMinimum(3)
            self.sd_count.setMaximum(len(self.orig_array))

            count_layout = QHBoxLayout()
            count_layout.addWidget(self.name)
            count_layout.addWidget(self.sd_count)
            count_layout.addWidget(self.label)

            self.code = TextEdit()
            self.code.setLineWrapMode(TextEdit.LineWrapMode.NoWrap)

            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addLayout(count_layout)
            layout.addWidget(self.code)

            self.setLayout(layout)

            self.sd_count.valueChanged.connect(self.on_count_changed)
            self.sd_count.setValue(len(self.orig_array))

            self.update_array()
            self.update_code()

        def on_count_changed(self, value: int) -> None:
            if value % 2 == 0:
                value += 1
            self.label.setText(f'{value / len(self.orig_array) * 100:.0f}%')
            self.update_array()
            self.update_code()

        def pressed(self, pos: np.ndarray) -> None:
            self.moved(pos)

        def moved(self, pos: np.ndarray) -> None:
            offset = pos - self.center
            self.orig_array += offset
            self.array += offset
            self.center = pos

        def released(self) -> None:
            self.update_code()

        def update_code(self) -> None:
            points = '\n'.join([
                '    ' + ', '.join([_glpos_to_str(pos) for pos in self.array[i: i + POS_PER_LINE]]) + ','
                for i in range(0, len(self.array), POS_PER_LINE)
            ])
            self.code.setPlainText(f'VItem(\n{points}\n)')

        def update_array(self) -> None:
            if self.orig_array is None:
                if len(self.path) % 2 == 0:
                    self.array = self.path[:-1]
                else:
                    self.array = self.path

            else:
                value = self.sd_count.value()
                if value % 2 == 0:
                    value += 1
                if len(self.orig_array) == value:
                    self.array = self.orig_array.copy()
                else:
                    self.array = resize_preserving_head_and_tail(self.orig_array, value)
                self.array[1::2] = approx_smooth_quadratic_bezier_handles(self.array[::2])
                self.viewer.overlay.update()

        def paint(self, p: QPainter, info: CameraInfo, is_active: bool) -> None:
            p.setBrush(Qt.BrushStyle.NoBrush)
            if is_active:
                p.setPen(QPen(Qt.GlobalColor.yellow, 3))
            else:
                p.setPen(QPen(QColor(255, 255, 255, 128), 3))

            mapped = [self.viewer.glw.map_to_widget(x, y) for x, y in info.map_points(self.array)]

            path = QPainterPath(mapped[0])
            for i in range(len(mapped) // 2):
                path.quadTo(mapped[i * 2 + 1], mapped[i * 2 + 2])

            p.drawPath(path)


def _glpos_to_str(pos: np.ndarray) -> str:
    s = ', '.join(map(lambda coord: f'{coord:.2f}'.rstrip('0').rstrip('.'), pos))
    return f'[{s}]'
