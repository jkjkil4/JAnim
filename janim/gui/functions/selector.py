from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent

from janim.items.item import Item
from janim.items.points import Points
from janim.locale.i18n import get_local_strings

if TYPE_CHECKING:
    from janim.camera.camera_info import CameraInfo
    from janim.gui.anim_viewer import AnimViewer

_ = get_local_strings('selector')


class Selector(QObject):
    '''
    子物件选择工具
    '''
    @dataclass
    class SelectedItem:
        item: Item
        min_glx: float
        min_gly: float
        max_glx: float
        max_gly: float

    def __init__(self, parent: AnimViewer) -> None:
        super().__init__(parent)
        self.viewer = parent

        self.viewer.glw.installEventFilter(self)
        self.viewer.overlay.installEventFilter(self)

        self.clear()
        self.painted_cursor_flag: bool = True
        self.fixed_camera_info: CameraInfo | None = None

    def clear(self) -> None:
        self.current: Selector.SelectedItem | None = None
        self.children: list[Selector.SelectedItem] = []
        self.selected_children: list[Selector.SelectedItem] = []
        self.viewer.overlay.update()

    def get_fixed_camera_info(self) -> CameraInfo:
        if self.fixed_camera_info is not None:
            return self.fixed_camera_info

        from janim.camera.camera import Camera
        info = Camera().points.info

        self.fixed_camera_info = info
        return info

    def glx_to_overlay_x(self, glx: float) -> float:
        return (glx + 1) / 2 * self.viewer.overlay.width()

    def gly_to_overlay_y(self, gly: float) -> float:
        return (-gly + 1) / 2 * self.viewer.overlay.height()

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
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            match event.button():
                case Qt.MouseButton.LeftButton:
                    self.select_parent_item(event)
                case Qt.MouseButton.RightButton:
                    self.deleteLater()
        else:
            match event.button():
                case Qt.MouseButton.LeftButton:
                    self.select_child_item(event)
                case Qt.MouseButton.RightButton:
                    self.remove_child_item(event)

        self.viewer.overlay.update()

    def on_glw_mouse_move(self, event: QMouseEvent) -> None:
        cursor_flag = self.compute_cursor_flag()
        if cursor_flag != self.painted_cursor_flag:
            self.viewer.overlay.update()

        if not event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            match event.buttons():
                case Qt.MouseButton.LeftButton:
                    self.select_child_item(event)
                case Qt.MouseButton.RightButton:
                    self.remove_child_item(event)

            self.viewer.overlay.update()

    def select_parent_item(self, event: QMouseEvent) -> None:
        self.children.clear()
        self.selected_children.clear()

        glx, gly = self.viewer.glw.map_to_gl2d(event.position())

        built = self.viewer.built
        global_t = built._time
        camera_info = built.current_camera_info()

        found: list[Selector.SelectedItem] = []

        tolerance = np.array([6 / self.viewer.glw.width(), 6 / self.viewer.glw.height()])

        for item, appr in built.visible_item_segments.get(global_t):
            if not appr.is_visible_at(global_t):
                continue
            box = item.current(as_time=global_t)(Points).points.box

            if item.is_fix_in_frame():
                mapped = self.get_fixed_camera_info().map_points(box.get_corners())
            else:
                mapped = camera_info.map_points(box.get_corners())
            min_glx, min_gly = mapped.min(axis=0) - tolerance
            max_glx, max_gly = mapped.max(axis=0) + tolerance
            if not min_glx <= glx <= max_glx or not min_gly <= gly <= max_gly:
                continue

            found.append(Selector.SelectedItem(item, min_glx, min_gly, max_glx, max_gly))

        if not found:
            self.current = None
        else:
            if self.current is None or self.current not in found:
                self.current = found[0]
            else:
                idx = found.index(self.current)
                self.current = found[(idx + 1) % len(found)]

            for item in self.current.item.get_children():
                box = item.current(as_time=global_t)(Points).points.box
                if item.is_fix_in_frame():
                    mapped = self.get_fixed_camera_info().map_points(box.get_corners())
                else:
                    mapped = camera_info.map_points(box.get_corners())
                self.children.append(
                    Selector.SelectedItem(
                        item,
                        *(mapped.min(axis=0) - tolerance),
                        *(mapped.max(axis=0) + tolerance)
                    )
                )

    def select_child_item(self, event: QMouseEvent) -> None:
        glx, gly = self.viewer.glw.map_to_gl2d(event.position())

        for child in self.children:
            if child in self.selected_children:
                continue
            if not child.min_glx <= glx <= child.max_glx or not child.min_gly <= gly <= child.max_gly:
                continue
            self.selected_children.append(child)

    def remove_child_item(self, event: QMouseEvent) -> None:
        glx, gly = self.viewer.glw.map_to_gl2d(event.position())

        for child in self.selected_children:
            if not child.min_glx <= glx <= child.max_glx or not child.min_gly <= gly <= child.max_gly:
                continue
            self.selected_children.remove(child)

    def compute_cursor_flag(self) -> bool:
        '''
        ``True`` 表示鼠标在画面上半部，反之在下半部
        '''
        glw = self.viewer.glw
        cursor_pos = glw.mapFromGlobal(glw.cursor().pos())
        return cursor_pos.y() < glw.height() / 2

    def on_overlay_paint(self, event: QPaintEvent) -> None:
        rect = self.viewer.overlay.rect().adjusted(2, 2, -2, -2)

        p = QPainter(self.viewer.overlay)

        ranges: list[tuple[float, float]] = []
        if self.selected_children:
            range_start = None
            range_end = None

            for i, child in enumerate(self.children):
                if child in self.selected_children:
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
            ranges.append((range_start, range_end))

        txt_list = [
            _('Subitem Selection Tool'),
            _('    Ctrl+Left Click: Select Parent Item'),
            _('    Left Click: Select Child Item'),
            _('    Right Click: Deselect Child Item'),
            _('    Ctrl+Right Click: Exit'),
            _('Selected Parent Item: ') + (
                'None'
                if self.current is None
                else f'{self.current.item.__class__.__name__} at 0x{id(self.current.item):X}'
            ),
            _('Selected Subitems: ') + ', '.join(
                (
                    f'[{range[0]}]'
                    if range[0] + 1 == range[1]
                    else f'[{range[0]}:{range[1]}]'
                )
                for range in ranges
            )
        ]

        if self.current is not None:
            p.setBrush(QColor(195, 131, 19, 32))
            p.setPen(QColor(195, 131, 19))
            p.drawRect(
                QRectF(
                    QPointF(self.glx_to_overlay_x(self.current.min_glx), self.gly_to_overlay_y(self.current.min_gly)),
                    QPointF(self.glx_to_overlay_x(self.current.max_glx), self.gly_to_overlay_y(self.current.max_gly))
                )
            )

            p.setBrush(QColor(194, 102, 219, 64))
            p.setPen(QColor(194, 102, 219))
            for child in self.selected_children:
                p.drawRect(
                    QRectF(
                        QPointF(self.glx_to_overlay_x(child.min_glx), self.gly_to_overlay_y(child.min_gly)),
                        QPointF(self.glx_to_overlay_x(child.max_glx), self.gly_to_overlay_y(child.max_gly))
                    )
                )

        p.setPen(Qt.GlobalColor.white)

        glw = self.viewer.glw
        # 只有当鼠标在窗口内时才更新字的位置
        if glw.rect().contains(glw.mapFromGlobal(glw.cursor().pos())):
            self.painted_cursor_flag = self.compute_cursor_flag()
        valign = Qt.AlignmentFlag.AlignBottom if self.painted_cursor_flag else Qt.AlignmentFlag.AlignTop
        p.drawText(rect, Qt.AlignmentFlag.AlignLeft | valign, '\n'.join(txt_list))
