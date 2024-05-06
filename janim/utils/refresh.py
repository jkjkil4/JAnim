from collections import defaultdict
from functools import partial, wraps
from typing import Any, Callable, Self, overload


@overload
def register[T](func=None, /, *, fallback_check: Callable[[Any], bool]) -> Callable[[T], T]: ...
@overload
def register[T](func: T) -> T: ...


def register(func=None, /, *, fallback_check=None):
    '''
    用于在需要时才进行值的重新计算，提升性能

    当一个方法 self.func 被修饰后，会记忆 self.func 被调用后的返回值，
    并在之后的调用中直接返回该值，而不对 self.func 进行真正的调用；
    需要 ``self.mark_refresh_required(self.func)`` 才会对 self.func 重新调用以更新返回值

    例如，``Item`` 的 ``get_family`` 方法不会每次都进行计算
    只有在 ``add`` 或 ``remove`` 执行后，才会将 ``get_family`` 标记为需要更新
    使得在下次调用 ``get_family`` 才重新计算结果并返回

    如果指定了 ``fallback_check`` 函数，则每次都会调用该函数，
    如果返回值为 True，则忽略缓存，并且得到的结果不记录到缓存中

    另见：

    - ``test.utils.test_refresh.RefreshTest``.
    '''
    if func is None:
        # Called with @register()
        return partial(_register, fallback_check=fallback_check)

    # Called with @register
    return _register(func)


def _register[T](
    func: T,
    *,
    fallback_check: Callable[[Any], bool] | None = None
) -> T:
    name = func.__name__

    @wraps(func)
    def wrapper(self: Refreshable, *args, **kwargs):
        if fallback_check is not None and fallback_check(self):
            return func(self, *args, **kwargs)

        data = self.refresh_data[name]

        if data.is_required:
            data.stored = func(self, *args, **kwargs)
            data.is_required = False

        return data.stored

    return wrapper


class Refreshable:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.refresh_data: defaultdict[str, RefreshData] = defaultdict(RefreshData)

    def mark_refresh(self, func: Callable | str) -> Self:
        '''
        标记指定的 ``func`` 需要进行更新
        '''
        name = func.__name__ if callable(func) else func
        data: RefreshData = self.refresh_data[name]
        data.is_required = True

        return self

    def reset_refresh(self) -> Self:
        self.refresh_data = defaultdict(RefreshData)


class RefreshData:
    def __init__(self):
        self.is_required = True
        self.stored: Any = None
