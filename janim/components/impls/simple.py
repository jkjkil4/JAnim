from __future__ import annotations

import sys
from typing import Iterable, Iterator, Self

from janim.components.core.attrs import ComponentAttrs
from janim.components.core.component import Component
from janim.utils.bezier import interpolate


class Cmpt_Float[ItemT](Component[ItemT]):
    """
    对 ``float`` 的 :class:`~.Component` 封装
    """

    _attrs = ComponentAttrs()
    _inner = _attrs.float()

    def __cmpt_init__(self, default_value):
        self._inner = default_value

    def interpolate(
        self, cmpt1: Cmpt_Float, cmpt2: Cmpt_Float, alpha: float, *, path_func=None
    ) -> None:
        if cmpt1._inner != cmpt2._inner or cmpt1._inner != self._inner:
            self._inner = interpolate(cmpt1._inner, cmpt2._inner, alpha)

    def set(self, value: float) -> Self:
        self._inner = value
        return self

    def get(self) -> float:
        return self._inner


class Cmpt_Alpha[ItemT](Cmpt_Float[ItemT]):
    """
    和 :class:`~.Cmpt_Float` 一样，只是方便 ``isinstance``
    """


class Cmpt_List[ItemT, T](Component[ItemT]):
    """
    对 ``list`` 的 :class:`~.Component` 封装
    """

    _attrs = ComponentAttrs()
    _inner = _attrs.direct_object(list, nullable=False, copyer=list.copy)

    def __cmpt_init__(self) -> None:
        self._inner = []

    def __len__(self) -> int:
        return len(self._inner)

    def __iter__(self) -> Iterator[T]:
        return iter(self._inner)

    def __getitem__(self, index):
        return self._inner[index]

    def __setitem__(self, index, value) -> None:
        self._inner[index] = value

    def __delitem__(self, index) -> None:
        del self._inner[index]

    def __contains__(self, value: object) -> bool:
        return value in self._inner

    def __bool__(self) -> bool:
        return bool(self._inner)

    def __repr__(self) -> str:
        return repr(self._inner)

    def __eq__(self, other) -> bool:
        return self._inner == other

    def append(self, value: T) -> None:
        self._inner.append(value)

    def extend(self, values: Iterable[T]) -> None:
        self._inner.extend(values)

    def insert(self, index: int, value: T) -> None:
        self._inner.insert(index, value)

    def remove(self, value: T) -> None:
        self._inner.remove(value)

    def pop(self, index: int = -1):
        return self._inner.pop(index)

    def clear(self) -> None:
        self._inner.clear()

    def index(self, value: T, start: int = 0, stop: int = sys.maxsize) -> int:
        return self._inner.index(value, start, stop)

    def count(self, value: T) -> int:
        return self._inner.count(value)


class Cmpt_Dict[ItemT, K, V](Component[ItemT]):
    """
    对 ``dict`` 的 :class:`~.Component` 封装
    """

    _attrs = ComponentAttrs()
    _inner = _attrs.direct_object(dict, nullable=False, copyer=dict.copy)

    def __cmpt_init__(self) -> None:
        self._inner = {}

    def __len__(self) -> int:
        return len(self._inner)

    def __iter__(self) -> Iterator[K]:
        return iter(self._inner)

    def __getitem__(self, key: K) -> V:
        return self._inner[key]

    def __setitem__(self, key: K, value: V) -> None:
        self._inner[key] = value

    def __delitem__(self, key: K) -> None:
        del self._inner[key]

    def __contains__(self, key: object) -> bool:
        return key in self._inner

    def __bool__(self) -> bool:
        return bool(self._inner)

    def __repr__(self) -> str:
        return repr(self._inner)

    def __eq__(self, other) -> bool:
        return self._inner == other

    def get(self, key: K, default=None):
        return self._inner.get(key, default)

    def keys(self):
        return self._inner.keys()

    def values(self):
        return self._inner.values()

    def items(self):
        return self._inner.items()

    def update(self, *args, **kwargs) -> None:
        self._inner.update(*args, **kwargs)

    def clear(self) -> None:
        self._inner.clear()

    def pop(self, key: K, default=...):
        if default is ...:
            return self._inner.pop(key)
        return self._inner.pop(key, default)
