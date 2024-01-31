import qdarkstyle
from PySide6.QtWidgets import QApplication


class Application(QApplication):
    '''
    在 ``QApplication`` 的基础上载入 ``qdarkstyle``
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet(qdarkstyle.load_stylesheet_pyside6())
