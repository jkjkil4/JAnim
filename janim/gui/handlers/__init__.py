
from typing import Callable, TYPE_CHECKING

import janim.gui.handlers.select_handler as select
import janim.gui.handlers.move_handler as move
import janim.gui.handlers.camera_handler as camera

from janim.gui.handlers.unknwon_handler import handler as unknown_handler   # noqa: F401

if TYPE_CHECKING:
    from janim.anims.timeline import Timeline
    from janim.gui.anim_viewer import AnimViewer

registered: dict[str, Callable[[AnimViewer, Timeline.GuiCommand]]] = {
    'select': select.handler,
    'move': move.handler,
    'camera': camera.handler
}


def handle_command(anim_viewer: AnimViewer, command: Timeline.GuiCommand) -> None:
    handler = registered.get(command.name, unknown_handler)
    handler(anim_viewer, command)
