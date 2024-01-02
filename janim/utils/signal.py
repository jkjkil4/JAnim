import functools
import inspect
from typing import Callable

import janim.utils.refresh as refresh

Key = str
FullQualname = str


class _SelfSlots:
    def __init__(self):
        self.self_normal_slots: list[Callable] = []
        self.self_refresh_slots: list[Callable] = []
        self.self_refresh_slots_of_relation: list[_SelfSlotOfRel] = []


class _Slots:
    def __init__(self):
        self.normal_slots: list[Callable] = []
        self.refresh_slots: list[_RefreshSlot] = []


class _AllSlots:
    def __init__(self):
        self.self_slots_dict: dict[FullQualname, _SelfSlots] = {}
        self.slots_dict: dict[int, _Slots] = {}


class _SelfSlotOfRel:
    def __init__(self, func: Callable, recurse_up: bool, recurse_down: bool):
        self.func = func
        self.recurse_up = recurse_up
        self.recurse_down = recurse_down


class _RefreshSlot:
    def __init__(self, obj: refresh.Refreshable, func: Callable | str):
        self.obj = obj
        self.func = func


class Signal:
    '''
    一般用于在 ``func`` 造成影响后，需要对其它数据进行更新时进行响应

    - 当 ``func`` 被该类修饰，使用 ``Class.func.emit(self)`` 后，
        - ``self_`` 型（修饰）：
            - 会以自身调用所有被 ``func.self_slot()`` 修饰的方法
            - 会将所有被 ``func.self_refresh()`` 修饰的方法标记需要重新计算
            - ``func.self_refresh_of_relation()`` 与 ``func.self_refresh()`` 相比，还可以传入 ``recurse_up/down``

        - 普通型（绑定）：
            - 会调用所有通过 ``func.connect(...)`` 记录的方法
            - 会将所有被 ``func.connect_refresh(...)`` 记录的方法标记需要重新计算

    - 提醒：
        - 可以在上述方法中传入 ``key`` 参数以区分调用
        - ``emit`` 方法可以传入额外的参数给被调用的 ``slots``

    - 注意：
        - 以 ``self_`` 开头的修饰器所修饰的方法需要与 ``func`` 在同一个类或者其子类中
        - ``Signal`` 的绑定与触发相关的调用需要从类名 ``Cls.func.xxx`` 访问，因为 ``obj.func.xxx`` 得到的是原方法

    =====

    例 | Example:

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

            @set_msg.self_refresh_of_relation()
            @refresh.register
            def get_test(self) -> str:
                return f'[{self.name}] {self.msg}'

        user = User('jkjkil')
        user.set_msg('hello')   # Output: User's message changed
        print(user.get_text())  # Output: [jkjkil] hello
    '''
    def __init__(self, func: Callable):
        self.func = func
        functools.update_wrapper(self, func)

        self.slots: dict[Key, _AllSlots] = {}

    def __get__(self, instance, owner):
        return self if instance is None else self.func.__get__(instance, owner)

    @staticmethod
    def get_cls_full_qualname_from_fback() -> str:
        cls_locals = inspect.currentframe().f_back.f_back.f_locals
        module = cls_locals['__module__']
        qualname = cls_locals['__qualname__']
        return f'{module}.{qualname}'

    @staticmethod
    def get_cls_full_qualname(cls: type) -> str:
        return f'{cls.__module__}.{cls.__qualname__}'

    def self_slot(self, *, key: str = ''):
        '''
        被修饰的方法会在 ``Signal`` 触发时被调用
        '''
        def decorator(func):
            full_qualname = self.get_cls_full_qualname_from_fback()

            all_slots = self.slots.setdefault(key, _AllSlots())
            self_slots = all_slots.self_slots_dict.setdefault(full_qualname, _SelfSlots())
            self_slots.self_normal_slots.append(func)

            return func

        return decorator

    def self_refresh(self, *, key: str = ''):
        '''
        被修饰的方法会在 ``Signal`` 触发时，标记需要重新计算
        '''
        def decorator(func):
            full_qualname = self.get_cls_full_qualname_from_fback()

            all_slots = self.slots.setdefault(key, _AllSlots())
            self_slots = all_slots.self_slots_dict.setdefault(full_qualname, _SelfSlots())
            self_slots.self_refresh_slots.append(func)

            return func

        return decorator

    def self_refresh_of_relation(self, *, recurse_up: bool = False, recurse_down: bool = False, key: str = ''):
        '''
        被修饰的方法会在 ``Signal`` 触发时，标记需要重新计算
        '''
        def decorator(func):
            full_qualname = self.get_cls_full_qualname_from_fback()
            slot = _SelfSlotOfRel(func, recurse_up, recurse_down)

            all_slots = self.slots.setdefault(key, _AllSlots())
            self_slots = all_slots.self_slots_dict.setdefault(full_qualname, _SelfSlots())
            self_slots.self_refresh_slots_of_relation.append(slot)

            return func

        return decorator

    def connect(self, sender: object, func: Callable, *, key: str = '') -> None:
        '''
        使 ``func`` 会在 ``Signal`` 触发时被调用
        '''
        all_slots = self.slots.setdefault(key, _AllSlots())
        slots = all_slots.slots_dict.setdefault(id(sender), _Slots())
        slots.normal_slots.append(func)

    def connect_refresh(self, sender: object, obj: object, func: Callable | str, *, key: str = '') -> None:
        '''
        使 ``func`` 会在 ``Signal`` 触发时被标记为需要重新计算
        '''
        slot = _RefreshSlot(obj, func)

        all_slots = self.slots.setdefault(key, _AllSlots())
        slots = all_slots.slots_dict.setdefault(id(sender), _Slots())
        slots.refresh_slots.append(slot)

    def emit(self, sender: object, *args, key: str = '', **kwargs):
        '''
        触发 ``Signal``
        '''
        try:
            all_slots = self.slots[key]
        except KeyError:
            return

        for cls in sender.__class__.mro():
            try:
                slots = all_slots.self_slots_dict[self.get_cls_full_qualname(cls)]
            except KeyError:
                continue

            # pre-check
            if slots.self_refresh_slots_of_relation:
                from janim.items.relation import Relation

                if not isinstance(sender, Relation):
                    # TODO: i18n
                    raise TypeError(f'self_refresh_of_relation() 无法在类 {sender.__class__} 中使用， 只能在 Relation 及其子类中使用')

            # self_normal_slots
            for func in slots.self_normal_slots:
                func(sender, *args, **kwargs)

            # self_refresh_slots
            for func in slots.self_refresh_slots:
                sender.mark_refresh(func)

            # self_refresh_slots_of_relation
            for slot in slots.self_refresh_slots_of_relation:
                sender.mark_refresh(slot.func, recurse_up=slot.recurse_up, recurse_down=slot.recurse_down)

        try:
            slots = all_slots.slots_dict[id(sender)]
        except KeyError: ...
        else:
            # normal_slots
            for func in slots.normal_slots:
                func(*args, **kwargs)

            # refresh_slots
            for slot in slots.refresh_slots:
                slot.obj.mark_refresh(slot.func)
