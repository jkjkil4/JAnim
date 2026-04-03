from __future__ import annotations

import numbers
from typing import Self

import numpy as np

from janim.anims.method_updater_meta import register_updater
from janim.components.component import CmptInfo, Component
from janim.items.effect.frame_effect import FrameEffect
from janim.items.geometry.polygon import Rect
from janim.items.item import Item
from janim.utils.bezier import interpolate
from janim.utils.config import Config
from janim.utils.data import AlignedData

frameclip_fragment_shader = '''
#version 330 core

in vec2 v_texcoord;

out vec4 f_color;

uniform sampler2D fbo;
uniform vec4 u_clip;    // left top right bottom
uniform bool u_debug;

#[JA_FINISH_UP_UNIFORMS]

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
    """
    一个用于创建简单矩形裁剪效果的类

    - ``clip`` 参数表示裁剪区域的四个边界，分别是左、上、右、下，范围是 0~1 表示百分比
    - ``debug`` 参数表示是否开启调试模式，开启后裁剪区域外的部分会显示为半透明红色
    """

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
        """
        得到裁剪后的显示区域的包围矩形
        """
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

#[JA_FINISH_UP_UNIFORMS]

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
    """
    与 :class:`FrameClip` 类似，但支持更多的变换操作（偏移、缩放、旋转）

    - ``clip`` 参数表示裁剪区域的四个边界，分别是左、上、右、下，范围是 0~1 表示百分比
    - ``offset`` 参数表示裁剪区域 x 与 y 方向的的偏移量，单位是百分比
    - ``scale`` 参数表示裁剪区域 x 与 y 方向的缩放量，单位是百分比
    - ``rotate`` 参数表示裁剪区域的旋转角度
    - ``debug`` 参数表示是否开启调试模式，开启后裁剪区域外的部分会显示为半透明红色
    """

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
        """
        得到裁剪后的显示区域的包围矩形
        """
        left, top, right, bottom, x_offset, y_offset, x_scale, y_scale, rotate = self.clip._attrs

        dl = Config.get.left_side + Config.get.bottom
        width, height = Config.get.frame_width, Config.get.frame_height
        p1 = dl + [width * left, height * bottom, 0]
        p2 = dl + [width * (1 - right), height * (1 - top), 0]

        rect = Rect(p1, p2, **kwargs)
        rect.points.shift([width * x_offset, height * y_offset, 0]).scale([x_scale, y_scale, 1]).rotate(rotate)

        return rect
