import os
import sys
from janim.utils.file_ops import get_janim_dir

includes = [partial_path.replace('\\', '/') for partial_path in sys.argv[1:]]


def is_included(file: str) -> bool:
    return any(file.endswith(include) for include in includes)


def main() -> None:
    for root, dirs, files in os.walk(get_janim_dir()):
        for file in files:
            if not file.endswith('.py'):
                continue
            source = os.path.relpath(os.path.join(root, file), os.path.join(get_janim_dir(), '..'))
            source = source.replace('\\', '/')
            if includes and not is_included(source):
                continue
            module_name = source.removesuffix('.py').replace('/', '.')
            dist = os.path.join(get_janim_dir(), 'locale', 'source', module_name + '.pot')
            cmd = f'xgettext -o "{dist}" "{source}"'
            print(cmd)
            os.system(cmd)


if __name__ == '__main__':
    main()
