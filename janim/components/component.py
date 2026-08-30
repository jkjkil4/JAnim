from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Iterable, Literal, Self, overload

from janim_backend import relation

from janim.anims.method_updater_meta import METHOD_UPDATER_KEY
from janim.exception import CmptGroupLookupError
from janim.items.relation import _items_relation_registry
from janim.locale import get_translator
from janim.utils.cmpt_lazy import (
    EXPIRED,
    FLAG_HANDLE_NAME,
    Expired,
    ObjConns,
)
from janim.utils.data import AlignedData

if TYPE_CHECKING:  # pragma: no cover
    from janim.items.item import Item

_ = get_translator('janim.components.component')


class CheckComponentMethods(type):
    """
    所有的 :class:`Component` 子类都会被检查是否实现了 ``copy``, ``_become`` 和 ``not_changed`` 方法

    含义：

    -   ``copy``:

        调用该函数后，产生一份组件的拷贝

        在该函数中，应使用 ``cmpt_copy = super().copy()`` 得到拷贝的组件对象，
        然后在这个对象的基础上，处理有关的拷贝操作，最后返回 ``cmpt_copy`` 对象

    -   ``_become``:

        会以另外一个（大概率是同类型的组件，该行为暂未稳定，有待明确）组件作为入参

        在该函数中，应先使用 ``super()._become(other)`` 处理父类的逻辑（如果有），
        然后再进行当前组件的处理逻辑，最终确保当前组件的数据变得和目标组件长得一样

    -   ``not_changed``:

        该函数需要返回一个 ``bool`` 值，表示是否能确定该组件的数据没有发生过变更，用于侦测组件修改

        例如 ``Cmpt_Points`` 的 ``_points`` 数据在未变动时内部 NumPy 数据的 ``id`` 保持不变，
        但是在发生修改后，就会成为完全不同 ``id`` 的 NumPy 数组

        所以 ``Cmpt_Points`` 内部的 NumPy 数组只要无法通过 ``is`` 判断相同，他的该函数就会返回 ``False``
        （哪怕变化后回到了相同值的数据，也仍返回 ``False``）

    另外，对于未附加额外数据，仅提供额外方法的组件，可以用 ``impl=True`` 跳过该子类的检查
    """

    def __new__(
        cls: type,
        name: str,
        bases: tuple[type, ...],
        attrdict: dict,
        *,
        impl=False,  # 若 impl=True，则会跳过下面的检查
    ):
        if 'become' in attrdict and name != 'Component':
            raise AttributeError(
                _('Perhaps you need to change the method name from `become` to `_become`')
            )

        if not impl:
            for key in ('copy', '_become', 'not_changed'):
                if not callable(attrdict.get(key, None)):
                    raise AttributeError(  # noqa: TRY004
                        _(
                            'Every subclass of Component must inherit and implement '
                            'the "{key}" method, but "{name}" does not'
                        ).format(key=key, name=name)
                    )

        return super().__new__(cls, name, bases, attrdict)


