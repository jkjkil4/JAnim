from functools import wraps
from typing import Any, TypeVar, Self, Callable, ParamSpec

P = ParamSpec('P')
R = TypeVar('R')


def register(func: Callable[P, R]) -> Callable[P, R]:
    '''
    用于在需要时才进行值的重新计算，提升性能

    当一个方法 self.func 被修饰后，会记忆 self.func 被调用后的返回值，
    并在之后的调用中直接返回该值，而不对 self.func 进行真正的调用；
    需要 ``self.mark_refresh_required(self.func)`` 才会对 self.func 重新调用以更新返回值

    例如，``Item`` 的 ``get_family`` 方法不会每次都进行计算
    只有在 ``add`` 或 ``remove`` 执行后，才会将 ``get_family`` 标记为需要更新
    使得在下次调用 ``get_family`` 才重新计算结果并返回

    可参考 ``test.items.item_test.ItemTest.test_refresh_required()``

    =====

    Used to recalculate values only when needed, improving performance.

    When a method self.func is decorated, it remembers the return value of self.func when called,
    and in subsequent calls, it directly returns that value without actually calling self.func;
    ``self.mark_refresh_required(self.func)`` is needed to re-call self.func to update the return value.

    For example, the ``get_family`` method of ``Item`` will not be calculated every time.
    It will only be marked as needing an update after the execution of ``add`` or ``remove``,
    making it recalculated and returning the result the next time ``get_family`` is called.

    另见 | See also:

    - ``test.utils.refresh_test.RefreshTest``.
    '''
    name = func.__name__

    @wraps(func)
    def wrapper(self: Refreshable, *args, **kwargs):
        data: RefreshData = self.refresh_data.setdefault(name, RefreshData())

        if data.is_required:
            data.stored = func(self, *args, **kwargs)
            data.is_required = False

        return data.stored

    return wrapper


class Refreshable:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.refresh_data: dict[str, RefreshData] = {}

    def mark_refresh(self, func: Callable | str) -> Self:
        '''
        标记指定的 ``func`` 需要进行更新

        Marks the specified ``func`` for an update.
        '''
        name = func.__name__ if isinstance(func, Callable) else func
        data: RefreshData = self.refresh_data.setdefault(name, RefreshData())
        data.is_required = True

        return self

    def reset_refresh(self) -> Self:
        self.refresh_data.clear()


class RefreshData:
    def __init__(self):
        self.is_required = True
        self.stored: Any = None
