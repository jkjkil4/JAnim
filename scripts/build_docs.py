from __future__ import annotations

import subprocess
import tarfile
from argparse import ArgumentParser
from pathlib import Path

from scripts import console, prompt_todos, step


def build_i18n_docs(
    lang: str,
    force: bool = False,
    open_docs: bool = False,
    pack: bool = False,
) -> int:
    """
    Build internationalized documentation using Sphinx.

    Args:
        lang: Language code (e.g., 'zh_CN', 'en')
        force: Use -E flag to force full rebuild
        open_docs: Open the built documentation in browser
        pack: Package the built documentation as tar file

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    project_root = Path(__file__).resolve().parents[1]
    doc_dir = project_root / 'doc'
    source_dir = doc_dir / 'source'
    output_dir = doc_dir / 'build' / 'html_i18n' / lang

    # Build the list of todos
    todos = [f'Build documentation for {lang}']
    if force:
        todos[0] += ' (with clean rebuild)'
    if open_docs:
        todos.append('Open built documentation in browser')
    if pack:
        todos.append('Package documentation as tar file')

    # Prompt user for confirmation
    if not prompt_todos(*todos):
        return 0

    console.print()

    # Build sphinx-build command
    sphinx_cmd = [
        'sphinx-build',
        '-b', 'html',
        '-D', f'language={lang}',
    ]

    if force:
        sphinx_cmd.append('-E')

    sphinx_cmd.extend([
        str(source_dir),
        str(output_dir),
    ])

    # Run sphinx-build from doc directory
    description = f'Building documentation for {lang}'
    if force:
        description += ' (clean build)'

    with step(description, 'Documentation build') as result:
        result.returncode = subprocess.run(sphinx_cmd, cwd=doc_dir).returncode

    if result.returncode != 0:
        return result.returncode

    # Open documentation if requested
    if open_docs:
        console.print()

        index_file = output_dir / 'index.html'
        if index_file.exists():
            import webbrowser
            webbrowser.open(str(index_file))
            console.print(f'Opened documentation at "{index_file}"', style='green')
        else:
            console.print(f'Warning: index.html not found at "{index_file}"', style='yellow')

    # Package documentation if requested
    if pack:
        console.print()

        from janim import __version__
        tar_filename = f'JAnim Documentation {lang} {__version__}.tar'
        tar_path = doc_dir / 'build' / tar_filename

        console.print(f'Packaging documentation as "{tar_filename}"', style='cyan')

        try:
            # Remove existing tar if it exists
            if tar_path.exists():
                tar_path.unlink()

            # Create tar file
            with tarfile.open(tar_path, 'w') as tar:
                tar.add(
                    output_dir,
                    arcname=f'JAnim Documentation {lang} {__version__}',
                )
        except Exception as e:
            console.print(f'Error creating tar file: {e}', style='red')
            result.returncode = 1
        else:
            console.print(f'Packaged documentation at "{tar_path}"', style='green')
            result.returncode = 0

    return 0


def main(
    lang: str,
    force: bool = False,
    open_docs: bool = False,
    pack: bool = False,
) -> int:
    """Main entry point for building documentation."""
    return build_i18n_docs(lang, force, open_docs, pack)


if __name__ == '__main__':
    parser = ArgumentParser(
        description='Build internationalized documentation using Sphinx.',
    )

    parser.add_argument(
        'lang',
        help='Language code (e.g., zh_CN, en)',
    )

    parser.add_argument(
        '-e', '-f', '--force',
        action='store_true',
        dest='force',
        help='Force full rebuild. '
             'Use this if Sphinx does not update as expected in some cases.',
    )

    parser.add_argument(
        '-o', '--open',
        action='store_true',
        dest='open_docs',
        help='Open the built documentation in browser after build completes',
    )

    parser.add_argument(
        '--pack',
        action='store_true',
        help='Package the built documentation as tar file '
             'named "JAnim Documentation {lang} {version}.tar"',
    )

    args = parser.parse_args()

    raise SystemExit(main(args.lang, args.force, args.open_docs, args.pack))
