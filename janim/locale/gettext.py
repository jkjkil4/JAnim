import os
import subprocess
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
            # Sometimes, URL is language-specific and intentionally part of the message
            # we need to ignore "Message contains an embedded URL" warnings, looks like:
            #
            # warning: Message contains an embedded URL.
            # Better move it out of the translatable string,
            # see https://www.gnu.org/software/gettext/manual/html_node/No-embedded-URLs.html
            #
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            for line in result.stderr.splitlines():
                if 'Message contains an embedded URL' not in line:
                    print(line, file=sys.stderr)


if __name__ == '__main__':
    main()
