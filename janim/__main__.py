import os
from argparse import ArgumentParser, Namespace

from janim.utils.file_ops import get_janim_dir


def main() -> None:
    parser = ArgumentParser(description='A library for simple animation effects')
    parser.set_defaults(func=None)

    parser.add_argument(
        '-v', '--version',
        action='store_true'
    )

    sp = parser.add_subparsers()
    run_parser(sp.add_parser('run', help='Run timeline(s) from specific namespace'))
    write_parser(sp.add_parser('write', help='Generate video file(s) of timeline(s) from specific namesapce'))
    examples_parser(sp.add_parser('examples', help='Show examples of janim'))
    tool_parser(sp.add_parser('tool', help='Run useful tools'))

    args = parser.parse_args()

    if args.version:
        from janim import __version__
        print(f'JAnim {__version__}')

    if args.func is None:
        if not args.version:
            parser.print_help()
        return

    args.func(args)


def render_args(parser: ArgumentParser) -> None:
    parser.add_argument(
        'filepath',
        help='Path to file holding the python code for the timeline'
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
    parser.add_argument(
        '-i', '--interact',
        action='store_true',
        help='Enable the network socket for interacting'
    )
    parser.set_defaults(func=run)


def write_parser(parser: ArgumentParser) -> None:
    render_args(parser)
    parser.add_argument(
        '-o', '--open',
        action='store_true',
        help='Open the video after writing'
    )
    parser.add_argument(
        '--format',
        choices=['mp4', 'mov'],
        default='mp4',
        help='Format of the output video'
    )
    parser.add_argument(
        '--audio_format',
        default='mp3',
        help='Format of the output audio'
    )
    parser.add_argument(
        '--video',
        action='store_true',
    )
    parser.add_argument(
        '--audio',
        action='store_true'
    )
    parser.set_defaults(func=write)


def examples_parser(parser: ArgumentParser) -> None:
    parser.set_defaults(filepath=os.path.join(get_janim_dir(), 'examples.py'))
    parser.add_argument(
        'timeline_names',
        nargs='*',
        help='Name of the example you want to see'
    )
    parser.set_defaults(all=None)
    parser.set_defaults(config=None)
    parser.set_defaults(func=run)
    parser.set_defaults(interact=False)


def tool_parser(parser: ArgumentParser) -> None:
    parser.add_argument(
        'tool_name',
        choices=['richtext', 'fonts'],
        nargs='*',
        help='Tool(s) that you want to use'
    )
    parser.set_defaults(func=tool)


def run(args: Namespace) -> None:
    from janim.cli import run
    run(args)


def write(args: Namespace) -> None:
    from janim.cli import write
    write(args)


def tool(args: Namespace) -> None:
    from janim.cli import tool
    tool(args)


if __name__ == '__main__':
    main()
