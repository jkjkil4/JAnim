from typing import TYPE_CHECKING, Literal, Self

import numpy as np

from janim.components.mark import Cmpt_Mark
from janim.typing import Vect


class Cmpt_Mark_TextCharImpl[ItemT](Cmpt_Mark[ItemT], impl=True):
    names = ['orig', 'right', 'up', 'advance']

    if TYPE_CHECKING:

        def get(  # type: ignore
            self,
            index: int | Literal['orig', 'right', 'up', 'advance'] = 0,
        ) -> np.ndarray: ...

        def set(  # type: ignore
            self,
            point: Vect,
            index: int | Literal['orig', 'right', 'up', 'advance'] = 0,
            *,
            root_only: bool = False,
        ) -> Self: ...


class Cmpt_Mark_TextLineImpl[ItemT](Cmpt_Mark[ItemT], impl=True):
    names = ['orig', 'right', 'up']

    if TYPE_CHECKING:

        def get(  # type: ignore
            self,
            index: int | Literal['orig', 'right', 'up'] = 0,
        ) -> np.ndarray: ...

        def set(  # type: ignore
            self,
            point: Vect,
            index: int | Literal['orig', 'right', 'up'] = 0,
            *,
            root_only: bool = False,
        ) -> Self: ...
