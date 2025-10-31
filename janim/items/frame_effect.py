from __future__ import annotations

import numbers
from typing import Any, Iterable, Self

import numpy as np

from janim.anims.method_updater_meta import register_updater
from janim.anims.timeline import Timeline
from janim.anims.updater import DataUpdater, UpdaterParams
from janim.components.component import CmptInfo, Component
from janim.components.simple import Cmpt_Dict, Cmpt_Float, Cmpt_List
from janim.items.geometry.polygon import Rect
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

    完整示例请参考 :ref:`样例学习 <basic_examples>` 中的对应代码
    '''
    renderer_cls = FrameEffectRenderer

    apprs = CmptInfo(Cmpt_List[Self, Timeline.ItemAppearance])

    _uniforms = CmptInfo(Cmpt_Dict[Self, str, Any])
    _optional_uniforms = CmptInfo(Cmpt_Dict[Self, str, Any])

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

    def apply_uniforms(self, *, optional: bool = False, **kwargs) -> None:
        if optional:
            self._optional_uniforms.update(kwargs)
        else:
            self._uniforms.update(kwargs)

    def dynamic_uniforms(self) -> dict:
        return {}

    def add(self, *objs, insert=False) -> Self:
        if objs:
            log.warning(
                _('Calling {cls}.add is unusual and may not work as expected. '
                  'If you want to apply additional items, use `apply` instead.')
                .format(cls=self.__class__.__name__)
            )
        super().add(*objs, insert=insert)
        return self

    def remove(self, *objs) -> Self:
        if objs:
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

        self._attrs = np.zeros(4, dtype=np.float32)

    def copy(self) -> Self:
        cmpt_copy = super().copy()
        cmpt_copy._attrs = self._attrs.copy()
        return cmpt_copy

    def become(self, other: Cmpt_FrameClip) -> Self:
        self._attrs = other._attrs.copy()
        return self

    def not_changed(self, other: Cmpt_FrameClip) -> bool:
        return np.all(self._attrs == other._attrs)

    @classmethod
    def align_for_interpolate(cls, cmpt1: Cmpt_FrameClip, cmpt2: Cmpt_FrameClip):
        return AlignedData(cmpt1.copy(), cmpt2.copy(), cmpt1.copy())

    def interpolate(self, cmpt1: Self, cmpt2: Self, alpha: float, *, path_func=None) -> None:
        self.set(*interpolate(cmpt1._attrs, cmpt2._attrs, alpha))

    def _set_updater(
        self,
        p,
        left=None, top=None, right=None, bottom=None,
    ):
        self.set(
            *(
                v if v is not None else interpolate(self._attrs[i], v, p.alpha)
                for i, v in enumerate((left, top, right, bottom))
            )
        )

    @register_updater(_set_updater)
    def set(
        self,
        left: float | None = None,
        top: float | None = None,
        right: float | None = None,
        bottom: float | None = None,
    ) -> Self:
        for i, v in enumerate((left, top, right, bottom)):
            if v is not None:
                self._attrs[i] = v

        return self


class FrameClip(FrameEffect):
    '''
    一个用于创建简单矩形裁剪效果的类

    - ``clip`` 参数表示裁剪区域的四个边界，分别是左、上、右、下，范围是 0~1 表示百分比
    - ``debug`` 参数表示是否开启调试模式，开启后裁剪区域外的部分会显示为半透明红色
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
        return dict(u_clip=self.clip._attrs)

    def create_border_rect(self, **kwargs) -> Rect:
        '''
        得到裁剪后的显示区域的包围矩形
        '''
        dl = Config.get.left_side + Config.get.bottom
        width, height = Config.get.frame_width, Config.get.frame_height
        left, top, right, bottom = self.clip._attrs
        p1 = dl + [width * left, height * bottom, 0]
        p2 = dl + [width * (1 - right), height * (1 - top), 0]
        return Rect(p1, p2, **kwargs)


transformable_frameclip_fragment_shader = '''
#version 330 core

in vec2 v_texcoord;

out vec4 f_color;

uniform sampler2D fbo;
uniform vec4 u_clip;    // left top right bottom
uniform vec2 u_offset;  // x, y
uniform vec2 u_scale;   // x, y
uniform float u_rotate;
uniform bool u_debug;

uniform vec2 JA_FRAME_RADIUS;

// used by JA_FINISH_UP
uniform bool JA_BLENDING;
uniform sampler2D JA_FRAMEBUFFER;

void main()
{
    vec2 uv = v_texcoord - u_offset;

    if (u_rotate != 0.0 || any(notEqual(u_scale, vec2(1.0)))) {
        uv -= vec2(0.5, 0.5);

        if (u_rotate != 0.0) {
            uv *= JA_FRAME_RADIUS;

            float cos_v = cos(-u_rotate);
            float sin_v = sin(-u_rotate);
            uv = vec2(
                uv.x * cos_v - uv.y * sin_v,
                uv.x * sin_v + uv.y * cos_v
            );

            uv /= JA_FRAME_RADIUS;
        }

        if (any(notEqual(u_scale, vec2(1.0)))) {
            uv /= u_scale;
        }

        uv += vec2(0.5, 0.5);
    }

    if (
        uv.x < u_clip[0] || uv.x > 1.0 - u_clip[2] ||
        uv.y < u_clip[3] || uv.y > 1.0 - u_clip[1]
    ) {
        if (u_debug) {
            f_color = vec4(1.0, 0.0, 0.0, 0.2);
            return;
        } else {
            discard;
        }
    }

    f_color = texture(fbo, uv);

    #[JA_FINISH_UP]
}
'''


