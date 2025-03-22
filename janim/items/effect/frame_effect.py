from typing import Self

from janim.anims.timeline import Timeline
from janim.components.component import CmptInfo
from janim.components.simple import Cmpt_List
from janim.items.item import Item
from janim.locale.i18n import get_local_strings
from janim.logger import log
from janim.render.renderer_frameeffect import FrameEffectRenderer

_ = get_local_strings('frame_effect')


class FrameEffect(Item):
    renderer_cls = FrameEffectRenderer

    apprs = CmptInfo(Cmpt_List[Self, Timeline.ItemAppearance])

    def __init__(
        self,
        *items: Item,
        fragment_shader: str,
        cache_key: str | None = None,
        root_only: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.fragment_shader = fragment_shader
        self.cache_key = cache_key

        self.apply(*items, root_only=root_only)

    def uniforms(self) -> dict:
        return {}

    def add(self, *objs, insert=False) -> Self:
        log.warning(
            _('Calling {cls}.add is unusual and may not work as expected. '
              'If you want to apply additional items, use `apply` instead.')
            .format(cls=self.__class__.__name__)
        )
        super().add(*objs, insert=insert)
        return self

    def remove(self, *objs) -> Self:
        log.warning(
            _('Calling {cls}.remove is unusual and may not work as expected. '
              'If you want to discard applied items, use `discard` instead.')
            .format(cls=self.__class__.__name__)
        )
        return super().remove(*objs)

    def apply(self, *items: Item, root_only: bool = False) -> Self:
        self.apprs.extend(
            self.timeline.item_appearances[sub]
            for item in items
            for sub in item.walk_self_and_descendants(root_only)
        )

    def discard(self, *items: Item, root_only: bool = False) -> Self:
        for item in items:
            for sub in item.walk_self_and_descendants(root_only):
                try:
                    self.apprs.remove(self.timeline.item_appearances[sub])
                except ValueError:
                    pass

    def _mark_render_disabled(self):
        for appr in self.apprs:
            appr.render_disabled = True
