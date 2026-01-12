
import time

import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSlider

from janim.gui.draw.base import (ACTIVE_COLOR, INACTIVE_COLOR, DrawOnce,
                                 point_to_str)
from janim.gui.draw.filter import OneEuroVec2
from janim.gui.utils.text_edit import TextEdit
from janim.locale.i18n import get_translator
from janim.utils.bezier import smooth_quadratic_path
from janim.utils.iterables import (resize_preserving_head_and_tail,
                                   resize_with_interpolation)

_ = get_translator('janim.gui.draw.vitem')

POS_PER_LINE = 5


class DrawVItem(DrawOnce):
    tab_name = 'VItem'
    desc_name = 'VItem' + _('(freehand-path)')
    icon_file = 'curve.png'

    def init(self) -> None:
        self.filter = OneEuroVec2(beta=0.0015)

        # full_points 自始至终都有
        # full_array 是在 finish 之后根据 full_points 创建的
        # array 是通过缩减点数量创建的
        self.full_points: list[np.ndarray] = []
        self.full_array: np.ndarray | None = None
        self.array: np.ndarray | None = None

    def start(self, position: QPointF) -> None:
        self.append(position)

    def append(self, position: QPointF) -> None:
        filtered = self.filter(*position.toTuple(), time.time())
        point = self.viewer.glw.map_to_point(QPointF(*filtered))
        self.full_points.append(point)

    def finish(self, position: QPointF) -> None:
        assert self.full_points

        last_point = self.viewer.glw.map_to_point(position)
        self.full_points[-1] = last_point

        if len(self.full_points) % 2 == 0:
            p2 = self.full_points[-2]
            p1 = self.full_points[-1]
            self.full_points.insert(-1, (p2 + p1) * 0.5)

        self.full_array = np.array(self.full_points)

        # GUI
        self.name_label = QLabel(_('Count'))
        self.ratio_label = QLabel()

        self.count = QSlider(Qt.Orientation.Horizontal)
        self.count.setMinimum(3)
        self.count.setMaximum(len(self.full_array))

        count_layout = QHBoxLayout()
        count_layout.addWidget(self.name_label)
        count_layout.addWidget(self.count)
        count_layout.addWidget(self.ratio_label)

        self.code = TextEdit()

        self.mainlayout = self.create_layout()
        self.mainlayout.addLayout(count_layout)
        self.mainlayout.addWidget(self.code)

        self.count.setValue(int(self.count.maximum() * 0.5))
        self.count.valueChanged.connect(self.on_count_changed)
        self.on_count_changed()

    def shift(self, shift: DrawOnce.ShiftInfo) -> None:
        assert self.full_array is not None
        assert self.array is not None

        self.full_array += shift.dpoint
        self.array += shift.dpoint

    def released(self, position):
        super().released(position)
        self.update_code()

    def get_value(self) -> int:
        value = self.count.value()
        if value % 2 == 0:
            value += 1
        return value

    def on_count_changed(self) -> None:
        ratio = self.get_value() / len(self.full_array) * 100
        self.ratio_label.setText(f'{ratio:.0f}%')
        self.update_array()
        self.update_code()

    def update_array(self) -> None:
        value = self.get_value()
        if value < 5:
            self.array = resize_with_interpolation(self.full_array, value)
        else:
            self.array = resize_preserving_head_and_tail(self.full_array, value)
            self.array = smooth_quadratic_path(self.array[::2])

        self.viewer.overlay.update()

    def update_code(self) -> None:
        points = '\n'.join([
            '    ' + ', '.join([point_to_str(pos) for pos in self.array[i: i + POS_PER_LINE]]) + ','
            for i in range(0, len(self.array), POS_PER_LINE)
        ])
        text = f'VItem(\n{points}\n)'
        self.setLayout(self.mainlayout)
        self.code.setPlainText(text)
        self.code_changed.emit(text)

    def paint(self, p: QPainter, is_active: bool) -> None:
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(ACTIVE_COLOR if is_active else INACTIVE_COLOR, 3))

        if self.array is None:
            positions = self.viewer.glw.map_from_points(self.full_points)

            path = QPainterPath(positions[0])
            for point in positions[1:]:
                path.lineTo(point)

        else:
            positions = self.viewer.glw.map_from_points(self.array)

            path = QPainterPath(positions[0])
            for i in range(len(positions) // 2):
                path.quadTo(positions[i * 2 + 1], positions[i * 2 + 2])

        p.drawPath(path)
