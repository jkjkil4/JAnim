import importlib
import time
import sys
from argparse import ArgumentParser, Namespace

from janim.anims.timeline import Timeline
from janim.logger import log


def main() -> None:
    parser = ArgumentParser(description='A library for simple animation effects')
    parser.set_defaults(func=None)

    sp = parser.add_subparsers()
    run_parser(sp.add_parser('run', help='Run a timeline from specific namespace'))

    args = parser.parse_args()
    if args.func is None:
        parser.print_help()
    else:
        args.func(args)


def run(args: Namespace):
    try:
        module = importlib.import_module(args.namespace)
    except ModuleNotFoundError:
        log.error(f'No module named \'{args.namespace}\'')
        return

    timelines = extract_timelines_from_module(args, module)
    if not timelines:
        return

    auto_play = len(timelines) == 1

    from PySide6.QtCore import QPoint, QTimer
    from janim.gui.anim_viewer import AnimViewer
    from janim.gui.application import Application

    app = Application()

    widgets: list[AnimViewer] = []
    for timeline in timelines:
        viewer = AnimViewer(timeline().build(), auto_play)
        widgets.append(viewer)

    t = time.time()

    log.info('Constructing window')

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

    app.exec()


def run_parser(parser: ArgumentParser) -> None:
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
        action='store_false',
        help='Render all timelines from a file'
    )
    parser.set_defaults(func=run)


def extract_timelines_from_module(args: Namespace, module) -> list[type[Timeline]]:
    timelines = []
    err = False

    if args.timeline_names:
        for name in args.timeline_names:
            try:
                timelines.append(module.__dict__[name])
            except KeyError:
                log.error(f'No timeline named \'{name}\'')
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


if __name__ == '__main__':
    main()
