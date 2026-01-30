import os
import sys

from janim.utils.file_ops import get_janim_dir


def main() -> None:
    assert len(sys.argv) == 2
    lang = sys.argv[1]
    src_dir = os.path.join(get_janim_dir(), 'locale', 'source')
    files = os.listdir(src_dir)
    for file in files:
        if not file.endswith('.pot'):
            continue
        dist = os.path.join(get_janim_dir(), 'locale', lang, 'LC_MESSAGES', file[:-4] + '.po')
        src = os.path.join(src_dir, file)
        if not os.path.exists(dist):
            cmd = f'msginit -i "{src}" -o "{dist}" -l {lang} --no-translator'
        else:
            cmd = f'msgmerge -U "{dist}" "{src}" --backup=off'
        print(cmd)
        os.system(cmd)


if __name__ == '__main__':
    main()
