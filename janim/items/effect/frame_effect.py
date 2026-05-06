from __future__ import annotations

from typing import Any, Iterable, Self

from janim.anims.timeline import Timeline
from janim.components.component import CmptInfo
from janim.components.simple import Cmpt_Dict, Cmpt_List
from janim.items.item import Item
from janim.locale import get_translator
from janim.logger import log
from janim.render.renderer_frameeffect import FrameEffectRenderer
from janim.render.shader import ShaderInjection, shader_injections_ctx

_ = get_translator('janim.items.frame_effect')


class FrameEffect(Item):
    """
    将传入的着色器 ``fragment_shader`` 应用到 ``items`` 上

    着色器基本格式：

    .. code-block:: glsl

        #version 330 core

        in vec2 v_texcoord; // 传入的纹理坐标
        out vec4 f_color;   // 输出的颜色

        uniform sampler2D fbo; // 传入的纹理（承载了 items 的渲染结果）

        #[JA_FINISH_UP_UNIFORMS]

        void main()
        {
            // 进行处理，例如
            f_color = texture(fbo, v_texcoord); // 读取纹理颜色
            f_color.rgb = 1.0 - f_color.rgb; // 反色

            #[JA_FINISH_UP]
        }

    其中 ``#[JA_FINISH_UP]`` 是一个占位符，JAnim 会在这里做一些额外的操作，前面的 ``#[JA_FINISH_UP_UNIFORMS]`` 与之对应

    上述代码最核心的是 ``main`` 中“进行处理”的部分，其余的代码作为固定的写法照抄即可

    如果懒得抄，可以用 :class:`SimpleFrameEffect`，这个类只要写“进行处理”这部分就好了，因为它把其余代码都封装了

    完整示例请参考 :ref:`基础样例 <basic_examples>` 中的对应代码
    """

    renderer_cls = FrameEffectRenderer

    _items = CmptInfo(Cmpt_List[Self, Item])
    _apprs = CmptInfo(Cmpt_List[Self, Timeline.ItemAppearance])

    _uniforms = CmptInfo(Cmpt_Dict[Self, str, Any])
    _optional_uniforms = CmptInfo(Cmpt_Dict[Self, str, Any])

    def __init__(
        self,
        *items: Item,
        fragment_shader: str,
        cache_key: str | None = None,
        root_only: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.fragment_shader = fragment_shader
        self.cache_key = cache_key
        self.injections = shader_injections_ctx.get()

        self.apply(*items, root_only=root_only)

    def apply_uniforms(self, *, optional: bool = False, **kwargs) -> None:
        if optional:
            self._optional_uniforms.update(kwargs)
        else:
            self._uniforms.update(kwargs)

    def dynamic_uniforms(self) -> dict:
        return {}

    def add(self, *objs, prepend=False, insert=None) -> Self:
        """
        .. warning::

            调用 :meth:`add` 很可能不会按预期工作

            如果你想应用额外的物件，需要使用 :meth:`apply`
        """
        if objs:
            log.warning(
                _(
                    'Calling {cls}.add is unusual and may not work as expected. '
                    'If you want to apply additional items, use `apply` instead.'
                ).format(cls=self.__class__.__name__)
            )
        super().add(*objs, prepend=prepend, insert=insert)
        return self

    def remove(self, *objs) -> Self:
        """
        .. warning::

            调用 :meth:`remove` 很可能不会按预期工作

            如果你想应用额外的物件，需要使用 :meth:`discard`
        """
        if objs:
            log.warning(
                _(
                    'Calling {cls}.remove is unusual and may not work as expected. '
                    'If you want to discard applied items, use `discard` instead.'
                ).format(cls=self.__class__.__name__)
            )
        return super().remove(*objs)

    def apply(self, *items: Item, root_only: bool = False) -> Self:
        """
        对更多物件应用效果
        """
        apply_items = [
            sub
            for item in items
            for sub in item.walk_self_and_descendants(root_only)
            if sub not in self._items
        ]
        self._items.extend(apply_items)
        self._apprs.extend(self.timeline.item_appearances[item] for item in apply_items)

    def discard(self, *items: Item, root_only: bool = False) -> Self:
        """
        对指定物件的取消应用效果
        """
        for item in items:
            for sub in item.walk_self_and_descendants(root_only):
                try:
                    self._items.remove(sub)
                    self._apprs.remove(self.timeline.item_appearances[sub])
                except ValueError:
                    pass

    def _mark_render_disabled(self, extras: list[Timeline.ExtraRenderGroup]):
        for appr in self._apprs:
            appr.render_disabled = True

        self._extra_lists = []  # 使得 Transform 以及类似动画能够正确应用 FrameEffect

        for rg in extras:
            if all((item in self._items) for item in rg.related_items):
                rg.render_disabled = True
                self._extra_lists.append(rg.func())


simple_frameeffect_shader = """
#version 330 core

in vec2 v_texcoord;

out vec4 f_color;

uniform sampler2D fbo;

#[JA_SIMPLE_FRAMEEFFECT_UNIFORMS]

#[JA_FINISH_UP_UNIFORMS]

void main()
{
    #[JA_SIMPLE_FRAMEEFFECT_SHADER]

    #[JA_FINISH_UP]
}
"""


class SimpleFrameEffect(FrameEffect):
    """
    :class:`FrameEffect` 的简化封装，具体请参考 :class:`FrameEffect` 中的说明

    .. note::

        如果该着色器代码中出现报错，会显示为 ``JA_SIMPLE_FRAMEEFFECT_SHADER`` 中出现的
    """

    def __init__(
        self,
        *items: Item,
        shader: str,
        uniforms: Iterable[str] = [],
        cache_key: str | None = None,
        root_only: bool = False,
        **kwargs,
    ):
        uniforms_code = '\n'.join(
            f'uniform {uniform};'  #
            for uniform in uniforms
        )
        with ShaderInjection(
            JA_SIMPLE_FRAMEEFFECT_UNIFORMS=uniforms_code,
            JA_SIMPLE_FRAMEEFFECT_SHADER=shader.strip(),
        ):
            super().__init__(
                *items,
                fragment_shader=simple_frameeffect_shader,
                cache_key=cache_key,
                root_only=root_only,
                **kwargs,
            )
