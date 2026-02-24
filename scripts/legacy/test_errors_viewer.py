
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QPainter, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from janim.gui.application import Application


class CompareWidget(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.compare_infos = get_compare_info()
        self.setup_ui()

        self.set_current_index(0)
        self.adjustSize()

    def setup_ui(self) -> None:
        self.label_correct = QLabel()
        self.label_correct_txt = QLabel()
        self.label_wrong = QLabel()
        self.label_wrong_txt = QLabel()

        self.label_diff = QLabel()

        self.label_correct.setStyleSheet("border: 1px solid white;")
        self.label_wrong.setStyleSheet("border: 1px solid white;")
        self.label_diff.setStyleSheet("border: 1px solid white;")

        self.vlayout_correct = QVBoxLayout()
        self.vlayout_correct.addWidget(self.label_correct)
        self.vlayout_correct.addWidget(self.label_correct_txt)

        self.vlayout_wrong = QVBoxLayout()
        self.vlayout_wrong.addWidget(self.label_wrong)
        self.vlayout_wrong.addWidget(self.label_wrong_txt)

        self.hlayout_compare = QHBoxLayout()
        self.hlayout_compare.addLayout(self.vlayout_correct)
        self.hlayout_compare.addLayout(self.vlayout_wrong)

        self.vlayout_diff = QVBoxLayout()
        self.vlayout_diff.addWidget(self.label_diff, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.vlayout_diff.addWidget(QLabel('Difference'), alignment=Qt.AlignmentFlag.AlignHCenter)

        self.vlayout = QVBoxLayout()
        self.vlayout.addLayout(self.hlayout_compare)
        self.vlayout.addLayout(self.vlayout_diff)

        self.setLayout(self.vlayout)
        self.setWindowTitle('Errors Viewer')

    def set_current_index(self, index: int) -> None:
        self.current_index = index

        if len(self.compare_infos) == 0:
            return

        pair = self.compare_infos[index]

        pix_correct = get_pixmap(pair.correct)
        pix_wrong = get_pixmap(pair.wrong)

        self.label_correct.setPixmap(pix_correct)
        self.label_correct_txt.setText(f'Correct:\n{pair.correct}')
        self.label_wrong.setPixmap(pix_wrong)
        self.label_wrong_txt.setText(f'Wrong:\n{pair.wrong}')

        diff_image = pix_correct.toImage()
        p = QPainter(diff_image)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Difference)
        p.drawImage(0, 0, pix_wrong.toImage())
        p.end()

        self.label_diff.setPixmap(QPixmap(diff_image))

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if len(self.compare_infos) == 0:
            return

        if event.key() == Qt.Key.Key_Right:
            new_index = (self.current_index + 1) % len(self.compare_infos)
            self.set_current_index(new_index)
        elif event.key() == Qt.Key.Key_Left:
            new_index = (self.current_index - 1) % len(self.compare_infos)
            self.set_current_index(new_index)


@dataclass
class CompareInfo:
    timeline_name: str
    frame: int

    correct: str
    wrong: str


def get_compare_info() -> list[CompareInfo]:
    errors_path = Path('test/__test_errors__')
    refs_path = Path('test/examples/ref')

    res: list[CompareInfo] = []
    for err_filename in os.listdir(errors_path):
        match = re.match(r'(.+?)_(\d+)_err.png', err_filename)
        timeline_name = match.group(1)
        ref_frame = err_frame = int(match.group(2))

        while True:
            ref_filename = f'{timeline_name}_{ref_frame}.png'
            ref_filepath = refs_path / ref_filename
            if ref_filepath.exists():
                break
            ref_frame -= 1
            assert ref_frame >= 0

        res.append(CompareInfo(timeline_name, err_frame, str(ref_filepath), str(errors_path / err_filename)))

    res.sort(key=lambda x: (x.timeline_name, x.frame))
    return res


@lru_cache(maxsize=None)
def get_pixmap(filepath: str) -> QPixmap:
    pix = QPixmap(filepath)
    return pix.scaled(pix.size() * 2, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)


app = Application()
w = CompareWidget()
w.show()
app.exec()
