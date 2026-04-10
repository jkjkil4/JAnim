from __future__ import annotations

import numbers
from typing import Self

import numpy as np

from janim.anims.method_updater_meta import register_updater
from janim.components.component import CmptInfo, Component
from janim.components.points import Cmpt_Points
from janim.components.simple import Cmpt_Float
from janim.items.effect.frame_effect import FrameEffect
from janim.items.geometry.polygon import Rect
from janim.items.item import Item
from janim.items.shape_matchers import FrameRect
from janim.render.base import Renderer
from janim.render.renderer_frameeffect import FrameEffectRenderer
from janim.render.renderer_vitem import VItemRenderer
from janim.typing import Vect
from janim.utils.bezier import interpolate
from janim.utils.config import Config
from janim.utils.data import AlignedData

frameclip_fragment_shader = '''
#version 330 core

in vec2 v_texcoord;

out vec4 f_color;

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

    f_color = frame_texture(v_texcoord);

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

    :param clip: 裁剪区域的四个边界，分别是左、上、右、下，范围是 0~1 表示百分比
    :param debug: 是否开启调试模式，开启后裁剪区域外的部分会显示为半透明红色
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

    f_color = frame_texture(uv);

    #[JA_FINISH_UP]
}
'''


class Cmpt_Attrs[ItemT](Component[ItemT]):
    """
    :class:`Cmpt_TransformableFrameClip` 和 :class:`Cmpt_RectClipTransform` 的基类
    """

    size: int = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._attrs = np.zeros(self.size, dtype=np.float32)

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


class Cmpt_TransformableFrameClip[ItemT](Cmpt_Attrs[ItemT], impl=True):
    size = 9

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
                v if v is None else interpolate(self._attrs[i], v, p.alpha)
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

    :param clip: 裁剪区域的四个边界，分别是左、上、右、下，范围是 0~1 表示百分比
    :param offset: 裁剪区域 x 与 y 方向的的偏移量，单位是百分比
    :param scale: 裁剪区域 x 与 y 方向的缩放量，单位是百分比
    :param rotate: 裁剪区域的旋转角度
    :param debug: 是否开启调试模式，开启后裁剪区域外的部分会显示为半透明红色

    可另行参考 :class:`RectClip`，它在一些情况下会好用得多
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


rectclip_fragment_shader = '''
#version 330 core

in vec2 v_texcoord;

out vec4 f_color;

uniform vec2 JA_FRAME_RADIUS;
uniform vec2 u_anchor;
uniform vec2 u_orig;
uniform vec2 u_vec_right;
uniform vec2 u_vec_up;
uniform float u_center_on;
uniform float u_scale;
uniform float u_rotate;

#[JA_FINISH_UP_UNIFORMS]

void main()
{
    vec2 pos = (v_texcoord * 2.0 - 1.0) * JA_FRAME_RADIUS;
    vec2 rel = pos - u_orig;
    float det = u_vec_right.x * u_vec_up.y - u_vec_right.y * u_vec_up.x;

    // 使用 Cramer 法则将 rel 分解到 u_vec_right 和 u_vec_up 基向量上
    if (abs(det) < 1e-6)
        discard;

    vec2 uv = vec2(
        (rel.x * u_vec_up.y - rel.y * u_vec_up.x) / det,
        (u_vec_right.x * rel.y - u_vec_right.y * rel.x) / det
    );

    if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0)
        discard;

    vec2 ratio = 0.5 * u_anchor / JA_FRAME_RADIUS + 0.5;
    ratio = mix(ratio, vec2(0.5, 0.5), u_center_on);
    vec2 anchor_to = u_orig + ratio.x * u_vec_right + ratio.y * u_vec_up;

    // 将 pos 减去 anchor_to，相当于考虑把 anchor 平移回原点后的坐标空间
    // 从而正确计算变换效果
    rel = pos - anchor_to;
    if (u_scale != 1.0)
        rel /= u_scale;
    if (u_rotate != 0.0) {
        float cos_v = cos(-u_rotate);
        float sin_v = sin(-u_rotate);
        rel = vec2(
            rel.x * cos_v - rel.y * sin_v,
            rel.x * sin_v + rel.y * cos_v
        );
    }
    rel += u_anchor;
    vec2 texcoord = (rel / JA_FRAME_RADIUS + 1.0) / 2;

    if (texcoord.x < 0.0 || texcoord.x > 1.0 || texcoord.y < 0.0 || texcoord.y > 1.0)
        discard;

    f_color = frame_texture(texcoord);

    #[JA_FINISH_UP]
}
'''


