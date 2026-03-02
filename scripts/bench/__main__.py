import os
import subprocess
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from scripts import console, prompt_columns, step
from scripts.bench.hashes import (get_tag_hash, get_tag_hashes_after_210,
                                  get_tested_hashes)


def main(untested_tags: bool, tags: list[str], hashes: list[str], open_preview: bool) -> int:
    if not untested_tags and not tags and not hashes:
        console.print('No tags or hashes specified.', style='red')
        return 1

    all_hashes: list[str] = []

    if untested_tags:
        tag_hashes = get_tag_hashes_after_210()
        tested_hashes = get_tested_hashes()
        if tag_hashes and tested_hashes:
            min_len = min(len(tag_hashes[0]), len(tested_hashes[0]))
            tag_hashes = [h[:min_len] for h in tag_hashes]
            tested_hashes = [h[:min_len] for h in tested_hashes]
            all_hashes += [h for h in tag_hashes if h not in tested_hashes]
        else:
            all_hashes += tag_hashes

    if tags:
        all_hashes += [get_tag_hash(t) for t in tags]

    all_hashes += hashes

    if untested_tags and not all_hashes:
        console.print('No untested tags found.', style='yellow')
        return 0

    if not prompt_columns(*all_hashes):
        return 0

    os.makedirs('.asv', exist_ok=True)
    with open('.asv/_tag_hashes.txt', 'w') as f:
        f.write('\n'.join(all_hashes))

    console.print()

    with step('Running benchmarks', 'Benchmarking') as result:
        result.returncode = subprocess.run(['asv', 'run', 'HASHFILE:.asv/_tag_hashes.txt']).returncode

    console.print()

    with step('Publishing results locally', 'Publishing') as result:
        result.returncode = subprocess.run(['asv', 'publish']).returncode

    console.print(
        '\n[cyan]hint:[/cyan] You can run `asv preview -b` directly to preview the results without running benchmarks;'
    )

    if not open_preview:
        console.print(
            '[cyan]hint:[/cyan] or pass -o/--open to open it automatically in your browser after benchmarking.'
        )
        return 0
    return subprocess.run(['asv', 'preview', '-b']).returncode


if __name__ == '__main__':
    parser = ArgumentParser(
        description='Run benchmarks',
        formatter_class=RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--untested_tags',
        action='store_true',
        help='Test all untested tags after v2.1.0',
    )
    parser.add_argument(
        '--tags',
        nargs='+',
        help='Specify one or more tags to test',
    )
    parser.add_argument(
        '--hashes',
        nargs='+',
        help='Specify one or more hashes to test',
    )
    parser.add_argument(
        '-o',
        '--open',
        action='store_true',
        dest='open_preview',
        help='Open the browser preview after benchmarking',
    )
    args = parser.parse_args()

    raise SystemExit(main(args.untested_tags, args.tags, args.hashes or [], args.open_preview or []))
