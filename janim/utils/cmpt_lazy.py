from __future__ import annotations

import inspect
from collections import defaultdict
from functools import cache, partial, update_wrapper, wraps
from typing import TYPE_CHECKING, Any, Callable, Concatenate, Self, overload

from janim_backend import relation

from janim.items.relation import _items_relation_registry

if TYPE_CHECKING:
    from janim.components.component import Component


FLAG_HANDLE_NAME = '__flag_handle'


@overload
def cmpt_lazy_method[T](func: T, *, recurse_up: bool = False, recurse_down: bool = False) -> T: ...
@overload
def cmpt_lazy_method[T](
    func: None = None, *, recurse_up: bool = False, recurse_down: bool = False
) -> Callable[[T], T]: ...


def cmpt_lazy_method(func=None, *, recurse_up=False, recurse_down=False):  # type: ignore
    """
    用于在需要时才重新计算调用组件方法得到的值，提升性能

    在需要重新计算的场景下，会通过 ``self.bind.reset_computed_for`` 重置，
    之后对 ``func`` 的调用才会重新计算返回值

    注：如果组件没有绑定到物件，不提供缓存
    """
    if func is None:
        return partial(_cmpt_lazy_method, recurse_up, recurse_down)
    return _cmpt_lazy_method(recurse_up, recurse_down, func)


def _cmpt_lazy_method(recurse_up: bool, recurse_down: bool, func):
    flag_handle = _items_relation_registry.create_flag(func.__name__, recurse_up, recurse_down)

    @wraps(func)
    def wrapper(self: Component, *args, **kwargs):
        bind = self._bind

        if (cached := bind.get_computed_for(flag_handle)) is not None:
            computed = cached
        else:
            computed = func(self, *args, **kwargs)
            bind.mark_computed_for(flag_handle, computed)

        return computed

    setattr(wrapper, relation.FLAG_HANDLE_NAME, flag_handle)

    return wrapper


type FullQualname = str
type Key = str

# ClsRefreshes 即各个类中出现的 @self_refresh
# ClsMroRefreshes 即把 mro() 中的 ClsRefreshes 收集得到的总和
# 因为在类创建环节使用 @self_refresh 时，类对象还没构造，所以我们只能用 qualname 来作为类的标识
type ClsRefreshes = defaultdict[FullQualname, defaultdict[Key, list[relation.FlagHandle]]]
type ClsMroRefreshes = defaultdict[Key, list[relation.FlagHandle]]

type ObjConns = defaultdict[tuple[CmptSignal, Key], list[Callable]]

SIGNAL_OBJ_CONNS_NAME = '__signal_obj_conns'


class CmptSignal[T, **P, R]:
    def __init__(self, func: Callable[Concatenate[T, P], R]):
        self.func = func
        update_wrapper(self, func)

        self.cls_refreshes: ClsRefreshes = defaultdict(lambda: defaultdict(list))

    # region typing

    @overload
    def __get__(self, instance: None, owner) -> Self: ...
    @overload
    def __get__(self, instance: object, owner) -> Callable[P, R]: ...

    def __get__(self, instance, owner):
        return self if instance is None else self.func.__get__(instance, owner)

    def __call__(self, *args, **kwargs):  # pragma: no cover
        return self.func(*args, **kwargs)

    # endregion

    # region utils

    @staticmethod
    def _get_cls_full_qualname_from_fback() -> str:
        cls_locals = inspect.currentframe().f_back.f_back.f_locals  # type: ignore
        module = cls_locals['__module__']
        qualname = cls_locals['__qualname__']
        return f'{module}.{qualname}'

    @staticmethod
    def _get_cls_full_qualname(cls_: type) -> str:
        return f'{cls_.__module__}.{cls_.__qualname__}'

    @cache  # noqa: B019
    def _get_cls_mro_refreshes(self, cls: type) -> ClsMroRefreshes:
        result: ClsMroRefreshes = defaultdict(list)

        for sup in cls.mro():
            full_qualname = self._get_cls_full_qualname(sup)

            sup_slots = self.cls_refreshes.get(full_qualname, None)
            if sup_slots is None:
                continue

            for key, value in sup_slots.items():
                result[key].extend(value)

        return result

    # endregion

    # region self_refresh

    @overload
    def self_refresh[Fn](self, func: Fn, *, key: str = '') -> Fn: ...
    @overload
    def self_refresh[Fn](self, func: None = None, *, key: str = '') -> Callable[[Fn], Fn]: ...

    def self_refresh(self, func=None, *, key: str = ''):  # type: ignore
        """
        被修饰的方法会在 ``Signal`` 触发时，标记需要重新计算
        """
        full_qualname = self._get_cls_full_qualname_from_fback()

        if func is None:
            # Called with @self_slot()
            return partial(self._self_refresh, full_qualname, key=key)
        # Called with @self_slot
        return self._self_refresh(full_qualname, func)

    def _self_refresh(self, full_qualname: str, func, key: str = ''):
        flag_handle = getattr(func, FLAG_HANDLE_NAME)
        self.cls_refreshes[full_qualname][key].append(flag_handle)
        return func

    # endregion

    # region connect

    @staticmethod
    def _get_obj_conns(sender: object) -> ObjConns | None:
        return getattr(sender, SIGNAL_OBJ_CONNS_NAME, None)

    @staticmethod
    def _get_obj_conns_or_default(sender: object) -> ObjConns:
        conns: ObjConns | None = getattr(sender, SIGNAL_OBJ_CONNS_NAME, None)
        if conns is None:
            conns = defaultdict(list)
            setattr(sender, SIGNAL_OBJ_CONNS_NAME, conns)
        return conns

    def connect(self, sender: object, func: Callable, *, key: str = '') -> None:
        """
        使 ``func`` 会在 ``Signal`` 触发时调用
        """
        obj_conns = self._get_obj_conns_or_default(sender)
        obj_conns[(self, key)].append(func)

    # endregion

    # region emit

    def emit(self, sender: Component, *args, key: str = '', **kwargs):
        # @self_refresh

        cls_mro_refreshes = self._get_cls_mro_refreshes(sender.__class__)
        refreshes = cls_mro_refreshes[key]
        sender._bind.reset_computed_for_list(refreshes)

        # .connect

        obj_conns = self._get_obj_conns(sender)
        if obj_conns is None:
            return
        conns = obj_conns.get((self, key), None)
        if conns is None:
            return

        for func in conns:
            func(*args, **kwargs)

    # endregion
