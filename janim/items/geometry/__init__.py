from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from janim.items.item import _ItemMeta
from janim.items.vitem import VItem
from janim.locale import get_translator

_ = get_translator('janim.items.geometry.__init__')


class _PreInitReshapeDict(_ItemMeta):
    """
    用于在 ``__init__`` 前先创建 ``reshape_params``，
    因为在子类还未进入 ``GeometryShape.__init__`` 的时候就要用到，
    等 ``GeometryShape.__init__`` 中再创建就来不及了
    """
    def __call__(cls, *args, **kwargs):
        obj = cls.__new__(cls, *args, **kwargs)
        setattr(obj, 'reshape_params', {})     # 名字与 ``GeometryShape.__init__`` 中的类型注解一致
        cls.__init__(obj, *args, **kwargs)
        return obj


class GeometryShape(VItem, metaclass=_PreInitReshapeDict):
    """
    几何物件的基类

    提供了 :meth:`reshape` 通用方法与相关辅助函数

    其中：

    -   ``_reshape`` 用于最底层的几何物件实现

    -   ``reshape`` 用于给子类可以覆盖，可以用来改变外部的顶层行为

        （例如 :class:`~.Polygon` 默认是使用 ``verts`` 和 ``close_path`` 构造，
        而 :class:`~.RegularPolygon` 覆盖 ``reshape`` 改为 ``n``、``radius`` 和 ``start_angle`` 构造）

    如果需要另行获取已记忆的参数值，比如获取 :class:`~.Star` 的 ``start_angle``，
    可以直接使用例如 ``.reshape_params['start_angle']`` 的方式
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 已被 metaclass 创建，所以仅用于类型注解
        if TYPE_CHECKING:
            self.reshape_params: dict[str, Any] = {}

    def _reshape(self):
        raise NotImplementedError(
            _('{cls_name} does not implement `{method_name}()`')
            .format(cls_name=self.__class__.__name__, method_name='_reshape')
        )

    def reshape(self) -> Self:
        """
        类似传递给 ``__init__`` 的参数，重新设置几何物件的形状

        可以缺省部分值，表示使用先前的
        """
        raise NotImplementedError(
            _('{cls_name} does not implement `{method_name}()`')
            .format(cls_name=self.__class__.__name__, method_name='reshape')
        )

    def _reshape_memorize(self, **kwargs):
        """
        用于记忆参数值
        """
        resolved = []

        # 因为现在的 Python 版本中 dict 遍历保持构造顺序，所以可以 append，返回忽略 keys 的 resolved 列表
        for key, value in kwargs.items():
            if value is None:
                resolved.append(self.reshape_params[key])
            else:
                self.reshape_params[key] = value
                resolved.append(value)

        return resolved

    def copy(self, *, root_only: bool = False) -> Self:
        copy_item = super().copy(root_only=root_only)
        copy_item.reshape_params = self.reshape_params.copy()
        return copy_item

    def become(self, other: GeometryShape) -> Self:
        super().become(self, other)
        self.reshape_params = other.reshape_params.copy()
        return self
