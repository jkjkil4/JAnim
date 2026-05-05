from __future__ import annotations

import subprocess
from pathlib import Path
from threading import Lock, Thread

from scripts import console


def tidy_sphinx_intl(lang: str) -> int:
    """
    Tidy translation catalogs by updating them via sphinx-intl.

    This function streams output and summarizes 'Not Changed' lines to keep logs readable.
    """

    project_root = Path(__file__).resolve().parents[2]
    doc_dir = project_root / 'doc'

    proc = subprocess.Popen(
        ['sphinx-intl', 'update', '-p', 'build/gettext', '-l', lang],
        cwd=doc_dir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
    )
    if proc.stdout is None or proc.stderr is None:
        raise RuntimeError('Failed to capture subprocess output.')

    not_changed_count = 0
    not_changed_lock = Lock()

    # Aggregate 'Not Changed' lines to avoid flooding the output while streaming.
    def handle_stream(stream) -> None:
        nonlocal not_changed_count
        for line in iter(stream.readline, ''):
            if line.lstrip().startswith('Not Changed:'):
                with not_changed_lock:
                    not_changed_count += 1
                continue
            console.print(line.rstrip('\n'), markup=False)

    threads = [
        Thread(target=handle_stream, args=(proc.stdout,)),
        Thread(target=handle_stream, args=(proc.stderr,)),
    ]
    for thread in threads:
        thread.start()

    returncode = proc.wait()
    for thread in threads:
        thread.join()

    if not_changed_count:
        console.print(f'{not_changed_count} files not changed.', markup=False)

    return returncode
