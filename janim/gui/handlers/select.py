from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout

from janim.anims.timeline import Timeline
from janim.gui.handlers.utils import (HandlerPanel, SourceDiff,
                                      get_confirm_buttons, jump)

if TYPE_CHECKING:
    from janim.gui.anim_viewer import AnimViewer


def handler(viewer: AnimViewer, command: Timeline.GuiCommand) -> None:
    jump(viewer, command)
    widget = SelectPanel(viewer, command)
    widget.show()


class SelectPanel(HandlerPanel):
    def __init__(self, viewer: AnimViewer, command: Timeline.GuiCommand):
        super().__init__(viewer, command)

        # setup ui

        diff = SourceDiff(command, self)
        btn_box, btn_ok, btn_cancel = get_confirm_buttons(self)

        vlayout = QVBoxLayout(self)
        vlayout.addWidget(diff)
        vlayout.addStretch()
        vlayout.addWidget(btn_box, 0, Qt.AlignmentFlag.AlignRight)

        self.setLayout(vlayout)

        # setup slots

        btn_ok.clicked.connect(diff.submit)
        btn_cancel.clicked.connect(self.close)
        diff.submitted.connect(self.close_and_rebuild_timeline)
