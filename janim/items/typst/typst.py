from __future__ import annotations

import itertools as it
import types
from typing import Iterable, Self, overload

import numpy as np

from janim.anims.updater import updater_params_ctx
from janim.constants import UP
from janim.exception import InvalidOrdinalError, PatternMismatchError
from janim.items.group import Group
from janim.items.svg.svg_item import BasepointVItem, SVGElemItem
from janim.items.typst.compile import (
    TypstSizeUnit,
    TypstVar,
    compile_typst,
    resolve_groups,
)
from janim.items.typst.element import TypstElemItem
from janim.items.typst.vars import (
    replace_vars_placeholders,
    stringify_vars_tree,
    TYPST_PT_TO_FRAME_RATIO,
)
from janim.items.vitem import VItem
from janim.locale import get_translator
from janim.utils.config import Config
from janim.utils.iterables import flatten
from janim.utils.space_ops import rotation_between_vectors

_ = get_translator('janim.items.svg.typst')

type TypstPattern = TypstDoc | str


class TypstDoc(Group[TypstElemItem]):
    """
    Typst 文档
    """

    group_key = 'data-typst-label'

    def __init__(
        self,
        text: str,
        *,
        # 文档内容相关
        shared_preamble: str | None = None,
        additional_preamble: str | None = None,
        vars: dict[str, TypstVar] | None = None,
        vars_size_unit: TypstSizeUnit | None = None,
        sys_inputs: dict[str, str] = {},
        # 缩放与尺寸
        scale: float = 1.0,  # 缩放系数，仅当 width 和 height 都为 None 时有效
        width: float | None = None,
        height: float | None = None,
        # 其它设置
        root: str | None = None,
        mark_basepoint: bool = False,
        **kwargs,
    ):
        self.text = text

        # Typst 产物得到的坐标以 pt 为单位，需要转换到 JAnim 坐标
        scale *= TYPST_PT_TO_FRAME_RATIO

        # 只有在不位于 Updater 内部时才缓存解析结果
        on_updater = updater_params_ctx.get(None) is not None

        if shared_preamble is None:
            shared_preamble = Config.get.typst_shared_preamble
        if additional_preamble is None:
            additional_preamble = ''

        parsed_vars = stringify_vars_tree(vars, vars_size_unit)
        children, groups_indices = compile_typst(
            text=text,
            shared_preamble=shared_preamble,  # type: ignore
            additional_preamble=additional_preamble,
            vars='' if parsed_vars is None else parsed_vars[0],
            sys_inputs=sys_inputs,
            root=root,
            mark_basepoint=mark_basepoint,
            scale=scale,
            cache=not on_updater,
        )
        if parsed_vars is not None:
            children = replace_vars_placeholders(children, parsed_vars[1], groups_indices)
        self.groups = resolve_groups(children, groups_indices)

        super().__init__(*children, **kwargs)

        box = self.points.box

        # 根据 width 和 height 缩放，如果都没有指定，则这部分无效
        if width is None and height is not None:
            factor = height / box.height
            self.points.set_size(box.width * factor, height, about_edge=None)
        elif width is not None and height is None:
            factor = width / box.width
            self.points.set_size(width, box.height * factor, about_edge=None)
        elif width is not None and height is not None:
            factor = min(width / box.width, height / box.height)
            self.points.set_size(width, height, about_edge=None)

        self.move_into_position()

    def move_into_position(self) -> None:
        self.points.scale(0.9, about_edge=None).to_border(UP)

    @classmethod
    def typstify(cls, obj: TypstPattern) -> TypstDoc:
        """
        将字符串变为 Typst 对象，而本身已经是的则直接返回
        """
        return obj if isinstance(obj, TypstDoc) else cls(obj)

    # region pattern-matching

    def get_label(self, name: str) -> Group[SVGElemItem]:
        return Group.from_iterable(self.groups[name])

    def match_pattern(
        self,
        target: TypstDoc,
        pattern: TypstPattern,
        ordinal: int = 0,
        target_ordinal: int | None = None,
    ) -> Self:
        """
        配对并通过变换使得配对的部分重合

        例如

        .. code-block:: python

            t1 = TypstMath('x^2 + y^2')
            t2 = TypstMath('x + y')
            t2.points.match_pattern(t1, '+')

        则会将 ``t2`` 进行变换使得二者的加号重合
        """
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

    type SingleMatchPattern = TypstPattern | tuple[TypstPattern, int]
    type MultiMatchPattern = (
        tuple[TypstPattern, Iterable[int]] | tuple[TypstPattern, types.EllipsisType]
    )

    @overload
    def __getitem__(self, key: int) -> VItem | BasepointVItem: ...
    @overload
    def __getitem__(self, key: slice) -> Group[VItem | BasepointVItem]: ...

    @overload
    def __getitem__(self, key: SingleMatchPattern) -> Group[VItem | BasepointVItem]: ...
    @overload
    def __getitem__(self, key: MultiMatchPattern) -> Group[Group[VItem | BasepointVItem]]: ...

    @overload
    def __getitem__(self, key: Iterable[int] | Iterable[bool]) -> Group[VItem | BasepointVItem]: ...

    def __getitem__(self, key):
        """
        重载了一些字符索引的用法，即 :meth:`get` 和 :meth:`slice` 的组合
        """
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
            case TypstDoc() | str() as pattern, ordinal if isinstance(
                ordinal, (Iterable, types.EllipsisType)
            ):
                return Group(*self.get(self.slice(pattern, ordinal)))

            case _:
                return super().__getitem__(key)

    @overload
    def patterns(self, *patterns: SingleMatchPattern) -> Group[VItem | BasepointVItem]: ...
    @overload
    def patterns(self, *patterns: MultiMatchPattern) -> Group[Group[VItem | BasepointVItem]]: ...

    @overload
    def patterns(
        self,
        *patterns: SingleMatchPattern | MultiMatchPattern,
    ) -> Group[VItem | BasepointVItem] | Group[Group[VItem | BasepointVItem]]: ...

    def patterns(self, *patterns):
        """
        一次性获取多个 pattern 匹配的结果，返回一个 :class:`~.Group`

        例如 ``typ.patterns(A, B, ...)`` 相当于 ``Group(typ[A], typ[B], ...)``
        """
        return Group.from_iterable(self[pattern] for pattern in patterns)

    def get(self, slices, gapless: bool = False):
        """
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

          ``item.get([slice(1, 3), slice(5, 7)], gapless=True) == [item[:1], item[1:3], item[3:5], item[5:7], item[7:]]``

        - 注：在这种情况下，所有嵌套结构都会先被展平后处理
        """  # noqa: E501
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
            return [self[start:stop] for start, stop in it.pairwise(sorted(indices))]

    @overload
    def slice(self, pattern: TypstPattern, ordinal: int) -> slice: ...
    @overload
    def slice(
        self, pattern: TypstPattern, ordinal: Iterable[int] | types.EllipsisType
    ) -> list[slice]: ...

    def slice(self, pattern, ordinal=0):
        """
        得到指定 ``pattern`` 在该物件中形状配对的切片

        - 默认返回首个匹配的（即 ``ordinal=0``）
        - ``ordinal`` 传入其它索引可得到随后匹配的特定部分
        - ``ordinal`` 传入索引列表可得到多个匹配的特定部分
        - ``ordinal`` 传入省略号 ``...`` 可以得到所有匹配的部分
        """
        pattern = self.typstify(pattern)
        indices = self.indices(pattern)

        if not indices:
            raise PatternMismatchError(
                _('No matches found for {pattern}').format(pattern=repr(pattern.text))
            )

        def get_slice(i: int):
            if not 0 <= i < len(indices):
                raise PatternMismatchError(
                    _('{ordinal} is out of range for {count} matches').format(
                        ordinal=i,
                        count=len(indices),
                    )
                )
            return slice(indices[i], indices[i] + len(pattern))

        match ordinal:
            case int(i):
                return get_slice(i)
            case _ if isinstance(ordinal, Iterable) and all(isinstance(i, int) for i in ordinal):
                return [get_slice(i) for i in ordinal]
            case types.EllipsisType():
                return [slice(i, i + len(pattern)) for i in indices]

        raise InvalidOrdinalError(_('ordinal {} is invalid').format(ordinal))

    def indices(self, pattern: TypstPattern) -> list[int]:
        """
        找出该公式中所有出现了 ``pattern`` 的位置

        - ``pattern`` 支持使用字符串或者 Typst 对象
        """
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
        """
        KMP 算法涉及的部分匹配表
        """
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
    """
    Typst 文本
    """

    def __init__(
        self,
        text: str,
        *,
        shared_preamble: str | None = None,
        preamble: str | None = None,
        use_math_environment: bool = False,
        **kwargs,
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
            **kwargs,
        )

    def move_into_position(self) -> None:
        self.points.to_center()


class TypstMath(TypstText):
    """
    Typst 公式

    相当于 :class:`TypstText` 传入 ``use_math_environment=True``
    """

    def __init__(
        self,
        text: str,
        *,
        shared_preamble: str | None = None,
        preamble: str | None = None,
        use_math_environment: bool = True,
        **kwargs,
    ):
        super().__init__(
            text,
            shared_preamble=shared_preamble,
            preamble=preamble,
            use_math_environment=use_math_environment,
            **kwargs,
        )
