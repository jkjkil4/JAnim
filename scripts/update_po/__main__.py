from __future__ import annotations

import os
import subprocess
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

from scripts import console, prompt_todos, step
from scripts.update_po.code import code_gettext, code_intl
from scripts.format_po import format_po_recursively
from scripts.update_po.tidy_sphinx_intl import tidy_sphinx_intl


def docs_main(lang: str) -> int:
    if lang == 'zh_CN':
        console.print(
            'Cannot generate translations for zh_CN because it is the source language for documentation.',
            style='red',
        )
        return 1

    project_root = Path(__file__).resolve().parents[2]
    doc_dir = project_root / 'doc'

    lc_dir = f'doc/source/locales/{lang}/LC_MESSAGES'

    ret = prompt_todos(
        'Extract translatable text from documentation to .pot files in doc/build/gettext',
        f'Generate .po files in doc/source/locales/{lang}/LC_MESSAGES from .pot files',
    )
    if not ret:
        return 0

    console.print()

    if os.name == 'nt':
        gettext_cmd = [doc_dir / 'make.bat', 'gettext']
    else:
        gettext_cmd = ['make', 'gettext']

    with step('Running gettext', 'gettext') as result:
        result.returncode = subprocess.run(gettext_cmd, cwd=doc_dir).returncode

    console.print()

    with step('Updating translation catalogs', 'Catalog update') as result:
        result.returncode = tidy_sphinx_intl(lang)

    console.print()

    with step('Formatting .po files', 'Formatting') as result:
        result.returncode = format_po_recursively(lc_dir)

    console.print(
        f'\nYou can edit .po files under {lc_dir}, '
        'either directly or with tools like Poedit.'
    )
    console.print(
        '\n[cyan]hint:[/cyan] Besides Poedit\'s built-in missing checks, '
        f'you can run `python scripts check-po docs {lang}` '
        'to list files with untranslated entries.'
    )
    console.print(
        '[cyan]hint:[/cyan] You don\'t need to compile .po files to .mo manually, '
        'because it is done automatically when building the docs.'
    )

    return 0


def code_main(lang: str, endswith: list[str] | None) -> int:
    if lang == 'en':
        console.print(
            'Cannot generate translations for en because it is the source language for code.',
            style='red',
        )
        return 1

    lc_dir = f'janim/locale/{lang}/LC_MESSAGES'

    ret = prompt_todos(
        'Extract _(\'...\') strings from .py source code to .pot files in janim/locale/source',
        f'Generate .po files in janim/locale/{lang}/LC_MESSAGES from .pot files',
    )
    if not ret:
        return 0

    console.print()

    with step('Running xgettext', 'xgettext') as result:
        code_gettext(endswith)
        result.returncode = 0

    console.print()

    with step('Updating translation catalogs', 'Catalog update') as result:
        code_intl(lang)
        result.returncode = 0

    console.print(
        f'\nYou can edit .po files under {lc_dir}, '
        'either direcrly or with tools like Poedit.'
    )
    console.print(
        '\n[cyan]hint:[/cyan] Besides Poedit\'s built-in missing checks, '
        f'you can run `python scripts check-po code {lang}` '
        'to list files with untranslated entries.'
    )
    console.print(
        '[cyan]hint:[/cyan] If you use Poedit, .mo files will be updated automatically. '
        f'If you edit files manually, run `python scripts compile-po code {lang}` '
        'to compile and update .mo files.'
    )


def main(target: str, lang: str, endswith: list[str] | None) -> int:
    if target == 'docs':
        return docs_main(lang)
    else:
        return code_main(lang, endswith)


if __name__ == '__main__':
    parser = ArgumentParser(
        description='Generate or update .po files for translating.',
        epilog='Examples:\n'
               '  python scripts update-po docs en\n'
               '  python scripts update-po code zh_CN\n'
               '  python scripts update-po code zh_CN --endswith value_tracker.py',
        formatter_class=RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'target',
        choices=['docs', 'code'],
        help='Update target: docs or code'
    )
    parser.add_argument(
        'lang',
        help='Language code (e.g., en, zh_CN)'
    )
    parser.add_argument(
        '--endswith',
        nargs='*',
        help=(
            'Only effective when target is "code". '
            'If omitted, extract messages from all .py files; '
            'if provided, extract only from .py file paths that end with any of the given suffixes.'
        )
    )
    args = parser.parse_args()

    raise SystemExit(main(args.target, args.lang, args.endswith))
