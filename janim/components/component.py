from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Callable, Self, TYPE_CHECKING, overload

import janim.utils.refresh as refresh

if TYPE_CHECKING:   # pragma: no cover
    from janim.items.item import Item


class _CmptMeta(type):
    def __new__(cls: type, name: str, bases: tuple[type, ...], attrdict: dict):
        for key in ('copy', '__eq__'):
            if not callable(attrdict.get(key, None)):
                raise AttributeError(f'Component 的每一个子类都必须继承并实现 `{key}` 方法，而 {name} 没有')
        return super().__new__(cls, name, bases, attrdict)


class Component(refresh.Refreshable, metaclass=_CmptMeta):
    @dataclass
    class BindInfo:
        '''
        对组件定义信息的封装

        - ``decl_cls``: 以 ``xxx = CmptInfo(...)`` 的形式被声明在哪个类中；
          如果一个类及其父类都有 ``xxx = CmptInfo(...)`` ，那么 ``decl_cls`` 是父类
        - ``at_item``: 这个组件对象是属于哪个物件对象的
        - ``key``: 这个组件对象的变量名

        例：

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

    def copy(self) -> Self:
        cmpt_copy = copy.copy(self)
        cmpt_copy.bind = None
        cmpt_copy.reset_refresh()
        return cmpt_copy

    def __eq__(self, other) -> bool: ...

    def mark_refresh(self, func: Callable | str, *, recurse_up=False, recurse_down=False) -> Self:
        '''
        详见： :meth:`~.Item.broadcast_refresh_of_component`
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

    例：

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
    @overload
    def __get__(self, obj: None, owner) -> Self: ...

    @overload
    def __get__(self, obj: object, owner) -> T: ...

    def __get__(self, obj, owner):
        return self


class _CmptGroup(Component):
    def __init__(self, cmpt_info_list: list[CmptInfo], **kwargs):
        super().__init__(**kwargs)
        self.cmpt_info_list = cmpt_info_list

    def init_bind(self, bind: Component.BindInfo) -> None:
        super().init_bind(bind)
        self._find_objects()

    def copy(self, *, new_cmpts: dict[str, Component]):
        cmpt_copy = super().copy()
        for key in cmpt_copy.objects.keys():
            cmpt_copy.objects[key] = new_cmpts[key]

        return cmpt_copy

    def __eq__(self, other: _CmptGroup) -> bool:
        for key in self.objects.keys():
            if self.objects[key] != other.objects[key]:
                return False

        return True

    def _find_objects(self) -> None:
        self.objects: dict[str, Component] = {}

        for cmpt_info in self.cmpt_info_list:
            key = self._find_key(cmpt_info)
            self.objects[key] = getattr(self.bind.at_item, key)

    def _find_key(self, cmpt_info: CmptInfo) -> str:
        from janim.items.item import CLS_CMPTINFO_NAME

        for key, val in self.bind.decl_cls.__dict__.get(CLS_CMPTINFO_NAME, {}).items():
            if val is cmpt_info:
                return key

        raise ValueError('CmptGroup 必须要与传入的内容在同一个类的定义中')

    def __getattr__(self, name: str):
        objects = []
        methods = []

        for obj in self.objects.values():
            if not hasattr(obj, name):
                continue

            attr = getattr(obj, name)
            if not callable(attr):
                continue

            objects.append(obj)
            methods.append(attr)

        if not methods:
            cmpt_str = ', '.join(cmpt.__class__.__name__ for cmpt in self.objects)
            raise AttributeError(f'({cmpt_str}) 中没有组件有叫作 {name} 的方法')

        def wrapper(*args, **kwargs):
            ret = [
                method(*args, **kwargs)
                for method in methods
            ]

            return self if ret == objects else ret

        return wrapper


def CmptGroup[T](*cmpt_info_list: CmptInfo[T]) -> CmptInfo[T]:
    '''
    用于将多个组件打包，使得可以同时调用

    例：

    .. code-block:: python

        class MyItem(Item):
            stroke = CmptInfo(Cmpt_Rgbas)
            fill = CmptInfo(Cmpt_Rgbas)
            color = CmptGroup(stroke, fill)

        item = MyItem()
        item.stroke.set(...)    # 只有 stroke 的被调用 | Only the method of stroke be called
        item.color.set(...)     # stroke 和 fill 的都被调用了 | the methods of stroke and fill are both called
    '''
    return CmptInfo(_CmptGroup, cmpt_info_list)
