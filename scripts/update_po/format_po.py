from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from rich.progress import Progress

from scripts import console, print_failed_list


def format_po_recursively(dirpath: str) -> int:
    """
    Format .po files in a directory to use consistent line wrapping strategy.

    sphinx-intl generated .po files have different line wrapping behavior compared to Poedit
    and gettext defaults, which introduces noise in git commits. This function reformats them
    to maintain consistency.
    """

    root = Path(dirpath)

    if not root.exists():
        console.print(f'Directory not found: {root}', style='red')
        return 1

    msgcat = shutil.which('msgcat')
    if not msgcat:
        console.print('msgcat not found. Please install gettext and ensure msgcat is in PATH.', style='red')
        return 1

    po_files = sorted(root.rglob('*.po'))
    if not po_files:
        console.print('No .po files found.', style='cyan')
        return 0

    failed_list: list[Path] = []

    with Progress(console=console) as progress:
        task = progress.add_task('[cyan]Formatting...', total=len(po_files))

        for po in po_files:
            newline = detect_newline(po)
            cmd = [msgcat, '--width=124', str(po)]
            try:
                result = subprocess.run(cmd, check=True, capture_output=True)
                po.write_bytes(normalize_newline(result.stdout, newline))
            except subprocess.CalledProcessError:
                failed_list.append(po)

            progress.advance(task)

    print_failed_list(failed_list)
    console.print(
        f'Formatted {len(po_files) - len(failed_list)} .po files.'
    )

    if failed_list:
        return 2
    return 0


def detect_newline(path: Path) -> bytes:
    content = path.read_bytes()
    if b'\r\n' in content:
        return b'\r\n'
    return b'\n'


def normalize_newline(content: bytes, newline: bytes) -> bytes:
    normalized = content.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
    if newline == b'\r\n':
        return normalized.replace(b'\n', b'\r\n')
    return normalized
