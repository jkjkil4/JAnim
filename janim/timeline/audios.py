from dataclasses import dataclass
from janim.anims_core.time import TimeRange
from janim.items.audio import Audio
from janim.timeline.core import TimelineCore


@dataclass
class PlayAudioInfo:
    """
    在 Timeline 中播放的音频，所对应的参数信息

    :param audio: 音频对象
    :param clip_range: 将音频对象中的哪一段裁剪出来
    :param range: 将裁剪出来的音频放在 Timeline 的什么时候播放
    """

    audio: Audio
    clip_range: TimeRange
    range: TimeRange


class AudiosMixin(TimelineCore):
    """
    向 :class:`~.Timeline` 提供播放音频的功能

    .. hint::

        该类中的方法都可以直接在 :class:`~.Timeline` 中使用
    """

    PlayAudioInfo = PlayAudioInfo  # 只是为了让 PlayAudioInfo 也出现在 Timeline 的类成员中

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.audio_infos: list[PlayAudioInfo] = []

    def play_audio(
        self,
        audio: Audio,
        *,
        delay: float = 0,
        begin: float = 0,
        end: float = -1,
        clip: tuple[float, float] | None = None,
    ) -> TimeRange:
        """
        在当前位置播放音频

        - 可以指定 ``begin`` 和 ``end`` 表示裁剪区段
        - 可以指定在当前位置往后 ``delay`` 秒才开始播放
        - 若指定 ``clip``，则会覆盖 ``begin`` 和 ``end`` （可以将 ``clip`` 视为这二者的简写）

        返回值表示播放的时间段
        """
        if clip is not None:
            begin, end = clip

        if end == -1:
            end = audio.duration()
        duration = end - begin
        at = self.current_time + delay

        info = PlayAudioInfo(
            audio,
            TimeRange(begin, end),
            TimeRange(at, at + duration),
        )
        self.audio_infos.append(info)

        return info.range.copy()

    def has_audio(self) -> bool:
        """
        该 Timeline 自身是否有可以播放的音频
        """
        return len(self.audio_infos) != 0

    def has_audio_for_all(self) -> bool:
        """
        考虑所有子 Timeline，是否有可以播放的音频

        .. note::

            不包括 :meth:`~.BuiltTimeline.to_playback_control_item` 构造的子 Timeline
        """
        if len(self.audio_infos) != 0:
            return True
        return any(
            item._built.timeline.has_audio_for_all()  #
            for item in self.subtimeline_items
        )
