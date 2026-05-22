import ast
import importlib.machinery
import inspect
import linecache
import os
import sys
import time
import types
from typing import Callable, Iterable, Sequence

from janim.anims.timeline import BuiltTimeline, Timeline
from janim.cli.options import (
    FormatOptions,
    HardwareOptions,
    LiveOptions,
    OutputOptions,
    RangeOptions,
    SharedOptions,
)
from janim.exception import EXITCODE_MODULE_NOT_FOUND, EXITCODE_NOT_FILE, ExitException
from janim.locale import get_translator
from janim.logger import log
from janim.utils.config import cli_config, default_config
from janim.utils.file_ops import STDIN_FILENAME, open_file
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
    if not timelines:
        return

    auto_play = len(timelines) == 1
    available_timeline_names = [
        timeline.__name__ for timeline in get_all_timelines_from_module(module)
    ]

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
            timeline().build(hide_subtitles=shared_options.hide_subtitles, show_debug_notice=True)
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
            available_timeline_names=available_timeline_names,
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

    video_with_audio = output_options.video_with_audio
    video = output_options.video
    audio = output_options.audio
    srt = output_options.srt

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

    is_gif = format_options.format == 'gif'

    prev_is_skipped = False

    for built in builts:
        name = built.timeline.__class__.__name__
        relative_path = os.path.dirname(inspect.getfile(built.timeline.__class__))

        output_dir = os.path.normpath(built.cfg.formated_output_dir(relative_path))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        video_with_audio = video_with_audio
        video = video
        audio = audio
        srt = srt
        open_result = open and built is builts[-1]

        has_audio = built.timeline.has_audio_for_all()

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


def get_module(file: str):
    """
    根据给定的输入 ``file`` 产生 ``module``

    - 当 ``file`` 为文件路径时，将文件读取为 module
    - 当 ``file`` 为 ``'-'`` 时，从 ``stdin`` 读取源码编译 module
    """
    if file == '-':
        return get_module_from_stdin()
    else:
        return get_module_from_file(file)


def get_module_from_stdin():
    """
    从 ``stdin`` 读取源码并编译为 module
    """
    source = sys.stdin.read()

    # 兼容相对于当前工作目录的导入
    sys.path.insert(0, os.getcwd())

    module_name = '__janim_main__'
    module = types.ModuleType(module_name)
    module.__file__ = STDIN_FILENAME

    # 让 inspect.getsourcelines 能从 linecache 读取 stdin 源码
    linecache.cache[STDIN_FILENAME] = (
        len(source),
        None,
        [line + '\n' for line in source.splitlines()],
        STDIN_FILENAME,
    )

    sys.modules[module_name] = module

    code = compile(source, STDIN_FILENAME, 'exec')
    exec(code, module.__dict__)

    return module


def get_module_from_file(file_name: str):
    """
    将给定的 ``file_name`` 读取为 module
    """
    if not os.path.exists(file_name):
        log.error(_('"{file_name}" doesn\'t exist').format(file_name=file_name))
        raise ExitException(EXITCODE_MODULE_NOT_FOUND)

    if not os.path.isfile(file_name):
        log.error(_('"{file_name}" isn\'t a file').format(file_name=file_name))
        raise ExitException(EXITCODE_NOT_FILE)

    # 兼容相对于源代码文件的导入
    sys.path.insert(0, os.path.abspath(os.path.dirname(file_name)))

    module_name = file_name.replace(os.sep, '.').replace('.py', '')
    loader = importlib.machinery.SourceFileLoader(module_name, file_name)
    module = loader.load_module()
    return module


