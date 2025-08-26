from __future__ import annotations

import os
import tempfile
from contextvars import ContextVar
from functools import partial
from pathlib import Path
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

    设置配置
    ----------------

    设置配置的三种方式：

    1.  在 Python 代码中，将配置写在时间轴类里

        .. code-block:: python

            class YourTimeline(Timeline):
                CONFIG = Config(
                    fps=120,
                    preview_fps=30
                )

                def construct(self) -> None:
                    ...

    另见：:py:obj:`~.Timeline.CONFIG`

    2.  使用命令行参数修改全局配置

        .. code-block:: sh

            janim write your_file.py YourTimeline -c fps 120 -c output_dir custom_dir

    3.  修改局部代码块的配置

        .. code-block:: python

            class YourTimeline(Timeline):
                def construct(self):
                    txt1 = Text('Using default font')

                    with Config(font='Noto Serif CJK SC'):
                        txt2 = Text('Using "Noto Serif CJK SC" font')

                    txt3 = Text('Using default font again')

                    group = Group(txt1, txt2, txt3).show()
                    group.points.arrange(DOWN, aligned_edge=LEFT)

    获取配置
    -------------

    使用 ``Config.get.xxx`` 得到属性，例如：

    .. code-block:: python

        class YourTimeline(Timeline):
            def construct(self):
                print(Config.get.fps)

    更多内容可以参考文档教程的 :doc:`配置系统 <../../tutorials/config_system>` 页面
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
    temp_dir: str | Path = None
    asset_dir: str | Path | list[str | Path] = None

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
