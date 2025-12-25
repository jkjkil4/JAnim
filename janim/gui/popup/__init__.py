from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QWidget

from janim.gui.popup.color_widget import ColorWidget
from janim.gui.popup.font_table import FontTable
from janim.gui.popup.painter import Painter
from janim.gui.popup.richtext_editor import RichTextEditor
from janim.gui.utils import apply_popup_flags
from janim.locale.i18n import get_translator

if TYPE_CHECKING:
    from janim.gui.anim_viewer import AnimViewer

_ = get_translator('janim.gui.popup.__init__')


def setup_popup_actions(viewer: AnimViewer, menu: QMenu) -> None:
    action_painter = menu.addAction(_('Draw(&D)'))
    action_painter.setShortcut('Ctrl+D')
    action_painter.setAutoRepeat(False)

    action_richtext_edit = menu.addAction(_('Rich text editor(&R)'))
    action_richtext_edit.setShortcut('Ctrl+R')
    action_richtext_edit.setAutoRepeat(False)

    action_font_table = menu.addAction(_('Font list(&F)'))
    action_font_table.setShortcut('Ctrl+F')
    action_font_table.setAutoRepeat(False)

    action_color_widget = menu.addAction(_('Color(&O)'))
    action_color_widget.setShortcut('Ctrl+O')
    action_color_widget.setAutoRepeat(False)

    connect_action_widget(viewer, action_painter, Painter)
    connect_action_widget(viewer, action_richtext_edit, RichTextEditor)
    connect_action_widget(viewer, action_font_table, FontTable)
    connect_action_widget(viewer, action_color_widget, ColorWidget)


def connect_action_widget(viewer: AnimViewer, action: QAction, widget_cls: type[QWidget]) -> None:
    widget = None

    def triggered() -> None:
        nonlocal widget
        if widget is None:
            widget = widget_cls(viewer)
            apply_popup_flags(widget)
            widget.destroyed.connect(destroyed)
        widget.show()

    def destroyed() -> None:
        nonlocal widget
        widget = None

    action.triggered.connect(triggered)
