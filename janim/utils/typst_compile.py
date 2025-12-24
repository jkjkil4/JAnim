
import hashlib
import os
import subprocess as sp

import typst

from janim.exception import (EXITCODE_TYPST_COMPILE_ERROR,
                             EXITCODE_TYPST_NOT_FOUND, ExitException)
from janim.locale.i18n import get_translator
from janim.logger import log
from janim.utils.config import Config
from janim.utils.file_ops import (get_janim_dir, get_typst_packages_dir,
                                  get_typst_temp_dir)

_ = get_translator('janim.utils.typst_compile')

_flag_use_external_typst = False


def set_use_external_typst(flag: bool) -> None:
    """
    设置是否使用外部 Typst 可执行程序进行编译
    """
    global _flag_use_external_typst
    _flag_use_external_typst = flag


def compile_typst(
    text: str,
    shared_preamble: str,
    additional_preamble: str,
    vars: str,
    sys_inputs: dict[str, str]
) -> str:
    """
    编译 Typst 文档
    """
    sys_inputs_pairs = get_sys_inputs_pairs(sys_inputs)

    typst_temp_dir = get_typst_temp_dir()
    hash_hex = compute_hash_hex(
        text,
        shared_preamble,
        additional_preamble,
        vars,
        sys_inputs_pairs
    )

    svg_file_path = os.path.join(typst_temp_dir, hash_hex + '.svg')
    if os.path.exists(svg_file_path):
        return svg_file_path

    typst_content = get_typst_template().format(
        shared_preamble=shared_preamble,
        additional_preamble=additional_preamble,
        vars=vars,
        typst_expression=text
    )

    if _flag_use_external_typst:
        _compile_typst_by_external_executable(
            typst_content,
            svg_file_path,
            sys_inputs_pairs
        )
    else:
        _compile_typst_by_internal_package(
            typst_content,
            svg_file_path,
            sys_inputs
        )

    return svg_file_path


_typst_fonts: typst.Fonts | None = None


def _compile_typst_by_internal_package(
    typst_content: str,
    svg_file_path: str,
    sys_inputs: dict[str, str]
) -> str:
    """
    通过 typst-py 包编译 Typst 文档
    """
    global _typst_fonts
    if _typst_fonts is None:
        _typst_fonts = typst.Fonts()

    try:
        typst.compile(
            input=typst_content.encode('utf-8'),
            output=svg_file_path,
            font_paths=_typst_fonts,
            package_path=get_typst_packages_dir(),
            sys_inputs=sys_inputs
        )
    except typst.TypstError as e:
        log.error(e.diagnostic.removesuffix('\n'), extra={'raw': True})
        log.error(_('Typst compilation error. Please check the output for more information.'))
        raise ExitException(EXITCODE_TYPST_COMPILE_ERROR)


def _compile_typst_by_external_executable(
    typst_content: str,
    svg_file_path: str,
    sys_inputs_pairs: list[str]
) -> str:
    """
    通过外部可执行程序编译 Typst 文档
    """
    commands = [
        Config.get.typst_bin,
        'compile',
        '-',
        svg_file_path,
        '-f', 'svg',
        '--package-path', get_typst_packages_dir()
    ]

    for pair in sys_inputs_pairs:
        commands += [
            '--input', pair
        ]

    try:
        process = sp.Popen(commands, stdin=sp.PIPE)
    except FileNotFoundError:
        log.error(_('Could not compile Typst document by external executable. '
                    'Please install Typst and add it to the environment variables, or use internal Typst instead.'))
        raise ExitException(EXITCODE_TYPST_NOT_FOUND)

    process.stdin.write(typst_content.encode('utf-8'))
    process.stdin.close()
    ret = process.wait()
    if ret != 0:
        log.error(_('Typst compilation error. Please check the output for more information.'))
        raise ExitException(EXITCODE_TYPST_COMPILE_ERROR)

    process.terminate()


def get_sys_inputs_pairs(sys_inputs: dict[str, str]) -> list[str]:
    """
    将 ``sys_inputs`` 字典转换为键值对字符串列表
    """
    return [f'{key}={value}' for key, value in sys_inputs.items()]


def compute_hash_hex(
    text: str,
    shared_preamble: str,
    additional_preamble: str,
    vars: str,
    sys_inputs_pairs: list[str]
) -> str:
    """
    计算 Typst 文档的哈希值，用于缓存
    """
    md5 = hashlib.md5(text.encode())
    md5.update(shared_preamble.encode())
    md5.update(additional_preamble.encode())
    md5.update(vars.encode())
    md5.update('\n'.join(sys_inputs_pairs).encode())

    return md5.hexdigest()


cached_typst_template: str | None = None


def get_typst_template() -> str:
    global cached_typst_template

    if cached_typst_template is not None:
        return cached_typst_template

    with open(os.path.join(get_janim_dir(), 'items', 'svg', 'typst_template.typ')) as f:
        text = f.read()

    cached_typst_template = text
    return text
