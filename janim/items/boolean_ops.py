from __future__ import annotations

import numpy as np
import pathops

from janim.exception import BooleanOpsError
from janim.items.item import Item
from janim.items.vitem import VItem
from janim.locale.i18n import get_local_strings
from janim.utils.bezier import PathBuilder

_ = get_local_strings('boolean_ops')

# Boolean operations between 2D items
# Borrowed from from https://github.com/ManimCommunity/manim/


def _convert_vitem_to_skia_path(vitem: VItem) -> pathops.Path:
    path = pathops.Path()
    subpaths = vitem.points.get_subpaths()
    for subpath in subpaths:
        quads = vitem.points.get_bezier_tuples_from_points(subpath)
        start = subpath[0]
        path.moveTo(*start[:2])
        for p0, p1, p2 in quads:
            path.quadTo(*p1[:2], *p2[:2])
        if np.isclose(subpath[0], subpath[-1]).all():
            path.close()
    return path


def _convert_skia_path_to_vitem(
    path: pathops.Path,
    vitem: VItem
) -> VItem:
    PathVerb = pathops.PathVerb
    builder: PathBuilder | None = None

    for path_verb, points in path:
        if path_verb == PathVerb.CLOSE:
            builder.close_path()
        else:
            points = np.hstack((np.array(points), np.zeros((len(points), 1))))
            if path_verb == PathVerb.MOVE:
                for point in points:
                    if builder is None:
                        builder = PathBuilder(start_point=point)
                    else:
                        builder.move_to(point)
            elif path_verb == PathVerb.CUBIC:
                builder.cubic_to(*points)
            elif path_verb == PathVerb.LINE:
                builder.line_to(points[0])
            elif path_verb == PathVerb.QUAD:
                builder.conic_to(*points)
            else:
                # i18n?
                raise BooleanOpsError(f'Unsupported: {path_verb}')

    vitem.points.set([] if builder is None else builder.get()).reverse()
    return vitem


class Union(VItem):
    '''
    并集

    常见情况下，传入两个及以上 :class:`~.VItem`，返回他它们区域的并集的外轮廓

    另外，如果只传入单个物件，则拷贝原路径

    该方法只有根物件参与计算，如果需要考虑所有子物件的并集，例如对 :class:`~.Text` 所有后代物件的并集，请参考 :meth:`from_group`
    '''
    def __init__(self, *vitems: VItem, **kwargs):
        if not vitems:
            raise BooleanOpsError(_('At least 1 item needed for Union.'))
        super().__init__(**kwargs)

        if len(vitems) == 1:
            self.points.set(vitems[0].points.get())
            return

        outpen = pathops.Path()
        pathops.union(
            [
                _convert_vitem_to_skia_path(vitem)
                for vitem in vitems
            ],
            outpen.getPen()
        )
        _convert_skia_path_to_vitem(outpen, self)

    @staticmethod
    def from_group(item: Item, **kwargs) -> Union:
        '''
        传入一个物件，将其所有后代物件作并集
        '''
        lst = [
            sub
            for sub in item.walk_self_and_descendants()
            if isinstance(sub, VItem)
        ]
        return Union(*lst, **kwargs)


class Difference(VItem):
    '''
    差集

    传入 ``subitem`` 和 ``clip``，返回 ``subitem`` 裁去 ``clip`` 区域的轮廓线
    '''
    def __init__(self, subitem: VItem, clip: VItem, **kwargs):
        super().__init__(**kwargs)
        outpen = pathops.Path()
        pathops.difference(
            [_convert_vitem_to_skia_path(subitem)],
            [_convert_vitem_to_skia_path(clip)],
            outpen.getPen(),
        )
        _convert_skia_path_to_vitem(outpen, self)


class Intersection(VItem):
    '''
    交集

    常见情况下，传入两个及以上 :class:`~.VItem`，返回它们区域交集的外轮廓

    另外，如果只传入单个物件，则拷贝原路径

    该方法只有根物件参与计算，如果需要考虑所有后代物件的交集，请参考 :meth:`from_group`
    '''
    def __init__(self, *vitems: VItem, **kwargs):
        if not vitems:
            raise BooleanOpsError(_('At least 1 item needed for Intersection.'))
        super().__init__(**kwargs)

        if len(vitems) == 1:
            self.points.set(vitems[0].points.get())
            return

        outpen = pathops.Path()
        pathops.intersection(
            [_convert_vitem_to_skia_path(vitems[0])],
            [_convert_vitem_to_skia_path(vitems[1])],
            outpen.getPen(),
        )
        new_outpen = outpen
        for _i in range(2, len(vitems)):
            new_outpen = pathops.Path()
            pathops.intersection(
                [outpen],
                [_convert_vitem_to_skia_path(vitems[_i])],
                new_outpen.getPen(),
            )
            outpen = new_outpen
        _convert_skia_path_to_vitem(outpen, self)

    @staticmethod
    def from_group(item: Item, **kwargs) -> Union:
        '''
        传入一个物件，将其所有后代物件作交集
        '''
        lst = [
            sub
            for sub in item.walk_self_and_descendants()
            if isinstance(sub, VItem)
        ]
        return Intersection(*lst, **kwargs)


class Exclusion(VItem):
    '''
    对称差集

    传入两个及以上 :class:`~.VItem`，返回它们的区域经过 XOR 运算后的外轮廓

    另外，如果只传入单个物件，则拷贝原路径

    该方法只有根物件参与计算，如果需要考虑所有后代物件的对称差集，请参考 :meth:`Exclusion.from_group`
    '''
    def __init__(self, *vitems: VItem, **kwargs):
        if not vitems:
            raise BooleanOpsError(_('At least 1 item needed for Exclusion.'))
        super().__init__(**kwargs)

        if len(vitems) == 1:
            self.points.set(vitems[0].points.get())
            return

        outpen = pathops.Path()
        pathops.xor(
            [_convert_vitem_to_skia_path(vitems[0])],
            [_convert_vitem_to_skia_path(vitems[1])],
            outpen.getPen(),
        )
        new_outpen = outpen
        for _i in range(2, len(vitems)):
            new_outpen = pathops.Path()
            pathops.xor(
                [outpen],
                [_convert_vitem_to_skia_path(vitems[_i])],
                new_outpen.getPen(),
            )
            outpen = new_outpen
        _convert_skia_path_to_vitem(outpen, self)

    @staticmethod
    def from_group(item: Item, **kwargs):
        '''
        传入一个物件，将其所有子物件依次作对称差集
        '''
        lst = [
            sub
            for sub in item.walk_self_and_descendants()
            if isinstance(sub, VItem)
        ]
        return Exclusion(*lst, **kwargs)
