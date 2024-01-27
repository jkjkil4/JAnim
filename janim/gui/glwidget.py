import moderngl as mgl
from PySide6.QtOpenGLWidgets import QOpenGLWidget


class GLWidget(QOpenGLWidget):
    def initializeGL(self) -> None:
        self.ctx = mgl.create_context()
