from typing import TYPE_CHECKING, NoReturn, Self, overload

from janim_backend.component import AttrField, AttrsStorage, CmptField, CmptsStorage  # noqa: F401

if TYPE_CHECKING:
    from janim.components.core.component import Component
    from janim.items.item import Item

    class AttrFieldDescriptor[T]:
        def __init__(self, field: AttrField): ...

        def on_modified[F](self, fn: F) -> F: ...

        @overload
        def __get__(self, obj: None, owner) -> Self: ...
        @overload
        def __get__(self, obj: Component, owner) -> T: ...

        def __get__(self, obj: Component | None, owner) -> Self | T: ...

        def __set__(self, obj: Component, value: T, /) -> None: ...

    class CmptInfo[T]:
        """
        在物件中声明组件信息

        例：

        .. code-block:: python

            class MyItem(Item):
                # 错误！
                # cmpt1 = MyCmpt()

                # 正确
                cmpt1 = CmptInfo(MyCmpt[Self])

                # 错误！
                # cmpt2 = MyCmptWithArgs(1)

                # 正确
                cmpt2 = CmptInfo(MyCmptWithArgs[Self], 1)
        """

        def __new__(cls, cls_: type[T], *args, **kwargs) -> Self: ...

        def create(self) -> Component: ...

        @overload
        def __get__(self, obj: None, owner) -> Self: ...
        @overload
        def __get__(self, obj: Item, owner) -> T: ...

        def __get__(self, obj, owner) -> Self | T: ...

        def __set__(self, obj, value, /) -> NoReturn: ...

else:
    from janim_backend.component import AttrFieldDescriptor, CmptInfo  # noqa: F401
