from __future__ import annotations

from typing import Iterable, Self

import numpy as np

from janim.anims.method_updater_meta import register_updater
from janim.anims.timeline import Timeline
from janim.anims.updater import DataUpdater, UpdaterParams
from janim.components.component import CmptInfo, Component
from janim.components.simple import Cmpt_List
from janim.items.item import Item
from janim.locale.i18n import get_local_strings
from janim.logger import log
from janim.render.renderer_frameeffect import FrameEffectRenderer
from janim.utils.bezier import interpolate
from janim.utils.config import Config
from janim.utils.data import AlignedData

_ = get_local_strings('frame_effect')


class FrameEffect(Item):
    '''
    将传入的着色器 ``fragment_shader`` 应用到 ``items`` 上

    着色器基本格式：

    .. code-block:: glsl

        #version 330 core

        in vec2 v_texcoord; // 传入的纹理坐标
        out vec4 f_color;   // 输出的颜色

        uniform sampler2D fbo; // 传入的纹理（承载了 items 的渲染结果）

        // used by JA_FINISH_UP
        uniform bool JA_BLENDING;
        uniform sampler2D JA_FRAMEBUFFER;

        void main()
        {
            // 进行处理，例如
            f_color = texture(fbo, v_texcoord); // 读取纹理颜色
            f_color.rgb = 1.0 - f_color.rgb; // 反色

            #[JA_FINISH_UP]
        }

    其中 ``#[JA_FINISH_UP]`` 是一个占位符，JAnim 会在这里做一些额外的操作

    上述代码最核心的是 ``main`` 中“进行处理”的部分，其余的代码作为固定的写法照抄即可

    如果懒得抄，可以用 :class:`SimpleFrameEffect`，这个类只要写“进行处理”这部分就好了，因为它把其余代码都封装了

    完整示例请参考 :ref:`样例学习 <examples>` 中的对应代码
    '''
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

    def _pop_uniforms(self) -> dict:
        uniforms = self._uniforms
        if self.cache_key is None:
            self._uniforms = {}
        return uniforms

    def _pop_optional_uniforms(self) -> dict:
        uniforms = self._optional_uniforms
        if self.cache_key is None:
            self._optional_uniforms = {}
        return uniforms

    def dynamic_uniforms(self) -> dict:
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


simple_frameeffect_shader = '''
#version 330 core

in vec2 v_texcoord;

out vec4 f_color;

uniform sampler2D fbo;

#[JA_SIMPLE_FRAMEEFFECT_UNIFORMS]

// used by JA_FINISH_UP
uniform bool JA_BLENDING;
uniform sampler2D JA_FRAMEBUFFER;

void main()
{
    #[JA_SIMPLE_FRAMEEFFECT_SHADER]

    #[JA_FINISH_UP]
}
'''


class SimpleFrameEffect(FrameEffect):
    '''
    :class:`FrameEffect` 的简化封装，具体请参考 :class:`FrameEffect` 中的说明

    .. warning::

        若着色器代码中出现报错，报错行数无法与 ``shader`` 代码中的行对应
    '''
    def __init__(
        self,
        *items: Item,
        shader: str,
        uniforms: Iterable[str] = [],
        cache_key: str | None = None,
        root_only: bool = False,
        **kwargs
    ):
        uniforms_code = '\n'.join(
            f'uniform {uniform};'
            for uniform in uniforms
        )
        super().__init__(
            *items,
            fragment_shader=simple_frameeffect_shader
                .replace('#[JA_SIMPLE_FRAMEEFFECT_UNIFORMS]', uniforms_code)
                .replace('#[JA_SIMPLE_FRAMEEFFECT_SHADER]', shader),
            cache_key=cache_key,
            root_only=root_only,
            **kwargs
        )


