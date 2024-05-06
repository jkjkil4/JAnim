import functools
import inspect
from collections import defaultdict
from dataclasses import dataclass
from typing import (Callable, Concatenate, Generic, ParamSpec, Self,
                    TypeVar, overload)

import janim.utils.refresh as refresh

type Key = str
type FullQualname = str

# 使 sphinx 可用
P = ParamSpec('P')
T = TypeVar('T')
R = TypeVar('R')


class _SelfSlots:
    def __init__(self):
        self.self_normal_slots: list[Callable] = []
        self.self_refresh_slots: list[Callable] = []
        self.self_refresh_slots_with_recurse: list[_SelfSlotWithRecurse] = []


class _Slots:
    def __init__(self):
        self.normal_slots: list[Callable] = []
        self.refresh_slots: list[_RefreshSlot] = []


class _AllSlots:
    def __init__(self):
        self.self_slots_dict: defaultdict[FullQualname, _SelfSlots] = defaultdict(_SelfSlots)
        self.slots_dict: defaultdict[int, _Slots] = defaultdict(_Slots)


@dataclass
class _SelfSlotWithRecurse:
    func: Callable
    recurse_up: bool
    recurse_down: bool


@dataclass
class _RefreshSlot:
    obj: refresh.Refreshable
    func: Callable | str


