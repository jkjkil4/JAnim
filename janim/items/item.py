from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Self, overload

from janim.anims.timeline import Timeline
from janim.components.component import CmptInfo, Component, _CmptGroup
from janim.items.relation import Relation
from janim.typing import SupportsInterpolate
from janim.utils.data import AlignedData
from janim.utils.iterables import resize_preserving_order

CLS_CMPTINFO_NAME = '__cls_cmptinfo'
OBJ_CMPTS_NAME = '__obj_cmpts'


class _ItemMeta(type):
    '''
    作为 metaclass 记录定义在类中的所有 CmptInfo
    '''
    def __new__(cls: type, name: str, bases: tuple[type, ...], attrdict: dict):
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

        timeline = Timeline.get_context(raise_exc=False)
        if timeline:
            timeline.register(self)

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

        datas: dict[CmptKey, CmptInitData] = {}

        for cls in reversed(self.__class__.mro()):
            for key, info in cls.__dict__.get(CLS_CMPTINFO_NAME, {}).items():
                info: CmptInfo
                if key in datas:
                    data = datas[key]

                    # TODO: remove
                    # 好像没有必要检查是否是派生类
                    # if not issubclass(info.cls, data.info.cls):
                    #     raise TypeError(
                    #         f'组件定义错误：{cls.__name__} 的组件 {key}({info.cls.__name__}) '
                    #         f'与父类的组件冲突 ({info.cls.__name__} 不是以 {data.info.cls.__name__} 为基类)'
                    #     )

                    data.info = info

                else:  # key not in datas
                    datas[key] = CmptInitData(info, cls)

        self.components: dict[str, Component] = {}

        for key, data in datas.items():
            obj = data.info.create()
            obj.init_bind(Component.BindInfo(data.decl_cls, self, key))

            self.__dict__[key] = self.components[key] = obj

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
        '''
        使用 ``func`` 对物件进行操作，并返回 ``self`` 以方便链式调用
        '''
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

        例：

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

    # region data

    @dataclass
    class Data[T: 'Item']:
        item: T

        components: dict[str, Component]
        parents: list[Item]
        children: list[Item]

        @staticmethod
        def store[U: 'Item'](item: U) -> Item.Data[U]:
            '''
            将物件的数据复制，并返回复制后的数据

            注：仅复制自身数据，不复制子物件的数据
            '''
            components: dict[str, Component] = {}

            for key, cmpt in item.components.items():
                if isinstance(cmpt, _CmptGroup):
                    # 因为现在的 Python 版本中，dict 取键值保留原序
                    # 所以 new_cmpts 肯定有 _CmptGroup 所需要的
                    components[key] = cmpt.copy(new_cmpts=components)
                else:
                    components[key] = cmpt.copy()

            parents = item.parents[:]
            children = item.children[:]

            return Item.Data(item, components, parents, children)

        @staticmethod
        def ref[U: 'Item'](item: U) -> Item.Data[U]:
            '''
            返回数据的引用，不进行复制
            '''
            return Item.Data(
                item,
                item.components,
                item.parents,
                item.children
            )

        def is_changed(self) -> bool:
            '''
            检查该数据与 ``item`` 现在的数据是否产生差异

            注：仅检查自身数据，不检查子物件的数据
            '''
            for stored_cmpt, item_cmpt in zip(self.components.values(), self.item.components.values()):
                if stored_cmpt != item_cmpt:
                    return True

            return self.parents != self.item.parents or self.children != self.item.children

        class _CmptGetter:
            def __init__(self, data: Item.Data):
                self.data = data

            def __getattr__(self, name: str):
                cmpt = self.data.components.get(name, None)
                if cmpt is None:
                    raise AttributeError(f"'{self.data.item.__class__.__name__}' 没有叫作 '{name}' 的组件")

                return cmpt

        @property
        def cmpt(self) -> T:
            '''
            将 ``.component['key']`` 简化为 ``.cmpt.key`` 且方便代码提示
            '''
            return Item.Data._CmptGetter(self)

        @staticmethod
        def align_for_interpolate(
            data1: Item.Data,
            data2: Item.Data
        ) -> AlignedData[Item.Data]:
            aligned = AlignedData(*[
                Item.Data(None, {}, [], [])
                for _ in range(3)
            ])

            # align components
            for key, cmpt1 in data1.components.items():
                cmpt2 = data2.components.get(key, None)

                if cmpt2 is None or not isinstance(cmpt1, SupportsInterpolate):
                    aligned.data1.components[key] = cmpt1
                    aligned.data2.components[key] = cmpt1
                    aligned.union.components[key] = cmpt1
                    continue

                cmpt_aligned = cmpt1.align_for_interpolate(cmpt1, cmpt2)
                aligned.data1.components[key] = cmpt_aligned.data1
                aligned.data2.components[key] = cmpt_aligned.data2
                aligned.union.components[key] = cmpt_aligned.union

            # align children
            max_len = max(len(data1.children), len(data2.children))
            aligned.data1.children = resize_preserving_order(data1.children, max_len)
            aligned.data2.children = resize_preserving_order(data2.children, max_len)

            return aligned

        def interpolate(self, data1: Item.Data, data2: Item.Data, alpha: float) -> None:
            for key, cmpt in self.components.items():
                cmpt1 = data1.components[key]
                cmpt2 = data2.components[key]

                assert isinstance(cmpt, SupportsInterpolate)

                cmpt.interpolate(cmpt1, cmpt2, alpha)

    def store_data(self):
        '''
        复制物件的数据并返回
        '''
        return Item.Data.store(self)

    # endregion

    # region timeline

    def show(self, **kwargs) -> None:
        '''
        显示物件
        '''
        Timeline.get_context().show(self, **kwargs)

    def hide(self, **kwargs) -> None:
        '''
        隐藏物件
        '''
        Timeline.get_context().hide(self, **kwargs)

    # endregion


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
