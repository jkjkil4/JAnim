from functools import lru_cache
import inspect
import os
import time
import types
from typing import Iterable, Sequence

from janim.anims.timeline import BuiltTimeline, Timeline
from janim.cli.options import (
    FormatOptions,
    HardwareOptions,
    LiveOptions,
    OutputOptions,
    RangeOptions,
    SharedOptions,
)
from janim.cli.plugins import get_plugins
from janim.cli.utils.extract_timeline import (
    extract_timelines_from_module,
    extract_timelines_from_modules,
    get_all_timelines_from_module,
)
from janim.cli.utils.get_module import get_module
from janim.locale import get_translator
from janim.logger import log
from janim.utils.config import cli_config, default_config
from janim.utils.file_ops import get_janim_dir, open_file
from janim.utils.typst_compile import set_use_external_typst

_ = get_translator('janim.cli.execute')


def run(
    file: str,
    timeline_names: Sequence[str],
    shared_options: SharedOptions,
    live_options: LiveOptions,
) -> None:
    module = get_module(file)
    if module is None:
        return
    set_use_external_typst(shared_options.external_typst)
    modify_cli_config(shared_options.configs)

    timelines = extract_timelines_from_module(module, timeline_names, shared_options.all)
    run_timelines(timelines, shared_options.hide_subtitles, live_options)


def examples(timeline_names: list[str]) -> None:
    builtin_examples = get_module(os.path.join(get_janim_dir(), 'examples.py'))

    modules: list[tuple[str, types.ModuleType]] = [
        ('JAnim Examples', builtin_examples),
    ]

    for plugin in get_plugins():
        module = plugin.get_examples_module()
        if module is not None:
            modules.append((f'{plugin.name} Examples', module))

    timelines = extract_timelines_from_modules(modules, timeline_names)
    run_timelines(timelines, False, LiveOptions(False, False))


def run_timelines(
    timelines: list[type[Timeline]], hide_subtitles: bool, live_options: LiveOptions
) -> None:
    if not timelines:
        return

    auto_play = len(timelines) == 1

    @lru_cache(maxsize=None)
    def get_all_timeline_names_from_module(module: types.ModuleType) -> list[str]:
        return [timeline.__name__ for timeline in get_all_timelines_from_module(module)]

    # isort: off
    from janim.gui.anim_viewer import AnimViewer  # 把 gui 组件放在前面导入，确保对 pyside6 的检测
    from PySide6.QtCore import QPoint, QTimer
    from janim.gui.application import Application
    # isort: on

    app = Application()

    log.info('======')

    built_timelines: list[BuiltTimeline] = []

    for timeline in timelines:
        built_timelines.append(
            timeline().build(hide_subtitles=hide_subtitles, show_debug_notice=True)
        )

    log.info('======')
    log.info(_('Constructing window'))

    t = time.time()

    widgets: list[AnimViewer] = []
    for i, built in enumerate(built_timelines):
        viewer = AnimViewer(
            built,
            auto_play=auto_play,
            interact=live_options.interact,
            watch=live_options.watch,
            available_timeline_names=get_all_timeline_names_from_module(
                inspect.getmodule(built.timeline)
            ),
        )
        widgets.append(viewer)
        viewer.show()
        if i != 0:
            viewer.move(widgets[i - 1].pos() + QPoint(24, 24))

    QTimer.singleShot(200, widgets[-1].activateWindow)

    log.info(_('Finished constructing in {time:.2f} s').format(time=time.time() - t))
    log.info('======')

    app.exec()


