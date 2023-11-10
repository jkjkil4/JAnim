from __future__ import annotations
from typing import Iterable, Tuple

from PySide6.QtGui import QVector4D
from PySide6.QtWidgets import QWidget, QLabel

from janim.items.item import Item
from janim.logger import log
from janim.gui.MainWindow import MainWindow

from janim.gui.ui_ToolkitWidget import *

class ToolkitWidget(QWidget):
    def __init__(self, mainWindow: MainWindow, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.mainWindow = mainWindow

        self.ui = Ui_ToolkitWidget()
        self.ui.setupUi(self)

        self.ui.cbbSelect.currentIndexChanged.connect(self.onCbbIndexChanged)
        self.ui.stkWidget.currentChanged.connect(self.adjustSize)

        self.displayingCIV: list[QLabel] = []

        self.ui.editCIV.editingFinished.connect(self.onCIVEditingFinished)
        self.ui.btnCIVClear.clicked.connect(self.onCIVClearClicked)

    def onCbbIndexChanged(self, idx: int) -> None:
        self.ui.stkWidget.setCurrentIndex(idx)

    def onCIVEditingFinished(self) -> None:
        self.onCIVClearClicked()

        item = None
        name = self.ui.editCIV.text()
        
        try:
            item = eval(name, self.mainWindow.glwidget.scene.embed_globals)
        except: 
            log.error(f'Cannot found "{name}".')
            return
    
        if not isinstance(item, Item):
            log.error(f'Found "{name}"{type(item)}, but it\'s not an instance of Item.')
            return
        
        item: Item
        camera = self.mainWindow.glwidget.scene.camera
        matrix = camera.compute_proj_matrix() * camera.compute_view_matrix()

        for i, subitem in enumerate(item):
            wnd_pos: QVector4D = matrix.map(QVector4D(*subitem.get_center(), 1))

            label = QLabel(str(i))
            label.setStyleSheet('color: white; background: rgba(0,0,0,128);')
            self.displayingCIV.append(label)
            self.mainWindow.overlay.addWidget(label, (wnd_pos.x(), wnd_pos.y()), Qt.AlignmentFlag.AlignCenter)
    
    def onCIVClearClicked(self) -> None:
        for widget in self.displayingCIV:
            self.mainWindow.overlay.removeWidget(widget)
        self.displayingCIV.clear()

    def setVisible(self, visible: bool) -> None:
        super().setVisible(visible)
        if visible:
            self.adjustSize()
    