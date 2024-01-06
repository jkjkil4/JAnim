from typing import TypeVar, Generic, Callable, Self

from janim.items.relation import Relation
from janim.components.component import Component, ITEM_COMPONENTS_NAME

GCompT = TypeVar('GCompT', bound=Component)


class Item(Generic[GCompT], Relation['Item']):
    def broadcast_refresh_of_component(
        self,
        component: Component,
        func: Callable | str,
        *,
        recurse_up=False,
        recurse_down=False
    ) -> Self:
        def mark(obj):
            obj_components: list[Component] = getattr(obj, ITEM_COMPONENTS_NAME)
            obj_component = obj_components[component.bind_idx]
            obj_component.mark_refresh(func)

        if recurse_up:
            for obj in self.walk_ancestors(component.bind.cls):
                mark(obj)

        if recurse_down:
            for obj in self.walk_descendants(component.bind.cls):
                mark(obj)


GRelT = TypeVar('GRelT', bound=Relation)


class Group(Relation[GRelT]):
    def __init__(self, *objs: GRelT, **kwargs):
        super().__init__(**kwargs)
        self.add(*objs)
