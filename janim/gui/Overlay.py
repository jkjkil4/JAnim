from __future__ import annotations
from typing import Iterable, Tuple

import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QWidget

from janim.gui.GLWidget import GLWidget

OverlayWidgetData = Tuple[Iterable[Tuple[float, float]], Qt.AlignmentFlag]

class Overlay(QWidget):
    def __init__(self, glwidget: GLWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.glwidget = glwidget

        self.datas: dict[QWidget, OverlayWidgetData] = {}

    def addWidget(
        self, 
        widget: QWidget, 
        coords: Iterable[float, float], 
        align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignCenter
    ) -> None:
        self.removeWidget(widget)
        tpl = self.datas[widget] = (coords, align)
        widget.setParent(self)
        widget.show()
        self._placeWidget(widget, tpl)
        
    def removeWidget(self, widget: QWidget) -> bool:
        if widget in self.datas:
            self.datas.pop(widget)
            widget.hide()
            widget.setParent(None)
            return True
        return False
    
    def _placeWidget(self, widget: QWidget, data: OverlayWidgetData) -> None:
        coords, align = data

        x = (coords[0] + 1) / 2 * self.width()
        y = (coords[1] + 1) / 2 * self.height()
        
        if align & Qt.AlignmentFlag.AlignHCenter:
            x -= widget.width() / 2
        elif align & Qt.AlignmentFlag.AlignRight:
            x -= widget.width()

        if align & Qt.AlignmentFlag.AlignVCenter:
            y -= widget.height() / 2
        elif align & Qt.AlignmentFlag.AlignBottom:
            y -= widget.height()
        
        widget.move(x, y)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        for widget, data in self.datas.items():
            self._placeWidget(widget, data)
        