class Cmpt_RectClipTransform[ItemT](Cmpt_Attrs[ItemT], impl=True):
    size = 2

    def _set_updater(self, p, scale=None, rotate=None):
        self.set(
            *(
                v if v is None else interpolate(self._attrs[i], v, p.alpha)
                for i, v in enumerate((scale, rotate))
            )
        )

    @register_updater(_set_updater)
    def set(
        self,
        scale: float | None = None,
        rotate: float | None = None,
    ) -> Self:
        for i, v in enumerate((scale, rotate)):
            if v is not None:
                self._attrs[i] = v

        return self


class RectClip(FrameEffect, FrameRect):
    """
    矩形裁剪效果

    与 :class:`FrameClip` 不同，裁剪区域由当前 :class:`FrameRect` 的几何形状动态决定，跟随该矩形的几何状态

    :param \\*items:
        需要应用该裁剪效果的物件

    :param anchor:
        裁剪内容变换时的锚点（场景坐标）

    :param center_on:
        是否让锚点始终居中于矩形中心；

        默认为 ``False``，则锚点位置相对于矩形边框的百分比始终不变；若为 ``True``，则内容整体会被平移使得锚点处于矩形中心

    :param scale:
        裁剪内容相对于锚点位置的缩放系数

    :param rotate:
        裁剪内容相对于锚点位置的旋转角度（弧度制）

    :param border:
        是否绘制裁剪矩形边框

    其中：

    - ``anchor`` 也可以使用 :meth:`set_anchor` 设置
    - ``center_on`` 也可以使用 :meth:`set_center_on` 设置
    - ``scale`` 和 ``rotate`` 也可以使用  ``.transform.set(...)`` 设置

    .. tip::

        :class:`RectClip` 几乎可以像一个 :class:`~.Rect` 一样操作，进行各种变换与对齐，这使得将其放到合适的位置变得更加容易

        并且在 ``border=True`` 时，:class:`~.Rect` 的各种视觉特性，例如边框颜色，泛光效果等，都是可用的

    .. janim-example:: RectClipExample
        :extract-from-test:
        :media: _static/videos/RectClipExample.mp4
        :url: https://janim.readthedocs.io/zh-cn/latest/janim/items/effect/clip.html#rectclip
    """

    class RCRenderer(Renderer):
        def __init__(self):
            self.effect_renderer = FrameEffectRenderer()
            self.vitem_renderer = VItemRenderer()

        def render(self, item: RectClip) -> None:
            self.effect_renderer.render(item)
            if item._border:
                self.vitem_renderer.render(item)

    renderer_cls = RCRenderer

    _anchor = CmptInfo(Cmpt_Points[Self])
    _center_on = CmptInfo(Cmpt_Float[Self], 0)

    transform = CmptInfo(Cmpt_RectClipTransform[Self])

    def __init__(
        self,
        *items: Item,
        anchor: Vect,
        center_on: bool = False,
        scale: float = 1,
        rotate: float = 0,
        border: bool = False,
        **kwargs
    ):
        super().__init__(
            *items,
            fragment_shader=rectclip_fragment_shader,
            cache_key='rectclip',
            **kwargs
        )
        self._border = border
        self.set_anchor(anchor)
        self.set_center_on(center_on)
        self.transform.set(scale, rotate)

    def set_anchor(self, point: Vect) -> Self:
        self._anchor.set([point])
        return self

    def get_anchor(self) -> np.ndarray:
        return self._anchor.get()[0].copy()

    def set_center_on(self, center_on: bool = True) -> Self:
        self._center_on.set(float(center_on))
        return self

    def is_center_on(self) -> bool:
        return self._center_on.get() > 0.5

    def dynamic_uniforms(self):
        points = self.points.get()[:, :2]
        orig, right, up = points[[4, 6, 2]]
        vec_right = right - orig
        vec_up = up - orig
        return dict(
            u_anchor=self._anchor.get()[0, :2],
            u_orig=points[4],
            u_vec_right=vec_right,
            u_vec_up=vec_up,
            u_center_on=self._center_on.get(),
            u_scale=self.transform._attrs[0],
            u_rotate=self.transform._attrs[1],
        )
