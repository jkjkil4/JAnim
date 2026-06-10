import inspect
import math
import os
import types
from typing import Iterable

from janim.anims_core.time import TimeRange
from janim.items.audio import Audio
from janim.items.item import Item
from janim.locale import get_translator
from janim.logger import log
from janim.timeline.audios import AudiosMixin
from janim.timeline.core import TimelineCore
from janim.timeline.subtitles import SubtitlesMixin

_ = get_translator('janim.timeline.misc')


class AudiosAndSubtitlesMixin(AudiosMixin, SubtitlesMixin):
    def aas(
        self,
        file_path: str,
        subtitle: str | Iterable[str],
        **kwargs,
    ) -> TimeRange:
        """
        :meth:`audio_and_subtitle` 的简写
        """
        return self.audio_and_subtitle(file_path, subtitle, **kwargs)

    def audio_and_subtitle(
        self,
        file_path: str,
        subtitle: str | Iterable[str],
        *,
        clip: tuple[float, float] | None | types.EllipsisType = ...,
        delay: float = 0,
        mul: float | Iterable[float] | None = None,
        **subtitle_kwargs,
    ) -> TimeRange:
        """
        播放音频，并在对应的区间显示字幕

        - 如果 ``clip=...`` （默认，省略号），则表示自动确定裁剪区间，将前后的空白去除（可以传入 ``clip=None`` 禁用自动裁剪）
        - 如果 ``mul`` 不是 ``None``，则会将音频振幅乘以该值
        """
        audio = Audio(file_path)
        if mul is not None:
            audio.mul(mul)

        if clip is ...:
            recommended = audio.recommended_range()
            if recommended is None:
                clip = None
            else:
                clip = (math.floor(recommended[0] * 10) / 10, math.ceil(recommended[1] * 10) / 10)

        t = self.play_audio(audio, delay=delay, clip=clip)
        self.subtitle(subtitle, t, **subtitle_kwargs)

        return t


class DebugMixin(TimelineCore):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.debug_list: list[Item] = []

    def debug(self, item: Item, msg: str | None = None) -> None:
        """
        将物件的动画栈显示在时间轴中

        .. tip::

            显示在时间轴中的一个黄色扁条表示在哪些区段中物件是可见的
        """
        if self.show_debug_notice:
            f_back: types.FrameType = inspect.currentframe().f_back  # type: ignore
            filename = os.path.basename(f_back.f_code.co_filename)
            obj_and_loc = _('Called self.debug({repr}) at {loc}').format(
                repr=repr(item), loc=f'{filename}:{f_back.f_lineno}'
            )
            if msg is None:
                log.info(obj_and_loc)
            else:
                log.info(obj_and_loc + '\nmsg=' + msg)
        self.debug_list.append(item)

    @staticmethod
    def fmt_time(t: float) -> str:
        time = round(t, 3)

        minutes = int(time // 60)
        time %= 60

        hours = minutes // 60
        minutes %= 60

        seconds = math.floor(time)
        ms = round((time - seconds) * 1e3)

        times = []
        if hours != 0:
            times.append(f'{hours}h')
        times.append(f'{minutes:>3d}m' if minutes != 0 else ' ' * 4)
        times.append(f'{seconds:>3d}s')
        times.append(f'{ms:>4d}ms' if ms != 0 else ' ' * 6)

        return ''.join(times)

    def dbg_time(self, ext_msg: str = '') -> None:  # pragma: no cover
        if ext_msg:
            ext_msg = f'[{ext_msg}]  '

        time = self.fmt_time(self.current_time)

        log.info(f't={time}  {ext_msg}at construct.{self._extract_lineno_in_construct()}')
