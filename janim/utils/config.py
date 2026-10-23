from __future__ import annotations

import os
import tempfile
from contextvars import ContextVar
from functools import partial
from pathlib import Path
from typing import Any, Callable, Generator, Self, Sequence

import attrs
import psutil
from colour import Color

from janim.constants import DEFAULT_ITEM_TO_EDGE_BUFF, DOWN, LEFT, RIGHT, UP
from janim.locale import get_translator
from janim.typing import Vect
from janim.utils.file_ops import guarantee_existence

_ = get_translator('janim.utils.config')

config_ctx_var: ContextVar[list[Config]] = ContextVar('config_ctx_var')


class Validator:
    def __init__(self, validator: Callable):
        self.validator = validator

    @staticmethod
    def type(type, typename: str) -> Validator:
        def validator(inst, attr: attrs.Attribute, value):
            if not isinstance(value, type):
                raise TypeError(
                    _('{attrname}={value!r} is incompatible with type {typename}').format(
                        attrname=attr.name, typename=typename, value=value
                    )
                )

        return Validator(validator)

    def __call__(self, inst, attr: attrs.Attribute, value) -> None:
        if value is None:
            return
        self.validator(inst, attr, value)

    def bound(self, *, min: Any = None, max: Any = None) -> Validator:
        def bounded_validator(inst, attr: attrs.Attribute, value):
            self.validator(inst, attr, value)
            if min is not None and value < min:
                raise ValueError(
                    _('{attrname}={value!r} should not be less than {min!r}').format(
                        attrname=attr.name, min=min, value=value
                    )
                )
            if max is not None and value > max:
                raise ValueError(
                    _('{attrname}={value!r} should not be greater than {max!r}').format(
                        attrname=attr.name, max=max, value=value
                    )
                )

        return Validator(bounded_validator)

    def neq_bound(self, *, min: Any = None, max: Any = None) -> Validator:
        def neq_bounded_validator(inst, attr: attrs.Attribute, value):
            self.validator(inst, attr, value)
            if min is not None and value <= min:
                raise ValueError(
                    _('{attrname}={value!r} should be greater than {min!r}').format(
                        attrname=attr.name, min=min, value=value
                    )
                )
            if max is not None and value >= max:
                raise ValueError(
                    _('{attrname}={value!r} should be less than {max!r}').format(
                        attrname=attr.name, max=max, value=value
                    )
                )

        return Validator(neq_bounded_validator)

    def or_sequence(self) -> Validator:
        def sequence_validator(inst, attr: attrs.Attribute, value):
            if isinstance(value, Sequence):
                for item in value:
                    self.validator(inst, attr, item)
            else:
                self.validator(inst, attr, value)

        return Validator(sequence_validator)


_field = partial(attrs.field, default=None)
_int_validator = Validator.type(int, 'int')
_float_validator = Validator.type((int, float), 'float')
_str_validator = Validator.type(str, 'str')
_path_validator = Validator.type((str, Path), 'str or Path')


class _ConfigMeta(type):
    @property
    def get(self) -> Config | ConfigGetter:
        return config_getter


@attrs.define(kw_only=True, slots=False)
class Config(metaclass=_ConfigMeta):
    """配置

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

        .. code-block:: bash

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
    """

    fps: int = _field(validator=_int_validator.bound(min=1))
    preview_fps: int = _field(validator=_int_validator.bound(min=1))
    anti_alias_width: float = _field(validator=_float_validator.bound(min=0))
    motion_blur: bool = _field(validator=Validator.type(bool, 'bool'))
    motion_blur_samples: int = _field(validator=_int_validator.bound(min=1))
    motion_blur_shutter: float = _field(
        validator=_float_validator.bound(min=0)
    )  # fraction of 1 / fps

    frame_height: float = _field(validator=_float_validator.neq_bound(min=0))
    frame_width: float = _field(validator=_float_validator.neq_bound(min=0))

    pixel_height: int = _field(validator=_int_validator.bound(min=1))
    pixel_width: int = _field(validator=_int_validator.bound(min=1))
    background_color: Color = _field(validator=Validator.type(Color, 'Color'))
    font: str | Sequence[str] = _field(validator=_str_validator.or_sequence())
    subtitle_font: str | Sequence[str] = _field(validator=_str_validator.or_sequence())
    subtitle_to_edge_buff: float = _field(validator=_float_validator)

    audio_framerate: int = _field(validator=_int_validator.bound(min=1))
    audio_channels: int = _field(validator=_int_validator.bound(min=1))

    wnd_pos: str = _field(validator=_str_validator)
    wnd_monitor: int = _field(validator=_int_validator.bound(min=0))

    typst_bin: str = _field(validator=_str_validator)
    typst_shared_preamble: str = _field(validator=_str_validator)
    typst_text_preamble: str = _field(validator=_str_validator)
    typst_math_preamble: str = _field(validator=_str_validator)

    output_dir: str | Path = _field(validator=_path_validator)
    temp_dir: str | Path = _field(validator=_path_validator)
    asset_dir: str | Path | Sequence[str | Path] = _field(validator=_path_validator.or_sequence())

    client_search_port: int = _field(validator=_int_validator)

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
    motion_blur=True,
    motion_blur_samples=8,
    motion_blur_shutter=1.0,
    # -
    frame_height=8.0,
    frame_width=16.0 / 9.0 * 8.0,  # aspect_ratio(16/9) * frame_height
    # -
    pixel_height=1080,
    pixel_width=1920,
    background_color=Color('#000000'),
    font='Consolas',
    subtitle_font='',
    subtitle_to_edge_buff=DEFAULT_ITEM_TO_EDGE_BUFF,
    # -
    audio_framerate=44100,
    audio_channels=2,
    # -
    wnd_pos='OR',
    wnd_monitor=0,
    # -
    typst_bin='typst',
    typst_shared_preamble='',
    typst_text_preamble='',
    typst_math_preamble='',
    # -
    output_dir='videos',
    temp_dir=guarantee_existence(os.path.join(tempfile.gettempdir(), 'janim')),
    asset_dir='',
    # -
    client_search_port=40565,
)
"""
默认配置

其中：

- ``preview_fps`` 在接入电源时是 60，未接入时是 30
- ``temp_dir`` 由操作系统决定
"""

