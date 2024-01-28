import qdarkstyle
from PySide6.QtWidgets import QApplication


class Application(QApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet(qdarkstyle.load_stylesheet_pyside6())
