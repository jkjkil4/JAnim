from __future__ import annotations

import numpy as np
import pathops

from janim.items.vitem import VItem


# Boolean operations between 2D items
# Borrowed from from https://github.com/ManimCommunity/manim/

def _convert_vitem_to_skia_path(vitem: VItem) -> pathops.Path:
    path = pathops.Path()
    subpaths = vitem.get_subpaths_from_points(vitem.get_all_points())
    for subpath in subpaths:
        quads = vitem.get_bezier_tuples_from_points(subpath)
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
    current_path_start = np.array([0.0, 0.0, 0.0])
    for path_verb, points in path:
        if path_verb == PathVerb.CLOSE:
            vitem.add_line_to(current_path_start)
        else:
            points = np.hstack((np.array(points), np.zeros((len(points), 1))))
            if path_verb == PathVerb.MOVE:
                for point in points:
                    current_path_start = point
                    vitem.path_move_to(point)
            elif path_verb == PathVerb.CUBIC:
                vitem.add_cubic_to(*points)
            elif path_verb == PathVerb.LINE:
                vitem.add_line_to(points[0])
            elif path_verb == PathVerb.QUAD:
                vitem.add_conic_to(*points)
            else:
                raise Exception(f"Unsupported: {path_verb}")
    return vitem.reverse_points()


class Union(VItem):
    def __init__(self, *vitems: VItem, **kwargs):
        if len(vitems) < 2:
            raise ValueError("At least 2 items needed for Union.")
        super().__init__(**kwargs)
        outpen = pathops.Path()
        paths = [
            _convert_vitem_to_skia_path(vitem)
            for vitem in vitems
        ]
        pathops.union(paths, outpen.getPen())
        _convert_skia_path_to_vitem(outpen, self)


class Difference(VItem):
    def __init__(self, subject: VItem, clip: VItem, **kwargs):
        super().__init__(**kwargs)
        outpen = pathops.Path()
        pathops.difference(
            [_convert_vitem_to_skia_path(subject)],
            [_convert_vitem_to_skia_path(clip)],
            outpen.getPen(),
        )
        _convert_skia_path_to_vitem(outpen, self)


class Intersection(VItem):
    def __init__(self, *vitems: VItem, **kwargs):
        if len(vitems) < 2:
            raise ValueError("At least 2 items needed for Intersection.")
        super().__init__(**kwargs)
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


class Exclusion(VItem):
    def __init__(self, *vitems: VItem, **kwargs):
        if len(vitems) < 2:
            raise ValueError("At least 2 items needed for Exclusion.")
        super().__init__(**kwargs)
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
