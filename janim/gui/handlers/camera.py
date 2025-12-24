from __future__ import annotations

from typing import TYPE_CHECKING

from janim.anims.timeline import Timeline

if TYPE_CHECKING:
    from janim.gui.anim_viewer import AnimViewer


def handler(viewer: AnimViewer, command: Timeline.GuiCommand) -> None:
    pass
