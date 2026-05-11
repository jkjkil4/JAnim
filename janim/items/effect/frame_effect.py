from __future__ import annotations

import inspect
import os
import re
from typing import Any, Iterable, Self

from janim.anims.timeline import RenderCollection
from janim.components.component import CmptInfo
from janim.components.simple import Cmpt_Dict, Cmpt_List
from janim.items.item import Item
from janim.locale import get_translator
from janim.logger import log
from janim.render.renderer_frameeffect import FrameEffectRenderer
from janim.render.shader import (
    ShaderInjection,
    _injection_ja_finish_up_uniforms,
    shader_injections_ctx,
)

_ = get_translator('janim.items.effect.frame_effect')


_frameeffect_injection = """
uniform sampler2D fbo;
vec4 frame_texture(vec2 texcoord)
{
    vec4 color = texture(fbo, texcoord);
    // 从 PMA 转换到直通颜色
    if (color.a != 0)
        color.rgb /= color.a;
    return color;
}
"""


class AppliedGroup(Item):
    """
    :class:`FrameEffect` 等类的基础类

    提供了 :meth:`apply` 和 :meth:`discord` 方法用于标记对指定的物件 应用/取消应用 效果
    """

    _items = CmptInfo(Cmpt_List[Self, Item])

    def __init__(self, *items: Item, root_only: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.apply(*items, root_only=root_only)

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
        return self

    def discard(self, *items: Item, root_only: bool = False) -> Self:
        """
        对指定物件的取消应用效果
        """
        for item in items:
            for sub in item.walk_self_and_descendants(root_only):
                try:
                    self._items.remove(sub)
                except ValueError:
                    pass
        return self

    def _render_collection_hook(self, collection: RenderCollection) -> None:
        self._render_collection = collection.delegates(self._items)


_regex_fbo_declaration = re.compile(r'uniform\s+sampler2D\s+fbo\s*;')
_regex_texture_fbo = re.compile(r'texture\s*\(\s*fbo\s*,')  # )


def _apply_fixes_for_compatibility(fragment_shader: str) -> str:
    """
    对 < 5.0.0 版本的着色器代码的兼容

    会尝试对旧版本着色器代码的一些关键部分进行替换，若产生替换，会给出提示和警告
    """
    from janim.utils.deprecation import is_removed

    if is_removed((5, 4)):
        return fragment_shader

    fixes: list[str] = []

    fragment_shader, count = re.subn(_regex_fbo_declaration, '', fragment_shader)
    if count != 0:
        fixes.append(_('Removed "{code}"').format(code='uniform sampler2D fbo;'))

    fragment_shader, count = re.subn(_regex_texture_fbo, 'frame_texture(', fragment_shader)  # )
    if count != 0:
        fixes.append(
            _('Replaced "{orig}" by "{code}"').format(
                orig='texture(fbo,',  # )
                code='frame_texture(',  # )
            )
        )

    if fixes:
        frame = inspect.currentframe().f_back.f_back
        filename = os.path.basename(frame.f_code.co_filename)
        lineno = frame.f_lineno

        log.warning(
            _(
                'Detected legacy-style shader code passed to FrameEffect at {file}:{lineno}\n'
                'An automatic migration has been attempted with the following changes:\n'
                '{fixes}\n'
                'The legacy usage will be deprecated in JAnim 5.4'
            ).format(
                file=filename,
                lineno=lineno,
                fixes='\n'.join(f'- {fix}' for fix in fixes),
            )
        )

    return fragment_shader


class FrameEffect(AppliedGroup):
    """
    将传入的着色器 ``fragment_shader`` 应用到 ``items`` 上

    着色器基本格式：

    .. code-block:: glsl

        #version 330 core

        in vec2 v_texcoord; // 传入的纹理坐标
        out vec4 f_color;   // 输出的颜色

        #[JA_FINISH_UP_UNIFORMS]

        void main()
        {
            // 进行处理，例如
            f_color = frame_texture(v_texcoord);    // 注意：需要用 frame_texture 读取纹理颜色（即 items 的渲染结果）
            f_color.rgb = 1.0 - f_color.rgb;        // 反色

            #[JA_FINISH_UP]
        }

    其中 ``#[JA_FINISH_UP]`` 是一个占位符，JAnim 会在这里做一些额外的操作，前面的 ``#[JA_FINISH_UP_UNIFORMS]`` 与之对应

    上述代码最核心的是 ``main`` 中“进行处理”的部分，其余的代码作为固定的写法照抄即可

    如果懒得抄，可以用 :class:`SimpleFrameEffect`，这个类只要写“进行处理”这部分就好了，因为它把其余代码都封装了

    完整示例请参考 :ref:`基础样例 <basic_examples>` 中的对应代码
    """

    renderer_cls = FrameEffectRenderer

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
        # 对 < 5.0.0 的兼容
        fragment_shader = _apply_fixes_for_compatibility(fragment_shader)

        super().__init__(*items, root_only=root_only, **kwargs)
        self.fragment_shader = fragment_shader
        self.cache_key = cache_key

        # 魔改 JA_FINISH_UP_UNIFORMS，加入 _frameeffect_injection 片段
        # 这样就不需要用户另外写一个 injection name 了
        with ShaderInjection(
            JA_FINISH_UP_UNIFORMS=_frameeffect_injection + _injection_ja_finish_up_uniforms
        ):
            self.injections = shader_injections_ctx.get()

    def apply_uniforms(self, *, optional: bool = False, **kwargs) -> None:
        if optional:
            self._optional_uniforms.update(kwargs)
        else:
            self._uniforms.update(kwargs)

    def dynamic_uniforms(self) -> dict:
        return {}


simple_frameeffect_shader = """
#version 330 core

in vec2 v_texcoord;

out vec4 f_color;

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
