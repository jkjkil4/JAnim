
import hashlib
import os
import subprocess as sp

from janim.constants import ORIGIN, UP
from janim.exception import (EXITCODE_TYPST_COMPILE_ERROR,
                             EXITCODE_TYPST_NOT_FOUND, ExitException)
from janim.items.svg.svg_item import SVGItem
from janim.logger import log
from janim.utils.config import Config
from janim.utils.file_ops import get_janim_dir, get_typst_temp_dir
from janim.locale.i18n import get_local_strings

_ = get_local_strings('typst')

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
            Config.get.typst_bin,
            'compile',
            typst_file_path,
            svg_file_path,
            '-f', 'svg'
        ]

        try:
            process = sp.Popen(commands)
        except FileNotFoundError:
            log.error(_('Could not compile typst file. '
                        'Please install typst and add it to the environment variables.'))
            raise ExitException(EXITCODE_TYPST_NOT_FOUND)

        ret = process.wait()
        if ret != 0:
            log.error(_('Typst compilation error. Please check the output for more information.'))
            raise ExitException(EXITCODE_TYPST_COMPILE_ERROR)

        process.terminate()

        return svg_file_path


class Typst(TypstDoc):
    '''
    Typst 公式
    '''
    def __init__(self, text: str, *, use_math_environment: bool = True, **kwargs):
        super().__init__(
            f'$ {text} $' if use_math_environment else text,
            **kwargs
        )

    def move_into_position(self) -> None:
        self.points.to_center()


class TypstText(Typst):
    '''
    Typst 文本

    相当于 :class:`Typst` 传入 ``use_math_environment=False``
    '''
    def __init__(self, text: str, use_math_environment: bool = False, **kwargs):
        super().__init__(
            text,
            use_math_environment=use_math_environment,
            **kwargs
        )


cached_typst_template: str | None = None


def get_typst_template() -> str:
    global cached_typst_template

    if cached_typst_template is not None:
        return cached_typst_template

    with open(os.path.join(get_janim_dir(), 'items', 'svg', 'typst_template.typ')) as f:
        text = f.read()

    cached_typst_template = text
    return text
