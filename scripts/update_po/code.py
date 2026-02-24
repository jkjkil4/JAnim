import subprocess
import sys
from pathlib import Path

from rich.progress import Progress
from scripts import console, print_failed_list


def code_gettext(endswith: list[str] | None) -> int:
    if endswith is not None:
        endswith = [x.replace('\\', '/') for x in endswith]

    def matches(file: str) -> bool:
        return not endswith or any(file.endswith(x) for x in endswith)

    project_root = Path(__file__).resolve().parents[2]
    root = Path(project_root / 'janim')

    pot_dir = root / 'locale' / 'source'
    pot_dir.mkdir(parents=True, exist_ok=True)

    source_files = [
        file.relative_to(project_root).as_posix()
        for file in root.rglob('*.py')
    ]
    filtered = list(filter(matches, source_files))

    failed_list: list[str] = []

    with Progress(console=console) as progress:
        task = progress.add_task('[cyan]Extracting...', total=len(filtered))

        for source in filtered:
            module_name = source.removesuffix('.py').replace('/', '.')
            dist = pot_dir / f'{module_name}.pot'
            dist.parent.mkdir(parents=True, exist_ok=True)
            cmd = ['xgettext', '-o', str(dist), source]
            # print(' '.join(cmd))

            # Sometimes, URL is language-specific and intentionally part of the message
            # we need to ignore "Message contains an embedded URL" warnings, looks like:
            #
            # warning: Message contains an embedded URL.
            # Better move it out of the translatable string,
            # see https://www.gnu.org/software/gettext/manual/html_node/No-embedded-URLs.html
            #
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                failed_list.append(source)
            for line in result.stderr.splitlines():
                if 'Message contains an embedded URL' not in line:
                    print(line, file=sys.stderr)

            progress.advance(task)

    print_failed_list(failed_list)
    console.print(
        f'Extracted {len(filtered) - len(failed_list)} .pot files.'
    )

    if failed_list:
        return 2
    return 0


def code_intl(lang: str) -> int:
    project_root = Path(__file__).resolve().parents[2]
    root = project_root / 'janim'
    pot_dir = root / 'locale' / 'source'
    po_dir = root / 'locale' / lang / 'LC_MESSAGES'

    if not pot_dir.exists():
        console.print(f'Directory not found: {pot_dir}', style='red')
        return 1

    po_files = sorted(pot_dir.glob('*.pot'))
    if not po_files:
        console.print('No .pot files found.', style='cyan')
        return 0

    po_dir.mkdir(parents=True, exist_ok=True)

    failed_list: list[Path] = []

    with Progress(console=console) as progress:
        task = progress.add_task(
            '[cyan]Updating...', total=len(po_files)
        )

        for pot_file in po_files:
            po_file = po_dir / pot_file.with_suffix('.po').name
            if not po_file.exists():
                cmd = [
                    'msginit',
                    '-i',
                    str(pot_file),
                    '-o',
                    str(po_file),
                    '-l',
                    lang,
                    '--no-translator',
                ]
            else:
                cmd = ['msgmerge', '-U', str(po_file), str(pot_file), '--backup=off']

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                failed_list.append(pot_file)

            progress.advance(task)

    print_failed_list(failed_list)
    console.print(
        f'Initialized/merged {len(po_files) - len(failed_list)} catalogs for language: {lang}.'
    )

    if failed_list:
        return 2
    return 0