class Cmpt_TransformableFrameClip[ItemT](Component[ItemT]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._attrs = np.zeros(9, dtype=np.float32)

    def copy(self) -> Self:
        cmpt_copy = super().copy()
        cmpt_copy._attrs = self._attrs.copy()
        return cmpt_copy

    def become(self, other: Cmpt_TransformableFrameClip) -> Self:
        self._attrs = other._attrs.copy()
        return self

    def not_changed(self, other: Cmpt_TransformableFrameClip) -> bool:
        return np.all(self._attrs == other._attrs)

    @classmethod
    def align_for_interpolate(cls, cmpt1: Cmpt_TransformableFrameClip, cmpt2: Cmpt_TransformableFrameClip):
        return AlignedData(cmpt1.copy(), cmpt2.copy(), cmpt1.copy())

    def interpolate(self, cmpt1: Self, cmpt2: Self, alpha: float, *, path_func=None) -> None:
        self.set(*interpolate(cmpt1._attrs, cmpt2._attrs, alpha))

    def _set_updater(
        self,
        p,
        left=None, top=None, right=None, bottom=None,
        x_offset=None, y_offset=None,
        x_scale=None, y_scale=None,
        rotate=None,
        *,
        scale=None
    ):
        if scale is not None:
            x_scale = y_scale = scale

        self.set(
            *(
                v if v is not None else interpolate(self._attrs[i], v, p.alpha)
                for i, v in enumerate((left, top, right, bottom, x_offset, y_offset, x_scale, y_scale, rotate))
            )
        )

    @register_updater(_set_updater)
    def set(
        self,
        left: float | None = None,
        top: float | None = None,
        right: float | None = None,
        bottom: float | None = None,
        x_offset: float | None = None,
        y_offset: float | None = None,
        x_scale: float | None = None,
        y_scale: float | None = None,
        rotate: float | None = None,
        *,
        scale: float | None = None
    ) -> Self:
        if scale is not None:
            x_scale = y_scale = scale

        for i, v in enumerate((left, top, right, bottom, x_offset, y_offset, x_scale, y_scale, rotate)):
            if v is not None:
                self._attrs[i] = v

        return self


class TransformableFrameClip(FrameEffect):
    '''
    与 :class:`FrameClip` 类似，但支持更多的变换操作（偏移、缩放、旋转）

    - ``clip`` 参数表示裁剪区域的四个边界，分别是左、上、右、下，范围是 0~1 表示百分比
    - ``offset`` 参数表示裁剪区域 x 与 y 方向的的偏移量，单位是百分比
    - ``scale`` 参数表示裁剪区域 x 与 y 方向的缩放量，单位是百分比
    - ``rotate`` 参数表示裁剪区域的旋转角度
    - ``debug`` 参数表示是否开启调试模式，开启后裁剪区域外的部分会显示为半透明红色
    '''

    clip = CmptInfo(Cmpt_TransformableFrameClip[Self])

    def __init__(
        self,
        *items: Item,
        clip: tuple[float, float, float, float] = (0, 0, 0, 0),
        offset: tuple[float, float] = (0, 0),
        scale: tuple[float, float] | float = (1, 1),
        rotate: float = 0,
        debug: bool = False,
        root_only: bool = False,
        **kwargs
    ):
        if isinstance(scale, numbers.Real):
            scale = (scale, scale)

        super().__init__(
            *items,
            fragment_shader=transformable_frameclip_fragment_shader,
            cache_key='transformable_frameclip',
            root_only=root_only,
            **kwargs
        )

        self.apply_uniforms(u_debug=debug)
        self.clip.set(*clip, *offset, *scale, rotate)

    def dynamic_uniforms(self):
        return dict(
            u_clip=self.clip._attrs[:4],
            u_offset=self.clip._attrs[4:6],
            u_scale=self.clip._attrs[6:8],
            u_rotate=self.clip._attrs[8]
        )

    def create_border_rect(self, **kwargs) -> Rect:
        '''
        得到裁剪后的显示区域的包围矩形
        '''
        left, top, right, bottom, x_offset, y_offset, x_scale, y_scale, rotate = self.clip._attrs

        dl = Config.get.left_side + Config.get.bottom
        width, height = Config.get.frame_width, Config.get.frame_height
        p1 = dl + [width * left, height * bottom, 0]
        p2 = dl + [width * (1 - right), height * (1 - top), 0]

        rect = Rect(p1, p2, **kwargs)
        rect.points.shift([width * x_offset, height * y_offset, 0]).scale([x_scale, y_scale, 1]).rotate(rotate)

        return rect


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
            iResolution=np.array([
                Config.get.frame_width, Config.get.frame_height
            ]) / Config.get.default_pixel_to_frame_ratio,
            iTime=0,
            optional=True
        )

    def create_updater(self, **kwargs) -> DataUpdater:
        return DataUpdater(self, self.updater, **kwargs)

    @staticmethod
    def updater(data: Shadertoy, p: UpdaterParams) -> None:
        data.apply_uniforms(
            iTime=p.elapsed,
            optional=True
        )


class AlphaEffect(SimpleFrameEffect):
    alpha = CmptInfo(Cmpt_Float[Self], 1.)

    def __init__(
        self,
        *items: Item,
        root_only: bool = False,
        **kwargs
    ):
        super().__init__(
            *items,
            root_only=root_only,
            shader='f_color = texture(fbo, v_texcoord); f_color.a *= alpha;',
            uniforms=['float alpha'],
            cache_key='alpha_effect',
            **kwargs
        )

    def dynamic_uniforms(self):
        return dict(alpha=self.alpha._value)
