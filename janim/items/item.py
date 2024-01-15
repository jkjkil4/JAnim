from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Callable, Self, overload

from janim.items.relation import Relation
from janim.components.component import Component, CmptInfo
from janim.anims.timeline import Timeline

CLS_CMPTINFO_NAME = '__cls_cmptinfo'


class _ItemMeta(type):
    '''
    作为 metaclass 记录定义在类中的所有 CmptInfo
    '''
    def __new__(cls, name: str, bases: tuple[type, ...], attrdict: dict):
        # 记录所有定义在类中的 CmptInfo
        cls_components: dict[str, Component] = {
            key: val
            for key, val in attrdict.items()
            if isinstance(val, CmptInfo)
        }

        attrdict[CLS_CMPTINFO_NAME] = cls_components

        return super().__new__(cls, name, bases, attrdict)


class Item(Relation['Item'], metaclass=_ItemMeta):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._init_components()

        self._astype_mock_cmpt: dict[tuple[type, str], Component] = {}

    def _init_components(self) -> None:
        '''
        创建出 CmptInfo 对应的 Component，
        并以同名存于对象中，起到在名称上覆盖类中的 CmptInfo 的效果

        因为 CmptInfo 的 __get__ 标注的返回类型是对应的 Component，
        所以以上做法没有影响基于类型标注的代码补全
        '''
        type CmptKey = str

        @dataclass
        class CmptInitData:
            info: CmptInfo[CmptInfo]
            decl_cls: type[Item]

        components: dict[CmptKey, CmptInitData] = {}

        for cls in reversed(self.__class__.mro()):
            for key, info in cls.__dict__.get(CLS_CMPTINFO_NAME, {}).items():
                info: CmptInfo
                if key in components:
                    data = components[key]

                    # TODO: remove
                    # 好像没有必要检查是否是派生类
                    # if not issubclass(info.cls, data.info.cls):
                    #     raise TypeError(
                    #         f'组件定义错误：{cls.__name__} 的组件 {key}({info.cls.__name__}) '
                    #         f'与父类的组件冲突 ({info.cls.__name__} 不是以 {data.info.cls.__name__} 为基类)'
                    #     )

                    data.info = info

                else:
                    components[key] = CmptInitData(info, cls)

        for key, data in components.items():
            obj = data.info.create()
            obj.init_bind(Component.BindInfo(data.decl_cls, self, key))
            self.__dict__[key] = obj

    def broadcast_refresh_of_component(
        self,
        cmpt: Component,
        func: Callable | str,
        *,
        recurse_up=False,
        recurse_down=False
    ) -> Self:
        '''
        为 :meth:`~.Component.mark_refresh()`
        进行 ``recurse_up/down`` 的处理
        '''
        if not recurse_up and not recurse_down:
            return

        mock_key = (cmpt.bind.decl_cls, cmpt.bind.key)

        def mark(items: Item):
            for item in items:
                if isinstance(item, cmpt.bind.decl_cls):
                    # 一般情况
                    item_cmpt: Component = getattr(item, cmpt.bind.key)
                    item_cmpt.mark_refresh(func)

                else:
                    # astype 情况
                    mock_cmpt = item._astype_mock_cmpt.get(mock_key, None)
                    if mock_cmpt is not None:
                        mock_cmpt.mark_refresh(func)

        if recurse_up:
            mark(self.ancestors())

        if recurse_down:
            mark(self.descendants())

    def do(self, func: Callable[[Self]]) -> Self:
        func(self)
        return self

    @overload
    def __getitem__(self, value: int) -> Item: ...

    @overload
    def __getitem__(self, value: slice) -> Group: ...

    def __getitem__(self, value):
        if isinstance(value, slice):
            return Group(*self.children[value])
        return self.children[value]

    # Do not define __iter__ and __len__ for Item class.
    # I think using item.children and item.parents explicitly is better.

    # region astype

    def astype[T](self, cls: type[T]) -> T:
        '''
        使得可以调用当前物件中没有的组件

        例 | Example:

        .. code-block:: python

            group = Group(
                Points(UP, RIGHT)
                Points(LEFT)
            )

        在这个例子中，并不能 ``group.points.get_all()`` 来获取子物件中的所有点，
        但是可以使用 ``group.astype(Points).points.get_all()`` 来做到
        '''
        if not issubclass(cls, Item):
            # TODO: i18n
            raise TypeError(f'{cls.__name__} 不是以 Item 为基类，无法作为 astype 的参数')

        return self._As(self, cls)

    class _As:
        def __init__(self, origin: Item, cls: type[Item]):
            self.origin = origin
            self.cls = cls

        def __getattr__(self, name: str):
            try:
                cmpt_info = getattr(self.cls, name)
                if not isinstance(cmpt_info, CmptInfo):
                    raise AttributeError()

            except AttributeError:
                # TODO i18n
                raise AttributeError(f"'{self.cls.__name__}' 没有叫作 '{name}' 的组件")

            # 找到 cmpt_info 是在哪个类中被定义的
            decl_cls: type[Item] | None = None
            for sup in self.cls.mro():
                if name in sup.__dict__.get(CLS_CMPTINFO_NAME, {}):
                    decl_cls = sup

            assert decl_cls is not None

            # 如果 self.origin 本身就是 decl_cls 的实例
            # 那么它自身肯定有名称为 name 的组件，对于这种情况实际上完全没必要 astype
            # 为了灵活性，这里将这个已有的组件返回
            if isinstance(self.origin, decl_cls):
                return getattr(self.origin, name)

            mock_key = (decl_cls, name)
            cmpt = self.origin._astype_mock_cmpt.get(mock_key, None)

            # 如果 astype 需求的组件已经被创建过，那么直接返回
            if cmpt is not None:
                return cmpt

            # astype 需求的组件还没创建，那么创建并记录
            cmpt = cmpt_info.create()
            cmpt.init_bind(Component.BindInfo(decl_cls, self.origin, name))

            self.origin._astype_mock_cmpt[(decl_cls, name)] = cmpt
            return cmpt

    # endregion

    @staticmethod
    def _get_timeline_context() -> Timeline:
        obj = Timeline.ctx_var.get(None)
        if obj is None:
            name = inspect.currentframe().f_back.f_code.co_name
            raise LookupError(f'Item.{name} 无法在 Timeline.build 之外使用')
        return obj

    def show(self, **kwargs) -> None:
        timeline = self._get_timeline_context()
        timeline.show(self, **kwargs)


class Group[T](Item):
    '''
    将物件组成一组
    '''
    def __init__(self, *objs: T, **kwargs):
        super().__init__(**kwargs)
        self.add(*objs)

    @overload
    def __getitem__(self, value: int) -> T: ...

    @overload
    def __getitem__(self, value: slice) -> Group[T]: ...

    def __getitem__(self, value):   # pragma: no cover
        return super().__getitem__(value)
