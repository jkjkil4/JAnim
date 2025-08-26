from __future__ import annotations

import hashlib
import itertools as it
import numbers
import os
import subprocess as sp
import types
from typing import Iterable, Literal, Self, overload

import numpy as np

from janim.constants import FRAME_PPI, ORIGIN, UP
from janim.exception import (EXITCODE_TYPST_COMPILE_ERROR,
                             EXITCODE_TYPST_NOT_FOUND, ExitException,
                             InvalidOrdinalError, InvalidTypstVarError,
                             PatternMismatchError)
from janim.items.points import Group, Points
from janim.items.svg.svg_item import BasepointVItem, SVGElemItem, SVGItem
from janim.items.vitem import VItem
from janim.locale.i18n import get_local_strings
from janim.logger import log
from janim.utils.config import Config
from janim.utils.file_ops import (get_janim_dir, get_typst_packages_dir,
                                  get_typst_temp_dir)
from janim.utils.iterables import flatten
from janim.utils.space_ops import rotation_between_vectors

_ = get_local_strings('typst')

type TypstPattern = TypstDoc | str
type TypstVar = Points | dict[str, TypstVar] | Iterable[TypstVar]


class TypstDoc(SVGItem):
    '''
    Typst 文档
    '''

    group_key = 'data-typst-label'

    def __init__(
        self,
        text: str,
        *,
        vars: dict[str, TypstVar] | None = None,
        vars_size_unit: Literal['pt', 'mm', 'cm', 'in', 'pt'] | None = None,
        sys_inputs: dict[str, str] = {},
        scale: float = 1.0,
        shared_preamble: str | None = None,
        additional_preamble: str | None = None,
        **kwargs
    ):
        self.text = text

        # 因为 Typst 默认字号=11，janim 默认字号=24，为了默认显示效果一致，将 Typst 内容缩放 24/11
        scale *= 24 / 11

        if shared_preamble is None:
            shared_preamble = Config.get.typst_shared_preamble
        if additional_preamble is None:
            additional_preamble = ''

        if vars is not None:
            factor_pt = Config.get.default_pixel_to_frame_ratio * (FRAME_PPI / 96) * scale
            factor_px = factor_pt * 4 / 3
            vars_str, vars_mapping = self.vars_str(vars, vars_size_unit or 1 / factor_px)
        else:
            vars_str = ''

        super().__init__(
            self.compile_typst(text, shared_preamble, additional_preamble, vars_str, sys_inputs),
            scale=scale,
            **kwargs
        )

        # 把占位元素替换为实际物件
        if vars is not None:
            new_children = self.children.copy()
            for label, item in vars_mapping.items():
                placeholders = self.get_label(label)

                for i, placeholder in enumerate(placeholders):
                    phbox = placeholder.points.box

                    item_to_replace = item if i == 0 else item.copy()
                    item_to_replace.points.set_size(width=phbox.width, height=phbox.height).move_to(phbox.center)

                    for suborder, sub in enumerate(item_to_replace.walk_self_and_descendants()):
                        sub.depth._depth = placeholder.depth._depth
                        sub.depth._order = placeholder.depth._order + 1e-4 * suborder

                    self.groups[label] = [item_to_replace]

                    idx = new_children.index(placeholder)
                    new_children.pop(idx)
                    new_children.insert(idx, item_to_replace)

            self.clear_children()
            self.add(*new_children)

    def move_into_position(self) -> None:
        self.points.scale(0.9, about_point=ORIGIN).to_border(UP)

    @staticmethod
    def compile_typst(
        text: str,
        shared_preamble: str,
        additional_preamble: str,
        vars: str,
        sys_inputs: dict[str, str]
    ) -> str:
        '''
        编译 Typst 文档
        '''
        sys_inputs_pairs = [
            f'{key}={value}'
            for key, value in sys_inputs.items()
        ]

        typst_temp_dir = get_typst_temp_dir()
        md5 = hashlib.md5(text.encode())
        md5.update(shared_preamble.encode())
        md5.update(additional_preamble.encode())
        md5.update(vars.encode())
        md5.update('\n'.join(sys_inputs_pairs).encode())
        hash_hex = md5.hexdigest()

        svg_file_path = os.path.join(typst_temp_dir, hash_hex + '.svg')
        if os.path.exists(svg_file_path):
            return svg_file_path

        typst_content = get_typst_template().format(
            shared_preamble=shared_preamble,
            additional_preamble=additional_preamble,
            vars=vars,
            typst_expression=text
        )

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
            log.error(_('Could not compile Typst file. '
                        'Please install Typst and add it to the environment variables.'))
            raise ExitException(EXITCODE_TYPST_NOT_FOUND)

        process.stdin.write(typst_content.encode('utf-8'))
        process.stdin.close()
        ret = process.wait()
        if ret != 0:
            log.error(_('Typst compilation error. Please check the output for more information.'))
            raise ExitException(EXITCODE_TYPST_COMPILE_ERROR)

        process.terminate()

        return svg_file_path

    @classmethod
    def typstify(cls, obj: TypstPattern) -> TypstDoc:
        '''
        将字符串变为 Typst 对象，而本身已经是的则直接返回
        '''
        return obj if isinstance(obj, TypstDoc) else cls(obj)

    @staticmethod
    def vars_str(vars: dict[str, TypstVar], unit_or_scale: str | float) -> tuple[str, dict[str, Points]]:
        mapping = {}
        lst = [
            f'#let {key} = {TypstDoc.var_str(var, f'__ja__{key}', unit_or_scale, mapping)}'
            for key, var in vars.items()
        ]
        return '#let __jabox = box.with(stroke: white)\n' + '\n'.join(lst), mapping

    @staticmethod
    def var_str(var: TypstVar, label: str, unit_or_scale: str | float, mapping: dict[str, Points]) -> str:
        if isinstance(var, Points):
            width = TypstDoc.length_str(var.points.box.width, unit_or_scale)
            height = TypstDoc.length_str(var.points.box.height, unit_or_scale)
            mapping[label] = var
            return f'[#__jabox(width: {width}, height: {height})<{label}>]'

        elif isinstance(var, dict):
            return '(' + ', '.join([
                f'{key}: {TypstDoc.var_str(v, f'{label}__{key}', unit_or_scale, mapping)}'
                for key, v in var.items()
            ]) + ')'

        elif isinstance(var, Iterable):
            return '(' + ', '.join([
                TypstDoc.var_str(v, f'{label}__{i}', unit_or_scale, mapping)
                for i, v in enumerate(var)
            ]) + ')'

        else:
            raise InvalidTypstVarError(
                _('{var} is not a valid value for embedding in Typst')
                .format(var=repr(var))
            )

    @staticmethod
    def length_str(length: float, unit_or_scale: str | float) -> str:
        if isinstance(unit_or_scale, numbers.Real):
            return f'{length * unit_or_scale}pt'
        elif isinstance(unit_or_scale, str):
            return f'{length}{unit_or_scale}'
        else:
            assert False

    # region pattern-matching

    def get_label(self, name: str) -> Group[SVGElemItem]:
        return Group.from_iterable(self.groups[name])

    def match_pattern(
        self,
        target: TypstDoc,
        pattern: TypstPattern,
        ordinal: int = 0,
        target_ordinal: int | None = None
    ) -> Self:
        '''
        配对并通过变换使得配对的部分重合

        例如

        .. code-block:: python

            t1 = TypstMath('x^2 + y^2')
            t2 = TypstMath('x + y')
            t2.points.match_pattern(t1, '+')

        则会将 ``t2`` 进行变换使得二者的加号重合
        '''
        if target_ordinal is None:
            target_ordinal = ordinal
        assert isinstance(ordinal, int)
        assert isinstance(target_ordinal, int)

        indicator1 = self[pattern, ordinal][0]
        indicator2 = target[self.typstify(pattern), target_ordinal][0]

        # 旋转
        vect1 = indicator1.points.identity[1]
        vect2 = indicator2.points.identity[1]

        if not np.isclose(np.dot(vect1, vect2), 1):
            rot = rotation_between_vectors(vect1, vect2)
            self.points.apply_matrix(rot)

        # 缩放
        l1 = max(indicator1.points.box.width, indicator1.points.box.height)
        l2 = max(indicator2.points.box.width, indicator2.points.box.height)

        if not np.isclose(l1, l2):
            self.points.scale(l2 / l1)

        # 移动使得重合
        self.points.move_to_by_indicator(indicator1, indicator2)
        return self

    @overload
    def __getitem__(self, key: int) -> VItem | BasepointVItem: ...
    @overload
    def __getitem__(self, key: slice) -> Group[VItem | BasepointVItem]: ...

    @overload
    def __getitem__(self, key: TypstPattern) -> Group[VItem | BasepointVItem]: ...
    @overload
    def __getitem__(self, key: tuple[TypstPattern, int]) -> Group[VItem | BasepointVItem]: ...
    @overload
    def __getitem__(self, key: tuple[TypstPattern, Iterable[int]]) -> Group[Group[VItem | BasepointVItem]]: ...
    @overload
    def __getitem__(self, key: tuple[TypstPattern, types.EllipsisType]) -> Group[Group[VItem | BasepointVItem]]: ...

    @overload
    def __getitem__(self, key: Iterable[int]) -> Group[VItem | BasepointVItem]: ...
    @overload
    def __getitem__(self, key: Iterable[bool]) -> Group[VItem | BasepointVItem]: ...

    def __getitem__(self, key: int | slice):
        '''
        重载了一些字符索引的用法，即 :meth:`get` 和 :meth:`slice` 的组合
        '''
        if isinstance(key, Iterable) and not isinstance(key, (str, list)):
            key = list(key)

        match key:
            case int() | slice():
                return super().__getitem__(key)

            # item['pattern']
            case TypstDoc() | str() as pattern:
                return self.get(self.slice(pattern, 0))
            # item['pattern', ordinal]
            case TypstDoc() | str() as pattern, int(ordinal):
                return self.get(self.slice(pattern, ordinal))
            # item['pattern', (o1, o2)]
            # item['pattern', ...]
            case TypstDoc() | str() as pattern, ordinal if isinstance(ordinal, (Iterable, types.EllipsisType)):
                return Group(*self.get(self.slice(pattern, ordinal)))

            # TODO: multi_slice

            case _:
                return super().__getitem__(key)

    def get(self, slices, gapless: bool = False):
        '''
        根据切片得到切分的子物件

        在默认情况下，``gapless=False``：

        - 表示通过给定的 ``slices`` 直接切取子物件，例如

          ``item.get(slice(1, 3)) == item[1:3]``

        - 支持使用列表获取一批的子物件，例如

          ``item.get([slice(1, 3), slice(4, 7)]) == [item[1:3], item[4:7]]``

        - 列表支持嵌套，并且结果保持原嵌套结构，例如

          ``item.get([slice(1, 3), [slice(4, 6), slice(10, 12)]]) == [item[1:3], [item[4:6], item[10:12]]]``

        若 ``gapless=True``：

        - 表示通过给定 ``slices`` 的所有起止位置将所有子物件切分并一起返回，例如

          ``item.get(slice(1, 3), gapless=True) == [item[:1], item[1:3], item[3:]]``

        - 也支持列表以及嵌套的列表，例如

          ``item.get([slice(1, 3), slice(5, 7)]) == [item[:1], item[1:3], item[3:5], item[5:7], item[7:]]``

        - 注：在这种情况下，所有嵌套结构都会先被展平后处理
        '''
        if not gapless:
            if isinstance(slices, slice):
                return self[slices]
            else:
                return [self.get(x) for x in slices]
        else:
            indices = {0, len(self)}
            for i in flatten(slices):
                assert isinstance(i, slice)
                indices.update({i.start, i.stop})
            return [
                self[start:stop]
                for start, stop in it.pairwise(sorted(indices))
            ]

    @overload
    def slice(self, pattern: TypstPattern, ordinal: int) -> slice: ...
    @overload
    def slice(self, pattern: TypstPattern, ordinal: Iterable[int] | types.EllipsisType) -> list[slice]: ...

    def slice(self, pattern, ordinal=0):
        '''
        得到指定 ``pattern`` 在该物件中形状配对的切片

        - 默认返回首个匹配的（即 ``ordinal=0``）
        - ``ordinal`` 传入其它索引可得到随后匹配的特定部分
        - ``ordinal`` 传入索引列表可得到多个匹配的特定部分
        - ``ordinal`` 传入省略号 ``...`` 可以得到所有匹配的部分
        '''
        pattern = self.typstify(pattern)
        indices = self.indices(pattern)

        if not indices:
            raise PatternMismatchError(
                _('No matches found for {pattern}')
                .format(pattern=repr(pattern.text))
            )

        def get_slice(i: int):
            if not 0 <= i < len(indices):
                raise PatternMismatchError(
                    _('{ordinal} is out of range for {count} matches')
                    .format(ordinal=i, count=len(indices))
                )
            return slice(indices[i], indices[i] + len(pattern))

        match ordinal:
            case int(i):
                return get_slice(i)
            case _ if isinstance(ordinal, Iterable) and all(isinstance(i, int) for i in ordinal):
                return [get_slice(i) for i in ordinal]
            case types.EllipsisType():
                return [
                    slice(i, i + len(pattern))
                    for i in indices
                ]

        raise InvalidOrdinalError(_('ordinal {} is invalid').format(ordinal))

    def indices(self, pattern: TypstPattern) -> list[int]:
        '''
        找出该公式中所有出现了 ``pattern`` 的位置

        - ``pattern`` 支持使用字符串或者 Typst 对象
        '''
        pattern = self.typstify(pattern)

        lps = pattern.lps
        indices, p = [], 0

        for index, shape in enumerate(self):
            while not (same := shape.points.same_shape(pattern[p])) and p != 0:
                p = lps[p - 1]
            if same:
                p += 1
            if p == len(pattern):
                indices.append(index - (p - 1))
                p = lps[p - 1]

        return indices

    lps_map: dict[str, list[int]] = {}

    @property
    def lps(self) -> list[int]:
        '''
        KMP 算法涉及的部分匹配表
        '''
        # 获取缓存
        lps = TypstDoc.lps_map.get(self.text, None)
        if lps is not None:
            return lps

        # 没缓存则计算
        lps = [0] * len(self)
        for index, shape in enumerate(self):
            p, same = index, False
            while p > 0 and not same:
                p = lps[p - 1]
                same = shape.points.same_shape(self[p])
            if same:
                p += 1
            lps[index] = p

        # 缓存并返回
        TypstDoc.lps_map[self.text] = lps
        return lps

    # endregion


