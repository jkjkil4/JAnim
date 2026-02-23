"""
Format .po files in a specified language to use consistent line wrapping strategy.

sphinx-intl generated .po files have different line wrapping behavior compared to Poedit
and gettext defaults, which introduces noise in git commits. This script reformats them
to maintain consistency.
"""

from __future__ import annotations

import shutil
import subprocess
from argparse import ArgumentParser
from pathlib import Path

from rich.console import Console
from rich.progress import Progress

console = Console()


def main(lang: str) -> int:
    root = Path(f"doc/source/locales/{lang}/LC_MESSAGES")

    if not root.exists():
        console.print(f"Directory not found: {root}", style="red")
        return 1

    msgcat = shutil.which("msgcat")
    if not msgcat:
        console.print("msgcat not found. Please install gettext and ensure msgcat is in PATH.", style="red")
        return 1

    po_files = sorted(root.rglob("*.po"))
    if not po_files:
        console.print("No .po files found.", style="cyan")
        return 0

    failed_list: list[Path] = []

    # Track progress using Rich Progress (like tqdm)
    with Progress(console=console) as progress:
        task = progress.add_task("[cyan]Formatting...", total=len(po_files))

        for po in po_files:
            cmd = [msgcat, "--width=124", "-o", str(po), str(po)]
            try:
                subprocess.run(cmd, check=True, capture_output=True)
            except subprocess.CalledProcessError:
                failed_list.append(po)

            progress.advance(task)

    # Output failed files list at the end
    if failed_list:
        console.print("\n[bold red]Failed files:[/bold red]")
        for po in failed_list:
            console.print(f"  • {po}", style="red")
        console.print(
            f"\n[bold yellow]Completed with {len(failed_list)} file(s) failed.[/bold yellow]"
        )

    console.print(
        f"[bold green]Formatted {len(po_files) - len(failed_list)} .po file(s).[/bold green]"
    )

    if failed_list:
        return 2

    return 0


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Format .po files with msgcat using consistent line wrapping.",
        epilog="Example: python scripts/format_po.py en"
    )
    parser.add_argument(
        "lang",
        help="Language code (e.g., en)",
    )
    args = parser.parse_args()

    raise SystemExit(main(args.lang))
