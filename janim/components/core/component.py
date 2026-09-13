from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Iterable, Literal, Self, overload

from janim_backend import relation
from janim_backend.component import CmptCore

from janim.anims.method_updater_meta import METHOD_UPDATER_KEY
from janim.components.core.attrs import ComponentAttrs
from janim.exception import CmptGroupLookupError
from janim.items.relation import _items_relation_registry
from janim.locale import get_translator
from janim.utils.cmpt_lazy import EXPIRED, FLAG_HANDLE_NAME, Expired
from janim.utils.data import AlignedData

if TYPE_CHECKING:
    from janim.items.item import Item

_ = get_translator('janim.components.component')


class AttrsCollector(type):
    """
    收集类依赖图中的所有 ``attrs = ComponentAttrs()`` 对象，
    构建合并后的类成员 ``_mro_attrs_def`` ，表示类注册的所有属性

    注册的这些属性会通过

    .. code-block:: python

        self._init_attrs(self._mro_attrs_def.fields)

    交由 Rust 后端高效管理

    -----

    额外性质（临时）：检查子类，不应实现旧 API `copy`、`become` 和 `not_changed` ，对于实现了的给出报错；只有标记了 `@AttrsCollector.allow` 的可以允许
    """

    @staticmethod
    def allow[F](func: F) -> F:
        setattr(func, '_ac_allowed', True)  # noqa: B010
        return func

    def __new__(
        cls: type,
        name: str,
        bases: tuple[type, ...],
        attrdict: dict,
        *,
        impl: bool = False,
    ):
        # TODO: 在之后的新版本移除这段关于旧版本方法的迁移提示，以及上方的 allow 标记工具
        if impl:
            raise AttributeError(
                _('Every subclass of Component does not need `impl=True` anymore.')
            )

        if name != 'Component':
            for key in ('copy', 'become', 'not_changed'):
                attr = attrdict.get(key, None)
                if attr is not None and not getattr(attr, '_ac_allowed', False):
                    raise AttributeError(
                        _(
                            'Every subclass of Component must not implement '
                            'the legecy "{key}" method, but "{name}" does. '
                            'The API has changed to a internally managed version, '
                            'please contact us about how to migrate.'
                        ).format(key=key, name=name)
                    )

        # 所有子类均禁止额外的属性设置
        attrdict['__slots__'] = ()

        return super().__new__(cls, name, bases, attrdict)  # type: ignore

    def __init__(self: type[Component], *args, **kwargs):  # type: ignore
        super().__init__(*args, **kwargs)

        attrs_list: list[ComponentAttrs] = []
        last_attrs_cls: type | None = None

        for sup in reversed(self.mro()):
            attrs = sup.__dict__.get('_attrs', None)
            if attrs is not None:
                attrs_list.append(attrs)
                last_attrs_cls = sup

        self._mro_attrs_def = ComponentAttrs.merge(attrs_list)
        """
        该类所具有的所有 ``CompoentField``

        将 ``cls.mro()`` 中的所有 ``_attrs`` 合并得到
        """

        self._last_attrs_cls = last_attrs_cls
        """
        该类 ``mro()`` 中最后一个带有 ``_attrs`` 定义的类对象
        """


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

    __slots__ = ('_computed_caches', '_flag_0', 'at_item', 'decl_cls', 'key')

    def __init__(self, decl_cls: type[Item], at_item: Item, key: str) -> None:
        self.decl_cls = decl_cls
        self.at_item = at_item
        self.key = key

        self._flag_0 = _items_relation_registry.indexize_key(self.key)
        self._computed_caches = {}

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


