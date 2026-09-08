from __future__ import annotations

from typing import Self

import numpy as np

from janim.anims.updater import DataUpdater, UpdaterParams
from janim.components.component import CmptInfo
from janim.components.simple import Cmpt_Alpha
from janim.items.effect.frame_effect import FrameEffect, SimpleFrameEffect
from janim.items.item import Item
from janim.render.shader import ShaderInjection
from janim.utils.config import Config


class AlphaEffect(SimpleFrameEffect):
    """
    透明度效果，使用 ``.alpha.set(...)`` 更新不透明度值

    示例：

    .. code-block:: python

        circles = Circle(fill_alpha=1) * 4
        circles.show()
        circles.points.arrange_in_grid(buff=-0.4)

        effect = AlphaEffect(circles)

        self.play(
            effect.anim.alpha.set(0),
            effect.anim.alpha.set(1),
            lag_ratio=1,
        )
    """

    alpha = CmptInfo(Cmpt_Alpha[Self], 1.0)

    def __init__(
        self,
        *items: Item,
        root_only: bool = False,
        **kwargs,
    ):
        super().__init__(
            *items,
            root_only=root_only,
            shader='f_color = frame_texture(v_texcoord); f_color.a *= alpha;',
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

    可以使用 :meth:`anim_update` 创建 ``iTime`` uniform 更新的动画，例如：

    .. code-block:: python

        # Originates from https://www.shadertoy.com/view/mtyGWy
        shader = Shadertoy(
            \"""
            /* This animation is the material of my first youtube tutorial about creative
            coding, which is a video in which I try to introduce programmers to GLSL
            and to the wonderful world of shaders, while also trying to share my recent
            passion for this community.
                                                Video URL: https://youtu.be/f4s1h2YETNY
            */

            //https://iquilezles.org/articles/palettes/
            vec3 palette( float t ) {
                vec3 a = vec3(0.5, 0.5, 0.5);
                vec3 b = vec3(0.5, 0.5, 0.5);
                vec3 c = vec3(1.0, 1.0, 1.0);
                vec3 d = vec3(0.263,0.416,0.557);

                return a + b*cos( 6.28318*(c*t+d) );
            }

            //https://www.shadertoy.com/view/mtyGWy
            void mainImage( out vec4 fragColor, in vec2 fragCoord ) {
                vec2 uv = (fragCoord * 2.0 - iResolution.xy) / iResolution.y;
                vec2 uv0 = uv;
                vec3 finalColor = vec3(0.0);

                for (float i = 0.0; i < 4.0; i++) {
                    uv = fract(uv * 1.5) - 0.5;

                    float d = length(uv) * exp(-length(uv0));

                    vec3 col = palette(length(uv0) + i*.4 + iTime*.4);

                    d = sin(d*8. + iTime)/8.;
                    d = abs(d);

                    d = pow(0.01 / d, 1.2);

                    finalColor += col * d;
                }

                fragColor = vec4(finalColor, 1.0);
            }
            \"""
        )

        self.play(
            shader.anim_update(duration=4),
        )
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

    def anim_update(self, **kwargs) -> DataUpdater:
        """
        创建 ``iTime`` uniform 更新的动画
        """
        return DataUpdater(self, self.updater, **kwargs)

    def create_updater(self, **kwargs) -> DataUpdater:
        """
        同 :meth:`anim_update` ，此为旧名称
        """
        return DataUpdater(self, self.updater, **kwargs)

    @staticmethod
    def updater(data: Shadertoy, p: UpdaterParams) -> None:
        data.apply_uniforms(
            iTime=p.elapsed,
            optional=True,
        )
