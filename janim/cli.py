import ast
import importlib.machinery
import inspect
import linecache
import os
import sys
import time
import types
from argparse import Namespace
from functools import lru_cache
from typing import Callable

from janim.anims.timeline import BuiltTimeline, Timeline
from janim.exception import (EXITCODE_MODULE_NOT_FOUND, EXITCODE_NOT_FILE,
                             ExitException)
from janim.locale.i18n import get_translator
from janim.logger import log
from janim.utils.config import cli_config, default_config
from janim.utils.file_ops import STDIN_FILENAME, open_file

_ = get_translator('janim.cli')


def run(args: Namespace) -> None:
    module = get_module(args.input)
    if module is None:
        return
    modify_typst_compile_flag(args)
    modify_cli_config(args)

    timelines = extract_timelines_from_module(args, module)
    if not timelines:
        return

    auto_play = len(timelines) == 1
    available_timeline_names = [timeline.__name__ for timeline in get_all_timelines_from_module(module)]

    # isort: off
    from janim.gui.anim_viewer import AnimViewer    # 把 gui 组件放在前面导入，确保对 pyside6 的检测
    from PySide6.QtCore import QPoint, QTimer
    from janim.gui.application import Application

    app = Application()

    log.info('======')

    built_timelines: list[BuiltTimeline] = []

    for timeline in timelines:
        built_timelines.append(timeline().build(hide_subtitles=args.hide_subtitles, show_debug_notice=True))

    log.info('======')
    log.info(_('Constructing window'))

    t = time.time()

    widgets: list[AnimViewer] = []
    for i, built in enumerate(built_timelines):
        viewer = AnimViewer(built,
                            auto_play=auto_play,
                            interact=args.interact,
                            watch=args.watch,
                            available_timeline_names=available_timeline_names)
        widgets.append(viewer)
        viewer.show()
        if i != 0:
            viewer.move(widgets[i - 1].pos() + QPoint(24, 24))

    QTimer.singleShot(200, widgets[-1].activateWindow)

    log.info(_('Finished constructing in {time:.2f} s').format(time=time.time() - t))
    log.info('======')

    app.exec()


def write(args: Namespace) -> None:
    module = get_module(args.input)
    if module is None:
        return
    modify_typst_compile_flag(args)
    modify_cli_config(args)

    timelines = extract_timelines_from_module(args, module)
    if not timelines:
        return

    from janim.render.writer import (AudioWriter, SRTWriter, VideoWriter,
                                     merge_video_and_audio)

    log.info('======')

    builts = [timeline().build(hide_subtitles=args.hide_subtitles) for timeline in timelines]

    # 当设定 video_with_audio 时，忽略 video 和 audio 选项
    if args.video_with_audio:
        if args.video:
            log.warning(_("'--video' is ignored because '--video_with_audio' is set"))
            args.video = False
        if args.audio:
            log.warning(_("'--audio' is ignored because '--video_with_audio' is set"))
            args.audio = False

    # 当四个选项都没设定时，将 video_with_audio 作为默认行为
    if not args.video_with_audio and not args.video and not args.audio and not args.srt:
        args.video_with_audio = True

    is_gif = args.format == 'gif'

    prev_is_skipped = False

    for built in builts:
        name = built.timeline.__class__.__name__
        relative_path = os.path.dirname(inspect.getfile(built.timeline.__class__))

        output_dir = os.path.normpath(built.cfg.formated_output_dir(relative_path))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        video_with_audio = args.video_with_audio
        video = args.video
        audio = args.audio
        srt = args.srt
        open_result = args.open and built is builts[-1]

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
            log.info(
                _('Skipping "{name}": no part to output')
                .format(name=name)
            )
            continue

        if writes_video:
            log.info(f'fps={built.cfg.fps}')
            log.info(f'resolution="{built.cfg.pixel_width}x{built.cfg.pixel_height}"')
            log.info(f'format="{args.format}"')
        if writes_audio:
            if not video_with_audio:
                log.info(f'audio_format="{args.audio_format}"')
            log.info(f'audio_framerate="{built.cfg.audio_framerate}"')
        log.info(f'output_dir="{output_dir}"')

        if writes_video:
            video_writer = VideoWriter(built)
            video_writer.write_all(
                os.path.join(output_dir,
                             f'{name}.{args.format}'),
                args.in_point,
                args.out_point,
                use_pbo=not args.disable_pbo,
                hwaccel=args.hwaccel,
                _keep_temp=video_with_audio
            )
            if open_result and not video_with_audio:
                open_file(video_writer.final_file_path)

        if writes_audio:
            audio_writer = AudioWriter(built)
            audio_writer.write_all(
                os.path.join(output_dir,
                             f'{name}.{args.audio_format}'),
                _keep_temp=video_with_audio
            )
            if open_result and not video_with_audio and not writes_video:
                open_file(audio_writer.final_file_path)

        if video_with_audio:
            merge_video_and_audio(built.cfg.ffmpeg_bin,
                                  video_writer.temp_file_path,
                                  audio_writer.temp_file_path,
                                  video_writer.final_file_path)
            if open_result:
                open_file(video_writer.final_file_path)

        if writes_srt:
            file_path = os.path.join(output_dir, f'{name}.srt')
            SRTWriter.writes(built, file_path)
            log.info(
                _('Generated SRT file "{file_path}"')
                .format(file_path=file_path)
            )

    log.info('======')


