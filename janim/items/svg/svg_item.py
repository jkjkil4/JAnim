
import os
from collections import defaultdict
from typing import Any, Callable, Self

import numpy as np
import svgelements as se

from janim.constants import ORIGIN, RIGHT
from janim.items.item import Item
from janim.items.points import Group
from janim.items.vitem import VItem
from janim.logger import log
from janim.utils.bezier import PathBuilder
from janim.utils.config import Config
from janim.utils.file_ops import find_file

# 这里的 3.272 是手动试出来的
DEFAULT_SVGITEM_SCALE_FACTOR = 3.272
STROKE_WIDTH_CONVERSION = 0.01

type SVGElemItem = VItem
type ItemBuilder = Callable[[], SVGElemItem]
type GroupIndexer = defaultdict[str, list[int]]


def _convert_point_to_3d(x: float, y: float) -> np.ndarray:
    return np.array([x, y, 0])


def _convert_opacity(x: float | None) -> float:
    return 0. if x is None else x


def _parse_color(hex, opacity) -> tuple[str, float]:
    # '#RRGGBBAA'
    if isinstance(hex, str) and hex.startswith('#') and len(hex) == 9:
        return hex[:7], int(hex[-2:], 16) / 255     # ('#RRGGBB', Alpha)

    return hex, _convert_opacity(opacity)


class SVGItem(Group[SVGElemItem]):
    '''
    传入 SVG 文件路径，解析为物件
    '''
    svg_part_default_kwargs = dict(
        stroke_radius=1.0 * STROKE_WIDTH_CONVERSION / 2,
        stroke_color=None,
        stroke_alpha=0,
        fill_color=None,
        fill_alpha=0
    )
    vitem_builders_map: dict[tuple, tuple[list[ItemBuilder], GroupIndexer]] = {}
    group_key: str | None = None

    def __init__(
        self,
        file_path: str,
        *,
        width: float | None = None,
        height: float | None = None,
        **kwargs
    ):
        items, self.groups = self.get_items_from_file(file_path)

        super().__init__(*items, **kwargs)

        box = self.points.box

        if width is None and height is None:
            self.points.scale(
                Config.get.default_pixel_to_frame_ratio * DEFAULT_SVGITEM_SCALE_FACTOR,
                about_point=ORIGIN
            )
        elif width is None and height is not None:
            self.points.set_size(
                height * box.width / box.height,
                height,
                about_point=ORIGIN
            )
        elif width is not None and height is None:
            self.points.set_size(
                width,
                width * box.height / box.width,
                about_point=ORIGIN
            )
        else:   # width is not None and height is not None
            self.points.set_size(width, height, about_point=ORIGIN)

        self(VItem).points.flip(RIGHT)

        self.move_into_position()

    def move_into_position(self) -> None:
        pass

    def copy(self, *, root_only=False, as_time: float | None = None, skip_dynamic: bool = False) -> Self:
        copy_item = super().copy(root_only=root_only, as_time=as_time, skip_dynamic=skip_dynamic)

        if not root_only:
            def get_idx(item: Item) -> int | None:
                try:
                    return self.children.index(item)
                except ValueError:
                    return None

            copy_item.groups = {
                key: [
                    copy_item[idx]
                    for item in group
                    if (idx := get_idx(item)) is not None
                ]
                for key, group in self.groups.items()
            }

        return copy_item

    @classmethod
    def get_items_from_file(cls, file_path: str) -> tuple[list[SVGElemItem], dict[str, list[SVGElemItem]]]:
        '''
        解析文件并得到物件列表
        '''
        file_path = find_file(file_path)
        mtime = os.path.getmtime(file_path)
        name = os.path.splitext(os.path.basename(file_path))[0]
        key = (name, mtime)

        cached = SVGItem.vitem_builders_map.get(key, None)
        if cached is not None:
            return cls.build_items(*cached)

        svg: se.SVG = se.SVG.parse(file_path)

        offset = np.array([svg.width / -2, svg.height / -2])

        builders: list[ItemBuilder] = []
        indexers: GroupIndexer = defaultdict(list)
        group_finder: defaultdict[Any, list[str]] = defaultdict(list)
        for shape in svg.elements():
            if isinstance(shape, se.Use):
                continue

            elif isinstance(shape, se.Group):
                if cls.group_key is None:
                    continue
                name = shape.values.get(cls.group_key, None)
                if name is None:
                    continue
                for elem in shape.select():
                    if not isinstance(elem, se.Path):
                        continue
                    group_finder[id(elem)].append(name)
                continue

            elif isinstance(shape, se.Path):
                builders.append(SVGItem.convert_path(shape, offset))

            elif type(shape) is se.SVGElement:
                continue
            else:
                # i18n?
                log.warning(f'Unsupported element type: {type(shape)}')
                continue

            if not group_finder:
                continue
            names = group_finder.get(id(shape), None)
            if names is None:
                continue
            for name in names:
                indexers[name].append(len(builders) - 1)

        SVGItem.vitem_builders_map[key] = (builders, indexers)
        return cls.build_items(builders, indexers)

    @staticmethod
    def build_items(
        builders: list[ItemBuilder],
        indexers: GroupIndexer
    ) -> tuple[list[SVGElemItem], dict[str, list[SVGElemItem]]]:
        items = [builder() for builder in builders]
        groups = {
            key: Group.from_iterable(items[idx] for idx in indices)
            for key, indices in indexers.items()
        }
        return items, groups

    @staticmethod
    def convert_path(path: se.Path, offset: np.ndarray) -> ItemBuilder:
        builder = PathBuilder()
        segment_class_to_func_map = {
            se.Move: (builder.move_to, ('end',)),
            se.Close: (builder.close_path, ()),
            se.Line: (builder.line_to, ('end',)),
            se.QuadraticBezier: (builder.conic_to, ('control', 'end')),
            se.CubicBezier: (builder.cubic_to, ('control1', 'control2', 'end')),
            se.Arc: (lambda segment: builder.arc_to(_convert_point_to_3d(*segment.end), segment.sweep), None),
        }

        for segment in path:
            segment_class = segment.__class__
            func, attr_names = segment_class_to_func_map[segment_class]
            if attr_names is None:
                func(segment)
            else:
                points = [
                    _convert_point_to_3d(*getattr(segment, attr_name))
                    for attr_name in attr_names
                ]
                func(*points)

        opacity = float(path.values.get('opacity', 1))

        stroke_color, stroke_alpha = _parse_color(path.stroke.hex, path.stroke.opacity)
        fill_color, fill_alpha = _parse_color(path.fill.hex, path.fill.opacity)

        vitem_styles = dict(
            stroke_radius=path.stroke_width * STROKE_WIDTH_CONVERSION / 2,
            stroke_color=stroke_color,
            stroke_alpha=stroke_alpha * opacity,
            fill_color=fill_color,
            fill_alpha=fill_alpha * opacity
        )
        vitem_points = builder.get()
        vitem_points[:, :2] += offset

        def vitem_builder() -> VItem:
            vitem = VItem(**SVGItem.svg_part_default_kwargs)
            vitem.apply_style(**vitem_styles)
            vitem.points.set(vitem_points)
            return vitem

        return vitem_builder
