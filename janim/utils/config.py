from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Self

config_ctx_var: ContextVar[list[Config]] = ContextVar('config_ctx_var')


class _ConfigMeta(type):
    @property
    def get(self) -> Config:
        return config_getter


@dataclass(kw_only=True)
class Config(metaclass=_ConfigMeta):
    fps: int | None = None

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


config_getter = _ConfigGetter()

default_config = Config(fps=60)
config_ctx_var.set([default_config])

print(Config.get.fps)
