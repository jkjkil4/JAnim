from janim import __version__

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QSurfaceFormat

from gui.MainWindow import MainWindow
from gui.GLWidget import GLWidget

def main():
    print(f"JAnim \033[32mv{__version__}\033[0m")

    app = QApplication()

    fmt = QSurfaceFormat()
    fmt.setVersion(3, 3)
    fmt.setSamples(4)
    QSurfaceFormat.setDefaultFormat(fmt)    

    w = GLWidget()
    w.show()

    app.exec()

if __name__ == '__main__':
    main()