class Component[ItemT](metaclass=CheckComponentMethods):
    @dataclass(slots=True)
    class BindInfo:
        """
        对组件定义信息的封装

        :param decl_cls:
            以 ``xxx = CmptInfo(...)`` 的形式被声明在哪个类中；
            如果一个类及其父类都有 ``xxx = CmptInfo(...)`` ，那么 ``decl_cls`` 是父类

        :param at_item: 这个组件对象当前绑定到了哪个物件对象
        :param key: 这个组件对象在物件中的变量名

        例：

        .. code-block:: python

            class MyCmpt(Component): ...

            class MyItem(Item):
                cmpt1 = CmptInfo(MyCmpt[Self])
                cmpt2 = CmptInfo(MyCmpt[Self])

            class MyItem2(MyItem):
                cmpt3 = CmptInfo(MyCmpt[Self])

            item = MyItem()

            # item.cmpt1.bind_info 与 BindInfo(MyItem, item, 'cmpt1') 一致
            # item.cmpt2.bind_info 与 BindInfo(MyItem, item, 'cmpt2') 一致

            item2 = MyItem2()

            # item2.cmpt1.bind_info 与 BindInfo(MyItem, item2, 'cmpt1') 一致
            # item2.cmpt3.bind_info 与 BindInfo(MyItem2, item2, 'cmpt3') 一致
        """

        decl_cls: type[Item]
        at_item: Item
        key: str

        _flag_0: int = field(init=False)
        _computed_caches: dict[relation.FlagHandle, Any] = field(default_factory=dict)

        def __post_init__(self) -> None:
            self._flag_0 = _items_relation_registry.indexize_key(self.key)

        def get_computed_for(self, flag_handle: relation.FlagHandle) -> Any | Expired:
            has_flag = self.at_item._rel_handle.get_computed_for(self._flag_0, flag_handle)
            if not has_flag:
                return EXPIRED
            return self._computed_caches[flag_handle]

        def mark_computed_for(self, flag_handle: relation.FlagHandle, data: Any) -> None:
            self._computed_caches[flag_handle] = data
            self.at_item._rel_handle.mark_computed_for(self._flag_0, flag_handle)

        def reset_computed_for(self, flag_handle: relation.FlagHandle) -> None:
            self.at_item._rel_handle.reset_computed_for(self._flag_0, flag_handle)

        def reset_computed_for_func(self, func: Callable) -> None:
            self.reset_computed_for(getattr(func, FLAG_HANDLE_NAME))

        def reset_computed_for_list(self, lst: list[relation.FlagHandle]) -> None:
            self.at_item._rel_handle.reset_computed_for_list(self._flag_0, lst)

        def reset_computed_for_all(self) -> None:
            for flag_handle in self._computed_caches:
                self.at_item._rel_handle.reset_computed_for(self._flag_0, flag_handle)
            self._computed_caches.clear()

    def __init__(self) -> None:
        super().__init__()
        self.bind: Component.BindInfo | None = None
        self._signal_obj_conns: ObjConns | None = None

    def init_bind(self, bind: BindInfo) -> None:
        """
        用于 ``Item._init_components``

        子类可以继承该函数，进行与所在物件相关的处理
        """
        self.bind = bind

    def __copy__(self) -> Self:
        """
        手动实现 ``__copy__``，这样性能比 ``copy.copy`` 高

        特别是 Component 作为频繁使用的对象这很重要
        """
        cls = self.__class__
        new = cls.__new__(cls)

        new.__dict__ = self.__dict__.copy()

        return new

    def copy(self) -> Self:
        cmpt_copy = self.__copy__()
        cmpt_copy.bind = None
        cmpt_copy._signal_obj_conns = None
        return cmpt_copy

    def become(self, other) -> Self:
        bind = self.bind
        if bind is not None:
            bind.reset_computed_for_all()
        self._become(other)
        return self

    def _become(self, other) -> None: ...

    def not_changed(self, other) -> bool: ...

    # region 获取其它物件中的组件

    @overload
    def get_same_cmpt(
        self, item: Item, *, use_mock: bool = False, create_mock: Literal[False]
    ) -> Self | None: ...
    @overload
    def get_same_cmpt(
        self, item: Item, *, use_mock: bool = False, create_mock: Literal[True] = True
    ) -> Self: ...

    def get_same_cmpt(
        self, item: Item, *, use_mock: bool = False, create_mock: bool = True
    ) -> Self | None:
        """
        得到 ``item`` 物件中与自身同 ``self.bind.key`` 的组件，默认会创建 mock

        注：若 ``self.bind`` 无效会由于尝试访问 ``None`` 的成员而抛出属性错误，
        但是我们并没在函数中检查这一点；若有必要的话，预期的做法是在函数外检查

        :param item: 得到哪个物件中的组件
        :param use_mock: 在没有对应组件时，是否能使用先前创建过的 mock
        :param create_mock: 在没有对应组件时，是否基于 :meth:`~.Item.astype` 创建 mock
        :return: 得到的组件，若 ``create_mock=False``，则可能返回 ``None``
        """
        cmpt = item.components.get(self.bind.key, None)
        if cmpt is not None:
            return cmpt

        if use_mock and (cmpt := item._astype_mock_cmpt.get(self.bind.key)) is not None:
            return cmpt

        if create_mock:
            return getattr(item.astype(self.bind.decl_cls), self.bind.key)

        return None

    def walk_same_cmpt_of_self_and_descendants(
        self,
        root_only: bool = False,
        *,
        use_mock: bool = False,
        create_mock: bool = False,
        unordered: bool = False,
    ) -> Iterable[Self]:
        """
        遍历该组件自身，以及所在物件的后代物件中的同类组件，默认不会创建 mock

        若设置了 ``root_only`` 或 ``self.bind`` 无效则会忽略后代组件

        :param root_only: 是否忽略后代组件，仅 ``yield`` 自己

        其余参数请参考 :meth:`walk_same_cmpt_of_descendants` 的文档
        """
        yield self
        if root_only or self.bind is None:
            return
        yield from self.walk_same_cmpt_of_descendants(use_mock=use_mock, create_mock=create_mock)

    def walk_same_cmpt_of_descendants(
        self, *, use_mock: bool = False, create_mock: bool = False, unordered: bool = False
    ) -> Iterable[Self]:
        """
        遍历所在物件的后代物件中的同类组件，默认不会创建 mock

        注：若 ``self.bind`` 无效会由于尝试访问 ``None`` 的成员而抛出属性错误，
        但是我们并没在函数中检查这一点；若有必要的话，预期的做法是在函数外检查

        :param use_mock: 在没有对应组件时，是否能使用先前创建过的 mock
        :param create_mock: 在没有对应组件时，是否基于 :meth:`~.Item.astype` 创建 mock
        :param unordered: 遍历是否不保证顺序，若指定，对于复杂结构的性能会更佳
        """
        root = self.bind.at_item
        if root._stored:
            return
        for item in root.walk_descendants(self.bind.decl_cls, unordered=unordered):
            cmpt = self.get_same_cmpt(item, use_mock=use_mock, create_mock=create_mock)
            if cmpt is None:
                continue
            yield cmpt

    # endregion

    @property
    def r(self) -> ItemT:
        """
        所位于的物件，便于链式调用同物件下其它的组件
        """
        return self.bind.at_item

    @classmethod
    def align_for_interpolate(cls, cmpt1, cmpt2) -> AlignedData[Self]:
        return AlignedData(cmpt1, cmpt1, cmpt1)

    def interpolate(self, cmpt1, cmpt2, alpha: float, *, path_func=None) -> None: ...

    # 仅用于在创建动画时忘记使用 .anim 或 .update 时抛出错误，另见 AnimGroup 的 _get_anim_object
    def __anim__(self):
        raise NotImplementedError()


