import os

import click
import cloup
from dataclass_click import dataclass_click

from janim.cli.options import (
    FormatOptions,
    HardwareOptions,
    LiveOptions,
    OutputOptions,
    RangeOptions,
    SharedOptions,
)
from janim.cli.toplevel import toplevel_group
from janim.locale import get_translator
from janim.utils.file_ops import get_janim_dir

_ = get_translator('janim.cli.parse')

help_option = click.help_option('-h', '--help')
DEFAULT_SECTION = cloup.Section('Commands')


@toplevel_group
@help_option
@click.option('--lang', help=_('Language code, e.g., en, zh_CN'))
@click.option('-v', '--version', is_flag=True)
@click.option(
    '--loglevel',
    default='INFO',
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], case_sensitive=False),
    help=_('Set the logging level (default: INFO)'),
)
@click.pass_context
def cli(ctx: click.Context, lang, version, loglevel) -> None:
    # fmt: off
    if version:
        from janim import __version__
        click.echo(f'JAnim {__version__}')

    if ctx.invoked_subcommand is None:
        if not version:
            click.echo(ctx.get_help())
        ctx.exit()

    from janim.logger import log
    log.setLevel(loglevel)
    # fmt: on


file_argument = click.argument(
    'file',
    metavar='<FILE>',
)
timeline_names_argument = click.argument(
    'timeline_names',
    nargs=-1,
    metavar='<TIMELINE>',
)


@cli.command(
    'run',
    help=_(
        'Preview timeline classes\n'
        '\n'
        "<FILE>      Python source file to load. Use '-' to read from stdin\n"
        '\n'
        '<TIMELINE>  Timeline class names to preview'
    ),
    section=DEFAULT_SECTION,
)
@help_option
@file_argument
@timeline_names_argument
@dataclass_click(SharedOptions, kw_name='shared_options')
@dataclass_click(LiveOptions, kw_name='live_options')
def run(**kwargs):
    from janim.cli.execute import run  # 目的是 lazy import 减轻 CLI help overhead

    run(**kwargs)


@cli.command(
    'write',
    help=_(
        'Export media files of timeline classes\n'
        '\n'
        "<FILE>      Python source file to load. Use '-' to read from stdin\n"
        '\n'
        '<TIMELINE>  Timeline class names to export'
    ),
    section=DEFAULT_SECTION,
)
@help_option
@file_argument
@timeline_names_argument
@dataclass_click(SharedOptions, kw_name='shared_options')
@click.option(
    '-o', '--open',
    is_flag=True,
    help=_('Open the video after writing'),
)  # fmt: skip
@cloup.option_group(
    _('Format Options'),
    _('Options for specifying the format of the output files'),
    dataclass_click(FormatOptions, kw_name='format_options'),
)
@cloup.option_group(
    _('Output Options'),
    _('Options for specifying the parts to be written'),
    dataclass_click(OutputOptions, kw_name='output_options'),
)
@cloup.option_group(
    _('Range Options'),
    _('Options for specifying in/out point'),
    dataclass_click(RangeOptions, kw_name='range_options'),
)
@cloup.option_group(
    _('Hardware Options'),
    _('Hardware options for writing the output files'),
    dataclass_click(HardwareOptions, kw_name='hardware_options'),
)
def write(**kwargs):
    from janim.cli.execute import write  # 目的是 lazy import 减轻 CLI help overhead

    write(**kwargs)


@cli.command(
    'examples',
    help=_(
        'Show examples of JAnim\n'
        '\n'
        '<TIMELINE>  Timeline class names to see'
    ),
    section=DEFAULT_SECTION,
)  # fmt: skip
@help_option
@timeline_names_argument
def examples(timeline_names):
    from janim.cli.execute import run  # 目的是 lazy import 减轻 CLI help overhead

    run(
        os.path.join(get_janim_dir(), 'examples.py'),
        timeline_names,
        SharedOptions(False, (), False, False),
        LiveOptions(False, False),
    )


available_tools = ['richtext', 'fonts', 'color']
tool_names = '{' + '|'.join(available_tools) + '}'


@cli.command(
    'tool',
    help=_(
        'Run useful tools\n'
        '\n'
        '{tool_names}  Tool(s) that you want to use'
    ).format(tool_names=tool_names),
    section=DEFAULT_SECTION,
)  # fmt: skip
@help_option
@click.argument(
    'tool_name',
    type=click.Choice(available_tools),
    nargs=-1,
    required=True,
)
def tool(tool_name: tuple[str, ...]):
    from janim.cli.execute import tool  # 目的是 lazy import 减轻 CLI help overhead

    tool(tool_name)
