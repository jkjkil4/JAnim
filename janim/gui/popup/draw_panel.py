from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QIcon, QMouseEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QRadioButton, QTabWidget,
                               QVBoxLayout, QWidget)

from janim.gui.draw import Draw, draw_handlers
from janim.locale.i18n import get_translator
from janim.utils.file_ops import get_gui_asset

if TYPE_CHECKING:
    from janim.gui.anim_viewer import AnimViewer

_ = get_translator('janim.gui.popup.draw_panel')


class DrawPanel(QWidget):
    def __init__(self, viewer: AnimViewer):
        super().__init__(viewer)
        self.viewer = viewer

        self.setup_ui()
        self.viewer.glw.installEventFilter(self)
        self.viewer.overlay.installEventFilter(self)

        self.tabs.currentChanged.connect(self.on_current_changed)
        self.tabs.tabCloseRequested.connect(self.on_close_requested)

    def setup_ui(self) -> None:
        layout = QVBoxLayout()

        note = QLabel(_('Note: This is used to determine the position on the screen. '
                        'To actually add the drawn content, you need to manually add the corresponding code.'))
        note.setWordWrap(True)
        layout.addWidget(note)

        bottom_layout = QHBoxLayout()
        layout.addLayout(bottom_layout, 1)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        bottom_layout.addWidget(self.tabs)

        rdb_layout = self.setup_rdb()
        bottom_layout.addLayout(rdb_layout)

        self.setLayout(layout)
        self.setStyleSheet('QScrollArea#itemWidget { border: none; }')
        self.setWindowTitle(_('Draw'))
        self.resize(650, 300)

    def setup_rdb(self) -> QHBoxLayout:
        layout = QVBoxLayout()

        self.rdb_move = QRadioButton(_('Move'))
        self.rdb_move.setIcon(QIcon(get_gui_asset('move.png')))
        self.rdb_move.setChecked(True)
        layout.addWidget(self.rdb_move)

        self.radio_buttons: list[tuple[QRadioButton, type[Draw]]] = []

        for cls in draw_handlers.values():
            rdb = QRadioButton(cls.desc_name)
            if cls.icon_file is not None:
                rdb.setIcon(QIcon(get_gui_asset(cls.icon_file)))
            layout.addWidget(rdb)

            self.radio_buttons.append((rdb, cls))

        layout.addStretch()

        return layout

    def on_current_changed(self, index: int) -> None:
        self.rdb_move.setChecked(True)
        self.viewer.overlay.update()

    def on_close_requested(self, index: int) -> None:
        self.tabs.removeTab(index)
        self.viewer.overlay.update()

    def is_none(self) -> bool:
        return self.rdb_move.isChecked()

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

        position = event.position()

        if self.is_none():
            widget: Draw | None = self.tabs.currentWidget()
            if widget is not None:
                widget.pressed(position)
                self.viewer.overlay.update()
            return

        for rdb, cls in self.radio_buttons:
            if rdb.isChecked():
                w = cls(self.viewer)
                self.tabs.blockSignals(True)
                self.tabs.addTab(w, cls.tab_name)
                self.tabs.setCurrentWidget(w)
                self.tabs.blockSignals(False)
                w.pressed(position)

        self.viewer.overlay.update()

    def on_glw_mouse_move(self, event: QMouseEvent) -> None:
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return

        position = event.position()

        widget: Draw = self.tabs.currentWidget()
        if widget is not None:
            widget.moved(position)

        self.viewer.overlay.update()

    def on_glw_mouse_release(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        position = event.position()

        widget: Draw = self.tabs.currentWidget()
        if widget is not None:
            widget.released(position)

        self.viewer.overlay.update()

    def on_overlay_paint(self, event: QPaintEvent) -> None:
        p = QPainter(self.viewer.overlay)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        current_widget = self.tabs.currentWidget()

        for i in range(self.tabs.count()):
            widget: Draw = self.tabs.widget(i)
            widget.paint(p, widget is current_widget)
