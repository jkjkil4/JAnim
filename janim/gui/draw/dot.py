
from PySide6.QtCore import QObject, QPointF, Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QCheckBox

from janim.gui.draw.base import (ACTIVE_COLOR, INACTIVE_COLOR, Draw,
                                 point_to_str)
from janim.gui.utils.text_edit import TextEdit
from janim.locale.i18n import get_translator

_ = get_translator('janim.gui.draw.dot')


class DrawDot(Draw):
    tab_name = 'Dot'
    desc_name = 'Dot'
    icon_file = 'dot.png'

    def init(self):
        self._position: QPointF | None = None

        self.code = TextEdit()
        self.cbb_coord_only = QCheckBox(_('Coordinate only'))

        self.mainlayout = self.create_layout()
        self.mainlayout.addWidget(self.code)
        self.mainlayout.addWidget(self.cbb_coord_only, 0, Qt.AlignmentFlag.AlignRight)

        self.global_coord_only = get_coord_only_instance()
        self.global_coord_only.changed.connect(self.on_global_coord_only_changed)

        self.cbb_coord_only.setChecked(self.global_coord_only.get())
        self.cbb_coord_only.stateChanged.connect(self.on_local_coord_only_changed)

    def pressed(self, position: QPointF) -> None:
        self._position = position

    def moved(self, position: QPointF) -> None:
        self._position = position

    def released(self, _) -> None:
        self._update_code()

    def on_global_coord_only_changed(self, state: bool) -> None:
        self.cbb_coord_only.blockSignals(True)
        self.cbb_coord_only.setChecked(state)
        self.cbb_coord_only.blockSignals(False)
        self._update_code()

    def on_local_coord_only_changed(self, state: bool) -> None:
        self.global_coord_only.set(state)
        self._update_code()

    def _update_code(self) -> None:
        text = point_to_str(self.viewer.glw.map_to_point(self._position))
        if not self.cbb_coord_only.isChecked():
            text = f'Dot({text})'
        self.setLayout(self.mainlayout)
        self.code.setPlainText(text)
        self.code_changed.emit(text)

    def paint(self, p: QPainter, is_active: bool) -> None:
        if self._position is None:
            return

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(ACTIVE_COLOR if is_active else INACTIVE_COLOR)

        p.drawEllipse(self._position, 3, 3)


class _CoordOnly(QObject):
    changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self.flag = False

    def get(self) -> bool:
        return self.flag

    def set(self, flag: bool) -> None:
        self.flag = flag
        self.changed.emit(flag)


# 全局单例，用于在不同 tab 中的 DrawDot 之间同步 coord_only 状态
_coord_only_instance: _CoordOnly | None = None


def get_coord_only_instance() -> _CoordOnly:
    global _coord_only_instance
    if _coord_only_instance is None:
        _coord_only_instance = _CoordOnly()

    return _coord_only_instance