class TypstText(TypstDoc):
    '''
    Typst 文本
    '''
    def __init__(
        self,
        text: str,
        *,
        shared_preamble: str | None = None,
        preamble: str | None = None,
        use_math_environment: bool = False,
        **kwargs
    ):
        if preamble is None:
            if use_math_environment:
                preamble = Config.get.typst_math_preamble
            else:
                preamble = Config.get.typst_text_preamble
        super().__init__(
            f'$ {text} $' if use_math_environment else text,
            shared_preamble=shared_preamble,
            additional_preamble=preamble,
            **kwargs
        )

    def move_into_position(self) -> None:
        self.points.to_center()


class TypstMath(TypstText):
    '''
    Typst 公式

    相当于 :class:`TypstText` 传入 ``use_math_environment=True``
    '''
    def __init__(
        self,
        text: str,
        *,
        shared_preamble: str | None = None,
        preamble: str | None = None,
        use_math_environment: bool = True,
        **kwargs
    ):
        super().__init__(
            text,
            shared_preamble=shared_preamble,
            preamble=preamble,
            use_math_environment=use_math_environment,
            **kwargs
        )


class Typst(TypstMath):
    def __init__(self, text: str, **kwargs):
        from janim.utils.deprecation import deprecated
        deprecated(
            'Typst',
            'TypstMath',
            remove=(3, 3)
        )
        super().__init__(text, **kwargs)


cached_typst_template: str | None = None


def get_typst_template() -> str:
    global cached_typst_template

    if cached_typst_template is not None:
        return cached_typst_template

    with open(os.path.join(get_janim_dir(), 'items', 'svg', 'typst_template.typ')) as f:
        text = f.read()

    cached_typst_template = text
    return text