class Component[ItemT](CmptCore, metaclass=AttrsCollector):
    """
    组件

    设计思想：包括“组件属性”和“组件操作”两大部分

    “组件属性”定义了组件的数据和状态，而“组件操作”则是提供给外部操作的，修改“组件属性”的接口

    **定义组件数据** ：

    我们可以通过

    .. code-block:: python

        class Cmpt_X(Component):
            _attrs = ComponentAttrs()
            field1 = _attrs.int()
            field2 = _attrs.ndarray(np.array([], dtype=np.float32))

    给 ``Cmpt_X`` 定义两个属性： ``field1`` 和 ``field2``

    这里的 ``_attrs = ComponentAttrs()`` 变量名 ``_attrs`` 是强制的，其余的变量名随意，
    不过在只允许通过接口操作数据的设计下，我们可能会将 ``field1`` 和 ``field2`` 前面也加上下划线

    **定义组件操作** ：

    也就是编写操作“组件属性”的有关方法，只需像操作普通变量一样操作那些属性变量即可

    .. code-block:: python

        class Cmpt_X(Component):
            _attrs = ComponentAttrs()
            _value = _attrs.int()

            def increment(self, delta: int) -> Self:
                self._value += delta

            def get(self) -> int:
                return self._value

    **杂项** ：

    - 在继承关系中，定义的“组件属性”会传递且合并，最终的子类拥有父类声明过的所有属性
    - 可以使用 ``.take_modified()`` 检查在上次调用该方法后，是否有修改过属性值
    - 可以使用 ``__cmpt_init__`` 自定义初始化构造函数，会透传传递给 ``__init__`` 的参数

    .. important::

        对于 :class:`~.Component` 及其子类，只有通过 ``_attrs`` 定义的“组件属性”能作为变量使用，其余任何自行定义的变量均无法正常使用
    """

    if TYPE_CHECKING:

        def __new__(cls, /) -> Self: ...

        def copy(self) -> Self: ...

    def __init__(self, *args, **kwargs):
        self._init_attrs(self._mro_attrs_def.fields)
        self.__cmpt_init__(*args, **kwargs)

    def __cmpt_init__(self, *args, **kwargs) -> None:
        pass

    _attrs = ComponentAttrs()
    _bind = _attrs.owned_object(BindInfo)
    _signal_obj_conns = _attrs.owned_object(defaultdict)

    def init_bind(self, bind: BindInfo) -> None:
        """
        用于 ``Item._init_components``

        子类可以继承该函数，进行与所在物件相关的处理
        """
        self._bind = bind

    def become(self, other: Component) -> Self:
        """
        将 ``other`` 所带有的状态应用到当前组件上

        对于 ``become`` 和 ``_become`` 的区别， ``become`` 会自动清理与该组件有关的惰性求值状态， ``_become`` 不会

        需要直接使用 ``_become`` 的情景：在 :meth:`~.Item.become` 和 :meth:`~.Item.restore` 方法中，
        不需要逐组件清理惰性求值状态，而是可以直接 ``reset_computed_for_self()`` 直接在物件级别清理所有组件的惰性求值状态，
        所以在 :meth:`~.Item.become` 和 :meth:`~.Item.restore` 这两个方法中，使用的是 ``_become`` 避免各自独立重置，从而提升效率
        """
        bind = self._bind
        if bind is not None:
            bind.reset_computed_for_all()
        self._become(other)
        return self

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
        得到 ``item`` 物件中与自身同 ``self._bind.key`` 的组件，默认会创建 mock

        注：若 ``self._bind`` 无效会由于尝试访问 ``None`` 的成员而抛出属性错误，
        但是我们并没在函数中检查这一点；若有必要的话，预期的做法是在函数外检查

        :param item: 得到哪个物件中的组件
        :param use_mock: 在没有对应组件时，是否能使用先前创建过的 mock
        :param create_mock: 在没有对应组件时，是否基于 :meth:`~.Item.astype` 创建 mock
        :return: 得到的组件，若 ``create_mock=False``，则可能返回 ``None``
        """
        cmpt = item.components.get(self._bind.key, None)
        if cmpt is not None:
            return cmpt

        if use_mock and (cmpt := item._astype_mock_cmpt.get(self._bind.key)) is not None:
            return cmpt

        if create_mock:
            return getattr(item.astype(self._bind.decl_cls), self._bind.key)

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

        若设置了 ``root_only`` 或 ``self._bind`` 无效则会忽略后代组件

        :param root_only: 是否忽略后代组件，仅 ``yield`` 自己

        其余参数请参考 :meth:`walk_same_cmpt_of_descendants` 的文档
        """
        yield self
        if root_only or self._bind is None:
            return
        yield from self.walk_same_cmpt_of_descendants(
            use_mock=use_mock, create_mock=create_mock, unordered=unordered
        )

    def walk_same_cmpt_of_descendants(
        self, *, use_mock: bool = False, create_mock: bool = False, unordered: bool = False
    ) -> Iterable[Self]:
        """
        遍历所在物件的后代物件中的同类组件，默认不会创建 mock

        注：若 ``self._bind`` 无效会由于尝试访问 ``None`` 的成员而抛出属性错误，
        但是我们并没在函数中检查这一点；若有必要的话，预期的做法是在函数外检查

        :param use_mock: 在没有对应组件时，是否能使用先前创建过的 mock
        :param create_mock: 在没有对应组件时，是否基于 :meth:`~.Item.astype` 创建 mock
        :param unordered: 遍历是否不保证顺序，若指定，对于复杂结构的性能会更佳
        """
        root = self._bind.at_item
        if root._stored:
            return
        for item in root.walk_descendants(self._bind.decl_cls, unordered=unordered):
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
        return self._bind.at_item  # type: ignore

    @classmethod
    def align_for_interpolate(cls, cmpt1: Self, cmpt2: Self) -> AlignedData[Self]:
        cmpt1_copy = cmpt1.copy()
        cmpt2_copy = cmpt2.copy()
        return AlignedData(cmpt1_copy, cmpt2_copy, cmpt1_copy.copy())

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
        self.cls: type[Component] = getattr(cls, '__origin__', cls)  # type: ignore
        self.args = args
        self.kwargs = kwargs

    def create(self) -> Component:
        return self.cls(*self.args, **self.kwargs)

    # 方便代码补全，没有实际意义
    @overload
    def __get__(self, obj: None, owner) -> Self: ...
    @overload
    def __get__(self, obj: object, owner) -> T: ...

    def __get__(self, obj, owner) -> Self | T:
        return self


