from __future__ import annotations

from argparse import ArgumentParser

from scripts import console, prompt_todos
from scripts.compile_po.code import code_compile


def docs_main(lang: str) -> int:
    console.print(
        'hint: You don\'t need to compile .po files to .mo manually '
        'for docs, because it is done automatically when building the docs.',
        style='cyan',
    )
    return 0


def code_main(lang: str) -> int:
    ret = prompt_todos(
        f'Compile .po files to .mo files in janim/locale/{lang}/LC_MESSAGES',
    )
    if not ret:
        return 0

    console.print()

    return code_compile(lang)


def main(target: str, lang: str) -> int:
    if target == 'docs':
        return docs_main(lang)
    else:
        return code_main(lang)


if __name__ == '__main__':
    parser = ArgumentParser(description='Compile .po files to .mo files.')
    parser.add_argument(
        'target',
        choices=['docs', 'code'],
        help='Compile target: docs (no-op, docs are compiled automatically) or code',
    )
    parser.add_argument(
        'lang',
        help='Language code (e.g., en, zh_CN)',
    )
    args = parser.parse_args()

    raise SystemExit(main(args.target, args.lang))
