from __future__ import annotations

import runpy
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parent


def _iter_available_commands() -> list[str]:
    commands: list[str] = []
    # Collect top-level script files as commands.
    for path in SCRIPTS_DIR.glob('*.py'):
        if path.name in ('__main__.py', '__init__.py'):
            continue
        commands.append(path.stem.replace('_', '-'))
    # Collect subdirectories that provide a __main__.py entrypoint.
    for path in SCRIPTS_DIR.iterdir():
        if not path.is_dir():
            continue
        if (path / '__main__.py').exists():
            commands.append(path.name.replace('_', '-'))
    return sorted(commands)


def _print_usage() -> int:
    prog = Path(sys.argv[0]).name
    print(f'Usage: {prog} <command> [args...]')
    print()
    print('Available commands:')
    for cmd in _iter_available_commands():
        print(f'  {cmd}')
    return 1


def main() -> int:
    if len(sys.argv) < 2:
        return _print_usage()

    raw_command = sys.argv[1]
    command = raw_command.replace('-', '_')
    file_path = SCRIPTS_DIR / f'{command}.py'
    dir_path = SCRIPTS_DIR / command
    dir_main_path = dir_path / '__main__.py'

    if file_path.exists():
        script_path = file_path
    elif dir_main_path.exists():
        script_path = dir_main_path
    else:
        print(f'Unknown command: {raw_command}')
        print()
        return _print_usage()

    original_argv = sys.argv[:]
    sys.argv = [str(script_path), *sys.argv[2:]]
    try:
        runpy.run_path(str(script_path), run_name='__main__')
        return 0
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        if isinstance(code, int):
            return code
        print(code, file=sys.stderr)
        return 1
    finally:
        sys.argv = original_argv


if __name__ == '__main__':
    raise SystemExit(main())