class _CmptGroup(Component):
    _attrs = ComponentAttrs()
    _cmpt_info_list = _attrs.direct_object(list, nullable=False)
    _cmpt_objects = _attrs.owned_object(dict)

    def __cmpt_init__(self, cmpt_info_list: list[CmptInfo]):
        self._cmpt_info_list = cmpt_info_list

    def init_bind(self, bind: BindInfo) -> None:
        super().init_bind(bind)
        self._find_objects()

    def _find_objects(self) -> None:
        """
        在 ``self._bind.at_item`` 中查找物件组所包括的组件对象，存入 ``self._cmpt_objects``

        例如对于

        .. code-block:: python

            stroke = CmptInfo(Cmpt_Rgbas[Self])
            fill = CmptInfo(Cmpt_Rgbas[Self])

            color = CmptGroup(stroke, fill)

        ``color`` 组件对象会得到与 ``stroke`` 和 ``fill`` 对应的组件对象
        """
        objects: dict[str, Component] = {}

        for cmpt_info in self._cmpt_info_list:
            key = self._find_key(cmpt_info)
            # 由于需要 astype，所以使用 getattr 而不是直接从 .components 中获取
            objects[key] = getattr(self._bind.at_item, key)  # type: ignore

        self._cmpt_objects = objects

    def _find_key(self, cmpt_info: CmptInfo) -> str:
        """
        查找 ``cmpt_info`` 在物件中定义为什么名字

        例如对于 ``points = CmptInfo(Cmpt_Points[Self])`` 会得到 ``"points"``
        """
        from janim.items.item import CLS_CMPTINFO_NAME

        for key, val in self._bind.decl_cls.__dict__.get(CLS_CMPTINFO_NAME, {}).items():  # type: ignore
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
        if name == '_cmpt_objects' or self._cmpt_objects is None:
            raise AttributeError()

        objects = []
        methods = []

        for obj in self._cmpt_objects.values():
            if not hasattr(obj, name):
                continue

            attr = getattr(obj, name)
            if not callable(attr):
                continue

            objects.append(obj)
            methods.append(attr)

        if not methods:
            cmpt_str = ', '.join(cmpt.__class__.__name__ for cmpt in self._cmpt_objects)
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
    return CmptInfo(_CmptGroup, cmpt_info_list)  # type: ignore
