# After editing .po file in Poedit, .mo could be updated automatically
# For most cases, we don't need to execute compile.py for updating
import os
import sys

from janim.utils.file_ops import get_janim_dir


def main() -> None:
    assert len(sys.argv) == 2
    lang = sys.argv[1]
    dir = os.path.join(get_janim_dir(), 'locale', lang, 'LC_MESSAGES')
    files = os.listdir(dir)
    for file in files:
        if not file.endswith('.po'):
            continue
        dist = os.path.join(dir, file[:-3] + '.mo')
        src = os.path.join(dir, file)
        cmd = f'msgfmt -o "{dist}" "{src}"'
        print(cmd)
        os.system(cmd)


if __name__ == '__main__':
    main()
