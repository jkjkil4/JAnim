from PySide6.QtWidgets import QPlainTextEdit


class TextEdit(QPlainTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        font = self.font()
        font.setFamily('Consolas')
        font.setPointSize(10)
        self.setFont(font)