def tool(args: Namespace) -> None:
    if not args.tool_name:
        log.error(_('No tool specified for use'))
        return

    from janim.gui.popup import ColorWidget, FontTable, RichTextEditor, QWidget

    log.info('======')
    log.info(_('Constructing window'))

    t = time.time()

    from janim.gui.application import Application

    app = Application()

    tool_map: dict[str, type[QWidget]] = {
        'richtext': RichTextEditor,
        'fonts': FontTable,
        'color': ColorWidget
    }

    widgets: list[QWidget] = []

    for key in args.tool_name:
        widget = tool_map[key]()
        widgets.append(widget)
        widget.show()

    log.info(_('Finished constructing in {time:.2f} s').format(time=time.time() - t))
    log.info('======')

    app.exec()


def modify_typst_compile_flag(args: Namespace) -> None:
    """
    用于 CLI 的 ``--external-typst`` 参数
    """
    from janim.utils.typst_compile import set_use_external_typst
    set_use_external_typst(args.external_typst)


def modify_cli_config(args: Namespace) -> None:
    """
    用于 CLI 的 ``-c`` 参数
    """
    if args.config:
        for key, value in args.config:
            dtype = type(getattr(default_config, key))
            setattr(cli_config, key, dtype(value))


def get_module(input: str):
    """
    根据给定的输入 ``input`` 产生 ``module``

    - 当 ``input`` 为文件路径时，将文件读取为 module
    - 当 ``input`` 为 ``'-'`` 时，从 ``stdin`` 读取源码编译 module
    """
    if input == '-':
        return get_module_from_stdin()
    else:
        return get_module_from_file(input)


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

    module_name = file_name.replace(os.sep, ".").replace(".py", "")
    loader = importlib.machinery.SourceFileLoader(module_name, file_name)
    module = loader.load_module()
    return module


def extract_timelines_from_module(args: Namespace, module) -> list[type[Timeline]]:
    """
    根据指定的 ``module`` 向用户询问使用哪些 :class:`~.Timeline`
    """
    timelines = []
    err = False

    if not args.all and args.timeline_names:
        for name in args.timeline_names:
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
        if len(classes) <= 1 or args.all:
            return classes

        if module.__file__ == STDIN_FILENAME:
            log.error(_('Multiple timelines found in stdin input. '
                        'Please specify timeline names with command line arguments.'))
            return []

        max_digits = len(str(len(classes)))

        name_to_class = {}
        for idx, timeline_class in enumerate(classes, start=1):
            name = timeline_class.__name__
            print(f"{str(idx).zfill(max_digits)}: {name}", file=sys.stderr)
            name_to_class[name] = timeline_class

        try:
            prompt_text = (
                '\n' + _('That module has multiple timelines, '
                         'which ones would you like to render?'
                         '\nTimeline Name or Number: ')
            )
            sys.stderr.write(prompt_text)   # input 只能输出到 stdout，所以这里手动输出到 stderr
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


@lru_cache(maxsize=1)
def get_all_timelines_from_module(module) -> list[type[Timeline]]:
    """
    从指定的 ``module`` 中得到所有可用的 :class:`~.Timeline`

    会缓存结果，如果 ``module`` 的内容有更新可能需要使用 ``get_all_timelines_from_module.cache_clear()`` 来清空缓存
    """
    classes = [
        value
        for value in module.__dict__.values()
        if (isinstance(value, type)
            and issubclass(value, Timeline)
            and value.__module__ == module.__name__                             # 定义于当前模块，排除了 import 导入的
            and not value.__name__.startswith('_')                              # 排除以下划线开头的
            and not getattr(value.construct, '__isabstractmethod__', False))    # construct 方法已被实现
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
