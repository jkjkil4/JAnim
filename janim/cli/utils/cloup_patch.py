"""
由于 ``cloup`` 和 ``dataclass_click`` 不兼容，这里是对 ``cloup`` 原有代码的 patch
"""

from typing import Any, Callable, Optional, Sequence

import click
from cloup import Option, OptionGroup  # noqa
from cloup.constraints import Constraint
from cloup.typing import F


def get_option_group_of(param: click.Option) -> Optional[OptionGroup]:
    return getattr(param, 'group', None)


def option_group(title: str, *args: Any, **kwargs: Any) -> Callable[[F], F]:
    if args and isinstance(args[0], str):
        return _option_group(title, options=args[1:], help=args[0], **kwargs)
    else:
        return _option_group(title, options=args, **kwargs)


def _option_group(
    title: str,
    options: Sequence[Callable[[F], F]],
    help: Optional[str] = None,
    constraint: Optional[Constraint] = None,
    hidden: bool = False,
) -> Callable[[F], F]:
    if not isinstance(title, str):
        raise TypeError(
            'the first argument of `@option_group` must be its title, a string; '
            'you probably forgot it'
        )

    if not options:
        raise ValueError('you must provide at least one option')

    def decorator(f: F) -> F:
        opt_group = OptionGroup(title, help=help, constraint=constraint, hidden=hidden)
        if not hasattr(f, '__click_params__'):
            f.__click_params__ = []  # type: ignore
        cli_params = f.__click_params__  # type: ignore
        for add_option in reversed(options):
            prev_len = len(cli_params)
            f = add_option(f)  # 将 add_option(f) 修改为了 f = add_option(f)
            added_options = cli_params[prev_len:]
            for new_option in added_options:
                # if not isinstance(new_option, Option):
                #     raise TypeError('only parameter of type `Option` can be added to option groups')
                existing_group = get_option_group_of(new_option)
                if existing_group is not None:
                    raise ValueError(
                        f'Option "{new_option}" was first assigned to group '
                        f'"{existing_group}" and then passed as argument to '
                        f'`@option_group({title!r}, ...)`'
                    )
                new_option.group = opt_group  # type: ignore
                if hidden:
                    new_option.hidden = True
        return f

    return decorator
