import sys

from PySide6.QtCore import Qt, QMargins
from PySide6.QtGui import QCloseEvent, QShortcut, QKeySequence
from PySide6.QtWidgets import QWidget, QMainWindow, QApplication, QStackedLayout

from janim.gui.GLWidget import GLWidget
from janim.gui.Overlay import Overlay
from janim.scene.scene import Scene

from janim.gl.texture import Texture
from janim.gl.render import ShaderProgram

from janim.config import get_configuration
from janim.logger import log

class MainWindow(QWidget):
    def __init__(self, scene: Scene, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.glwidget = GLWidget(scene, self)
        self.overlay = Overlay(self)
        self.is_closed = False

        self.stkLayout = QStackedLayout()
        self.stkLayout.setContentsMargins(QMargins())
        self.stkLayout.setSpacing(0)
        self.stkLayout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        self.stkLayout.addWidget(self.glwidget)
        self.stkLayout.addWidget(self.overlay)
        self.setLayout(self.stkLayout)

        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

    def moveToPosition(self) -> None:
        conf = get_configuration()
        window_position = conf['window']['position']
        window_monitor = conf['window']['monitor']

        if len(window_position) != 2 or window_position[0] not in 'UOD' or window_position[1] not in 'LOR':
            log.error(f'window.position has wrong argument "{window_position}".')
            sys.exit(2)
        
        screens = QApplication.screens()
        if window_monitor < len(screens):
            screen = screens[window_monitor]
        else:
            screen = screens[0]
            log.warning(f'window.monitor has invaild value {window_monitor}, please use 0~{len(screens) - 1} instead.')
        screen_size = screen.availableSize()
        
        if window_position[1] == 'O':
            width = screen_size.width()
            x = 0
        else:
            width = screen_size.width() / 2
            x = 0 if window_position[1] == 'L' else width
        
        if window_position[0] == 'O':
            height = screen_size.height()
            y = 0
        else:
            height = screen_size.height() / 2
            y = 0 if window_position[0] == 'U' else height
        
        self.move(x, y)
        self.resize(width, height)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.is_closed = True
        self.glwidget.scene.loop_helper.event_loop.quit()
        Texture.release_all()
        ShaderProgram.release_all()
        super().closeEvent(event)

    def emit_frame(self) -> None:
        self.glwidget.update()

    def finish(self) -> None:
        pass
        
    
