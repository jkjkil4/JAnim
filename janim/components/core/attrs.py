from __future__ import annotations

import itertools as it
from functools import cache
from types import FunctionType
from typing import Iterable, Literal, overload

import numpy as np

from janim.components.core.backend import AttrField, AttrFieldDescriptor
from janim.utils.data import owned


class ComponentAttrs:
    """
    用于在组件类中定义“组件属性”的辅助类
    """

    def __init__(self):
        self.fields: list[AttrField] = []

    def _register(self, field: AttrField) -> AttrFieldDescriptor:
        self.fields.append(field)
        return AttrFieldDescriptor(field)

    def int(self, default: int = 0) -> AttrFieldDescriptor[int]:
        """
        注册一个整数类型的属性
        """
        return self._register(AttrField.Int(default))

    def bool(self, default: bool = False) -> AttrFieldDescriptor[bool]:
        """
        注册一个布尔类型的属性
        """
        return self._register(AttrField.Bool(default))

    def float(self, default: float = 0.0) -> AttrFieldDescriptor[float]:
        """
        注册一个浮点数类型的属性
        """
        return self._register(AttrField.Float(default))

    def ndarray(self, default: np.ndarray) -> AttrFieldDescriptor[np.ndarray]:
        """
        注册一个 ``np.ndarray`` 类型的属性

        特点：

        - 会保证后续设置的 NumPy 数组仍然和初始数组拥有相同的 ``dtype``
        - 会保证获取的 NumPy 输入是只读的（可通过 ``.copy()`` 获取可写的拷贝）
        """
        return self._register(
            AttrField.NDArray(
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

    def owned_object[T](self, _: type[T]) -> AttrFieldDescriptor[T | None]:
        """
        拥有唯一所有权的对象，且在 ``_become`` 中不会被替换

        初始值为 ``None``，设置的具体对象不会随着拷贝转移，从而不会意外产生多份引用

        .. note::

            传入的首个参数仅用作类型注解
        """
        return self._register(AttrField.OwnedObject())

    @overload
    def direct_object[T](
        self, _: type[T], *, nullable: Literal[False], copyer: FunctionType | None = None
    ) -> AttrFieldDescriptor[T]: ...
    @overload
    def direct_object[T](
        self, _: type[T], *, nullable: Literal[True], copyer: FunctionType | None = None
    ) -> AttrFieldDescriptor[T | None]: ...

    def direct_object[T](
        self, _: type[T], *, nullable: bool, copyer: FunctionType | None = None
    ) -> AttrFieldDescriptor[T] | AttrFieldDescriptor[T | None]:
        """
        忽略 ``setter`` / ``getter`` 的直接访问的对象

        若 ``copyer=None``，则在拷贝出的各个实例间共享对象，否则使用 ``copyer`` 进行拷贝

        初始值为 ``None``，设置的具体对象允许随着拷贝转移，共享引用

        .. note::

            传入的首个参数仅用作类型注解

        .. warning::

            实例的初始值会是 ``None``，但对于 ``nullable=False`` 的情况而言，为了使用方便，类型注解省略了 ``None`` 的部分，
            因此务必保证在构建时初始化该值，从而与类型注解一致
        """
        return self._register(AttrField.DirectObject(copyer))

    @staticmethod
    def merge(attrs_list: Iterable[ComponentAttrs]) -> ComponentAttrs:
        """
        合并多个 :class:`ComponentAttrs` 的组件属性
        """
        merged = ComponentAttrs()
        merged.fields = list(it.chain.from_iterable(attrs.fields for attrs in attrs_list))
        return merged
