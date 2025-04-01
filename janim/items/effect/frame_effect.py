from __future__ import annotations

from typing import Self

import numpy as np

from janim.anims.timeline import Timeline
from janim.anims.updater import DataUpdater, UpdaterParams
from janim.components.component import CmptInfo
from janim.components.simple import Cmpt_List
from janim.items.item import Item
from janim.locale.i18n import get_local_strings
from janim.logger import log
from janim.render.renderer_frameeffect import FrameEffectRenderer
from janim.utils.config import Config

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

        self._uniforms = {}
        self._optional_uniforms = {}

        self.apply(*items, root_only=root_only)

    def apply_uniforms(self, *, optional: bool = False, **kwargs) -> None:
        if optional:
            self._optional_uniforms.update(kwargs)
        else:
            self._uniforms.update(kwargs)

    def pop_uniforms(self) -> dict:
        uniforms = self._uniforms
        self._uniforms = {}
        return uniforms

    def pop_optional_uniforms(self) -> dict:
        uniforms = self._optional_uniforms
        self._optional_uniforms = {}
        return uniforms

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


shadertoy_fragment_shader = '''
#version 330 core

in vec2 v_texcoord;

out vec4 f_color;

uniform vec2 iResolution;
uniform float iTime;

#[JA_SHADERTOY]

// used by JA_FINISH_UP
uniform bool JA_BLENDING;
uniform sampler2D JA_FRAMEBUFFER;

void main()
{
    mainImage(f_color, v_texcoord * iResolution);

    #[JA_FINISH_UP]
}

'''


class Shadertoy(FrameEffect):
    def __init__(
        self,
        shader: str,
        *,
        cache_key: str | None = None,
        root_only: bool = False,
        **kwargs
    ):
        super().__init__(
            fragment_shader=shadertoy_fragment_shader.replace('#[JA_SHADERTOY]', shader),
            cache_key=cache_key,
            root_only=root_only,
            **kwargs
        )

        self.apply_uniforms(
            iResolution=np.array([Config.get.frame_width, Config.get.frame_height]) / Config.get.default_pixel_to_frame_ratio,
            iTime=0,
            optional=True
        )

    def create_updater(self, **kwargs) -> DataUpdater:
        return DataUpdater(self, self.updater, **kwargs)

    @staticmethod
    def updater(data: Shadertoy, p: UpdaterParams) -> None:
        data.apply_uniforms(
            iTime=p.global_t - p.range.at,
            optional=True
        )
