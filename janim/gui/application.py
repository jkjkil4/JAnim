import os
from PySide6.QtGui import QSurfaceFormat
from PySide6.QtWidgets import QApplication

from janim.exception import cancel_listen_exception, listen_exception
from janim.utils.file_ops import readall, get_janim_dir


class Application(QApplication):
    """
    在 ``QApplication`` 的基础上载入 ``qdarkstyle``
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        qss_file = os.path.join(get_janim_dir(), 'gui', 'styles.qss')
        stylesheet = readall(qss_file)
        self.setStyleSheet(stylesheet)

        fmt = QSurfaceFormat.defaultFormat()
        fmt.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
        fmt.setVersion(4, 3)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        QSurfaceFormat.setDefaultFormat(fmt)

        listen_exception(self.on_exception)
        self.destroyed.connect(lambda: cancel_listen_exception(self.on_exception))

    def on_exception(self, exc_type, exc_value, exc_traceback):
        if exc_type is KeyboardInterrupt:
            self.quit()
            return True
