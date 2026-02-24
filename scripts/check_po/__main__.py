"""
Check .po files for untranslated (or fuzzy) entries using msgfmt --statistics.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from argparse import ArgumentParser
from pathlib import Path

from rich.console import Console
from rich.progress import Progress

console = Console()

_TRANSLATED_RE = re.compile(r'(\d+) translated')
_FUZZY_RE = re.compile(r'(\d+) fuzzy')
_UNTRANSLATED_RE = re.compile(r'(\d+) untranslated')


def _null_path() -> str:
    return 'NUL' if os.name == 'nt' else '/dev/null'


def _msgfmt_stats(path: Path) -> tuple[int, int, int] | None:
    msgfmt = shutil.which('msgfmt')
    if not msgfmt:
        console.print('msgfmt not found. Please install gettext and ensure msgfmt is in PATH.', style='red')
        return None

    env = os.environ.copy()
    env['LC_ALL'] = 'C'
    result = subprocess.run(
        [msgfmt, '--statistics', str(path), '-o', _null_path()],
        capture_output=True,
        text=True,
        env=env,
    )
    output = (result.stderr or '') + (result.stdout or '')
    translated_match = _TRANSLATED_RE.search(output)
    fuzzy_match = _FUZZY_RE.search(output)
    untranslated_match = _UNTRANSLATED_RE.search(output)
    if not any([translated_match, fuzzy_match, untranslated_match]):
        if result.returncode != 0 and output:
            console.print(output.strip(), style='red')
        console.print(f'Failed to parse msgfmt output for: {path}', style='red')
        return None

    translated = int(translated_match.group(1)) if translated_match else 0
    fuzzy = int(fuzzy_match.group(1)) if fuzzy_match else 0
    untranslated = int(untranslated_match.group(1)) if untranslated_match else 0
    return translated, fuzzy, untranslated


def main(target: str, lang: str) -> int:
    # Resolve the LC_MESSAGES path and ensure it exists.
    if target == 'docs':
        root = Path('doc/source/locales') / lang / 'LC_MESSAGES'
    else:
        root = Path('janim/locale') / lang / 'LC_MESSAGES'
    if not root.exists():
        console.print(f'Directory not found: {root}', style='red')
        return 1

    # Collect all .po files under the target directory.
    po_files = sorted(root.rglob('*.po'))
    if not po_files:
        console.print('No .po files found.', style='cyan')
        return 0

    # Check and collect untranslated entry counts.
    missing_entries: list[tuple[Path, int]] = []
    skipped_files: list[Path] = []

    with Progress(console=console) as progress:
        task = progress.add_task('[cyan]Checking...', total=len(po_files))
        for po in po_files:
            stats = _msgfmt_stats(po)
            if stats is None:
                rel_path = po.relative_to(root)
                skipped_files.append(rel_path)
                progress.advance(task)
                continue
            _, fuzzy, untranslated = stats
            missing = fuzzy + untranslated
            if missing:
                rel_path = po.relative_to(root)
                missing_entries.append((rel_path, missing))
            progress.advance(task)

    # Final report.
    if not missing_entries and not skipped_files:
        console.print('No untranslated entries found.', style='green')
        return 0

    exit_code = 0
    if missing_entries:
        total_missing = sum(count for _, count in missing_entries)
        console.print('\nFiles with untranslated entries:', style='bold yellow')
        for rel_path, missing in missing_entries:
            console.print(f'  • {rel_path} ({missing})', style='yellow')
        console.print(f'\nTotal untranslated entries: {total_missing}.', style='bold yellow')
        exit_code = 2

    if skipped_files:
        console.print('\nSkipped files:', style='bold red')
        for rel_path in skipped_files:
            console.print(f'  • {rel_path}', style='red')
        if exit_code == 0:
            exit_code = 1

    return exit_code


if __name__ == '__main__':
    parser = ArgumentParser(description='Check .po files for untranslated (or fuzzy) entries.')
    parser.add_argument('target', choices=['docs', 'code'], help='Check target: docs or code')
    parser.add_argument('lang', help='Language code (e.g., en)')
    args = parser.parse_args()

    raise SystemExit(main(args.target, args.lang))
