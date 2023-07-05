from __future__ import annotations
from janim.items.item import Item

class Group(Item):
    def __init__(self, *items: Item) -> None:
        super().__init__()
        self.add(*items)

class MethodGroup:
    def __init__(self, *items: Item | MethodGroup) -> None:
        self.items = items
    
    def __getattr__(self, method_name: str):
        def wrap(*method_args, **method_kwargs) -> MethodGroup:
            for item in self.items:
                if isinstance(item, MethodGroup):
                    method = getattr(item, method_name)
                    method(*method_args, **method_kwargs)
                elif hasattr(item, method_name):
                    method = getattr(item, method_name)
                    if callable(method):
                        method(*method_args, **method_kwargs)
            return self
        return wrap

    def __getitem__(self, value):
        if isinstance(value, slice):
            return MethodGroup(*self.items[value])
        return self.items[value]

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)
