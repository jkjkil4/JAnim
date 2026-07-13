from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
from typst4janim import Element, ShapeInfo, TextGlyphInfo

from janim.items.text import BASEPOINT_MARKS, BasepointVItem
from janim.items.vitem import VItem

__all__ = [
    'TypstElemItem',
    'TypTextGlyph',
    'MarkedTypTextGlyph',
    'TypShape',
]

type TypstElemItem = TypTextGlyph | MarkedTypTextGlyph | TypShape

type _Rgba = tuple[float, float, float, float]


@dataclass
class ParseArgs:
    shared: dict[int, Any]
    offset: np.ndarray
    mark_basepoint: bool


def parse_element(element: Element, scale: float, args: ParseArgs) -> TypstElemItem:
    return _element_map[element.elemtype](element, scale, args)


def _transform_points(
    points: np.ndarray, transform2x3: np.ndarray, scale: float, offset: np.ndarray
) -> np.ndarray:
    points = points.copy()
    points[:, :2] @= transform2x3[:, :2].T
    points[:, :2] += transform2x3[:, 2] + offset
    points[:, 1] *= -1
    points[:, :2] *= scale
    return points


@staticmethod
def _apply_styles(
    item: VItem,
    fill_rgba: _Rgba | None,
    stroke_rgba: _Rgba | None,
    stroke_thickness: float,
    scale: float,
) -> None:
    if fill_rgba is not None:
        item.fill.set_rgbas([fill_rgba])

    if stroke_rgba is None:
        item.stroke.set(alpha=0)
    else:
        item.stroke.set_rgbas([stroke_rgba])

    if stroke_thickness is not None:
        item.radius.set(stroke_thickness / 2 * scale)


class TypTextGlyph(VItem):
    def __init__(self, element: Element, scale: float, args: ParseArgs):
        info: TextGlyphInfo = element.info
        points: np.ndarray = args.shared[info.points_id]

        super().__init__()
        self.points.set(_transform_points(points, element.transform, scale, args.offset))
        _apply_styles(self, info.fill_rgba, info.stroke_rgba, info.stroke_thickness, scale)


class MarkedTypTextGlyph(TypTextGlyph, BasepointVItem):
    def __init__(self, element: Element, scale: float, args: ParseArgs):
        super().__init__(element, scale, args)
        self.mark.set_points(
            _transform_points(BASEPOINT_MARKS, element.transform, scale, args.offset)
        )


def _text_glyph(
    element: Element, scale: float, args: ParseArgs
) -> TypTextGlyph | MarkedTypTextGlyph:
    cls = MarkedTypTextGlyph if args.mark_basepoint else TypTextGlyph
    return cls(element, scale, args)


class TypShape(VItem):
    def __init__(self, element: Element, scale: float, args: ParseArgs):
        info: ShapeInfo = element.info

        super().__init__()
        self.points.set(_transform_points(info.points, element.transform, scale, args.offset))
        _apply_styles(self, info.fill_rgba, info.stroke_rgba, info.stroke_thickness, scale)


_element_map: dict[str, Callable[[Element, float, ParseArgs], TypstElemItem]] = {
    'TextGlyph': _text_glyph,
    'Shape': TypShape,
}
