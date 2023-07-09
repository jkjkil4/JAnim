from typing import Optional

from PySide6.QtWidgets import QWidget, QMainWindow

class MainWindow(QMainWindow):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

    
