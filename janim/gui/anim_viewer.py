import numpy as np

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout

from janim.anims.timeline import TimelineAnim
from janim.gui.glwidget import GLWidget


class AnimViewer(QWidget):
    def __init__(self, anim: TimelineAnim, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.anim = anim
