from __future__ import annotations
from typing import Iterable, Tuple

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QLabel

from janim.gui.Overlay import Overlay

from janim.gui.ui_ToolkitWidget import *

class ToolkitWidget(QWidget):
    def __init__(self, overlay: Overlay, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.overlay = overlay

        self.ui = Ui_ToolkitWidget()
        self.ui.setupUi(self)

        self.ui.cbbSelect.currentIndexChanged.connect(self.onCbbIndexChanged)
        self.ui.stkWidget.currentChanged.connect(self.adjustSize)

        self.displayingCIV: QWidget | None = None

        self.ui.editCIV.editingFinished.connect(self.onCIVEditingFinished)
        self.ui.btnCIVClear.clicked.connect(self.onCIVClearClicked)

    def onCbbIndexChanged(self, idx: int) -> None:
        self.ui.stkWidget.setCurrentIndex(idx)

    def onCIVEditingFinished(self) -> None:
        if self.displayingCIV is not None:
            self.overlay.removeWidget(self.displayingCIV)
        self.displayingCIV = QLabel('测试')
        self.displayingCIV.setStyleSheet('color: white; background: rgba(0,0,0,128);')
        self.overlay.addWidget(self.displayingCIV, (0, 0), Qt.AlignmentFlag.AlignCenter)
    
    def onCIVClearClicked(self) -> None:
        if self.displayingCIV is not None:
            self.overlay.removeWidget(self.displayingCIV)
            self.displayingCIV = None

    def setVisible(self, visible: bool) -> None:
        super().setVisible(visible)
        if visible:
            self.adjustSize()
    