def extract_timelines_from_module(
    module,
    timeline_names: Sequence[str],
    all: bool,
) -> list[type[Timeline]]:
    """
    根据指定的 ``module`` 向用户询问使用哪些 :class:`~.Timeline`
    """
    timelines = []
    err = False

    if not all and timeline_names:
        for name in timeline_names:
            try:
                timeline = module.__dict__[name]
                if not isinstance(timeline, type) or not issubclass(timeline, Timeline):
                    raise KeyError()
                timelines.append(timeline)
            except KeyError:
                log.error(_('No timeline named "{name}"').format(name=name))
                err = True
    else:
        classes = get_all_timelines_from_module(module)
        if len(classes) <= 1 or all:
            return classes

        if module.__file__ == STDIN_FILENAME:
            log.error(
                _(
                    'Multiple timelines found in stdin input. '  #
                    'Please specify timeline names with command line arguments.'
                )
            )
            return []

        max_digits = len(str(len(classes)))

        name_to_class = {}
        for idx, timeline_class in enumerate(classes, start=1):
            name = timeline_class.__name__
            print(f'{str(idx).zfill(max_digits)}: {name}', file=sys.stderr)
            name_to_class[name] = timeline_class

        try:
            prompt_text = '\n' + _(
                'That module has multiple timelines, which ones would you like to render?\n'  #
                'Timeline Name or Number: '
            )
            sys.stderr.write(prompt_text)  # input 只能输出到 stdout，所以这里手动输出到 stderr
            sys.stderr.flush()
            user_input = input()
        except KeyboardInterrupt:
            user_input = ''

        for split_str in user_input.replace(' ', '').split(','):
            if not split_str:
                continue
            if split_str.isnumeric():
                idx = int(split_str) - 1
                if 0 <= idx < len(classes):
                    timelines.append(classes[idx])
                else:
                    log.error(_('Invaild number {num}').format(num=idx + 1))
                    err = True
            else:
                try:
                    timelines.append(name_to_class[split_str])
                except KeyError:
                    log.error(_('No timeline named {split_str}').format(split_str=split_str))
                    err = True

    return [] if err else timelines


def get_all_timelines_from_module(module) -> list[type[Timeline]]:
    """
    从指定的 ``module`` 中得到所有可用的 :class:`~.Timeline`

    会缓存结果，如果 ``module`` 的内容有更新可能需要使用 ``get_all_timelines_from_module.cache_clear()`` 来清空缓存
    """
    classes = [
        value
        for value in module.__dict__.values()
        if (
            isinstance(value, type)
            and issubclass(value, Timeline)
            # 定义于当前模块，排除了 import 导入的
            and value.__module__ == module.__name__
            # 排除以下划线开头的
            and not value.__name__.startswith('_')
            # construct 方法已被实现
            and not getattr(value.construct, '__isabstractmethod__', False)
        )
    ]
    if len(classes) <= 1:
        return classes

    lineno_key = get_lineno_key_function(module)

    if lineno_key is not None:
        classes.sort(key=lineno_key)

    return classes


def get_lineno_key_function(module) -> Callable[[type], tuple[int, int]] | None:
    """
    返回一个函数，其对于列表中的每个类：

    - 如果能找到 class 在 module 中所定义的行数，则返回 ``(0, 行数)``
    - 如果找不到，则返回 ``(1, 0)``

    **特殊情况说明：**

    对于重新载入的 module，如果代码里删除了某个类的代码，这个类仍然会出现在 module 中，
    但此时无法在 module 源代码中找到这个类的定义，所以把找不到的类返回 ``(1, 0)``，这样依据这个进行排序就会将其排序到最后

    更多技术细节请参阅 https://github.com/jkjkil4/JAnim/pull/36
    """
    file = inspect.getfile(module)
    if not file:
        return None

    # 模仿 inspect.findsource 的做法
    linecache.checkcache(file)
    lines = linecache.getlines(file, module.__dict__)
    if not lines:
        return None

    source = ''.join(lines)
    tree = ast.parse(source)

    collector = _ClassDefCollector()
    collector.visit(tree)

    defs = collector.defs

    def lineno_key(cls: type) -> tuple[int, int]:
        lineno = defs.get(cls.__name__, None)
        if lineno is None:
            return (1, 0)
        return (0, lineno)

    return lineno_key


class _ClassDefCollector(ast.NodeVisitor):
    def __init__(self):
        self.defs: dict[str, int] = {}

    def visit_ClassDef(self, node: ast.ClassDef):
        # 因为我们只关心最后一次定义的位置，所以直接赋值就行
        self.defs[node.name] = node.lineno
        # 由于只关心最顶层的 classdef，所以不需要 generic_visit
