from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QObject, QRectF, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent

from janim.gui.handlers.select import (ItemBox, compute_boxes_of_children,
                                       select_next_item_at_position)
from janim.locale.i18n import get_translator

if TYPE_CHECKING:
    from janim.camera.camera_info import CameraInfo
    from janim.gui.anim_viewer import AnimViewer

_ = get_translator('janim.gui.functions.selector')


class Selector(QObject):
    """
    子物件选择工具
    """

    def __init__(self, parent: AnimViewer) -> None:
        super().__init__(parent)
        self.viewer = parent

        self.viewer.glw.installEventFilter(self)
        self.viewer.overlay.installEventFilter(self)

        self.clear()
        self.painted_cursor_flag: bool = True
        self.fixed_camera_info: CameraInfo | None = None

    def clear(self) -> None:
        self.current: ItemBox | None = None
        self.children: list[ItemBox] = []
        self.selected_children: list[ItemBox] = []
        self.viewer.overlay.update()

    def get_fixed_camera_info(self) -> CameraInfo:
        if self.fixed_camera_info is not None:
            return self.fixed_camera_info

        from janim.camera.camera import Camera
        info = Camera().points.info

        self.fixed_camera_info = info
        return info

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

        self.current = select_next_item_at_position(self.viewer, event.position(), self.current)
        if self.current is not None:
            self.children = compute_boxes_of_children(self.viewer, self.current.item)

    def select_child_item(self, event: QMouseEvent) -> None:
        glx, gly = self.viewer.glw.map_to_gl2d(event.position())

        for child in self.children:
            if child in self.selected_children:
                continue
            if not child.contains(glx, gly):
                continue
            self.selected_children.append(child)

    def remove_child_item(self, event: QMouseEvent) -> None:
        glx, gly = self.viewer.glw.map_to_gl2d(event.position())

        for child in self.selected_children:
            if not child.contains(glx, gly):
                continue
            self.selected_children.remove(child)

    def compute_cursor_flag(self) -> bool:
        """
        ``True`` 表示鼠标在画面上半部，反之在下半部
        """
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

        glw = self.viewer.glw

        if self.current is not None:
            p.setBrush(QColor(195, 131, 19, 32))
            p.setPen(QColor(195, 131, 19))
            p.drawRect(
                QRectF(
                    glw.map_from_gl2d(self.current.min_glx, self.current.min_gly),
                    glw.map_from_gl2d(self.current.max_glx, self.current.max_gly)
                )
            )

            p.setBrush(QColor(194, 102, 219, 64))
            p.setPen(QColor(194, 102, 219))
            for child in self.selected_children:
                p.drawRect(
                    QRectF(
                        glw.map_from_gl2d(child.min_glx, child.min_gly),
                        glw.map_from_gl2d(child.max_glx, child.max_gly)
                    )
                )

        p.setPen(Qt.GlobalColor.white)

        glw = self.viewer.glw
        # 只有当鼠标在窗口内时才更新字的位置
        if glw.rect().contains(glw.mapFromGlobal(glw.cursor().pos())):
            self.painted_cursor_flag = self.compute_cursor_flag()
        valign = Qt.AlignmentFlag.AlignBottom if self.painted_cursor_flag else Qt.AlignmentFlag.AlignTop
        p.drawText(rect, Qt.AlignmentFlag.AlignLeft | valign, '\n'.join(txt_list))
