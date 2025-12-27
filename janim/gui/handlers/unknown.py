from __future__ import annotations

from typing import TYPE_CHECKING

from janim.anims.timeline import Timeline
from janim.logger import log
from janim.locale.i18n import get_translator
from janim.gui.handlers.utils import jump

if TYPE_CHECKING:
    from janim.gui.anim_viewer import AnimViewer

_ = get_translator('janim.gui.handlers.unknown')


def handler(viewer: AnimViewer, command: Timeline.GuiCommand) -> None:
    log.warning(_('Unknown GUI command "{name}"').format(name=command.name))
    jump(viewer, command)
