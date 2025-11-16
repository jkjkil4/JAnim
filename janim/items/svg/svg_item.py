from __future__ import annotations

import os
from collections import defaultdict
from functools import partial
from typing import Any, Callable, Iterable, Self

import numpy as np
import svgelements as se

from janim.constants import FRAME_PPI, ORIGIN, RIGHT, TAU, UP
from janim.items.geometry.arc import Circle
from janim.items.geometry.line import Line
from janim.items.geometry.polygon import Polygon, Polyline, Rect, RoundedRect
from janim.items.item import Item
from janim.items.points import Group
from janim.items.text import BasepointVItem, Text, TextLine
from janim.items.vitem import VItem
from janim.locale.i18n import get_local_strings
from janim.logger import log
from janim.utils.bezier import PathBuilder, quadratic_bezier_points_for_arc
from janim.utils.config import Config
from janim.utils.file_ops import find_file
from janim.utils.space_ops import rotation_about_z

_ = get_local_strings('svg_item')


type SVGElemItem = VItem | BasepointVItem | TextLine
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
        scale: float = 1.0,     # 缩放系数，仅当 width 和 height 都为 None 时有效
        width: float | None = None,
        height: float | None = None,
        mark_basepoint: bool = False,
        stroke_radius: float | Iterable[float] | None = None,
        **kwargs
    ):
        items, self.groups = self.get_items_from_file(file_path, mark_basepoint)

        super().__init__(*items, **kwargs)

        box = self.points.box

        if width is None and height is None:
            # 因为解析 svg 时按照默认的 PPI=96 读取，而 janim 默认 PPI=144，所以要缩放 (FRAME_PPI / 96)
            factor = Config.get.default_pixel_to_frame_ratio * (FRAME_PPI / 96) * scale
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

        self(VItem).points.flip(RIGHT, about_edge=None)
        self.scale_descendants_stroke_radius(factor)
        if stroke_radius is not None:
            self(VItem).radius.set(stroke_radius)
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
    def get_items_from_file(
        cls,
        file_path: str,
        mark_basepoint: bool = False
    ) -> tuple[list[SVGElemItem], dict[str, list[SVGElemItem]]]:
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

        svg: se.SVG = se.SVG.parse(file_path)   # PPI=96

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
                builder = SVGItem.convert_path(shape, offset, mark_basepoint)
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
            elif isinstance(shape, se.Text):
                if shape.text is None:
                    continue
                builder = SVGItem.convert_text(shape, offset)
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
    def get_rot_and_shift_from_matrix(mat: se.Matrix) -> tuple[np.ndarray, np.ndarray]:
        rot = np.array([
            [mat.a, mat.c],
            [mat.b, mat.d]
        ])
        shift = np.array([mat.e, mat.f, 0])
        return rot, shift

    @staticmethod
    def convert_path(path: se.Path, offset: np.ndarray, mark_basepoint: bool = False) -> ItemBuilder:
        builder = PathBuilder()

        transform_cache: tuple[se.Matrix, np.ndarray, np.ndarray] | None = None

        def get_transform() -> tuple[se.Matrix, np.ndarray, np.ndarray]:
            nonlocal transform_cache
            if transform_cache is not None:
                return transform_cache

            # 通过这种方式得到的 transform 是考虑了 svg 中所有父级 group 的 transform 共同作用的
            # 所以可以通过这个 transform 对 arc 作逆变换，正确计算 arc 路径，再变换回来
            transform = se.Matrix(path.values.get('transform', ''))
            rot, shift = SVGItem.get_rot_and_shift_from_matrix(transform)
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
            se.Move: (builder.move_to_and_ignore_previous_move, ('end',)),
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

        if mark_basepoint:
            # 对于 Typst 生成的 SVG，SVG 对象在没有 transform 作用的情况下
            # 原点就在其基线上，所以将原点作用 transform 即可得到 SVG 对象（一般而言是文字）的基线
            transform = se.Matrix(path.values.get('transform', ''))
            rot, shift = SVGItem.get_rot_and_shift_from_matrix(transform)
            marks = np.array([ORIGIN, RIGHT, UP])
            marks[:, :2] @= rot.T
            marks[:, :2] += shift[:2] + offset

            def vitem_builder() -> BasepointVItem:
                vitem = BasepointVItem(**vitem_styles)
                vitem.points.set(vitem_points)
                vitem.mark.set_points(marks)
                return vitem
        else:
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
        styles = SVGItem.get_styles_from_shape(text)

        transform = se.Matrix(text.values.get('transform', ''))
        rot, shift = SVGItem.get_rot_and_shift_from_matrix(transform)

        family = text.font_family.strip('"').strip('\'')
        ratio = Config.get.default_pixel_to_frame_ratio
        # 因为字体默认 PPI=72，而 janim 默认 PPI=144，所以乘上 (72 / FRAME_PPI)
        font_size = text.font_size / ratio * (72 / FRAME_PPI)

        offset_3d = _point_to_3d(*offset)

        def points_fn(points: np.ndarray) -> np.ndarray:
            points = points.copy()
            points[:, :2] @= rot.T
            points += shift + offset_3d
            return points

        def builder() -> TextLine:
            txt = Text(text.text,
                       font=family,
                       font_size=font_size,
                       weight=text.font_weight,
                       style=text.font_style,
                       center=False,
                       **styles)
            assert len(txt) == 1
            line = txt[0]
            assert np.all(line.get_mark_orig() == ORIGIN)
            # 貌似 svgelements 对于列表的 x y dx dy 只能解析出一个值
            # 所以这里直接处理为 x+dx 和 y+dy，比较粗糙
            line.points.shift([text.x + text.dx, -(text.y + text.dy), 0]).flip(RIGHT, about_edge=None)
            line.points.apply_points_fn(points_fn, about_edge=None)

            return line

        return builder

    @staticmethod
    def convert_image(image: se.Image, offset: np.ndarray) -> ItemBuilder:
        # TODO: convert_image
        pass