frameclip_fragment_shader = '''
#version 330 core

in vec2 v_texcoord;

out vec4 f_color;

uniform sampler2D fbo;
uniform vec4 u_clip;    // left top right bottom
uniform bool u_debug;

// used by JA_FINISH_UP
uniform bool JA_BLENDING;
uniform sampler2D JA_FRAMEBUFFER;

void main()
{
    if (
        v_texcoord.x < u_clip[0] || v_texcoord.x > 1.0 - u_clip[2] ||
        v_texcoord.y < u_clip[3] || v_texcoord.y > 1.0 - u_clip[1]
    ) {
        if (u_debug) {
            f_color = vec4(1.0, 0.0, 0.0, 0.2);
            return;
        } else {
            discard;
        }
    }

    f_color = texture(fbo, v_texcoord);

    #[JA_FINISH_UP]
}
'''


class Cmpt_FrameClip[ItemT](Component[ItemT]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._clip = np.zeros(4, dtype=np.float32)

    def copy(self) -> Self:
        cmpt_copy = super().copy()
        cmpt_copy._clip = self._clip.copy()
        return cmpt_copy

    def become(self, other: Cmpt_FrameClip) -> Self:
        self._clip = other._clip.copy()
        return self

    def not_changed(self, other: Cmpt_FrameClip) -> bool:
        return np.all(self._clip == other._clip)

    @classmethod
    def align_for_interpolate(cls, cmpt1: Cmpt_FrameClip, cmpt2: Cmpt_FrameClip):
        return AlignedData(cmpt1.copy(), cmpt2.copy(), cmpt1.copy())

    def interpolate(self, cmpt1: Self, cmpt2: Self, alpha: float, *, path_func=None) -> None:
        self.set(*interpolate(cmpt1._clip, cmpt2._clip, alpha))

    def _set_updater(self, p, left=None, top=None, right=None, bottom=None):
        if left is not None:
            left = interpolate(self._clip[0], left, p.alpha)
        if top is not None:
            top = interpolate(self._clip[1], top, p.alpha)
        if right is not None:
            right = interpolate(self._clip[2], right, p.alpha)
        if bottom is not None:
            bottom = interpolate(self._clip[3], bottom, p.alpha)
        self.set(left, top, right, bottom)

    @register_updater(_set_updater)
    def set(
        self,
        left: float | None = None,
        top: float | None = None,
        right: float | None = None,
        bottom: float | None = None,
    ) -> Self:
        if left is not None:
            self._clip[0] = left
        if top is not None:
            self._clip[1] = top
        if right is not None:
            self._clip[2] = right
        if bottom is not None:
            self._clip[3] = bottom

        return self


class FrameClip(FrameEffect):
    '''
    一个用于创建简单矩形裁剪效果的类

    ``clip`` 参数表示裁剪区域的四个边界，分别是左、上、右、下，范围是 0~1 表示百分比
    '''

    clip = CmptInfo(Cmpt_FrameClip[Self])

    def __init__(
        self,
        *items: Item,
        clip: tuple[float, float, float, float] = (0, 0, 0, 0),
        debug: bool = False,
        root_only: bool = False,
        **kwargs
    ):
        super().__init__(
            *items,
            fragment_shader=frameclip_fragment_shader,
            cache_key='frameclip',
            root_only=root_only,
            **kwargs
        )

        self.apply_uniforms(u_debug=debug)
        self.clip.set(*clip)

    def dynamic_uniforms(self):
        return dict(u_clip=self.clip._clip.data)


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
    '''
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

    .. warning::

        实际的报错行数要减去 10

        例如，如果在上面的例子中将 ``iResolution`` 误写为了 ``Resolution``，
        会导致 ``0(12) : error C1503: undefined variable "Resolution"`` 的报错，
        报错信息说的是在第 12 行，实际是第 2 行

        行数标注：

        .. code-block:: python

            Shadertoy(
                0 \'''
                1 void mainImage( out vec4 fragColor, in vec2 fragCoord ) {
                2     vec2 uv = fragCoord.xy / iResolution.xy;
                3     vec3 color = vec3(uv.x, uv.y, 0.5);
                4     fragColor = vec4(color, 1.0);
                5 }
                6 \'''
            ).show()
    '''
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
