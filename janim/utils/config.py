from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Self

import psutil
from colour import Color

from janim.typing import Vect
from janim.constants import LEFT, RIGHT, DOWN, UP

config_ctx_var: ContextVar[list[Config]] = ContextVar('config_ctx_var')


class _ConfigMeta(type):
    @property
    def get(self) -> Config | ConfigGetter:
        return config_getter


@dataclass(kw_only=True)
class Config(metaclass=_ConfigMeta):
    '''配置

    使用 ``Config.get.xxx`` 得到属性，例如 ``Config.get.fps`` 则得到当前设置的帧率

    使用 ``with Config(key=value):`` 在指定的配置下执行内容，例如：

    .. code-block:: python

        print(Config.get.fps)   # 60

        with Config(fps=120, pixel_width=1280):
            print(Config.get.fps)           # 120
            print(Config.get.pixel_width)   # 1280
            print(Config.get.pixel_height)  # 1080

    其中没有设置的属性则采用默认设置 :py:obj:`~.default_config`
    '''
    fps: int = None
    preview_fps: int = None
    anti_alias_width: float = None

    aspect_ratio: float = None
    frame_height: float = None

    pixel_height: int = None
    pixel_width: int = None
    background_color: Color = None

    wnd_pos: str = None
    wnd_monitor: int = None

    ffmpeg_bin: str = None
    output_dir: str = None

    def __enter__(self) -> Self:
        lst = config_ctx_var.get()
        self.token = config_ctx_var.set([*lst, self])
        return self

    def __exit__(self, exc_type, exc_value, tb) -> None:
        config_ctx_var.reset(self.token)


def is_power_plugged() -> bool:
    battery = psutil.sensors_battery()
    return battery is None or battery.power_plugged


default_config = Config(
    fps=60,
    preview_fps=60 if is_power_plugged() else 30,
    anti_alias_width=0.015,

    aspect_ratio=16.0 / 9.0,
    frame_height=8.0,

    pixel_height=1080,
    pixel_width=1920,
    background_color=Color('#000000'),

    wnd_pos='UR',
    wnd_monitor=0,

    ffmpeg_bin='ffmpeg',
    output_dir='videos',
)
'''
默认配置

其中 ``preview_fps`` 在接入电源时是 60，未接入时是 30
'''

config_ctx_var.set([default_config])


class ConfigGetter:
    '''
    与配置数据相关联的数据的获取

    请仍然使用 ``Config.get.xxx`` 来获取定义在该类中的内容
    '''
    def __getattr__(self, name: str) -> None:
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


config_getter = ConfigGetter()
