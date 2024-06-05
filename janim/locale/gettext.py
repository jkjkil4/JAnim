import os
from janim.utils.file_ops import get_janim_dir


def main() -> None:
    for root, dirs, files in os.walk(get_janim_dir()):
        for file in files:
            if not file.endswith('.py'):
                continue
            dist = os.path.join(get_janim_dir(), 'locale', 'source', file[:-3] + '.pot')
            source = os.path.join(root, file)
            cmd = f'xgettext -o "{dist}" "{source}"'
            print(cmd)
            os.system(cmd)


if __name__ == '__main__':
    main()
