import cloup
from cloup import HelpFormatter, HelpTheme, Style

__all__ = [
    'toplevel_group',
]


formatter_settings = HelpFormatter.settings(
    theme=HelpTheme(
        invoked_command=Style(fg='bright_yellow'),
        heading=Style(fg='bright_white', bold=True),
        constraint=Style(fg='magenta'),
        col1=Style(fg='bright_yellow'),
    )
)


toplevel_group = cloup.group(
    invoke_without_command=True,
    context_settings={'formatter_settings': formatter_settings},
)
