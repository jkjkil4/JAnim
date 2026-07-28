from dataclasses import dataclass
from typing import Annotated

import click
from dataclass_click import option

from janim.locale import get_translator
from janim.logger import log

_ = get_translator('janim.cli.options')


@dataclass
class SharedOptions:
    all: Annotated[
        bool,
        option(is_flag=True, help=_('Extract all timelines from the file')),
    ]
    configs: Annotated[
        tuple[tuple[str, str], ...],
        option(
            '-c', '--config',
            type=(str, str),
            multiple=True,
            metavar='KEY VALUE',
            help=_('Override config'),
        ),
    ]  # fmt: skip
    hide_subtitles: Annotated[
        bool,
        option(is_flag=True, help=_('Hide subtitles')),
    ]
    external_typst: Annotated[
        bool,
        option(is_flag=True, help=_('Use external Typst executable for compiling Typst documents')),
    ]


@dataclass
class LiveOptions:
    interact: Annotated[
        bool,
        option(
            '-i', '--interact',
            is_flag=True,
            help=_('Enable the network socket for interacting with VS Code'),
        ),
    ]  # fmt: skip
    watch: Annotated[
        bool,
        option(
            '-w', '--watch',
            is_flag=True,
            help=_('Watches the file and rebuild on changes'),
        ),
    ]  # fmt: skip


@dataclass
class FormatOptions:
    format: Annotated[
        str,
        option(
            default='mp4',
            type=click.Choice(['mp4', 'webm', 'mov', 'gif']),
            help=_('Output video format (mp4 by default, webm/mov for transparent background)'),
        ),
    ]
    audio_format: Annotated[
        str,
        option(
            default='mp3',
            help=_('Output audio format (valid only when outputting audio separately)'),
        ),
    ]


@dataclass
class OutputOptions:
    video_with_audio: Annotated[
        bool,
        option(
            is_flag=True,
            help=_(
                'Video with audio (default; will be replaced by --video if there is no audio, and by both --video and --audio if the format is GIF)'
            ),
        ),
    ]
    video: Annotated[
        bool,
        option(
            '--video',
            is_flag=True,
            help=_('Video only'),
        ),
    ]
    audio: Annotated[
        bool,
        option(
            '--audio',
            is_flag=True,
            help=_('Audio only'),
        ),
    ]
    srt: Annotated[
        bool,
        option(
            '--srt',
            is_flag=True,
            help=_('Generate SRT file'),
        ),
    ]

    def resolve(self) -> tuple[bool, bool, bool, bool]:
        """
        返回按照覆盖规则解析后的 ``(video_with_audio, video, audio, srt)``
        """

        video_with_audio = self.video_with_audio
        video = self.video
        audio = self.audio
        srt = self.srt

        # 当设定 video_with_audio 时，忽略 video 和 audio 选项
        if video_with_audio:
            if video:
                log.warning(_("'--video' is ignored because '--video_with_audio' is set"))
                video = False
            if audio:
                log.warning(_("'--audio' is ignored because '--video_with_audio' is set"))
                audio = False

        # 当四个选项都没设定时，将 video_with_audio 作为默认行为
        if not video_with_audio and not video and not audio and not srt:
            video_with_audio = True

        return (video_with_audio, video, audio, srt)


@dataclass
class RangeOptions:
    in_point: Annotated[
        float | None,
        option(
            '--from',
            help=_('Set In Point; use negative value to indicate time relative to the end'),
        ),
    ]
    out_point: Annotated[
        float | None,
        option(
            '--to',
            help=_('Set Out Point; use negative value to indicate time relative to the end'),
        ),
    ]


@dataclass
class HardwareOptions:
    disable_pbo: Annotated[
        bool,
        option(
            '--disable_pbo',
            is_flag=True,
            help=_('Disable PBO (Pixel Buffer Object) for writing video'),
        ),
    ]
    hwaccel: Annotated[
        bool,
        option(
            '--hwaccel',
            is_flag=True,
            help=_('Use hardware acceleration for writing video'),
        ),
    ]