cli_config = Config()
"""
命令行配置

会被命令行 ``--config`` 参数自动修改
"""

config_ctx_var.set([default_config])


class ConfigGetter:
    """
    与配置数据相关联的数据的获取

    请仍然使用 ``Config.get.xxx`` 来获取定义在该类中的内容
    """

    def __init__(self, config_ctx: list[Config] | None = None):
        self.config_ctx = config_ctx

    def walk(self) -> Generator[Config, None, None]:
        yield cli_config
        yield from reversed(self.config_ctx or config_ctx_var.get())

    def __getattr__(self, name: str) -> Any:
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
        return default_config.frame_width / default_config.pixel_width

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
        """
        将 ``:/path/to/file`` 转换为相对于 ``relative_path`` 的路径
        """
        output_dir = str(self.output_dir)

        if output_dir.startswith((':/', ':\\')):
            return os.path.join(relative_path, output_dir[2:])

        return output_dir

    def scaled_pixel_size(self, scale: float) -> dict[str, int]:
        """
        根据缩放比例计算缩放后的 **像素尺寸**

        使用示例：

        .. code-block:: python

            Config(
                **Config.get.scaled_pixel_size(0.5)
            )
        """
        return {
            'pixel_width': int(self.pixel_width * scale),
            'pixel_height': int(self.pixel_height * scale),
        }

    def scaled_frame_size(self, scale: float) -> dict[str, float]:
        """
        根据缩放比例计算缩放后的 **画面尺寸**

        使用示例：

        .. code-block:: python

            Config(
                **Config.get.scaled_frame_size(0.5)
            )
        """
        return {
            'frame_width': self.frame_width * scale,
            'frame_height': self.frame_height * scale,
        }

    def scaled_width(self, scale: float) -> dict[str, float]:
        """
        根据缩放比例计算缩放后的 **画面宽度和像素宽度**

        使用示例：

        .. code-block:: python

            Config(
                **Config.get.scaled_width(0.5)
            )
        """
        return {
            'pixel_width': int(self.pixel_width * scale),
            'frame_width': self.frame_width * scale,
        }

    def scaled_height(self, scale: float) -> dict[str, float]:
        """
        根据缩放比例计算缩放后的 **画面高度和像素高度**

        使用示例：

        .. code-block:: python

            Config(
                **Config.get.scaled_height(0.5)
            )
        """
        return {
            'pixel_height': int(self.pixel_height * scale),
            'frame_height': self.frame_height * scale,
        }

    def scaled_size(self, scale: float) -> dict[str, float]:
        """
        根据缩放比例计算缩放后的 **画面尺寸和像素尺寸**

        使用示例：

        .. code-block:: python

            Config(
                **Config.get.scaled_size(0.5)
            )
        """
        return {
            **self.scaled_width(scale),
            **self.scaled_height(scale),
        }

    def swapped_size(self) -> dict[str, int]:
        """
        获取交换宽高后的 **画面尺寸和像素尺寸**

        使用示例（将横屏配置转为竖屏）：

        .. code-block:: python

            Config(
                **Config.get.swapped_size()
            )
        """
        return {
            'pixel_width': self.pixel_height,
            'pixel_height': self.pixel_width,
            'frame_width': self.frame_height,
            'frame_height': self.frame_width,
        }


config_getter = ConfigGetter()
