from __future__ import annotations

import os
import tempfile
from contextvars import ContextVar
from functools import partial
from typing import Generator, Iterable, Self

import attrs
import psutil
from colour import Color

from janim.constants import DOWN, LEFT, RIGHT, UP
from janim.locale.i18n import get_local_strings
from janim.typing import Vect
from janim.utils.file_ops import guarantee_existence

_ = get_local_strings('config')

config_ctx_var: ContextVar[list[Config]] = ContextVar('config_ctx_var')


def optional_type_validator(type, typename: str):
    def validator(inst, attr: attrs.Attribute, value):
        if value is None:
            return
        if not isinstance(value, type):
            raise TypeError(
                _("{attrname}={value!r} is incompatible with type {typename}")
                .format(attrname=attr.name, typename=typename, value=value)
            )

    return validator


_field = partial(attrs.field, default=None)
_opt_int_validator = optional_type_validator(int, 'int')
_opt_float_validator = optional_type_validator((int, float), 'float')


class _ConfigMeta(type):
    @property
    def get(self) -> Config | ConfigGetter:
        return config_getter


@attrs.define(kw_only=True, slots=False)
class Config(metaclass=_ConfigMeta):
    '''配置

    大部分的参数不作说明，稍微说明一下这些参数：

    - ``fps``: 输出视频时的帧率
    - ``preview_fps``: 在预览窗口时的帧率
    - 在代码内设置 ``background_color`` 时，不能使用 ``background_color='#RRGGBB'``，应使用 ``background_color=Color('#RRGGBB')``
    - ``output_dir`` 以 ``:`` 开头时，表示相对于 ``.py`` 文件的路径，例如 ``output_dir=':/videos'``

    基础用法
    ------------

    使用 ``Config.get.xxx`` 得到属性，例如 ``Config.get.fps`` 则得到当前设置的帧率

    使用 ``with Config(key=value):`` 在指定的配置下执行内容，例如：

    .. code-block:: python

        print(Config.get.fps)   # 60

        with Config(fps=120, pixel_width=1280):
            print(Config.get.fps)           # 120
            print(Config.get.pixel_width)   # 1280
            print(Config.get.pixel_height)  # 1080

    其中没有设置的属性则采用默认设置 :py:obj:`~.default_config`

    全局配置
    ------------

    在使用命令行参数时，使用 ``-c 配置名 值`` 可以修改全局配置，设定的全局配置会覆盖其它配置

    例如 ``janim write your_file.py YourTimeline -c fps 120`` 可以将渲染帧率设置为 120

    可以同时修改多个，例如：

    .. code-block:: sh

        janim write your_file.py YourTimeline -c fps 120 -c output_dir custom_dir

    这个命令会将动画以 120 的帧率输出到 ``custom_dir`` 这个指定的文件夹中

    时间轴配置
    ------------

    定义类变量 ``CONFIG``，例如：

    .. code-block:: python

        class YourTimeline(Timeline):
            CONFIG = Config(
                fps=120,
                preview_fps=30
            )

            def construct(self) -> None:
                ...

    这样则是设定这个时间轴的配置，渲染时帧率 120，预览（显示为窗口）时帧率 30

    另见：:py:obj:`~.Timeline.CONFIG`
    '''
    fps: int = _field(validator=_opt_int_validator)
    preview_fps: int = _field(validator=_opt_int_validator)
    anti_alias_width: float = _field(validator=_opt_float_validator)

    frame_height: float = _field(validator=_opt_float_validator)
    frame_width: float = _field(validator=_opt_float_validator)

    pixel_height: int = _field(validator=_opt_int_validator)
    pixel_width: int = _field(validator=_opt_int_validator)
    background_color: Color = _field(validator=optional_type_validator(Color, 'Color'))
    font: str | Iterable[str] = None
    subtitle_font: str | Iterable[str] = None

    audio_framerate: int = _field(validator=_opt_int_validator)
    audio_channels: int = _field(validator=_opt_int_validator)

    wnd_pos: str = None
    wnd_monitor: int = _field(validator=_opt_int_validator)

    typst_bin: str = None
    typst_shared_preamble: str = None
    typst_text_preamble: str = None
    typst_math_preamble: str = None

    ffmpeg_bin: str = None
    ffprobe_bin: str = None
    output_dir: str = None
    temp_dir: str = None
    asset_dir: str | list[str] = None

    client_search_port: int = _field(validator=_opt_int_validator)

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

    frame_height=8.0,
    frame_width=16.0 / 9.0 * 8.0,   # aspect_ratio(16/9) * frame_height

    pixel_height=1080,
    pixel_width=1920,
    background_color=Color('#000000'),
    font='Consolas',
    subtitle_font='',

    audio_framerate=44100,
    audio_channels=2,

    wnd_pos='OR',
    wnd_monitor=0,

    typst_bin='typst',
    typst_shared_preamble='',
    typst_text_preamble='',
    typst_math_preamble='',

    ffmpeg_bin='ffmpeg',
    ffprobe_bin='ffprobe',
    output_dir='videos',
    temp_dir=guarantee_existence(os.path.join(tempfile.gettempdir(), 'janim')),
    asset_dir='',

    client_search_port=40565
)
'''
默认配置

其中：

- ``preview_fps`` 在接入电源时是 60，未接入时是 30
- ``temp_dir`` 由操作系统决定
'''

cli_config = Config()
'''
命令行配置

会被命令行 ``--config`` 参数自动修改
'''

config_ctx_var.set([default_config])


class ConfigGetter:
    '''
    与配置数据相关联的数据的获取

    请仍然使用 ``Config.get.xxx`` 来获取定义在该类中的内容
    '''
    def __init__(self, config_ctx: list[Config] | None = None):
        self.config_ctx = config_ctx

    def walk(self) -> Generator[Config, None, None]:
        yield cli_config
        yield from reversed(self.config_ctx or config_ctx_var.get())

    def __getattr__(self, name: str) -> None:
        for config in self.walk():
            value = getattr(config, name)
            if value is not None:
                return value

        return None

    @property
    def aspect_ratio(self) -> float:
        return self.frame_width / self.frame_height

    @property
    def frame_x_radius(self) -> float:
        return self.frame_width / 2

    @property
    def frame_y_radius(self) -> float:
        return self.frame_height / 2

    @property
    def pixel_to_frame_ratio(self) -> float:
        return self.frame_width / self.pixel_width

    @property
    def default_pixel_to_frame_ratio(self) -> float:
        return self.frame_width / default_config.pixel_width

    @property
    def left_side(self) -> Vect:
        return LEFT * self.frame_x_radius

    @property
    def right_side(self) -> Vect:
        return RIGHT * self.frame_x_radius

    @property
    def bottom(self) -> Vect:
        return DOWN * self.frame_y_radius

    @property
    def top(self) -> Vect:
        return UP * self.frame_y_radius

    def formated_output_dir(self, relative_path: str) -> str:
        '''
        将 ``:/path/to/file`` 转换为相对于 ``relative_path`` 的路径
        '''
        output_dir = self.output_dir

        if output_dir.startswith((':/', ':\\')):
            return os.path.join(relative_path, output_dir[2:])

        return output_dir


config_getter = ConfigGetter()
