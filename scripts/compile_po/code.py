import subprocess
from pathlib import Path

from rich.progress import Progress

from scripts import console, print_failed_list


def code_compile(lang: str) -> int:
    """
    Compile .po files into .mo files.

    After editing .po file in Poedit, .mo could be updated automatically.
    For most cases, we don't need to execute code_compile for updating.
    """
    project_root = Path(__file__).resolve().parents[2]
    root = project_root / 'janim'
    po_dir = root / 'locale' / lang / 'LC_MESSAGES'

    if not po_dir.exists():
        console.print(f'Directory not found: {po_dir}', style='red')
        return 1

    po_files = sorted(po_dir.glob('*.po'))
    if not po_files:
        console.print('No .po files found.', style='cyan')
        return 0

    failed_list: list[Path] = []

    with Progress(console=console) as progress:
        task = progress.add_task('[cyan]Compiling...', total=len(po_files))

        for po_file in po_files:
            mo_file = po_file.with_suffix('.mo')
            cmd = ['msgfmt', '-o', str(mo_file), str(po_file)]
            result = subprocess.run(cmd)
            if result.returncode != 0:
                failed_list.append(po_file)

            progress.advance(task)

    print_failed_list(failed_list)
    console.print(
        f'Compiled {len(po_files) - len(failed_list)} catalogs for language: {lang}.'
    )

    if failed_list:
        return 2
    return 0
