from __future__ import annotations

import hashlib
import itertools as it
import os
import subprocess as sp
import types
from typing import Iterable, Self, overload

import numpy as np

from janim.constants import ORIGIN, UP
from janim.exception import (EXITCODE_TYPST_COMPILE_ERROR,
                             EXITCODE_TYPST_NOT_FOUND, ExitException,
                             InvalidOrdinalError, PatternMismatchError)
from janim.items.points import Group
from janim.items.svg.svg_item import SVGElemItem, SVGItem
from janim.items.vitem import VItem
from janim.locale.i18n import get_local_strings
from janim.logger import log
from janim.utils.config import Config
from janim.utils.file_ops import get_janim_dir, get_typst_temp_dir
from janim.utils.iterables import flatten
from janim.utils.space_ops import rotation_between_vectors

_ = get_local_strings('typst')

type TypstPattern = TypstDoc | str


class TypstDoc(SVGItem):
    '''
    Typst 文档
    '''

    group_key = 'data-typst-label'

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

        typst_content = get_typst_template().replace('[typst_expression]', text)

        commands = [
            Config.get.typst_bin,
            'compile',
            '-',
            svg_file_path,
            '-f', 'svg'
        ]

        try:
            process = sp.Popen(commands, stdin=sp.PIPE)
        except FileNotFoundError:
            log.error(_('Could not compile typst file. '
                        'Please install typst and add it to the environment variables.'))
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

            t1 = Typst('x^2 + y^2')
            t2 = Typst('x + y')
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
    def __getitem__(self, key: int) -> VItem: ...
    @overload
    def __getitem__(self, key: slice) -> Group[VItem]: ...

    @overload
    def __getitem__(self, key: TypstPattern) -> Group[VItem]: ...
    @overload
    def __getitem__(self, key: tuple[TypstPattern, int]) -> Group[VItem]: ...
    @overload
    def __getitem__(self, key: tuple[TypstPattern, Iterable[int]]) -> Group[Group[VItem]]: ...
    @overload
    def __getitem__(self, key: tuple[TypstPattern, types.EllipsisType]) -> Group[Group[VItem]]: ...

    @overload
    def __getitem__(self, key: Iterable[int]) -> Group[VItem]: ...
    @overload
    def __getitem__(self, key: Iterable[bool]) -> Group[VItem]: ...

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
