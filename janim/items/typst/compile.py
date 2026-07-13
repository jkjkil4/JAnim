import hashlib
import os
from collections import defaultdict
from functools import lru_cache
from typing import Callable, Iterable, Literal

import typst4janim
import numpy as np

from janim.exception import EXITCODE_TYPST_COMPILE_ERROR, ExitException
from janim.items.points import Points
from janim.items.typst.element import TypstElemItem, parse_element, ParseArgs
from janim.locale import get_translator
from janim.logger import log
from janim.utils.file_ops import get_janim_dir, get_typst_packages_dir

__all__ = [
    'TypstVar',
    'TypSizeUnit',
]

_ = get_translator('janim.utils.typst_compile')

type TypstVar = Points | dict[str, TypstVar] | Iterable[TypstVar]
type TypSizeUnit = Literal['pt', 'mm', 'cm', 'in', 'pt']

type TypstElemItems = list[TypstElemItem]
type GroupsIndices = dict[str, list[int]]
type Builder = Callable[[float], tuple[TypstElemItems, GroupsIndices]]


_cached_builders = {}


def compile_typst(
    *,
    text: str,
    shared_preamble: str,
    additional_preamble: str,
    vars: str,
    sys_inputs: dict[str, str],
    root: str | None,
    mark_basepoint: bool,
    scale: float,
    cache: bool,
) -> tuple[TypstElemItems, GroupsIndices]:
    builder = None
    if cache:
        hash_hex = _compute_hash_hex(
            text,
            shared_preamble,
            additional_preamble,
            vars,
            sys_inputs,
            root or '',
            mark_basepoint,
        )
        builder = _cached_builders.get(hash_hex, None)

    if builder is None:
        typst_content = get_typst_template().format(
            shared_preamble=shared_preamble,
            additional_preamble=additional_preamble,
            vars=vars,
            typst_expression=text,
        )
        builder = _compile_builder(typst_content, sys_inputs, root, mark_basepoint)

    if cache:
        _cached_builders[hash_hex] = builder  # type: ignore

    return builder(scale)


def _compile_builder(
    typst_content: str, sys_inputs: dict[str, str], root: str | None, mark_basepoint: bool
) -> Builder:
    try:
        collected = typst4janim.compile(
            typst_content.encode('utf-8'), sys_inputs, root, get_typst_packages_dir()
        )
        _print_warnings(collected.warnings)
    except typst4janim.TypstError:
        log.error(_('Typst compilation error. Please check the output for more information.'))
        raise ExitException(EXITCODE_TYPST_COMPILE_ERROR)

    offset = np.array(collected.size) / -2
    args = ParseArgs(collected.shared, offset, mark_basepoint)

    def build(scale: float) -> tuple[TypstElemItems, GroupsIndices]:
        items = [parse_element(element, scale, args) for element in collected.elements]
        return (items, collected.groups)

    return build


def resolve_groups(
    children: list[TypstElemItem], groups_indices: dict[str, list[int]]
) -> dict[str, list[TypstElemItem]]:
    return {label: [children[idx] for idx in indices] for label, indices in groups_indices.items()}


def _compute_hash_hex(
    text: str,
    shared_preamble: str,
    additional_preamble: str,
    vars: str,
    sys_inputs: dict[str, str],
    root: str,
    mark_basepoint: bool,
) -> str:
    """
    计算 Typst 文档的哈希值，用于缓存
    """
    md5 = hashlib.md5(text.encode())
    md5.update(shared_preamble.encode())
    md5.update(additional_preamble.encode())
    md5.update(vars.encode())
    md5.update('\n'.join(f'{key}={value}' for key, value in sys_inputs.items()).encode())
    md5.update(root.encode())
    md5.update(b'1' if mark_basepoint else b'0')

    return md5.hexdigest()


def _print_warnings(warnings: list[str]) -> None:
    if not warnings:
        return
    counts: defaultdict[str, int] = defaultdict(int)
    for warning in warnings:
        counts[warning] += 1
    messages = _get_warning_messages()
    for warning, count in counts.items():
        message = messages.get(warning, warning)
        suffix = '' if count == 1 else f' (x{count})'
        log.warning(f'typst: {message}{suffix}')


@lru_cache(maxsize=1)
def _get_warning_messages() -> dict[str, str]:
    return {
        'ClipPathNotSupported': _('Clip paths are not supported'),
        'ImageGlyphNotSupported': _('Bitmap glyphs (image glyphs) are not supported, only outline glyphs'),
        'GradientNotSupported': _('Gradients are not supported, solid colors will be used instead'),
        'TilingNotSupported': _('Tiling patterns are not supported, solid colors will be used instead'),
        'ImageNotSupported': _('Images are not supported'),
    }  # fmt: skip


cached_typst_template: str | None = None


def get_typst_template() -> str:
    global cached_typst_template

    if cached_typst_template is not None:
        return cached_typst_template

    with open(os.path.join(get_janim_dir(), 'items', 'typst', 'typst_template.typ')) as f:
        text = f.read()

    cached_typst_template = text
    return text
