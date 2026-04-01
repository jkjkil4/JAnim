import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

ACTION_WIDGET_FLAG_KEY = '__action_widget'


def apply_popup_flags(widget: QWidget) -> None:
    widget.setWindowFlag(Qt.WindowType.Tool)
    widget.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    widget.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
    if sys.platform == "darwin":
        setattr(widget, ACTION_WIDGET_FLAG_KEY, True)
