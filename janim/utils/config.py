from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Self

from janim.typing import Vect
from janim.constants import LEFT, RIGHT, DOWN, UP

config_ctx_var: ContextVar[list[Config]] = ContextVar('config_ctx_var')


class _ConfigMeta(type):
    @property
    def get(self) -> Config | _ConfigGetter:
        return config_getter


@dataclass(kw_only=True)
class Config(metaclass=_ConfigMeta):
    fps: int = None

    aspect_ratio: float = None
    frame_height: float = None

    pixel_height: int = None
    pixel_width: int = None

    def __enter__(self) -> Self:
        lst = config_ctx_var.get()
        self.token = config_ctx_var.set([*lst, self])
        return self

    def __exit__(self, exc_type, exc_value, tb) -> None:
        config_ctx_var.reset(self.token)


class _ConfigGetter:
    def __getattr__(self, name: str):
        lst = config_ctx_var.get()
        for config in reversed(lst):
            value = getattr(config, name)
            if value is not None:
                return value

        return None

    @property
    def frame_width(self) -> float:
        return Config.get.aspect_ratio * Config.get.frame_height

    @property
    def frame_x_radius(self) -> float:
        return Config.get.frame_width / 2

    @property
    def frame_y_radius(self) -> float:
        return Config.get.frame_height / 2

    @property
    def left_side(self) -> Vect:
        return LEFT * Config.get.frame_x_radius

    @property
    def right_side(self) -> Vect:
        return RIGHT * Config.get.frame_x_radius

    @property
    def bottom(self) -> Vect:
        return DOWN * Config.get.frame_y_radius

    @property
    def top(self) -> Vect:
        return UP * Config.get.frame_y_radius


config_getter = _ConfigGetter()

default_config = Config(
    fps=60,
    aspect_ratio=16.0 / 9.0,
    frame_height=8.0,
    pixel_height=1080,
    pixel_width=1920
)
config_ctx_var.set([default_config])
