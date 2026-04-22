from __future__ import annotations

from typing import Self

import numpy as np

from janim.anims.updater import DataUpdater, UpdaterParams
from janim.components.component import CmptInfo
from janim.components.simple import Cmpt_Float
from janim.items.effect.frame_effect import FrameEffect, SimpleFrameEffect
from janim.items.item import Item
from janim.render.shader import ShaderInjection
from janim.utils.config import Config


class AlphaEffect(SimpleFrameEffect):
    alpha = CmptInfo(Cmpt_Float[Self], 1.0)

    def __init__(
        self,
        *items: Item,
        root_only: bool = False,
        **kwargs,
    ):
        super().__init__(
            *items,
            root_only=root_only,
            shader='f_color = texture(fbo, v_texcoord); f_color.a *= alpha;',
            uniforms=['float alpha'],
            cache_key='alpha_effect',
            **kwargs,
        )

    def dynamic_uniforms(self):
        return dict(alpha=self.alpha._value)


shadertoy_fragment_shader = """
#version 330 core

in vec2 v_texcoord;

out vec4 f_color;

uniform vec2 iResolution;
uniform float iTime;

#[JA_SHADERTOY]

#[JA_FINISH_UP_UNIFORMS]

void main()
{
    mainImage(f_color, v_texcoord * iResolution);

    #[JA_FINISH_UP]
}
"""


class Shadertoy(FrameEffect):
    """
    一个用于创建类似 Shadertoy 着色器效果的类

    例:

    .. code-block:: python

        Shadertoy(
            \'''
            void mainImage( out vec4 fragColor, in vec2 fragCoord ) {
                vec2 uv = fragCoord.xy / iResolution.xy;
                vec3 color = vec3(uv.x, uv.y, 0.5);
                fragColor = vec4(color, 1.0);
            }
            \'''
        ).show()

    .. note::

        如果该着色器代码中出现报错，会显示为 ``JA_SHADERTOY`` 中出现的
    """

    def __init__(
        self,
        shader: str,
        *,
        cache_key: str | None = None,
        root_only: bool = False,
        **kwargs,
    ):
        with ShaderInjection(JA_SHADERTOY=shader.strip()):
            super().__init__(
                fragment_shader=shadertoy_fragment_shader,
                cache_key=cache_key,
                root_only=root_only,
                **kwargs,
            )

        self.apply_uniforms(
            iResolution=np.array([Config.get.frame_width, Config.get.frame_height])
            / Config.get.default_pixel_to_frame_ratio,
            iTime=0,
            optional=True,
        )

    def create_updater(self, **kwargs) -> DataUpdater:
        return DataUpdater(self, self.updater, **kwargs)

    @staticmethod
    def updater(data: Shadertoy, p: UpdaterParams) -> None:
        data.apply_uniforms(
            iTime=p.elapsed,
            optional=True,
        )
