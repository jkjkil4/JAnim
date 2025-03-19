
from typing import TYPE_CHECKING, Self

from janim.components.rgbas import Cmpt_Rgbas
from janim.constants import WHITE
from janim.items.item import Item
from janim.locale.i18n import get_local_strings
from janim.logger import log
from janim.render.renderer_frameeffect import FrameEffectRenderer
from janim.typing import JAnimColor

if TYPE_CHECKING:
    from janim.anims.timeline import Timeline

_ = get_local_strings('frame_effect')


class FrameEffect(Item):
    renderer_cls = FrameEffectRenderer

    def __init__(
        self,
        *items: Item,
        fragment_shader: str,
        clear_color: JAnimColor = WHITE,
        root_only: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.fragment_shader = fragment_shader
        self.clear_color = Cmpt_Rgbas.format_color(clear_color)
        self.apprs: list[Timeline.ItemAppearance] = []

        self.apply(*items, root_only=root_only)

    def add(self, *objs, insert=False) -> Self:
        log.warning(_('Calling FrameEffect.add is unusual and may not work as expected. '
                      'If you want to apply additional items, use `apply` instead.'))
        super().add(*objs, insert=insert)
        return self

    def apply(self, *items: Item, root_only: bool = False) -> Self:
        self.apprs.extend(
            self.timeline.item_appearances[sub]
            for item in items
            for sub in item.walk_self_and_descendants(root_only)
        )

    def _mark_render_disabled(self):
        for appr in self.apprs:
            appr.render_disabled = True
