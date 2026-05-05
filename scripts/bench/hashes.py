import re
import subprocess as sp


def get_tag_hashes_after_210() -> list[str]:
    # Get all tag hashes, ordered by time (newest first)
    result = sp.run(['git', 'rev-list', '--abbrev-commit', '--tags', '--no-walk'], stdout=sp.PIPE, text=True)
    hashes = result.stdout.splitlines()

    # Get the hash for tag v2.1.0
    result = sp.run(['git', 'rev-list', '--abbrev-commit', '-n', '1', 'v2.1.0'], stdout=sp.PIPE, text=True)
    hash_210 = result.stdout.strip()

    # Collect all hashes that come after v2.1.0
    result = []
    for h in hashes:
        if h == hash_210:
            break
        result.append(h)
    return result


regex_hash_line = re.compile(r'^\s*[0-9a-f]+\s*$')


def get_tested_hashes() -> list[str]:
    result = sp.run(['asv', 'show'], stdout=sp.PIPE, text=True)
    lines = result.stdout.splitlines()
    hashes = [
        line.strip()
        for line in lines
        if re.match(regex_hash_line, line)
    ]
    return hashes


def get_tag_hash(tag: str) -> str:
    result = sp.run(['git', 'rev-list', '--abbrev-commit', '-n', '1', tag], stdout=sp.PIPE, text=True)
    return result.stdout.strip()