class Signal(Generic[T, P, R]):
    '''
    一般用于在 ``func`` 造成影响后，需要对其它数据进行更新时进行作用

    =====

    当 ``func`` 被该类修饰，使用 ``Class.func.emit(self)`` 后，

    对于 ``self_`` 型（修饰）：

    - 会以自身调用所有被 ``func.self_slot()`` 修饰的方法
    - 会将所有被 ``func.self_refresh()`` 修饰的方法标记需要重新计算
    - ``func.self_refresh_with_recurse()`` 与 ``func.self_refresh()`` 相比，还可以传入 ``recurse_up/down``

    对于 普通型（绑定）：

    - 会调用所有通过 ``func.connect(...)`` 记录的方法
    - 会将所有被 ``func.connect_refresh(...)`` 记录的方法标记需要重新计算

    提醒：

    - 可以在上述方法中传入 ``key`` 参数以区分调用
    - ``emit`` 方法可以传入额外的参数给被调用的 ``slots``

    注意：

    - 以 ``self_`` 开头的修饰器所修饰的方法需要与 ``func`` 在同一个类或者其子类中
    - ``Signal`` 的绑定与触发相关的调用需要从类名 ``Cls.func.xxx`` 访问，因为 ``obj.func.xxx`` 得到的是原方法

    =====

    例:

    .. code-block:: python

        class User(refresh.Refreshable):
            def __init__(self, name: str):
                super().__init__()
                self.name = name
                self.msg = ''

            @Signal
            def set_msg(self, msg: str) -> None:
                self.msg = msg
                User.set_msg.emit(self)

            @set_msg.self_slot()
            def notifier(self) -> None:
                print("User's message changed")

            @set_msg.self_refresh()
            @refresh.register
            def get_text(self) -> str:
                return f'[{self.name}] {self.msg}'

        user = User('jkjkil')
        user.set_msg('hello')   # Output: User's message changed
        print(user.get_text())  # Output: [jkjkil] hello


    .. code-block:: python

        class A:
            @Signal
            def fn_A(self) -> None:
                print('fn_A()')
                A.fn_A.emit(self)

        class B:
            def fn_B(self) -> None:
                print('fn_B()')

        a, b = A(), B()
        A.fn_A.connect(a, b.fn_B)

        a.fn_A()
        \'\'\'
        Output:
        fn_A()
        fn_B()
        \'\'\'


    另见:

    - :meth:`~.Relation.parents_changed()`
    - :meth:`~.Relation.children_changed()`
    '''
    def __init__(self, func: Callable[Concatenate[T, P], R]):
        self.func = func
        functools.update_wrapper(self, func)

        self.slots: defaultdict[Key, _AllSlots] = defaultdict(_AllSlots)

    @overload
    def __get__(self, instance: None, owner) -> Self: ...
    @overload
    def __get__(self, instnace: object, owner) -> Callable[P, R]: ...

    def __get__(self, instance, owner):
        return self if instance is None else self.func.__get__(instance, owner)

    def __call__(self, *args, **kwargs):    # pragma: no cover
        return self.func(*args, **kwargs)

    @staticmethod
    def _get_cls_full_qualname_from_fback() -> str:
        cls_locals = inspect.currentframe().f_back.f_back.f_locals
        module = cls_locals['__module__']
        qualname = cls_locals['__qualname__']
        return f'{module}.{qualname}'

    @staticmethod
    def _get_cls_full_qualname(cls: type) -> str:
        return f'{cls.__module__}.{cls.__qualname__}'

    def self_slot(self, *, key: str = ''):
        '''
        被修饰的方法会在 ``Signal`` 触发时被调用
        '''
        def decorator(func):
            full_qualname = self._get_cls_full_qualname_from_fback()

            all_slots = self.slots[key]
            self_slots = all_slots.self_slots_dict[full_qualname]
            self_slots.self_normal_slots.append(func)

            return func

        return decorator

    def self_refresh(self, *, key: str = ''):
        '''
        被修饰的方法会在 ``Signal`` 触发时，标记需要重新计算
        '''
        def decorator(func):
            full_qualname = self._get_cls_full_qualname_from_fback()

            all_slots = self.slots[key]
            self_slots = all_slots.self_slots_dict[full_qualname]
            self_slots.self_refresh_slots.append(func)

            return func

        return decorator

    def self_refresh_with_recurse(self, *, recurse_up: bool = False, recurse_down: bool = False, key: str = ''):
        '''
        被修饰的方法会在 ``Signal`` 触发时，标记需要重新计算
        '''
        def decorator(func):
            full_qualname = self._get_cls_full_qualname_from_fback()
            slot = _SelfSlotWithRecurse(func, recurse_up, recurse_down)

            all_slots = self.slots[key]
            self_slots = all_slots.self_slots_dict[full_qualname]
            self_slots.self_refresh_slots_with_recurse.append(slot)

            return func

        return decorator

    def connect(self, sender: object, func: Callable, *, key: str = '') -> None:
        '''
        使 ``func`` 会在 ``Signal`` 触发时被调用
        '''
        all_slots = self.slots[key]
        slots = all_slots.slots_dict[id(sender)]
        slots.normal_slots.append(func)

    def connect_refresh(self, sender: object, obj: object, func: Callable | str, *, key: str = '') -> None:
        '''
        使 ``func`` 会在 ``Signal`` 触发时被标记为需要重新计算
        '''
        slot = _RefreshSlot(obj, func)

        all_slots = self.slots[key]
        slots = all_slots.slots_dict[id(sender)]
        slots.refresh_slots.append(slot)

    def emit(self, sender: object, *args, key: str = '', **kwargs):
        '''
        触发 ``Signal``
        '''
        all_slots = self.slots.get(key, None)
        if all_slots is None:
            return

        for cls in sender.__class__.mro():
            full_qualname = self._get_cls_full_qualname(cls)
            if full_qualname not in all_slots.self_slots_dict:
                continue

            slots = all_slots.self_slots_dict[full_qualname]

            # self_normal_slots
            for func in slots.self_normal_slots:
                func(sender, *args, **kwargs)

            # self_refresh_slots
            for func in slots.self_refresh_slots:
                sender.mark_refresh(func)

            # self_refresh_slots_with_recurse
            for slot in slots.self_refresh_slots_with_recurse:
                sender.mark_refresh(slot.func, recurse_up=slot.recurse_up, recurse_down=slot.recurse_down)

        sender_id = id(sender)
        if sender_id in all_slots.slots_dict:
            slots = all_slots.slots_dict[sender_id]

            # normal_slots
            for func in slots.normal_slots:
                func(*args, **kwargs)

            # refresh_slots
            for slot in slots.refresh_slots:
                slot.obj.mark_refresh(slot.func)
