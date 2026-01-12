
import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QPainterPath

from janim.gui.draw.base import (ACTIVE_COLOR_TRANSPARENT, INACTIVE_COLOR,
                                 DrawOnce, point_to_str)
from janim.gui.utils.text_edit import TextEdit


class DrawRect(DrawOnce):
    tab_name = 'Rect'
    desc_name = 'Rect'
    icon_file = 'rect.png'

    def init(self) -> None:
        self._pos1 = self._pos2 = None
        self.points: np.ndarray | None = None

    def start(self, position: QPointF) -> None:
        self._pos1 = self._pos2 = position

    def append(self, position: QPointF) -> None:
        self._pos2 = position

    def finish(self, _) -> None:
        x1, y1 = self._pos1.toTuple()
        x2, y2 = self._pos2.toTuple()
        self._pos1 = self._pos2 = None

        dlx, dly = min(x1, x2), max(y1, y2)
        urx, ury = max(x1, x2), min(y1, y2)

        map_to_point = self.viewer.glw.map_to_point
        self.points = np.array([
            map_to_point(QPointF(urx, ury)),    # UR
            map_to_point(QPointF(dlx, ury)),    # UL
            map_to_point(QPointF(dlx, dly)),    # DL
            map_to_point(QPointF(urx, dly)),    # DR
        ])

        hor = np.isclose(self.points[1, 1:] - self.points[0, 1:], 0).all()
        ver = np.isclose(self.points[2, [0, 2]] - self.points[1, [0, 2]], 0).all()
        self.simplify = hor and ver

        # GUI
        self.code = TextEdit()

        self.mainlayout = self.create_layout()
        self.mainlayout.addWidget(self.code)

    def shift(self, shift: DrawOnce.ShiftInfo) -> None:
        self.points += shift.dpoint

    def released(self, position) -> None:
        super().released(position)
        self._update_code()

    def _update_code(self) -> None:
        if self.simplify:
            text = f'Rect({self._args_of_indices([2, 0])})'
        else:
            text = f'Polygon({self._args_of_indices([0, 1, 2, 3])})'
        self.setLayout(self.mainlayout)
        self.code.setPlainText(text)
        self.code_changed.emit(text)

    def _args_of_indices(self, indices: list[int]) -> str:
        lst = [point_to_str(self.points[idx]) for idx in indices]
        return ', '.join(lst)

    def paint(self, p: QPainter, is_active: bool) -> None:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(ACTIVE_COLOR_TRANSPARENT if is_active else INACTIVE_COLOR)

        if self._pos1 is not None and self._pos2 is not None:
            p.drawRect(QRectF(self._pos1, self._pos2))

        if self.points is not None:
            positions = self.viewer.glw.map_from_points(self.points)

            path = QPainterPath()
            path.moveTo(positions[0])
            path.lineTo(positions[1])
            path.lineTo(positions[2])
            path.lineTo(positions[3])
            path.closeSubpath()

            p.drawPath(path)
