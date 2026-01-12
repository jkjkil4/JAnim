from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QLabel, QLayout, QScrollArea, QVBoxLayout,
                               QWidget)

from janim.locale.i18n import get_translator

if TYPE_CHECKING:
    from janim.gui.anim_viewer import AnimViewer

_ = get_translator('janim.gui.draw.base')

ACTIVE_COLOR = Qt.GlobalColor.yellow
ACTIVE_COLOR_TRANSPARENT = QColor(255, 255, 0, 180)
INACTIVE_COLOR = QColor(255, 255, 255, 128)


class Draw(QScrollArea):
    tab_name = '(None)'
    desc_name = '(None)'
    icon_file: str | None = None

    code_changed = Signal(str)

    def __init__(self, viewer: AnimViewer):
        super().__init__()
        self.setWidgetResizable(True)
        self.setObjectName('itemWidget')

        layout = QVBoxLayout()
        layout.addWidget(QLabel(_('Constructing ...')))
        self.set_layout(layout)

        self.viewer = viewer
        self.init()

    def init(self) -> None: ...

    def pressed(self, position: QPointF) -> None: ...
    def moved(self, position: QPointF) -> None: ...
    def released(self, position: QPointF) -> None: ...

    def paint(self, p: QPainter, is_active: bool) -> None: ...

    def create_layout(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        return layout

    def set_layout(self, layout: QLayout) -> None:
        prev = self.widget()
        if prev is not None:
            prev.deleteLater()
        self.setWidget(QWidget())
        self.widget().setLayout(layout)


class DrawOnce(Draw):
    class ShiftInfo:
        def __init__(self, viewer: AnimViewer, pos1: QPointF, pos2: QPointF):
            map_to_point = viewer.glw.map_to_point
            self.dpos = pos2 - pos1
            self.dpoint = map_to_point(pos2) - map_to_point(pos1)

    def __init__(self, viewer: AnimViewer):
        self._finished: bool = False
        super().__init__(viewer)

    def pressed(self, position: QPointF) -> None:
        if not self._finished:
            self.start(position)
        else:
            self._drag_prev = position

    def moved(self, position: QPointF) -> None:
        if not self._finished:
            self.append(position)
        else:
            self.shift(DrawOnce.ShiftInfo(self.viewer, self._drag_prev, position))
            self._drag_prev = position

    def released(self, position: QPointF) -> None:
        if not self._finished:
            self.finish(position)
            self._finished = True

    def start(self, position: QPointF) -> None: ...
    def append(self, position: QPointF) -> None: ...
    def finish(self, position: QPointF) -> None: ...
    def shift(self, shift: ShiftInfo) -> None: ...


def point_to_str(pos: np.ndarray) -> str:
    s = ', '.join(map(lambda coord: f'{coord:.2f}'.rstrip('0').rstrip('.'), pos))
    return f'[{s}]'
