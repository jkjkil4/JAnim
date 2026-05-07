from __future__ import annotations

import itertools as it
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable

import numpy as np
import OpenGL.GL as gl

from janim.items.item import Item
from janim.render.base import Renderer
from janim.utils.space_ops import normalize

if TYPE_CHECKING:
    from janim.anims.timeline import ItemWithRenderFunc, RenderGroupReturn, Timeline


@dataclass
class RenderCollection:
    """
    用于辅助将渲染代理给特殊物件，比如 :class:`~.FrameEffect` 等
    """

    timeline: Timeline
    apprs: list[tuple[Timeline.ItemAppearance, Item]]
    extras: list[tuple[Timeline.ExtraRenderGroup, RenderGroupReturn]]

    def __post_init__(self):
        self._apprs_is_delegated: list[bool] | None = None
        self._extras_is_delegated: list[bool] | None = None

    def iter_items(self):
        for _, item in self.apprs:
            yield item
        for _, items_render in self.extras:
            for item, _ in items_render:
                yield item

    def delegates(self, items: Iterable[Item]) -> RenderCollection:
        """
        调用该方法来代理与 ``items`` 相关联的渲染

        会返回一个 :class:`RenderCollection` 实例，应通过在后续调用其 :meth:`render` 方法来渲染代理出去的物件
        """
        timeline_apprs = self.timeline.item_appearances

        items_set = set(items)
        apprs_set = set(timeline_apprs[item] for item in items_set)

        if self._apprs_is_delegated is None:
            self._apprs_is_delegated = [False] * len(self.apprs)
        if self._extras_is_delegated is None:
            self._extras_is_delegated = [False] * len(self.extras)

        delegated_apprs = []
        delegated_extras = []

        for i, appr in enumerate(self.apprs):
            if appr[0] in apprs_set:
                self._apprs_is_delegated[i] = True
                delegated_apprs.append(appr)

        for i, extra in enumerate(self.extras):
            related_items = extra[0].related_items
            if not related_items:
                continue

            if all(item in items_set for item in related_items):
                self._extras_is_delegated[i] = True
                delegated_extras.append(extra)

        return self.__class__(self.timeline, delegated_apprs, delegated_extras)

    def render(self, blending: bool) -> None:
        # 得到所有将要渲染的目标
        if self._apprs_is_delegated is None:
            appr_renders = [(item, appr.render) for appr, item in self.apprs]
        else:
            appr_renders = [
                (item, appr.render)
                for (appr, item), is_delegated in zip(
                    self.apprs, self._apprs_is_delegated, strict=True
                )
                if not is_delegated
            ]

        if self._extras_is_delegated is None:
            extra_renders_list = [renders for _, renders in self.extras]
        else:
            extra_renders_list = [
                renders
                for (_, renders), is_delegated in zip(
                    self.extras, self._extras_is_delegated, strict=True
                )
                if not is_delegated
            ]

        renders = it.chain(appr_renders, *extra_renders_list)

        # 用于按照预期的顺序排序的 key 回调
        render_data = Renderer.data_ctx.get()
        info = render_data.camera_info

        camera_vec = normalize(-info.camera_axis)
        camera_loc = info.camera_location

        def key(x: ItemWithRenderFunc):
            ref = x[0].distance_sort_reference_point
            if ref is None:
                distance = np.inf
            else:
                distance = np.dot(camera_vec, ref - camera_loc)
            return (distance, x[0].depth)

        # 排序后进行渲染
        self._render(sorted(renders, key=key, reverse=True), blending)

    @classmethod
    def _render(cls, renders: Iterable[ItemWithRenderFunc], blending: bool) -> None:
        for data, render in renders:
            render(data)
            # 如果没有 blending，我们认为当前是在向透明 framebuffer 绘制
            # 所以每次都需要使用 glFlush 更新 framebuffer 信息使得正确渲染
            if not blending:
                gl.glFlush()
