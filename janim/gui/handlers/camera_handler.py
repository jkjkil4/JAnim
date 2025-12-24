from typing import TYPE_CHECKING

from janim.anims.timeline import Timeline

if TYPE_CHECKING:
    from janim.gui.anim_viewer import AnimViewer


def handler(anim_viewer: AnimViewer, command: Timeline.GuiCommand) -> None:
    pass
