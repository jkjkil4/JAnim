
import os
from collections import defaultdict
from typing import Any, Callable, Self
from functools import partial

import numpy as np
import svgelements as se

from janim.constants import ORIGIN, RIGHT, TAU
from janim.items.item import Item
from janim.items.points import Group
from janim.items.vitem import VItem
from janim.items.geometry.line import Line
from janim.items.geometry.arc import Circle
from janim.items.geometry.polygon import Rect, Polygon, Polyline, RoundedRect
from janim.locale.i18n import get_local_strings
from janim.logger import log
from janim.utils.bezier import PathBuilder, quadratic_bezier_points_for_arc
from janim.utils.config import Config
from janim.utils.file_ops import find_file
from janim.utils.space_ops import rotation_about_z

_ = get_local_strings('svg_item')

# 这里的 3.272 是手动试出来的
DEFAULT_SVGITEM_SCALE_FACTOR = 3.272

type SVGElemItem = VItem
type ItemBuilder = Callable[[], SVGElemItem]
type GroupIndexer = defaultdict[str, list[int]]


def _point_to_3d(x: float, y: float) -> np.ndarray:
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
            factor = Config.get.default_pixel_to_frame_ratio * DEFAULT_SVGITEM_SCALE_FACTOR
            self.points.scale(
                factor,
                about_point=ORIGIN
            )
        elif width is None and height is not None:
            factor = height / box.height
            self.points.set_size(
                box.width * factor,
                height,
                about_point=ORIGIN
            )
        elif width is not None and height is None:
            factor = width / box.width
            self.points.set_size(
                width,
                box.height * factor,
                about_point=ORIGIN
            )
        else:   # width is not None and height is not None
            factor = min(width / box.width, height / box.height)
            self.points.set_size(width, height, about_point=ORIGIN)

        self.points.flip(RIGHT)
        self.scale_descendants_stroke_radius(factor)
        self.move_into_position()

    def move_into_position(self) -> None:
        pass

    def copy(self, *, root_only=False) -> Self:
        copy_item = super().copy(root_only=root_only)

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

    def scale_descendants_stroke_radius(self, factor: float) -> Self:
        '''将所有后代物件的 stroke_radius 都乘上一个值'''
        for item in self.walk_descendants(VItem):
            item.radius.set(item.radius.get() * factor)

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
                    if not isinstance(elem, se.Shape):
                        continue
                    group_finder[id(elem)].append(name)
                continue

            elif isinstance(shape, se.Path):
                builder = SVGItem.convert_path(shape, offset)
            elif isinstance(shape, se.SimpleLine):
                builder = SVGItem.convert_line(shape, offset)
            elif isinstance(shape, se.Rect):
                builder = SVGItem.convert_rect(shape, offset)
            elif isinstance(shape, (se.Circle, se.Ellipse)):
                builder = SVGItem.convert_ellipse(shape, offset)
            elif isinstance(shape, se.Polygon):
                builder = SVGItem.convert_polygon(shape, offset)
            elif isinstance(shape, se.Polyline):
                builder = SVGItem.convert_polyline(shape, offset)
            # elif isinstance(shape, se.Text):
            #     builder = SVGItem.convert_text(shape, offset)
            # elif isinstance(shape, se.Image):
            #     builder = SVGItem.convert_image(shape, offset)

            elif type(shape) is se.SVGElement:
                continue
            else:
                log.warning(_('Unsupported element type: {type}').format(type=type(shape)))
                continue

            builders.append(builder)

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
    def get_styles_from_shape(shape: se.Shape) -> dict:
        opacity = float(shape.values.get('opacity', 1))

        stroke_color, stroke_alpha = _parse_color(shape.stroke.hex, shape.stroke.opacity)
        fill_color, fill_alpha = _parse_color(shape.fill.hex, shape.fill.opacity)

        return dict(
            stroke_radius=shape.stroke_width / 2,        # stroke_width 貌似不会为 None，所以这里直接使用
            stroke_color=stroke_color,
            stroke_alpha=stroke_alpha * opacity,
            fill_color=fill_color,
            fill_alpha=fill_alpha * opacity
        )

    @staticmethod
    def convert_path(path: se.Path, offset: np.ndarray) -> ItemBuilder:
        builder = PathBuilder()

        transform_cache: tuple[se.Matrix, np.ndarray, np.ndarray] | None = None

        def get_transform() -> tuple[se.Matrix, np.ndarray, np.ndarray]:
            nonlocal transform_cache
            if transform_cache is not None:
                return transform_cache

            # 通过这种方式得到的 transform 是考虑了 svg 中所有父级 group 的 transform 共同作用的
            # 所以可以通过这个 transform 对 arc 作逆变换，正确计算 arc 路径，再变换回来
            transform = se.Matrix(path.values.get('transform', ''))
            rot = np.array([
                [transform.a, transform.c],
                [transform.b, transform.d]
            ])
            shift = np.array([transform.e, transform.f, 0])
            transform.inverse()
            transform_cache = (transform, rot, shift)
            return transform_cache

        def convert_arc(arc: se.Arc):
            transform, rot, shift = get_transform()

            # 对 arc 作逆变换，使得 arc 的路径可以被正确计算
            arc *= transform

            n_components = int(np.ceil(8 * abs(arc.sweep) / TAU))

            # 得到单位圆上所需角度的片段
            arc_points = quadratic_bezier_points_for_arc(arc.sweep, arc.get_start_t(), n_components)

            # 变换至椭圆，并考虑旋转参数，以及平移椭圆中心
            arc_points[:, 0] *= arc.rx
            arc_points[:, 1] *= arc.ry
            arc_points @= np.array(rotation_about_z(arc.get_rotation().as_radians)).T
            arc_points += [*arc.center, 0]

            # 变换回来
            arc_points[:, :2] @= rot.T
            arc_points += shift

            builder.append(arc_points[1:])

        segment_class_to_func_map = {
            se.Move: (builder.move_to, ('end',)),
            se.Close: (builder.close_path, ()),
            se.Line: (builder.line_to, ('end',)),
            se.QuadraticBezier: (builder.conic_to, ('control', 'end')),
            se.CubicBezier: (builder.cubic_to, ('control1', 'control2', 'end')),
        }

        for segment in path:
            segment_class = segment.__class__
            if segment_class is se.Arc:
                convert_arc(segment)
            else:
                func, attr_names = segment_class_to_func_map[segment_class]
                points = [
                    _point_to_3d(*getattr(segment, attr_name))
                    for attr_name in attr_names
                ]
                func(*points)

        vitem_styles = SVGItem.get_styles_from_shape(path)
        vitem_points = builder.get()
        vitem_points[:, :2] += offset

        def vitem_builder() -> VItem:
            vitem = VItem(**vitem_styles)
            vitem.points.set(vitem_points)
            return vitem

        return vitem_builder

    @staticmethod
    def convert_line(line: se.SimpleLine, offset: np.ndarray) -> ItemBuilder:
        styles = SVGItem.get_styles_from_shape(line)
        start = _point_to_3d(*offset) + _point_to_3d(line.x1, line.y1)
        end = _point_to_3d(*offset) + _point_to_3d(line.x2, line.y2)
        return partial(Line, start, end, **styles)

    @staticmethod
    def convert_rect(rect: se.Rect, offset: np.ndarray) -> ItemBuilder:
        styles = SVGItem.get_styles_from_shape(rect)
        pos1 = _point_to_3d(*offset) + _point_to_3d(rect.x, rect.y)
        if rect.rx == 0 or rect.ry == 0:
            pos2 = pos1 + _point_to_3d(rect.width, rect.height)
            return partial(Rect, pos1, pos2, **styles)
        else:
            pos2 = pos1 + _point_to_3d(rect.width, rect.height * rect.rx / rect.ry)

            def builder() -> RoundedRect:
                item = RoundedRect(
                    pos1,
                    pos2,
                    corner_radius=rect.rx,
                    **styles
                )
                item.points.set_height(rect.height, about_point=pos1)
                return item

            return builder

    @staticmethod
    def convert_ellipse(ellipse: se.Circle | se.Ellipse, offset: np.ndarray) -> ItemBuilder:
        styles = SVGItem.get_styles_from_shape(ellipse)
        shift = _point_to_3d(*offset) + _point_to_3d(ellipse.cx, ellipse.cy)

        def builder() -> Circle:
            item = Circle(ellipse.rx, **styles)
            item.points.set_height(2 * ellipse.ry, stretch=True)
            item.points.shift(shift)
            return item

        return builder

    @staticmethod
    def convert_polygon(polygon: se.Polygon, offset: np.ndarray) -> ItemBuilder:
        styles = SVGItem.get_styles_from_shape(polygon)
        offset_3d = _point_to_3d(*offset)
        points = [
            offset_3d + _point_to_3d(*point)
            for point in polygon
        ]
        return partial(Polygon, *points, **styles)

    @staticmethod
    def convert_polyline(polyline: se.Polyline, offset: np.ndarray) -> ItemBuilder:
        styles = SVGItem.get_styles_from_shape(polyline)
        offset_3d = _point_to_3d(*offset)
        points = [
            offset_3d + _point_to_3d(*point)
            for point in polyline
        ]
        return partial(Polyline, *points, **styles)

    @staticmethod
    def convert_text(text: se.Text, offset: np.ndarray) -> ItemBuilder:
        # TODO: convert_text
        pass

    @staticmethod
    def convert_image(image: se.Image, offset: np.ndarray) -> ItemBuilder:
        # TODO: convert_image
        pass
