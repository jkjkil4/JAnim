import importlib.machinery
import inspect
import os
import platform
import subprocess as sp
import time
from argparse import Namespace
from functools import lru_cache

from janim.anims.timeline import Timeline
from janim.exception import (EXITCODE_MODULE_NOT_FOUND, EXITCODE_NOT_FILE,
                             ExitException)
from janim.locale.i18n import get_local_strings
from janim.logger import log
from janim.utils.config import cli_config, default_config

_ = get_local_strings('cli')


def run(args: Namespace) -> None:
    module = get_module(args.filepath)
    if module is None:
        return
    modify_default_config(args)

    timelines = extract_timelines_from_module(args, module)
    if not timelines:
        return

    from janim.gui.anim_viewer import AnimViewer

    auto_play = len(timelines) == 1
    available_timeline_names = [timeline.__name__ for timeline in get_all_timelines_from_module(module)]

    from PySide6.QtCore import QPoint, QTimer

    from janim.gui.application import Application

    app = Application()

    log.info('======')

    widgets: list[AnimViewer] = []
    for timeline in timelines:
        viewer = AnimViewer(timeline().build(),
                            auto_play=auto_play,
                            interact=args.interact,
                            available_timeline_names=available_timeline_names)
        widgets.append(viewer)

    log.info('======')
    log.info(_('Constructing window'))

    t = time.time()

    for i, widget in enumerate(widgets):
        widget.show()
        if i != 0:
            widget.move(widgets[i - 1].pos() + QPoint(24, 24))

    QTimer.singleShot(200, widgets[-1].activateWindow)

    log.info(_('Finished constructing in {time:.2f} s').format(time=time.time() - t))
    log.info('======')

    app.exec()


def write(args: Namespace) -> None:
    module = get_module(args.filepath)
    if module is None:
        return
    modify_default_config(args)

    timelines = extract_timelines_from_module(args, module)
    if not timelines:
        return

    from janim.render.writer import AudioWriter, VideoWriter

    log.info('======')

    built = [timeline().build() for timeline in timelines]

    log.info('======')

    both = not args.video and not args.audio

    log.info('======')

    for anim in built:
        name = anim.timeline.__class__.__name__
        relative_path = os.path.dirname(inspect.getfile(anim.timeline.__class__))

        output_dir = os.path.normpath(anim.cfg.formated_output_dir(relative_path))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        writes_video = both or args.video
        writes_audio = (both or args.audio) and anim.timeline.has_audio()

        if writes_video:
            log.info(f'fps={anim.cfg.fps}')
            log.info(f'resolution="{anim.cfg.pixel_width}x{anim.cfg.pixel_height}"')
            log.info(f'format="{args.format}"')
        if writes_audio:
            log.info(f'audio_format="{args.audio_format}"')
            log.info(f'audio_framerate="{anim.cfg.audio_framerate}"')
        log.info(f'output_dir="{output_dir}"')

        if writes_video:
            writer = VideoWriter(anim)
            writer.write_all(
                os.path.join(output_dir,
                             f'{name}.{args.format}')
            )
            if args.open and anim is built[-1]:
                open_file(writer.final_file_path)

        if writes_audio:
            writer = AudioWriter(anim)
            writer.write_all(
                os.path.join(output_dir,
                             f'{name}.{args.audio_format}')
            )

    log.info('======')


def tool(args: Namespace) -> None:
    if not args.tool_name:
        log.error(_('No tool specified for use'))
        return

    # 不直接从对应的 module 导入，是为了经过 anim_viewer 中对 pyside6 安装的检查
    from janim.gui.anim_viewer import (ColorWidget, FontTable, QWidget,
                                       RichTextEditor)

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


def modify_default_config(args: Namespace) -> None:
    '''
    用于 CLI 的 ``-c`` 参数
    '''
    if args.config:
        for key, value in args.config:
            dtype = type(getattr(default_config, key))
            setattr(cli_config, key, dtype(value))


def get_module(file_name: str):
    '''
    根据给定的文件名 ``file_name`` 产生 ``module``
    '''
    if not os.path.exists(file_name):
        log.error(_('"{file_name}" doesn\'t exist').format(file_name=file_name))
        raise ExitException(EXITCODE_MODULE_NOT_FOUND)

    if not os.path.isfile(file_name):
        log.error(_('"{file_name}" isn\'t a file').format(file_name=file_name))
        raise ExitException(EXITCODE_NOT_FILE)

    module_name = file_name.replace(os.sep, ".").replace(".py", "")
    loader = importlib.machinery.SourceFileLoader(module_name, file_name)
    module = loader.load_module()
    return module


def extract_timelines_from_module(args: Namespace, module) -> list[type[Timeline]]:
    '''
    根据指定的 ``module`` 向用户询问使用哪些 :class:`~.Timeline`
    '''
    timelines = []
    err = False

    if not args.all and args.timeline_names:
        for name in args.timeline_names:
            try:
                timelines.append(module.__dict__[name])
            except KeyError:
                log.error(_('No timeline named "{name}"').format(name=name))
                err = True
    else:
        classes = get_all_timelines_from_module(module)
        if len(classes) <= 1 or args.all:
            return classes

        max_digits = len(str(len(classes)))

        name_to_class = {}
        for idx, timeline_class in enumerate(classes, start=1):
            name = timeline_class.__name__
            print(f"{str(idx).zfill(max_digits)}: {name}")
            name_to_class[name] = timeline_class

        try:
            user_input = input(
                '\n' + _('That module has multiple timelines, '
                         'which ones would you like to render?'
                         '\nTimeline Name or Number: ')
            )
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
    '''
    从指定的 ``module`` 中得到所有可用的 :class:`~.Timeline`

    会缓存结果，如果 ``module`` 的内容有更新可能需要使用 ``get_all_timelines_from_module.cache_clear()`` 来清空缓存
    '''
    classes = [
        value
        for value in module.__dict__.values()
        if (isinstance(value, type)
            and issubclass(value, Timeline)
            and value.__module__ == module.__name__                             # 定义于当前模块，排除了 import 导入的
            and not getattr(value.construct, '__isabstractmethod__', False))    # construct 方法已被实现
    ]
    if len(classes) <= 1:
        return classes

    def key(cls):
        try:
            return (0, inspect.getsourcelines(cls)[1])
        except OSError:
            # 对于重新载入的 module，如果代码里删除了某个类的代码，这个类仍然会出现在 module 中
            # 但是此时这个类无法获得到行数，所以会产生 OSError
            # 这里把已删除的类排序到最后
            return (1, 0)

    classes.sort(key=key)

    return classes


def open_file(file_path: str) -> None:
    '''
    打开指定的文件
    '''
    current_os = platform.system()
    if current_os == "Windows":
        os.startfile(file_path)
    else:
        commands = []
        if current_os == "Linux":
            commands.append("xdg-open")
        elif current_os.startswith("CYGWIN"):
            commands.append("cygstart")
        else:  # Assume macOS
            commands.append("open")

        commands.append(file_path)

        FNULL = open(os.devnull, 'w')
        sp.call(commands, stdout=FNULL, stderr=sp.STDOUT)
        FNULL.close()