def write(
    file: str,
    timeline_names: Sequence[str],
    shared_options: SharedOptions,
    open: bool,
    format_options: FormatOptions,
    output_options: OutputOptions,
    range_options: RangeOptions,
    hardware_options: HardwareOptions,
) -> None:
    module = get_module(file)
    if module is None:
        return
    set_use_external_typst(shared_options.external_typst)
    modify_cli_config(shared_options.configs)

    timelines = extract_timelines_from_module(module, timeline_names, shared_options.all)
    if not timelines:
        return

    from janim.render.writer import AudioWriter, SRTWriter, VideoWriter, merge_video_and_audio

    log.info('======')

    builts = [
        timeline().build(hide_subtitles=shared_options.hide_subtitles)  #
        for timeline in timelines
    ]

    resolved_output_options = output_options.resolve()

    is_gif = format_options.format == 'gif'

    prev_is_skipped = False

    for built in builts:
        name = built.timeline.__class__.__name__
        relative_path = os.path.dirname(inspect.getfile(built.timeline.__class__))

        output_dir = os.path.normpath(built.cfg.formated_output_dir(relative_path))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        open_result = open and built is builts[-1]

        has_audio = built.timeline.has_audio_for_all()

        # 将 resolved_output_options 解包出来，并根据当前 built 的实际状况调整选项
        video_with_audio, video, audio, srt = resolved_output_options

        # 如果其实没办法做到 video_with_audio，那么把 video_with_audio 用 video 和 audio 替代
        fallback = not has_audio or is_gif
        if video_with_audio and fallback:
            video_with_audio = False
            video = True
            audio = True

        writes_video = video_with_audio or video
        writes_audio = (video_with_audio or audio) and has_audio
        writes_srt = srt and built.timeline.has_subtitle()

        skip = not writes_video and not writes_audio and not writes_srt

        # 这个判断使得连续跳过多个时，不输出额外的分割线
        if not (prev_is_skipped and skip):
            log.info('======')

        prev_is_skipped = skip

        if skip:
            log.info(_('Skipping "{name}": no part to output').format(name=name))
            continue

        if writes_video:
            log.info(f'fps={built.cfg.fps}')
            log.info(f'resolution="{built.cfg.pixel_width}x{built.cfg.pixel_height}"')
            log.info(f'format="{format_options.format}"')
        if writes_audio:
            if not video_with_audio:
                log.info(f'audio_format="{format_options.audio_format}"')
            log.info(f'audio_framerate="{built.cfg.audio_framerate}"')
        log.info(f'output_dir="{output_dir}"')

        if writes_video:
            video_writer = VideoWriter(built)
            video_writer.write_all(
                os.path.join(output_dir, f'{name}.{format_options.format}'),
                range_options.in_point,
                range_options.out_point,
                use_pbo=not hardware_options.disable_pbo,
                hwaccel=hardware_options.hwaccel,
                _keep_temp=video_with_audio,
            )
            if open_result and not video_with_audio:
                open_file(video_writer.final_file_path)

        if writes_audio:
            audio_writer = AudioWriter(built)
            audio_writer.write_all(
                os.path.join(output_dir, f'{name}.{format_options.audio_format}'),
                _keep_temp=video_with_audio,
            )
            if open_result and not video_with_audio and not writes_video:
                open_file(audio_writer.final_file_path)

        if video_with_audio:
            merge_video_and_audio(
                built.cfg.ffmpeg_bin,
                video_writer.temp_file_path,
                audio_writer.temp_file_path,
                video_writer.final_file_path,
            )
            if open_result:
                open_file(video_writer.final_file_path)

        if writes_srt:
            file_path = os.path.join(output_dir, f'{name}.srt')
            SRTWriter.writes(built, file_path)
            log.info(_('Generated SRT file "{file_path}"').format(file_path=file_path))

    log.info('======')


def tool(tools: Iterable[str]) -> None:
    if not tools:
        log.error(_('No tool specified for use'))
        return

    from janim.gui.popup import ColorWidget, FontTable, QWidget, RichTextEditor

    log.info('======')
    log.info(_('Constructing window'))

    t = time.time()

    from janim.gui.application import Application

    app = Application()

    tool_map: dict[str, type[QWidget]] = {
        'richtext': RichTextEditor,
        'fonts': FontTable,
        'color': ColorWidget,
    }

    widgets: list[QWidget] = []

    for key in tools:
        widget = tool_map[key]()
        widgets.append(widget)
        widget.show()

    log.info(_('Finished constructing in {time:.2f} s').format(time=time.time() - t))
    log.info('======')

    app.exec()


def modify_cli_config(configs: Iterable[tuple[str, str]]) -> None:
    """
    根据 (key, value) 列表修改 :py:obj:`~.cli_config`
    """
    for key, value in configs:
        dtype = type(getattr(default_config, key))
        setattr(cli_config, key, dtype(value))
