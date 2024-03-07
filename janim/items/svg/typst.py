
import hashlib
import os
import subprocess as sp

from janim.constants import ORIGIN, UP
from janim.items.svg.svg_item import SVGItem
from janim.utils.file_ops import get_janim_dir, get_typst_temp_dir

TYPST_BIN = 'typst'
TYPST_FILENAME = 'temp.typ'


class TypstDoc(SVGItem):
    '''
    ``Typst`` 文档
    '''
    def __init__(self, text: str, **kwargs):
        self.text = text

        super().__init__(self.compile_typst(text), **kwargs)

    def move_into_position(self) -> None:
        self.points.scale(0.9, about_point=ORIGIN).to_border(UP)

    @staticmethod
    def compile_typst(text: str) -> str:
        '''
        编译 ``Typst`` 文档
        '''
        typst_temp_dir = get_typst_temp_dir()
        hash_hex = hashlib.md5(text.encode()).hexdigest()

        svg_file_path = os.path.join(typst_temp_dir, hash_hex + '.svg')
        if os.path.exists(svg_file_path):
            return svg_file_path

        typst_file_path = os.path.join(typst_temp_dir, TYPST_FILENAME)

        with open(typst_file_path, 'wt') as f:
            f.write(get_typst_template().replace('[typst_expression]', text))

        commands = [
            TYPST_BIN,
            'compile',
            typst_file_path,
            svg_file_path,
            '-f', 'svg'
        ]

        process = sp.Popen(commands)
        process.wait()
        process.terminate()

        return svg_file_path


class Typst(TypstDoc):
    '''
    Typst 公式
    '''
    def __init__(self, text: str, **kwargs):
        super().__init__(f'$ {text} $', **kwargs)

    def move_into_position(self) -> None:
        self.points.to_center()


cached_typst_template: str | None = None


def get_typst_template() -> str:
    global cached_typst_template

    if cached_typst_template is not None:
        return cached_typst_template

    with open(os.path.join(get_janim_dir(), 'items', 'svg', 'typst_template.typ')) as f:
        text = f.read()

    cached_typst_template = text
    return text
