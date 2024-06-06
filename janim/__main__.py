import os
from argparse import ArgumentParser, Namespace

from janim.locale.i18n import get_local_strings, set_lang
from janim.utils.file_ops import get_janim_dir

_ = get_local_strings('__main__')


def main() -> None:
    global _

    initial_parser = ArgumentParser(add_help=False)
    initial_parser.add_argument('--lang')
    initial_args = initial_parser.parse_known_args()[0]

    if initial_args.lang:
        set_lang(initial_args.lang)
        _ = get_local_strings('__main__')

    parser = ArgumentParser(description=_('A library for simple animation effects'))
    parser.set_defaults(func=None)

    parser.add_argument(
        '--lang',
        help=_('Language code, e.g., en, zh_CN')
    )
    parser.add_argument(
        '-v', '--version',
        action='store_true'
    )

    sp = parser.add_subparsers()
    run_parser(sp.add_parser('run', help=_('Run timeline(s) from specific file')))
    write_parser(sp.add_parser('write', help=_('Generate media file(s) of timeline(s) from specific file')))
    examples_parser(sp.add_parser('examples', help=_('Show examples of JAnim')))
    tool_parser(sp.add_parser('tool', help=_('Run useful tools')))

    args = parser.parse_args()

    if args.version:
        from janim import __version__
        print(f'JAnim {__version__}')

    if args.func is None:
        if not args.version:
            parser.print_help()
        return

    args.func(args)


def render_args(
    parser: ArgumentParser,
    timeline_names_help: str,
    all_help: str
) -> None:
    parser.add_argument(
        'filepath',
        help=_('Path to file holding the Python code')
    )
    parser.add_argument(
        'timeline_names',
        nargs='*',
        help=timeline_names_help
    )
    parser.add_argument(
        '-a', '--all',
        action='store_true',
        help=all_help
    )
    parser.add_argument(
        '-c', '--config',
        nargs=2,
        metavar=('key', 'value'),
        action='append',
        help=_('Override config')
    )


def run_parser(parser: ArgumentParser) -> None:
    render_args(
        parser,
        _('Name of the Timeline class you want to preview'),
        _('Preview all timelines from a file')
    )
    parser.add_argument(
        '-i', '--interact',
        action='store_true',
        help=_('Enable the network socket for interacting with vscode')
    )
    parser.set_defaults(func=run)


def write_parser(parser: ArgumentParser) -> None:
    render_args(
        parser,
        _('Name of the Timeline class you want to write'),
        _('Write all timelines from a file')
    )
    parser.add_argument(
        '-o', '--open',
        action='store_true',
        help=_('Open the video after writing')
    )
    parser.add_argument(
        '--format',
        choices=['mp4', 'mov'],
        default='mp4',
        help=_('Format of the output video')
    )
    parser.add_argument(
        '--audio_format',
        default='mp3',
        help=_('Format of the output audio')
    )
    parser.add_argument(
        '--video',
        action='store_true',
        help=_('Video only')
    )
    parser.add_argument(
        '--audio',
        action='store_true',
        help=_('Audio only')
    )
    parser.set_defaults(func=write)


def examples_parser(parser: ArgumentParser) -> None:
    parser.set_defaults(filepath=os.path.join(get_janim_dir(), 'examples.py'))
    parser.add_argument(
        'timeline_names',
        nargs='*',
        help=_('Name of the example you want to see')
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
        help=_('Tool(s) that you want to use')
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
