import numbers
from typing import Iterable

from janim.constants import FRAME_PPI
from janim.items.points import Points
from janim.items.typst.compile import TypstElemItem, TypstSizeUnit, TypstVar, GroupsIndices
from janim.utils.config import Config
from janim.exception import InvalidTypstVarError
from janim.locale import get_translator

_ = get_translator('janim.items.typst.vars')


TYPST_PT_TO_FRAME_RATIO = (
    # PPI 转换
    FRAME_PPI / 96
    # pt 转 px
    * 4 / 3
    # px 转 JAnim 坐标
    * Config.get.default_pixel_to_frame_ratio  # type: ignore
    # 因为 Typst 默认字号=11，janim 默认字号=24，为了默认显示效果一致，将 Typst 内容缩放 24/11
    * 24 / 11
)  # fmt: skip

FRAME_TO_TYPST_PT_RATIO = 1 / TYPST_PT_TO_FRAME_RATIO


def stringify_vars_tree(
    vars_tree: dict[str, TypstVar] | None, vars_size_unit: TypstSizeUnit | None
) -> tuple[str, dict[str, Points]] | None:
    if vars_tree is None:
        return None

    if vars_size_unit is None:
        unit_or_scale = FRAME_TO_TYPST_PT_RATIO
    else:
        unit_or_scale = vars_size_unit

    mapping: dict[str, Points] = {}
    lst = [
        f'#let {key} = {stringify_var(var, f"__ja__{key}", unit_or_scale, mapping)}'
        for key, var in vars_tree.items()
    ]
    parsed = '#let __jabox = box.with(stroke: white)\n' + '\n'.join(lst)
    return parsed, mapping


def replace_vars_placeholders(
    children: list[TypstElemItem], mapping: dict[str, Points], groups_indices: GroupsIndices
) -> list[Points]:
    new_children: list[Points] = children.copy()  # type: ignore
    for label, item in mapping.items():
        group_indices = groups_indices[label]  # TODO: warning if not exist?

        for i, phindex in enumerate(group_indices):
            placeholder = new_children[phindex]
            phbox = placeholder.points.box

            item_to_replace = item if i == 0 else item.copy()
            item_to_replace.points.set_size(width=phbox.width, height=phbox.height)
            item_to_replace.points.move_to(phbox.center)

            for suborder, sub in enumerate(item_to_replace.walk_self_and_descendants()):
                sub.depth._depth = placeholder.depth._depth
                sub.depth._order = placeholder.depth._order + 1e-4 * suborder

            new_children[phindex] = item_to_replace

    return new_children


def stringify_var(
    var: TypstVar, label: str, unit_or_scale: str | float, mapping: dict[str, Points]
) -> str:
    if isinstance(var, Points):
        width = stringify_length(var.points.box.width, unit_or_scale)
        height = stringify_length(var.points.box.height, unit_or_scale)
        mapping[label] = var
        return f'[#__jabox(width: {width}, height: {height})<{label}>]'

    elif isinstance(var, dict):
        return (
            '('
            + ', '.join(
                [
                    f'{key}: {stringify_var(v, f"{label}__{key}", unit_or_scale, mapping)}'
                    for key, v in var.items()
                ]
            )
            + ')'
        )

    elif isinstance(var, Iterable):
        return (
            '('
            + ', '.join(
                [
                    stringify_var(v, f'{label}__{i}', unit_or_scale, mapping)
                    for i, v in enumerate(var)
                ]
            )
            + ')'
        )

    else:
        raise InvalidTypstVarError(
            _('{var} is not a valid item for embedding in Typst').format(var=repr(var))
        )


def stringify_length(length: float, unit_or_scale: str | float) -> str:
    if isinstance(unit_or_scale, numbers.Real):
        return f'{length * unit_or_scale}pt'  # type: ignore
    elif isinstance(unit_or_scale, str):
        return f'{length}{unit_or_scale}'
    else:
        assert False
