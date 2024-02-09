import importlib
import time
import sys
import os
import platform
import subprocess as sp
from argparse import ArgumentParser, Namespace

from janim.anims.timeline import Timeline
from janim.logger import log
from janim.utils.config import Config, default_config


def main() -> None:
    parser = ArgumentParser(description='A library for simple animation effects')
    parser.set_defaults(func=None)

    sp = parser.add_subparsers()
    run_parser(sp.add_parser('run', help='Run timeline(s) from specific namespace'))
    write_parser(sp.add_parser('write', help='Generate video file(s) of timeline(s) from specific namesapce'))
    examples_parser(sp.add_parser('examples', help='Show examples of janim'))

    args = parser.parse_args()
    if args.func is None:
        parser.print_help()
    else:
        args.func(args)


def render_args(parser: ArgumentParser) -> None:
    parser.add_argument(
        'namespace',
        help='Namespace to file holding the python code for the timeline'
    )
    parser.add_argument(
        'timeline_names',
        nargs='*',
        help='Name of the Timeline class you want to see'
    )
    parser.add_argument(
        '-a', '--all',
        action='store_true',
        help='Render all timelines from a file'
    )
    parser.add_argument(
        '-c', '--config',
        nargs=2,
        metavar=('key', 'value'),
        action='append',
        help='Override config'
    )


def run_parser(parser: ArgumentParser) -> None:
    render_args(parser)
    parser.set_defaults(func=run)


def write_parser(parser: ArgumentParser) -> None:
    render_args(parser)
    parser.add_argument(
        '-o', '--open',
        action='store_true',
        help='Open the file after writing'
    )
    parser.set_defaults(func=write)


def examples_parser(parser: ArgumentParser) -> None:
    parser.set_defaults(namespace='janim.examples')
    parser.add_argument(
        'timeline_names',
        nargs='*',
        help='Name of the example you want to see'
    )
    parser.set_defaults(all=None)
    parser.set_defaults(config=None)
    parser.set_defaults(func=run)


def run(args: Namespace) -> None:
    module = get_module(args.namespace)
    if module is None:
        return
    modify_default_config(args)

    timelines = extract_timelines_from_module(args, module)
    if not timelines:
        return

    auto_play = len(timelines) == 1

    from PySide6.QtCore import QPoint, QTimer
    from janim.gui.anim_viewer import AnimViewer
    from janim.gui.application import Application

    app = Application()

    log.info('======')

    widgets: list[AnimViewer] = []
    for timeline in timelines:
        viewer = AnimViewer(timeline().build(), auto_play)
        widgets.append(viewer)

    log.info('======')
    log.info('Constructing window')

    t = time.time()

    if sys.platform.startswith('win'):
        import ctypes

        desktop = ctypes.windll.user32.GetDesktopWindow()
        ctypes.windll.user32.SetForegroundWindow(desktop)

    for i, widget in enumerate(widgets):
        if i != 0:
            widget.move(widgets[i - 1].pos() + QPoint(24, 24))
        widget.show()

    QTimer.singleShot(100, widgets[-1].activateWindow)

    log.info(f'Finished constructing in {time.time() - t:.2f} s')
    log.info('======')

    app.exec()


def write(args: Namespace) -> None:
    module = get_module(args.namespace)
    if module is None:
        return
    modify_default_config(args)

    timelines = extract_timelines_from_module(args, module)
    if not timelines:
        return

    from janim.render.file_writer import FileWriter

    log.info('======')

    built = [timeline().build() for timeline in timelines]

    log.info('======')

    output_dir = os.path.normpath(Config.get.output_dir)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    log.info(f'fps={Config.get.fps}')
    log.info(f'resolution="{Config.get.pixel_width}x{Config.get.pixel_height}"')
    log.info(f'output_dir="{output_dir}"')

    log.info('======')

    for anim in built:
        writer = FileWriter(anim)
        writer.write_all(os.path.join(Config.get.output_dir, anim.timeline.__class__.__name__))
        if args.open and anim is built[-1]:
            open_file(writer.final_file_path)

    log.info('======')


def modify_default_config(args: Namespace) -> None:
    if args.config:
        for key, value in args.config:
            dtype = type(getattr(default_config, key))
            setattr(default_config, key, dtype(value))


def get_module(namespace: str):
    try:
        return importlib.import_module(namespace)
    except ModuleNotFoundError:
        log.error(f'No module named "{namespace}"')
        return None


def extract_timelines_from_module(args: Namespace, module) -> list[type[Timeline]]:
    timelines = []
    err = False

    if not args.all and args.timeline_names:
        for name in args.timeline_names:
            try:
                timelines.append(module.__dict__[name])
            except KeyError:
                log.error(f'No timeline named "{name}"')
                err = True
    else:
        import inspect

        classes = [
            value
            for value in module.__dict__.values()
            if isinstance(value, type) and issubclass(value, Timeline) and value.__module__ == module.__name__
        ]
        if len(classes) <= 1:
            return classes
        classes.sort(key=lambda x: inspect.getsourcelines(x)[1])
        if args.all:
            return classes

        max_digits = len(str(len(classes)))

        name_to_class = {}
        for idx, timeline_class in enumerate(classes, start=1):
            name = timeline_class.__name__
            print(f"{str(idx).zfill(max_digits)}: {name}")
            name_to_class[name] = timeline_class

        user_input = input(
            "\nThat module has multiple timelines, "
            "which ones would you like to render?"
            "\nTimeline Name or Number: "
        )
        for split_str in user_input.replace(' ', '').split(','):
            if not split_str:
                continue
            if split_str.isnumeric():
                idx = int(split_str) - 1
                if 0 <= idx < len(classes):
                    timelines.append(classes[idx])
                else:
                    log.error(f'Invaild number {idx + 1}')
                    err = True
            else:
                try:
                    timelines.append(name_to_class[split_str])
                except KeyError:
                    log.error(f'No timeline named {split_str}')
                    err = True

    return [] if err else timelines


def open_file(file_path: str) -> None:
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


if __name__ == '__main__':
    main()
