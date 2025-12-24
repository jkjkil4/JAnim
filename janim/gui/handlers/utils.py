from __future__ import annotations

from typing import TYPE_CHECKING

from janim.anims.timeline import Timeline

if TYPE_CHECKING:
    from janim.gui.anim_viewer import AnimViewer


def jump(viewer: AnimViewer, command: Timeline.GuiCommand) -> None:
    """
    跳转到该命令执行的 ``global_t``
    """
    tlview = viewer.timeline_view
    tlview.set_progress(tlview.time_to_progress(command.global_t))
    viewer.set_play_state(False)
