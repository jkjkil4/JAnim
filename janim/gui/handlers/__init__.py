from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import janim.gui.handlers.camera as camera
import janim.gui.handlers.move as move
import janim.gui.handlers.select as select
from janim.gui.handlers.unknown import handler as unknown_handler  # noqa: F401

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
