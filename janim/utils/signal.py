from __future__ import annotations

import gc
import inspect
import weakref
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache, partial, update_wrapper
from typing import Callable, Concatenate, Self, overload

import janim.utils.refresh as refresh

type Key = str
type FullQualname = str

SIGNAL_OBJ_SLOTS_NAME = '__signal_obj_slots'


class _SelfSlots:
    def __init__(self):
        self.normal_slots: list[Callable] = []
        self.refresh_slots: list[Callable] = []
        self.refresh_slots_with_recurse: list[_SelfSlotWithRecurse] = []


class _ObjSlots:
    def __init__(self):
        self.normal_slots: list[Callable] = []
        self.refresh_slots: list[_RefreshSlot] = []


@dataclass
class _SelfSlotWithRecurse:
    func: Callable
    recurse_up: bool
    recurse_down: bool


@dataclass
class _RefreshSlot:
    obj: weakref.ReferenceType[refresh.Refreshable]
    func: Callable | str


class Signal[T, **P, R]:
    # for gc
    objects_with_slots: weakref.WeakSet[defaultdict[tuple[Signal, Key], _ObjSlots]] = weakref.WeakSet()

    def __init__(self, func: Callable[Concatenate[T, P], R]):
        self.func = func
        update_wrapper(self, func)

        self.all_slots: defaultdict[FullQualname, defaultdict[Key, _SelfSlots]] \
            = defaultdict(lambda: defaultdict(_SelfSlots))

    # region typing

    @overload
    def __get__(self, instance: None, owner) -> Self: ...
    @overload
    def __get__(self, instnace: object, owner) -> Callable[P, R]: ...

    def __get__(self, instance, owner):
        return self if instance is None else self.func.__get__(instance, owner)

    def __call__(self, *args, **kwargs):    # pragma: no cover
        return self.func(*args, **kwargs)

    # endregion

    # region utils

    @staticmethod
    def _get_cls_full_qualname_from_fback() -> str:
        cls_locals = inspect.currentframe().f_back.f_back.f_locals
        module = cls_locals['__module__']
        qualname = cls_locals['__qualname__']
        return f'{module}.{qualname}'

    @staticmethod
    def _get_cls_full_qualname(cls: type) -> str:
        return f'{cls.__module__}.{cls.__qualname__}'

    @lru_cache
    def _get_cls_slots(self, cls: type) -> defaultdict[Key, _SelfSlots]:
        result: defaultdict[Key, _SelfSlots] = defaultdict(_SelfSlots)

        for sup in cls.mro():
            full_qualname = self._get_cls_full_qualname(sup)

            sup_slots = self.all_slots.get(full_qualname, None)
            if sup_slots is None:
                continue

            for key, value in sup_slots.items():
                r = result[key]
                r.normal_slots.extend(value.normal_slots)
                r.refresh_slots.extend(value.refresh_slots)
                r.refresh_slots_with_recurse.extend(value.refresh_slots_with_recurse)

        return result

    @staticmethod
    def _get_obj_slots(sender: object) -> defaultdict[tuple[Signal, Key], _ObjSlots] | None:
        return getattr(sender, SIGNAL_OBJ_SLOTS_NAME, None)

    @staticmethod
    def _get_obj_slots_with_default(sender: object) -> defaultdict[tuple[Signal, Key], _ObjSlots]:
        obj_slots = getattr(sender, SIGNAL_OBJ_SLOTS_NAME, None)
        if obj_slots is None:
            obj_slots = defaultdict(_ObjSlots)
            Signal.objects_with_slots.add(sender)
            setattr(sender, SIGNAL_OBJ_SLOTS_NAME, obj_slots)
        return obj_slots

    # endregion

    # region slots

    def self_slot(self, func=None, /, *, key: str = ''):
        '''
        被修饰的方法会在 ``Signal`` 触发时被调用
        '''
        full_qualname = self._get_cls_full_qualname_from_fback()

        if func is None:
            # Called with @self_slot()
            return partial(self._self_slot, full_qualname, key=key)

        # Called with @self_slot
        return self._self_slot(full_qualname, func)

    def _self_slot[T](self, full_qualname: str, func: T, key: str = '') -> T:
        self.all_slots[full_qualname][key].normal_slots.append(func)
        return func

    def self_refresh(self, func=None, *, key: str = ''):
        '''
        被修饰的方法会在 ``Signal`` 触发时，标记需要重新计算
        '''
        full_qualname = self._get_cls_full_qualname_from_fback()

        if func is None:
            # Called with @self_slot()
            return partial(self._self_refresh, full_qualname, key=key)

        # Called with @self_slot
        return self._self_refresh(full_qualname, func)

    def _self_refresh[T](self, full_qualname: str, func: T, key: str = '') -> T:
        self.all_slots[full_qualname][key].refresh_slots.append(func)
        return func

    def self_refresh_with_recurse(self, *, recurse_up: bool = False, recurse_down: bool = False, key: str = ''):
        '''
        被修饰的方法会在 :class:`~.Signal` 触发时，标记需要重新计算

        并且会根据 ``recurse_up`` 和 ``recurse_down`` 进行递归传递
        '''
        def decorator(func):
            full_qualname = self._get_cls_full_qualname_from_fback()
            slot = _SelfSlotWithRecurse(func, recurse_up, recurse_down)
            self.all_slots[full_qualname][key].refresh_slots_with_recurse.append(slot)
            return func

        return decorator

    def connect(self, sender: object, func: Callable, *, key: str = '') -> None:
        '''
        使 ``func`` 会在 ``Signal`` 触发时被调用
        '''
        obj_slots = self._get_obj_slots_with_default(sender)
        obj_slots[(self, key)].normal_slots.append(func)

    def connect_refresh(self, sender: object, obj: object, func: Callable | str, *, key: str = '') -> None:
        '''
        使 ``func`` 会在 ``Signal`` 触发时被标记为需要重新计算
        '''
        obj_slots = self._get_obj_slots_with_default(sender)
        slot = _RefreshSlot(weakref.ref(obj), func)
        obj_slots[(self, key)].refresh_slots.append(slot)

    def emit(self, sender: object, *args, key: str = '', **kwargs):
        cls_slots = self._get_cls_slots(sender.__class__)
        slots = cls_slots[key]

        # @self_slot
        for func in slots.normal_slots:
            func(sender, *args, **kwargs)

        # @self_refresh
        for func in slots.refresh_slots:
            sender.mark_refresh(func)

        # @self_refresh_with_recurse
        for slot in slots.refresh_slots_with_recurse:
            sender.mark_refresh(slot.func, recurse_up=slot.recurse_up, recurse_down=slot.recurse_down)

        ####

        obj_slots = self._get_obj_slots(sender)
        if obj_slots is None:
            return
        slots = obj_slots.get((self, key), None)
        if slots is None:
            return

        # @connect
        for func in slots.normal_slots:
            func(*args, **kwargs)

        # @connect_refresh
        for slot in slots.refresh_slots:
            obj = slot.obj()
            if obj is None:
                continue    # pragma: no cover
            obj.mark_refresh(slot.func)


def _signal_gc_callback(phase: str, info: dict) -> None:
    if phase != 'start' or info['generation'] != 2:
        return

    total = 0

    for sender in Signal.objects_with_slots:
        obj_slots = Signal._get_obj_slots(sender)
        assert obj_slots is not None

        for slots in obj_slots.values():
            len1 = len(slots.refresh_slots)
            slots.refresh_slots = [
                slot
                for slot in slots.refresh_slots
                if slot.obj() is not None
            ]
            len2 = len(slots.refresh_slots)
            total += (len1 - len2)

    # if total != 0:
    #     log.debug(
    #         'Cleaned {count} references caused by Signal.connect_refresh'
    #         .format(count=total)
    #     )


gc.callbacks.append(_signal_gc_callback)
