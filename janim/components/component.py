from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Self, TYPE_CHECKING

import janim.utils.refresh as refresh

if TYPE_CHECKING:   # pragma: no cover
    from janim.items.item import Item


class Component(refresh.Refreshable):
    @dataclass
    class BindInfo:
        '''
        对组件定义信息的封装

        - ``decl_cls``: 以 ``xxx = CmptInfo(...)`` 的形式被声明在哪个类中；
          如果一个类及其父类都有 ``xxx = CmptInfo(...)`` ，那么 ``decl_cls`` 是父类
        - ``at_item``: 这个组件对象是属于哪个物件对象的
        - ``key``: 这个组件对象的变量名

        例如 | Example：

        .. code-block:: python

            class MyCmpt(Component): ...

            class MyItem(Item):
                cmpt1 = CmptInfo(MyCmpt)
                cmpt2 = CmptInfo(MyCmpt)

            class MyItem2(MyItem):
                cmpt3 = CmptInfo(MyCmpt)

            item = MyItem()

            # item.cmpt1.bind_info 与 BindInfo(MyItem, item, 'cmpt1') 一致
            # item.cmpt2.bind_info 与 BindInfo(MyItem, item, 'cmpt2') 一致

            item2 = MyItem2()

            # item2.cmpt1.bind_info 与 BindInfo(MyItem, item2, 'cmpt1') 一致
            # item2.cmpt3.bind_info 与 BindInfo(MyItem2, item2, 'cmpt3') 一致
        '''
        decl_cls: type
        at_item: Item
        key: str

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.bind: Component.BindInfo | None = None

    def init_bind(self, bind: BindInfo):
        '''
        用于 ``Item._init_components``

        子类可以继承该函数，进行与所在物件相关的处理
        '''
        self.bind = bind

    def mark_refresh(self, func: Callable | str, *, recurse_up=False, recurse_down=False) -> Self:
        '''
        详见 | See: :meth:`~.Item.broadcast_refresh_of_component`
        '''
        super().mark_refresh(func)

        if self.bind is not None:
            self.bind.at_item.broadcast_refresh_of_component(
                self,
                func,
                recurse_up=recurse_up,
                recurse_down=recurse_down
            )

    def get_same_cmpt(self, item: Item) -> Self:
        if isinstance(item, self.bind.decl_cls):
            return getattr(item, self.bind.key)

        return getattr(item.astype(self.bind.decl_cls), self.bind.key)


class CmptInfo[T]:
    '''
    在类中定义组件需要使用该类

    例 | Example:

    .. code-block:: python

        class MyItem(Item):
            # Wrong!
            # cmpt1 = MyCmpt()

            # Right
            cmpt1 = CmptInfo(MyCmpt)

            # Wrong!
            # cmpt2 = MyCmptWithArgs(1)

            # Right
            cmpt2 = CmptInfo(MyCmptWithArgs, 1)
    '''
    def __init__(self, cls: type[T], *args, **kwargs):
        self.__doc__ = ""
        self.cls = cls
        self.args = args
        self.kwargs = kwargs

    def create(self) -> Component:
        return self.cls(*self.args, **self.kwargs)

    # 方便代码补全，没有实际意义
    def __get__(self, obj, owner) -> T:
        return self


def CmptGroup[T](*cmpt_info_list: CmptInfo[T]) -> CmptInfo[T]:
    '''
    用于将多个组件打包，使得可以同时调用

    例 | Example:

    .. code-block:: python

        class MyItem(Item):
            stroke = CmptInfo(Cmpt_Rgbas)
            fill = CmptInfo(Cmpt_Rgbas)
            color = CmptGroup(stroke, fill)

        item = MyItem()
        item.stroke.set(...)    # 只有 stroke 的被调用 | Only the method of stroke be called
        item.color.set(...)     # stroke 和 fill 的都被调用了 | the methods of stroke and fill are both called
    '''
    class _CmptGroup(Component):
        def init_bind(self, bind_info: Component.BindInfo) -> None:
            super().init_bind(bind_info)
            self._find_objects()

        def _find_objects(self) -> None:
            self.objects: list[Component] = [
                getattr(
                    self.bind.at_item,
                    self._find_key(cmpt_info)
                )
                for cmpt_info in cmpt_info_list
            ]

        def _find_key(self, cmpt_info: CmptInfo) -> str:
            from janim.items.item import CLS_CMPTINFO_NAME

            for key, val in self.bind.decl_cls.__dict__.get(CLS_CMPTINFO_NAME, {}).items():
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

            if not methods:
                cmpt_str = ', '.join(cmpt.__class__.__name__ for cmpt in self.objects)
                raise AttributeError(f'({cmpt_str}) 中没有组件有叫作 {name} 的方法')

            def wrapper(*args, **kwargs):
                ret = [
                    method(*args, **kwargs)
                    for method in methods
                ]

                return self if ret == self.objects else ret

            return wrapper

    return CmptInfo(_CmptGroup)
