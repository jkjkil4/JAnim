from __future__ import annotations

import copy
import numbers
import types
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Callable, Self

import numpy as np

from janim.components.component import CmptInfo, Component
from janim.exception import JAnimException
from janim.locale.i18n import get_translator
from janim.logger import log
from janim.typing import SupportsTracking
from janim.utils.bezier import interpolate
from janim.utils.data import AlignedData

_ = get_translator('janim.components.data')

type ClassInfo = type | types.UnionType | tuple[ClassInfo, ...]
type CopyFn[T] = Callable[[T], T]                   # (a) -> copied
type NotChangedFn[T] = Callable[[T, T], bool]       # (a, b) -> is_not_changed
type InterpolateFn[T] = Callable[[T, T, float], T]  # (a, b, alpha) -> interpolated

type UpdateFn[T] = Callable[[T, T], T]              # (state, patch) -> now

type _Funcs[T] = tuple[CopyFn[T], NotChangedFn[T], InterpolateFn[T]]

_default_funcs: _Funcs = (copy.copy, lambda a, b: a == b, interpolate)


class Cmpt_Data[ItemT, T](Component[ItemT]):
    """
    详见 :class:`~.ValueTracker`
    """
    def __init__(self):
        self.copy_func: CopyFn[T] | None = None
        self.not_changed_func: NotChangedFn[T] | None = None
        self.interpolate_func: InterpolateFn[T] | None = None

    def copy(self) -> Self:
        cmpt_copy = super().copy()

        with self._cls_name():
            # compatibility
            fn = self.copy_func or Cmpt_Data.copy_for_value
            cmpt_copy.set(fn(self.value))

        return cmpt_copy

    def become(self, other: Cmpt_Data) -> Self:
        with self._cls_name():
            # compatibility
            fn = other.copy_func or Cmpt_Data.copy_for_value
            self.set(fn(other.value))

        return self

    def not_changed(self, other: Cmpt_Data) -> bool:
        with self._cls_name():
            # compatibility
            fn = self.not_changed_func or Cmpt_Data.check_not_changed_for_value
            return fn(self.value, other.value)

    @classmethod
    def align_for_interpolate(
        cls, cmpt1: Cmpt_Data, cmpt2: Cmpt_Data
    ) -> AlignedData[Self]:
        cmpt1_copy = cmpt1.copy()
        cmpt2_copy = cmpt2.copy()
        return AlignedData(cmpt1_copy, cmpt2_copy, cmpt1_copy.copy())

    def interpolate(
        self, cmpt1: Cmpt_Data, cmpt2: Cmpt_Data, alpha: float, *, path_func=None
    ) -> None:
        with self._cls_name():
            # compatibility
            nc_fn = self.not_changed_func or Cmpt_Data.check_not_changed_for_value

            nc_cmpt1_cmpt2 = nc_fn(cmpt1.value, cmpt2.value)
            nc_cmpt1_self = nc_fn(cmpt1.value, self.value)

            if not nc_cmpt1_cmpt2 or not nc_cmpt1_self:
                if nc_cmpt1_cmpt2:
                    # compatibility
                    fn = cmpt1.copy_func or Cmpt_Data.copy_for_value
                    self.set(fn(cmpt1.value))
                else:
                    # compatibility
                    fn = cmpt1.interpolate_func or Cmpt_Data.interpolate_for_value
                    self.set(fn(cmpt1.value, cmpt2.value, alpha))

    def set(self, value: T) -> Self:
        """设置当前值"""
        self.value = value
        return self

    def get(self) -> T:
        """得到当前值"""
        return self.value

    def increment(self, value: T) -> Self:
        """将值增加 ``value``，只对一些简单的类型有效"""
        self.value += value
        return self

    def update(self, patch: T) -> Self:
        """基于字典的部分项更新原有字典"""
        with self._cls_name():
            self.value = Cmpt_Data.update_for_value(self.value, patch)
        return self

    def set_func(
        self,
        copy_func: CopyFn[T] | None = None,
        not_changed_func: NotChangedFn[T] | None = None,
        interpolate_func: InterpolateFn[T] | None = None,
    ) -> Self:
        if any(x is not None for x in (copy_func, not_changed_func, interpolate_func)):
            from janim.utils.deprecation import is_removed
            if is_removed((4, 3)):
                raise RuntimeError(
                    'Compatibility with previous ValueTracker APIs ended in JAnim 4.3'
                )
            else:
                log.warning(
                    _('ValueTracker was refactored in 4.0 and no longer directly accepts '
                      'copy_func, not_changed_func, or interpolate_func.\n'
                      'Use Cmpt_Data.register_funcs to register handlers for your types, '
                      'See documentation page '
                      'https://janim.readthedocs.io/en/latest/tutorials/value_tracker.html '
                      'for details.\n'
                      'Compatibility with the previous approach ends in JAnim 4.3')
                )

        if copy_func is not None:
            self.copy_func = copy_func
        if not_changed_func is not None:
            self.not_changed_func = not_changed_func
        if interpolate_func is not None:
            self.interpolate_func = interpolate_func
        return self

    # region helper class definition

    class IsinstanceResolver[T]:
        def __init__(self):
            self._isinstance_checks: list[tuple[ClassInfo, T]] = []
            self._resolve_cache: dict[type, T] = {}

        def register(self, isinstance_check: ClassInfo, resolved: T) -> None:
            self._isinstance_checks.insert(0, (isinstance_check, resolved))

        def update_cache(self, value, resolved: T) -> None:
            self._resolve_cache[value.__class__] = resolved

        def resolve(self, value) -> T | None:
            resolved = self._resolve_cache.get(value.__class__, None)
            if resolved is not None:
                return resolved

            for check, resolved in self._isinstance_checks:
                if isinstance(value, check):
                    self._resolve_cache[value.__class__] = resolved
                    return resolved

            return None

        def clear_cache(self) -> None:
            self._resolve_cache.clear()

    _funcs_resolver = IsinstanceResolver[_Funcs]()
    _update_func_resolver = IsinstanceResolver[UpdateFn | None]()

    @contextmanager
    def _cls_name(self):
        if self.bind is None:
            yield
            return

        token = TrackerShapeError.source_cls_name_ctx.set(self.bind.at_item.__class__.__name__)
        try:
            yield
        finally:
            TrackerShapeError.source_cls_name_ctx.reset(token)

    # endregion

    # region funcs

    @staticmethod
    def _clear_resolve_cache() -> None:
        Cmpt_Data._funcs_resolver.clear_cache()
        Cmpt_Data._update_func_resolver.clear_cache()

    @staticmethod
    def register_funcs[T](
        isinstance_check: ClassInfo,

        copy_func: CopyFn[T],
        not_changed_func: NotChangedFn[T],
        interpolate_func: InterpolateFn[T]
    ) -> None:
        funcs = (copy_func, not_changed_func, interpolate_func)
        Cmpt_Data._funcs_resolver.register(isinstance_check, funcs)

    @staticmethod
    def copy_for_value[T](value: T) -> T:
        fn = Cmpt_Data._resolve_funcs(value)[0]
        return fn(value)

    @staticmethod
    def check_not_changed_for_value[T](a: T, b: T) -> bool:
        fn = Cmpt_Data._resolve_funcs(a)[1]
        return fn(a, b)

    @staticmethod
    def interpolate_for_value[T](a: T, b: T, alpha: float) -> T:
        fn = Cmpt_Data._resolve_funcs(a)[2]
        return fn(a, b, alpha)

    @staticmethod
    def _resolve_funcs[T](value: T) -> _Funcs[T]:
        funcs = Cmpt_Data._funcs_resolver.resolve(value)
        if funcs is not None:
            return funcs

        if isinstance(value, SupportsTracking):
            funcs = (
                value.__class__.copy,
                value.__class__.not_changed,
                value.__class__.interpolate
            )
            Cmpt_Data._funcs_resolver.update_cache(value, funcs)
            return funcs

        log.warning(
            _('Type "{type}" has no registered function for tracking, '
              'the default function will be used\n'
              'See documentation page '
              'https://janim.readthedocs.io/en/latest/tutorials/value_tracker.html '
              'for details')
            .format(type=value.__class__.__name__)
        )
        Cmpt_Data._funcs_resolver.update_cache(value, _default_funcs)
        return _default_funcs

    # endregion

    # region update_func

    @staticmethod
    def register_update_func[T](
        isinstance_check: ClassInfo,
        update_func: UpdateFn[T]
    ) -> None:
        Cmpt_Data._update_func_resolver.register(isinstance_check, update_func)

    @staticmethod
    def update_for_value[T](state: T, patch: T) -> T:
        func: UpdateFn[T] | None = Cmpt_Data._update_func_resolver.resolve(state)
        if func is None:
            Cmpt_Data._update_func_resolver.update_cache(state, None)
            return patch
        return func(state, patch)

    # endregion


