import functools
from typing import Any, Sequence, TypeVar, Generic, Self, Callable, ParamSpec, Concatenate, overload

from janim.utils.bind import Bind


CLS_FUNC_LIST_NAME = '__cls_refresh_func_list'
OBJ_DATA_NAME = '__refresh_data'

P = ParamSpec('P')
T = TypeVar('T')
R = TypeVar('R')


class register(Generic[T, P, R]):
    '''
    用于在需要时才进行值的重新计算，提升性能

    当一个方法 ``cls.func`` 被修饰后，会记忆 ``obj.func`` 被调用后的返回值，
    并在之后的调用中直接返回该值，而不对 ``obj.func`` 进行真正的调用；
    需要 ``obj.func.mark()`` 才会对 ``obj.func`` 重新调用以更新返回值

    注意：要使该修饰器生效，需要 ``cls`` 或者基类有使用 ``metaclass=RefreshMeta``

    可参考 ``test.utils.refresh_test.RefreshTest``

    =====

    Used to recalculate values only when needed, improving performance.

    When a method ``cls.func`` is decorated, it remembers the return value of ``obj.func`` when called,
    and in subsequent calls, it directly returns that value without actually calling ``obj.func``;
    ``obj.func.mark()`` is needed to re-call ``obj.func`` to update the return value.

    Note: To make this decorator work, ``cls`` or the base class needs to use ``metaclass=RefreshMeta``.

    See ``test.utils.refresh_test.RefreshTest``.
    '''
    def __init__(self, func: Callable[Concatenate[T, P], R] | property):
        self.func = func
        self.is_property = isinstance(self.func, property)
        functools.update_wrapper(self, func)

    def __get__(self, instance, owner) -> Callable[P, R] | Self:
        return self if instance is None else Bind(self, instance, owner)

    def __call__(self, obj: T, *args: P.args, **kwargs: P.kwargs) -> R:
        data: RefreshMeta.Data = obj.__dict__[OBJ_DATA_NAME][self.func]

        # 在需要时才进行重新求值
        # Re-evaluate only when needed
        if data.required:
            if self.is_property:
                data.stored = self.func.__get__(obj)
            else:
                data.stored = self.func(obj, *args, **kwargs)
            data.required = False

        return data.stored

    @overload
    def mark(self) -> None: ...

    def mark(self, obj: T) -> None:
        '''
        标记需要进行重新求值

        Marks the need for re-evaluation.
        '''
        data: RefreshMeta.Data = obj.__dict__[OBJ_DATA_NAME][self.func]
        data.required = True


def reset(obj) -> None:
    '''
    重置标记，使对象的所有被记录的方法都需要重新求值

    Reset the marks, causing all methods recorded for the object to be re-evaluated.
    '''
    for data in obj.__dict__[OBJ_DATA_NAME].values():
        data: RefreshMeta.Data
        data.required = True


class RefreshMeta(type):
    class Data:
        def __init__(self):
            self.required = True
            self.stored: Any = None

    def __new__(cls, classname: str, superclasses: Sequence[type], attributedict: dict):
        # 将该类中所有被 register 修饰的方法进行记录
        # Record all methods decorated with register in this class
        func_list = [
            attr
            for attr in attributedict.values()
            if isinstance(attr, register)
        ]
        attributedict[CLS_FUNC_LIST_NAME] = func_list

        return super().__new__(cls, classname, superclasses, attributedict)

    def __init__(self, classname: str, superclasses: Sequence[type], attributedict: dict):
        super().__init__(classname, superclasses, attributedict)

    def __call__(self, *args, **kwargs):
        obj = super().__call__(*args, **kwargs)

        # 遍历 mro，构建该对象需要重新求值的标记以及暂存数据
        # Traverse mro, build marks for re-evaluation and temporary storage data for this object
        obj.__dict__[OBJ_DATA_NAME] = {
            rgst.func: RefreshMeta.Data()
            for cls in self.mro()
            for rgst in cls.__dict__.get(CLS_FUNC_LIST_NAME, [])
        }

        return obj
