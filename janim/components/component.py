from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Generator, Self, overload

from janim_backend import relation

from janim.anims.method_updater_meta import METHOD_UPDATER_KEY
from janim.exception import CmptGroupLookupError
from janim.items.relation import _items_relation_registry
from janim.locale import get_translator
from janim.utils.cmpt_lazy import FLAG_HANDLE_NAME, SIGNAL_OBJ_CONNS_NAME
from janim.utils.data import AlignedData

if TYPE_CHECKING:  # pragma: no cover
    from janim.items.item import Item

_ = get_translator('janim.components.component')


class _CmptMeta(type):
    def __new__(
        cls: type,
        name: str,
        bases: tuple[type, ...],
        attrdict: dict,
        *,
        impl=False,  # 若 impl=True，则会跳过下面的检查
    ):
        if not impl:
            for key in ('copy', 'become', 'not_changed'):
                if not callable(attrdict.get(key, None)):
                    raise AttributeError(  # noqa: TRY004
                        _(
                            'Every subclass of Component must inherit and implement '
                            'the "{key}" method, but "{name}" does not'
                        ).format(key=key, name=name)
                    )
        return super().__new__(cls, name, bases, attrdict)


class Component[ItemT](metaclass=_CmptMeta):
    def __init__(self) -> None:
        super().__init__()
        self._bind = _items_relation_registry.create_binder()

    def init_bind(self, info: relation.BindInfo) -> None:
        """
        用于 ``Item._init_components``

        子类可以继承该函数，进行与所在物件相关的处理
        """
        self._bind.bind_to(info)

    def __copy__(self) -> Self:
        """
        手动实现 ``__copy__``，这样性能比 copy.copy 高

        特别是 Component 作为频繁使用的对象这很重要
        """
        cls = self.__class__
        new = cls.__new__(cls)

        new.__dict__ = self.__dict__.copy()

        return new

    def copy(self) -> Self:
        cmpt_copy = self.__copy__()
        cmpt_copy._bind = _items_relation_registry.create_binder()
        setattr(cmpt_copy, SIGNAL_OBJ_CONNS_NAME, None)
        return cmpt_copy

    def become(self, other) -> Self:
        self._bind.reset_computed_for_all()

    def not_changed(self, other) -> bool: ...

    def get_same_cmpt(self, item: Item) -> Self:
        return self.get_same_cmpt_if_exists(item) or getattr(
            item.astype(self._bind.decl_cls), self._bind.key
        )

    def get_same_cmpt_without_mock(self, item: Item) -> Self | None:
        return item.components.get(self._bind.key, None)

    def get_same_cmpt_if_exists(self, item: Item) -> Self | None:
        cmpt = item.components.get(self._bind.key, None)
        if cmpt is not None:
            return cmpt

        return item._astype_mock_cmpt.get(self._bind.key, None)

    def walk_same_cmpt_of_self_and_descendants_without_mock(
        self,
        root_only: bool = False,
    ) -> Generator[Self, None, None]:
        yield self
        if root_only or not self._bind.is_binded():
            return
        yield from self.walk_same_cmpt_of_descendants_without_mock()

    def walk_same_cmpt_of_descendants_without_mock(self) -> Generator[Self, None, None]:
        root: Item = self._bind.at_item
        if not root._stored:
            for item in root.walk_descendants(self._bind.decl_cls):
                cmpt = self.get_same_cmpt_without_mock(item)
                if cmpt is None:
                    continue
                yield cmpt

    @property
    def r(self) -> ItemT:
        """
        所位于的物件，便于链式调用同物件下其它的组件
        """
        return self._bind.at_item

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

    def init_bind(self, info: relation.BindInfo) -> None:
        super().init_bind(info)
        self._find_objects()

    def copy(self, *, new_cmpts: dict[str, Component]) -> Self:
        cmpt_copy = super().copy()
        cmpt_copy.objects = {key: new_cmpts[key] for key in cmpt_copy.objects}

        return cmpt_copy

    def become(self, other) -> Self:  # pragma: no cover
        super().become(other)

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
            self.objects[key] = getattr(self._bind.at_item, key)

    def _find_key(self, cmpt_info: CmptInfo) -> str:
        from janim.items.item import CLS_CMPTINFO_NAME

        for key, val in self._bind.decl_cls.__dict__.get(CLS_CMPTINFO_NAME, {}).items():
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
