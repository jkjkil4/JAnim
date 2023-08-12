from typing import Optional

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QWidget, QMainWindow

from janim.gui.GLWidget import GLWidget
from janim.scene.scene import Scene

from janim.gl.texture import Texture
from janim.gl.render import ShaderProgram


class MainWindow(GLWidget):
    def __init__(self, scene: Scene, parent: Optional[QWidget] = None) -> None:
        super().__init__(scene, parent)
        self.glwidget = self
        self.is_closed = False

    def closeEvent(self, event: QCloseEvent) -> None:
        self.is_closed = True
        self.glwidget.scene.loop_helper.event_loop.quit()
        Texture.release_all()
        ShaderProgram.release_all()
        super().closeEvent(event)

    def emit_frame(self) -> None:
        if not self.glwidget.timer.isActive():
            self.glwidget.update()

    def finish(self) -> None:
        pass
        
    
