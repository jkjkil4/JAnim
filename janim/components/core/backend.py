from typing import TYPE_CHECKING, Self, overload

from janim_backend.component import AttrField, AttrsStorage

if TYPE_CHECKING:
    from janim.components.core.component import Component

    class AttrFieldDescriptor[T]:
        def __init__(self, field: AttrField): ...

        def on_modified[F](self, fn: F) -> F: ...

        @overload
        def __get__(self, obj: None, owner) -> Self: ...
        @overload
        def __get__(self, obj: Component, owner) -> T: ...

        def __get__(self, obj: Component | None, owner) -> Self | T: ...

        def __set__(self, obj: Component, value: T, /) -> None: ...

else:
    from janim_backend.component import AttrFieldDescriptor
