from __future__ import annotations

from typing import Callable, TYPE_CHECKING

import janim.utils.refresh as refresh
from janim.typing import Self

FUNC_AS_ABLE_NAME = '__as_able'

if TYPE_CHECKING:
    from janim.items.item import Item


class Component(refresh.Refreshable):
    class BindInfo:
        def __init__(self, def_cls: type, at_item: Item, key: str):
            self.decl_cls = def_cls
            self.at_item = at_item
            self.key = key

    def as_able[**P, R](func: Callable[P, R]) -> Callable[P, R]:
        # TODO: for_many 的注释
        func.__dict__[FUNC_AS_ABLE_NAME] = True
        return func

    @staticmethod
    def is_as_able(func: Callable) -> bool:
        return func.__dict__.get(FUNC_AS_ABLE_NAME, False)

    @staticmethod
    def extract_as(obj: Component | Item._As._TakedCmpt) -> tuple[Item, type, str]:
        if isinstance(obj, Component):
            return (
                obj.bind_info.at_item,
                obj.bind_info.decl_cls,
                obj.bind_info.key
            )
        else:
            from janim.items.item import CLS_CMPTINFO_NAME

            as_type = None
            for sup in obj.item_as.cls.mro():
                if obj.cmpt_name in sup.__dict__.get(CLS_CMPTINFO_NAME, {}):
                    as_type = sup

            assert as_type is not None

            return (
                obj.item_as.origin,
                as_type,
                obj.cmpt_name
            )

    def __init__(
        self,
        *args,
        bind_info: BindInfo | None = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.bind_info = bind_info

    def set_bind_info(self, bind_info: BindInfo):
        self.bind_info = bind_info

    def mark_refresh(self, func: Callable | str, *, recurse_up=False, recurse_down=False) -> Self:
        super().mark_refresh(func)

        if self.bind_info is not None:
            self.bind_info.at_item.broadcast_refresh_of_component(
                self,
                func,
                recurse_up=recurse_up,
                recurse_down=recurse_down
            )


class CmptInfo[T]:
    def __init__(self, cls: type[T], *args, **kwargs):
        self.cls = cls
        self.args = args
        self.kwargs = kwargs

    # 方便代码补全，没有实际意义
    def __get__(self, obj, owner) -> T:
        return self


def CmptGroup[T](*cmpt_info_list: CmptInfo[T]) -> CmptInfo[T]:
    class _CmptGroup(Component):
        def __init__(self, *, bind_info: Component.BindInfo | None = None):
            if bind_info is None:
                raise ValueError('CmptGroup 只能在类定义中使用')

            super().__init__(bind_info=bind_info)
            self._find_objects()

        def _find_objects(self) -> None:
            self.objects: list[Component] = [
                getattr(
                    self.bind_info.at_item,
                    self._find_key(cmpt_info)
                )
                for cmpt_info in cmpt_info_list
            ]

        def _find_key(self, cmpt_info: CmptInfo) -> str:
            from janim.items.item import CLS_CMPTINFO_NAME

            for key, val in self.bind_info.decl_cls.__dict__.get(CLS_CMPTINFO_NAME, {}).items():
                if val is cmpt_info:
                    return key

            raise ValueError('CmptGroup 必须要与传入的内容在同一个类的定义中')

        def __getattr__(self, name: str):
            methods = []

            for obj in self.objects:
                if not hasattr(obj, name):
                    continue

                attr = getattr(obj, name)
                if not callable(attr):
                    continue

                methods.append(attr)

            def wrapper(*args, **kwargs):
                ret = [
                    method(*args, **kwargs)
                    for method in methods
                ]

                return self if ret == self.objects else ret

            return wrapper

    return CmptInfo(_CmptGroup)
