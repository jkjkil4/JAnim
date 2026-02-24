from contextlib import contextmanager
from dataclasses import dataclass

from rich.console import Console

console = Console()


@dataclass
class StepResult:
    returncode: int | None = None


@contextmanager
def step(start_message: str, name: str):
    _top_border(f'{start_message}', 'bold cyan')
    result = StepResult()

    try:
        yield result
    except KeyboardInterrupt:
        raise SystemExit(-1)

    if result.returncode is None:
        return

    if result.returncode != 0:
        _bottom_border(
            f'{name} failed with code {result.returncode}',
            'bold red',
        )
        raise SystemExit(result.returncode)
    _bottom_border(f'{name} completed', 'bold green')


def _top_border(message: str, style: str) -> None:
    border = f'╭──── {message}'
    console.print(border, style=style)


def _bottom_border(message: str, style: str) -> None:
    border = f'╰──── {message}'
    console.print(border, style=style)


def print_failed_list(failed_list: list) -> None:
    """
    Print a formatted list of failed items and summary.
    """
    if not failed_list:
        return

    console.print('\nFailed files:', style='bold red')
    for item in failed_list:
        # Handle both Path objects and strings
        display_name = item.name if hasattr(item, 'name') else str(item)
        console.print(f'  • {display_name}', style='red')
    console.print(
        f'\nCompleted with {len(failed_list)} files failed.',
        style='yellow',
    )


def prompt_todos(*todos: str) -> bool:
    """
    Print a formatted list of todo items and prompt user for confirmation.

    Returns True if user confirms (y), False otherwise (n)
    """
    assert todos

    console.print('\nTodos:', style='bold cyan')
    for i, text in enumerate(todos, 1):
        console.print(f'  {i}. {text}', style='cyan')
    console.print()

    response = console.input('[cyan]Continue? (y/N):[/cyan] ').strip().lower()
    return response in ('y', 'yes')
