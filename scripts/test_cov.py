from __future__ import annotations

import subprocess
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

from scripts import console, prompt_todos, step


def main(html: bool) -> int:
    # Prepare todo list
    todos = [
        'Run coverage run -m test to run test suite and analyze coverage',
    ]
    if html:
        todos.append('Generate coverage HTML report and open it')

    if not prompt_todos(*todos):
        return 0

    console.print()

    # Run coverage analysis
    with step('Running tests with coverage', 'Coverage analysis') as result:
        result.returncode = subprocess.run(
            ['coverage', 'run', '-m', 'test'],
        ).returncode

    # Generate HTML report if requested
    if html:
        console.print()

        with step('Generating coverage HTML report', 'HTML generation') as result:
            result.returncode = subprocess.run(['coverage', 'html']).returncode

        console.print()

        # Open the HTML report in default browser
        html_path = Path('htmlcov/index.html').resolve()
        if html_path.exists():
            import webbrowser
            webbrowser.open(f'file:///{html_path}')
            console.print(f'Opened coverage report at [cyan]{html_path}[/cyan]')
        else:
            console.print(f'HTML report not found at {html_path}', style='yellow')

    return 0


if __name__ == '__main__':
    parser = ArgumentParser(
        description='Run tests with coverage analysis',
        epilog='Example:\n'
               '  python scripts test-cov --html',
        formatter_class=RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--html',
        action='store_true',
        help='Generate HTML coverage report and open it in the default browser',
    )
    args = parser.parse_args()

    raise SystemExit(main(args.html))