class CustomData[ItemT, T](CmptInfo[Cmpt_Data[ItemT, T]]):
    """
    用于例如

    .. code-block:: python

        class PhysicalBlock(Square):
            physic = CustomData()

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                self.physic.set({
                    'speed': ORIGIN,    # 默认静止
                    'accel': ORIGIN,    # 并且没有加速度
                })

    可以完善类型注解

    .. code-block:: python

        class PhysicData(TypedDict):
            speed: np.ndarray
            accel: np.ndarray

        class PhysicalBlock(Square):
            physic = CustomData[Self, PhysicData]()

            ...
    """
    def __init__(self):
        super().__init__(Cmpt_Data)


# region register

def _format_keys(keys: set) -> str:
    return '[' + ', '.join(sorted((f'"{k}"' for k in keys))) + ']'


class TrackerShapeError(JAnimException):
    def __init__(self, message: str, *, missing: set | None = None, extra: set | None = None):
        parts: list[str] = [message]
        if missing:
            parts.append(_('missing keys: {keys}').format(keys=_format_keys(missing)))
        if extra:
            parts.append(_('extra keys: {keys}').format(keys=_format_keys(extra)))
        super().__init__('; '.join(parts))
        self.missing = missing or set()
        self.extra = extra or set()

    source_cls_name_ctx: ContextVar[str] = ContextVar('config_ctx_var')     # 透传来源类名，用于报错时的类名显示

    @staticmethod
    def get_source_cls_name() -> str:
        return TrackerShapeError.source_cls_name_ctx.get('ValueTracker?')


