import os
import re
from collections import defaultdict
from dataclasses import dataclass

from janim.utils.file_ops import get_janim_dir


@dataclass
class Detected:
    filepath: str
    previous_name: str
    correct_name: str


def main() -> None:
    # Find .py files where module name and get_translator() name differ

    proj_path = os.path.join(get_janim_dir(), '..')
    detected_map: dict[str, Detected] = {}

    for root, dirs, files in os.walk(get_janim_dir()):
        for file in files:
            if not file.endswith('.py'):
                continue
            source = os.path.relpath(os.path.join(root, file), proj_path)
            correct_name = source.removesuffix('.py').replace('/', '.').replace('\\', '.')

            with open(source, 'rt', encoding='utf-8') as f:
                content = f.read()

            for match in re.finditer(r"_ = get_translator\('(.+?)'\)", content):
                name = match.group(1)
                if name != correct_name:
                    detected_map[name] = Detected(source, name, correct_name)
                    break

    if not detected_map:
        print('No mismatched translator names found')
        return

    # Collect i18n files that need renaming

    renames_map: defaultdict[str, list[tuple[str, str]]] = defaultdict(list)

    for root, dirs, files in os.walk(os.path.join(get_janim_dir(), 'locale')):
        for file in files:
            base, ext = os.path.splitext(file)
            if ext not in ('.pot', '.po', '.mo'):
                continue
            if base not in detected_map:
                continue
            relpath = os.path.relpath(root, proj_path)
            renames_map[base].append((os.path.join(relpath, file),
                                      os.path.join(relpath, f'{detected_map[base].correct_name}{ext}')))

    # Prompt and perform replacements

    for name, detected in detected_map.items():
        replace_from = f"_ = get_translator('{name}')"
        replace_to = f"_ = get_translator('{detected.correct_name}')"
        print('------')
        print(' - ', repr(replace_from))
        print('[+]', repr(replace_to))

        renames = renames_map[name]
        for rename_from, rename_to in renames:
            print('------')
            print(' - ', rename_from)
            print('[+]', rename_to)

        prompt = input('Do you want to apply the above changes? (Y/n) ')

        if prompt.lower() != 'y':
            continue

        # Replace translator name in source files

        with open(detected.filepath, 'rt', encoding='utf-8') as f:
            content = f.read()

        new_content = content.replace(replace_from, replace_to)

        with open(detected.filepath, 'wt', encoding='utf-8') as f:
            f.write(new_content)

        # Rename i18n files

        for rename_from, rename_to in renames:
            os.rename(rename_from, rename_to)

    print('Replacements completed')


if __name__ == '__main__':
    main()
