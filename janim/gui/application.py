import qdarkstyle
from PySide6.QtGui import QSurfaceFormat
from PySide6.QtWidgets import QApplication


class Application(QApplication):
    '''
    在 ``QApplication`` 的基础上载入 ``qdarkstyle``
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet(qdarkstyle.load_stylesheet_pyside6())

        fmt = QSurfaceFormat.defaultFormat()
        fmt.setVersion(4, 3)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        QSurfaceFormat.setDefaultFormat(fmt)