def _assert_seq_len_match[T: Callable](fn: T) -> T:
    def wrapper(a, b, *args):
        len_a = len(a)
        len_b = len(b)
        if len_a != len_b:
            cls_name = TrackerShapeError.get_source_cls_name()
            raise TrackerShapeError(
                _('Existing sequence and new value must have the same length for {cls_name}; '
                  'existing length {len_a}, new length {len_b}')
                .format(cls_name=cls_name, len_a=len_a, len_b=len_b)
            )
        return fn(a, b, *args)
    return wrapper


def _assert_dict_keys_match[T: Callable](fn: T) -> T:
    def wrapper(a: dict, b: dict, *args):
        a_keys = set(a.keys())
        b_keys = set(b.keys())
        missing = a_keys - b_keys
        extra = b_keys - a_keys
        if missing or extra:
            cls_name = TrackerShapeError.get_source_cls_name()
            raise TrackerShapeError(
                _('Existing dictionary and new value must share the same keys for {cls_name}')
                .format(cls_name=cls_name),

                missing=missing,
                extra=extra
            )
        return fn(a, b, *args)
    return wrapper


Cmpt_Data.register_funcs(
    tuple,
    lambda a: tuple(Cmpt_Data.copy_for_value(x) for x in a),
    _assert_seq_len_match(
        lambda a, b: all(
            Cmpt_Data.check_not_changed_for_value(x, y) for x, y in zip(a, b, strict=True)
        )
    ),
    _assert_seq_len_match(
        lambda a, b, alpha: tuple(
            Cmpt_Data.interpolate_for_value(x, y, alpha) for x, y in zip(a, b, strict=True)
        )
    )
)

Cmpt_Data.register_funcs(
    list,
    lambda a: [Cmpt_Data.copy_for_value(x) for x in a],
    _assert_seq_len_match(
        lambda a, b: all(
            Cmpt_Data.check_not_changed_for_value(x, y) for x, y in zip(a, b, strict=True)
        )
    ),
    _assert_seq_len_match(
        lambda a, b, alpha: [
            Cmpt_Data.interpolate_for_value(x, y, alpha) for x, y in zip(a, b, strict=True)
        ]
    )
)

Cmpt_Data.register_funcs(   # noqa: E305
    dict,
    lambda a: {k: Cmpt_Data.copy_for_value(v) for k, v in a.items()},
    _assert_dict_keys_match(
        lambda a, b: all(
            Cmpt_Data.check_not_changed_for_value(a[k], b[k]) for k in a.keys()
        )
    ),
    _assert_dict_keys_match(
        lambda a, b, alpha: {
            k: Cmpt_Data.interpolate_for_value(a[k], b[k], alpha) for k in a.keys()
        }
    )
)

def _dict_update_func(state: dict, patch: dict) -> dict:    # noqa: E302
    extra = set(patch.keys()) - set(state.keys())
    if extra:
        raise TrackerShapeError(
            _('Update contains keys not present in current value'),
            extra=extra
        )
    now = state.copy()
    for key, value in patch.items():
        now[key] = Cmpt_Data.update_for_value(state[key], value)
    return now

Cmpt_Data.register_update_func(     # noqa: E305
    dict,
    _dict_update_func
)

Cmpt_Data.register_funcs(   # 只是对于短 numpy 数组的简单实现，对于大规模数组，应考虑 Cmpt_Points
    np.ndarray,
    np.ndarray.copy,
    lambda a, b: np.all(a == b),
    interpolate
)

# 设计上，越后面的越早判断，因此将最常见的 numbers 放在最后 register

Cmpt_Data.register_funcs(
    numbers.Number,
    *_default_funcs
)

Cmpt_Data.register_funcs(
    bool,
    copy.copy,
    lambda a, b: a == b,
    lambda a, b, alpha: interpolate(a, b, alpha) >= 0.5
)

# endregion