class CmptInfo[T]:
    """
    在类中定义组件需要使用该类

    例：

    .. code-block:: python

        class MyItem(Item):
            # 错误！
            # cmpt1 = MyCmpt()

            # 正确
            cmpt1 = CmptInfo(MyCmpt[Self])

            # 错误！
            # cmpt2 = MyCmptWithArgs(1)

            # 正确
            cmpt2 = CmptInfo(MyCmptWithArgs[Self], 1)
    """

    def __init__(self, cls: type[T], *args, **kwargs):
        self.__doc__ = ''
        self.cls = getattr(cls, '__origin__', cls)
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

    def copy(self, *, new_cmpts: dict[str, Component]) -> Self:
        cmpt_copy = super().copy()
        cmpt_copy.objects = {key: new_cmpts[key] for key in cmpt_copy.objects}

        return cmpt_copy

    def _become(self, other) -> None:  # pragma: no cover
        pass

    def not_changed(self, other: _CmptGroup) -> bool:
        for key, obj in self.objects.items():
            if not obj.not_changed(other.objects[key]):
                return False

        return True

    @classmethod
    def align(
        cls,
        cmpt1: _CmptGroup,
        cmpt2: _CmptGroup,
        data1_cmpts: dict[str, Component],
        data2_cmpts: dict[str, Component],
        union_cmpts: dict[str, Component],
    ):
        cmpt1_copy = cmpt1.copy(new_cmpts=data1_cmpts)
        cmpt2_copy = cmpt2.copy(new_cmpts=data2_cmpts)
        cmpt_union = cmpt1.copy(new_cmpts=union_cmpts)
        return AlignedData(cmpt1_copy, cmpt2_copy, cmpt_union)

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

        raise CmptGroupLookupError(
            _('CmptGroup must be defined within the same class as the content passed in')
        )

    def _returned_self(self, cmpt: Component | Item._AsTypeWrapper, ret) -> bool:
        if isinstance(cmpt, Component):
            return cmpt is ret
        return cmpt._astype_obj is ret._astype_obj

    def __getattr__(self, name: str):
        if name == 'objects':
            raise AttributeError()

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
            raise AttributeError(
                _('None of the components ({cmpt_str}) have a method named {name}').format(
                    cmpt_str=cmpt_str, name=name
                )
            )

        def wrapper(*args, **kwargs):
            ret = [method(*args, **kwargs) for method in methods]

            return self if all(self._returned_self(a, b) for a, b in zip(objects, ret)) else ret

        meta = getattr(methods[0], METHOD_UPDATER_KEY, None)
        if meta is not None:
            setattr(wrapper, METHOD_UPDATER_KEY, meta)

        return wrapper


def CmptGroup[T](*cmpt_info_list: CmptInfo[T]) -> CmptInfo[T]:
    """
    用于将多个组件打包，使得可以同时调用

    例：

    .. code-block:: python

        class MyItem(Item):
            stroke = CmptInfo(Cmpt_Rgbas[Self])
            fill = CmptInfo(Cmpt_Rgbas[Self])
            color = CmptGroup(stroke, fill)

        item = MyItem()
        item.stroke.set(...)    # 只有 stroke 的被调用
        item.color.set(...)     # stroke 和 fill 的都被调用了
    """
    return CmptInfo(_CmptGroup, cmpt_info_list)
