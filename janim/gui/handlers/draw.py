from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QMargins, QObject, Qt
from PySide6.QtGui import QMouseEvent, QPaintEvent, QPainter
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QScrollArea, QVBoxLayout, QWidget

from janim.anims.timeline import Timeline
from janim.exception import GuiCommandError
from janim.gui.draw.base import Draw
from janim.gui.draw.dot import DrawDot
from janim.gui.draw.rect import DrawRect
from janim.gui.draw.vitem import DrawVItem
from janim.gui.handlers.utils import HandlerPanel, SourceDiff, get_confirm_buttons, jump
from janim.locale import get_translator

if TYPE_CHECKING:
    from janim.gui.anim_viewer import AnimViewer

_ = get_translator('janim.gui.handlers.draw')


def handler(viewer: AnimViewer, command: Timeline.GuiCommand) -> None:
    type = command.body
    cls = _types.get(type, None)
    if cls is None:
        raise GuiCommandError(
            _('Invalid draw type "{type}" (availables: {lst})').format(
                type=type,
                lst=list(_types.keys()),
            )
        )

    jump(viewer, command)
    widget = DrawPanel(viewer, command, cls)
    widget.show()


_types = {
    'dot': DrawDot,
    'rect': DrawRect,
    'vitem': DrawVItem,
}


class DrawPanel(HandlerPanel):
    def __init__(
        self,
        viewer: AnimViewer,
        command: Timeline.GuiCommand,
        draw_cls: type[Draw],
    ):
        super().__init__(viewer, command)
        self.draw_cls = draw_cls
        self.draw = draw_cls(self.viewer)
        self.init_draw()

        viewer.glw.installEventFilter(self)
        viewer.overlay.installEventFilter(self)

        # setup ui

        self.diff = SourceDiff(command, self)

        diff_layout = QVBoxLayout()
        diff_layout.setContentsMargins(QMargins())
        diff_layout.addWidget(self.diff)
        diff_layout.addStretch()

        diff_widget = QWidget(self)
        diff_widget.setLayout(diff_layout)

        area = QScrollArea(self)
        area.setWidgetResizable(True)
        area.setWidget(diff_widget)

        btn_reset = QPushButton(_('Reset'))
        btn_reset.setMinimumWidth(70)

        btn_box, self.btn_ok, btn_cancel = get_confirm_buttons(self)
        self.btn_ok.setEnabled(False)

        hlayout_bottom = QHBoxLayout()
        hlayout_bottom.addWidget(btn_reset)
        hlayout_bottom.addStretch()
        hlayout_bottom.addWidget(btn_box)

        self.vlayout = QVBoxLayout()
        self.vlayout.addWidget(self.draw, 3)
        self.vlayout.addWidget(area, 2)
        self.vlayout.addLayout(hlayout_bottom)

        self.setLayout(self.vlayout)
        self.resize(600, 400)

        # setup slots

        btn_reset.clicked.connect(self.reset)
        self.btn_ok.clicked.connect(self.diff.submit)
        btn_cancel.clicked.connect(self.close)

    def reset(self) -> None:
        self.diff.set_replacement('')
        self.btn_ok.setEnabled(False)

        self.vlayout.removeWidget(self.draw)
        self.draw.deleteLater()

        self.draw = self.draw_cls(self.viewer)
        self.init_draw()
        self.viewer.overlay.update()

        self.vlayout.insertWidget(0, self.draw, 3)

    def init_draw(self) -> None:
        self.draw.init()
        self.draw.code_changed.connect(lambda code: self.diff.set_replacement(code))

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.viewer.glw:
            match event.type():
                case QEvent.Type.MouseButtonPress:
                    self.on_glw_mouse_press(event)
                case QEvent.Type.MouseMove:
                    self.on_glw_mouse_move(event)
                case QEvent.Type.MouseButtonRelease:
                    self.on_glw_mouse_release(event)

        if watched is self.viewer.overlay:
            if event.type() is QEvent.Type.Paint:
                self.on_overlay_paint(event)

        return super().eventFilter(watched, event)

    def on_glw_mouse_press(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        self.draw.pressed(event.position())
        self.viewer.overlay.update()

    def on_glw_mouse_move(self, event: QMouseEvent) -> None:
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return

        self.draw.moved(event.position())
        self.viewer.overlay.update()

    def on_glw_mouse_release(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        self.draw.released(event.position())
        self.viewer.overlay.update()
        self.btn_ok.setEnabled(True)

    def on_overlay_paint(self, event: QPaintEvent) -> None:
        p = QPainter(self.viewer.overlay)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        self.draw.paint(p, True)
