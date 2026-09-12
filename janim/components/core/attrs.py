from __future__ import annotations

import itertools as it
from functools import cache
from types import FunctionType
from typing import TYPE_CHECKING, Iterable, Literal, Self, overload

import numpy as np
from janim_backend.component import CmptField

from janim.utils.data import owned

if TYPE_CHECKING:
    from janim.components.core.component import Component


class ComponentAttrs:
    """
    用于在组件类中定义“组件属性”的辅助类
    """

    def __init__(self):
        self.fields: list[CmptField] = []

    def _register(self, field: CmptField) -> CmptFieldDescriptor:
        self.fields.append(field)
        return CmptFieldDescriptor(field)

    def int(self, default: int = 0) -> CmptFieldDescriptor[int]:
        """
        注册一个整数类型的属性
        """
        return self._register(CmptField.Int(default))

    def bool(self, default: bool = False) -> CmptFieldDescriptor[bool]:
        """
        注册一个布尔类型的属性
        """
        return self._register(CmptField.Bool(default))

    def float(self, default: float = 0.0) -> CmptFieldDescriptor[float]:
        """
        注册一个浮点数类型的属性
        """
        return self._register(CmptField.Float(default))

    def ndarray(self, default: np.ndarray) -> CmptFieldDescriptor[np.ndarray]:
        """
        注册一个 ``np.ndarray`` 类型的属性

        特点：

        - 会保证后续设置的 NumPy 数组仍然和初始数组拥有相同的 ``dtype``
        - 会保证获取的 NumPy 输入是只读的（可通过 ``.copy()`` 获取可写的拷贝）
        """
        return self._register(
            CmptField.NDArray(
                default,
                self._ndarray_setter_for_dtype(default.dtype),  # type: ignore
            )
        )

    @staticmethod
    @cache
    def _ndarray_setter_for_dtype(dtype):
        def _ndarray_setter(array: np.ndarray | owned[np.ndarray]) -> np.ndarray:
            # 当传入的是 owned_array 时，不需要使用 np.array 产生拷贝，可以直接使用
            if array.__class__ is owned:
                inner = array.inner  # type: ignore
                if inner.dtype == dtype:
                    inner.setflags(write=False)
                    return inner
                # dtype 不同时，无法直接使用，替换 array 回退到拷贝的逻辑
                array = inner
            inner = np.array(array, dtype=dtype)
            inner.setflags(write=False)
            return inner

        return _ndarray_setter

    def owned_object[T](self, _: type[T]) -> CmptFieldDescriptor[T | None]:
        """
        拥有唯一所有权的对象

        初始值为 ``None``，设置的具体对象不会随着拷贝转移，从而不会意外产生多份引用

        .. note::

            传入参数仅用作类型注解
        """
        return self._register(CmptField.OwnedObject())

    @overload
    def direct_object[T](
        self, _: type[T], *, nullable: Literal[False], copyer: FunctionType | None = None
    ) -> CmptFieldDescriptor[T]: ...
    @overload
    def direct_object[T](
        self, _: type[T], *, nullable: Literal[True], copyer: FunctionType | None = None
    ) -> CmptFieldDescriptor[T | None]: ...

    def direct_object[T](
        self, _: type[T], *, nullable: bool, copyer: FunctionType | None = None
    ) -> CmptFieldDescriptor[T] | CmptFieldDescriptor[T | None]:
        """
        忽略 ``setter`` / ``getter`` 的直接访问的对象

        若 ``copyer=None``，则在拷贝出的各个实例间共享对象，否则使用 ``copyer`` 进行拷贝

        初始值为 ``None``，设置的具体对象允许随着拷贝转移，共享引用

        .. note::

            传入参数仅用作类型注解

        .. warning::

            实例的初始值会是 ``None``，但对于 ``nullable=False`` 的情况而言，为了使用方便，类型注解省略了 ``None`` 的部分，
            因此务必保证在构建时初始化该值，从而与类型注解一致
        """
        return self._register(CmptField.DirectObject(copyer))

    @staticmethod
    def merge(attrs_list: Iterable[ComponentAttrs]) -> ComponentAttrs:
        """
        合并多个 :class:`ComponentAttrs` 的组件属性
        """
        merged = ComponentAttrs()
        merged.fields = list(it.chain.from_iterable(attrs.fields for attrs in attrs_list))
        return merged


if TYPE_CHECKING:

    class CmptFieldDescriptor[T]:
        def __init__(self, field: CmptField): ...

        def on_modified[F](self, fn: F) -> F: ...

        @overload
        def __get__(self, obj: None, owner) -> Self: ...
        @overload
        def __get__(self, obj: Component, owner) -> T: ...

        def __get__(self, obj: Component | None, owner) -> Self | T: ...

        def __set__(self, obj: Component, value: T, /) -> None: ...

else:
    from janim_backend.component import CmptFieldDescriptor
