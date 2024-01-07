from __future__ import annotations

import functools
from typing import Callable, Self

from janim.items.relation import Relation
from janim.components.component import Component, FUNC_FOR_MANY_KEY


class Item[
    GCmptT_Get: Component, GCmptT_Apply: Component
](Relation['Item']):
    class _Get:
        def __init__(self, item: Item):
            self.item = item

        def __getattr__(self, method_name: str):
            matched: Callable = None

            # 从自身的组件中寻找能调用的方法
            for cmpt in self.item.components:
                if not cmpt.can_get or not hasattr(cmpt, method_name):
                    continue

                attr = getattr(cmpt, method_name)
                if not callable(attr):
                    continue

                matched = attr
                break

            if matched is None:
                # 从后代物件的组件中寻找能调用的方法
                for descendant in self.item.descendants():
                    for cmpt in descendant.components:
                        if not cmpt.can_get and hasattr(cmpt, method_name):
                            continue

                        attr: Callable = getattr(cmpt, method_name)
                        if not callable(attr) or not attr.__dict__.get(FUNC_FOR_MANY_KEY, False):
                            continue

                        matched = attr
                        break

                    if matched is not None:
                        break

            if matched is None:
                raise KeyError(f'没找到可调用的方法 `{method_name}`')

            if matched.__dict__.get(FUNC_FOR_MANY_KEY, False):
                return functools.partial(matched, _as=self.item)
            return matched

    class _Apply:
        def __init__(self, item: Item):
            self.item = item

        def __getattr__(self, method_name: str):
            type CmptId = tuple[type, int]
            matched: dict[CmptId, Callable] = {}

            items = [self.item, *self.item.descendants()]

            # 寻找可调用的方法
            for item in items:
                for cmpt in item.components:
                    if not cmpt.can_apply:
                        continue

                    cmpt_id: CmptId = (cmpt.bind.cls, cmpt.bind_idx)
                    if cmpt_id in matched:
                        continue
                    if not hasattr(cmpt, method_name):
                        continue

                    attr = getattr(cmpt, method_name)
                    if not callable(attr):
                        continue
                    if item is not self.item and FUNC_FOR_MANY_KEY not in attr.__dict__:
                        continue

                    matched[cmpt_id] = attr

            if not matched:
                raise KeyError(f'没找到可调用的方法 `{method_name}`')

            def wrapper(*args, **kwargs):
                for method in matched.values():
                    if method.__dict__.get(FUNC_FOR_MANY_KEY, False):
                        method(*args, _as=self.item, **kwargs)
                    else:
                        method(*args, **kwargs)

                return self

            return wrapper

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.components: list[Component] = []

    def broadcast_refresh_of_component(
        self,
        component: Component,
        func: Callable | str,
        *,
        recurse_up=False,
        recurse_down=False
    ) -> Self:
        '''
        为 :meth:`janim.components.component.Component.mark_refresh()`
        进行 ``recurse_up/down`` 的处理
        '''
        def mark(item: Item):
            item_component = item.components[component.bind_idx]
            item_component.mark_refresh(func)

        if recurse_up:
            for item in self.walk_ancestors(component.bind.cls):
                mark(item)

        if recurse_down:
            for item in self.walk_descendants(component.bind.cls):
                mark(item)

    @property
    def get(self) -> GCmptT_Get:
        return Item._Get(self)

    @property
    def apply(self) -> GCmptT_Apply:
        return Item._Apply(self)


class Group[GT, AT](Item[GT, AT]):
    def __init__(self, *objs: Item[GT, AT], **kwargs):
        super().__init__(**kwargs)
        self.add(*objs)
