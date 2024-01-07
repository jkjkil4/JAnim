from __future__ import annotations

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
            matched: tuple[Component, Callable] = None

            # 从自身的组件中寻找能调用的方法
            for cmpt in self.item.components:
                if cmpt.can_get and hasattr(cmpt, method_name):
                    attr = getattr(cmpt, method_name)
                    if callable(attr):
                        matched = (cmpt, attr)
                        break

            if matched is None:
                # 从后代物件的组件中寻找能调用的方法
                for descendant in self.item.descendants():
                    for cmpt in descendant.components:
                        if cmpt.can_get and hasattr(cmpt, method_name):
                            attr: Callable = getattr(cmpt, method_name)
                            if callable(attr) and attr.__dict__.get(FUNC_FOR_MANY_KEY, False):
                                matched = (cmpt, attr)
                                break

            if matched is None:
                raise KeyError(f'没找到可调用的方法 `{method_name}`')

            def wrapper(*args, **kwargs):
                cmpt, attr = matched

                if not attr.__dict__.get(FUNC_FOR_MANY_KEY, False):
                    return attr(*args, **kwargs)

                return attr(
                    *(
                        item.components[cmpt.bind_idx]
                        for item in self.item.walk_descendants(cmpt.bind.cls)
                    ),
                    **kwargs
                )

            return wrapper

    class _Apply:
        def __init__(self, item: Item):
            self.item = item

        def __getattr__(self, method_name: str):
            # TODO: ...
            pass

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

