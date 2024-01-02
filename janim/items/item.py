from typing import TypeVar

from janim.items.relation import Relation


class Item(Relation['Item']):
    pass


T = TypeVar('T', bound=Relation)


class Group(Relation[T]):
    def __init__(self, *objs: T, **kwargs):
        super().__init__(**kwargs)
        self.add(*objs)
