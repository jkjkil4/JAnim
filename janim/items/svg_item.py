from __future__ import annotations
from typing import Optional

import os
import hashlib
from xml.etree import ElementTree as ET

import svgelements as se
import numpy as np

from janim.constants import *
from janim.items.vitem import VItem
from janim.items.geometry.line import Line
from janim.items.geometry.polygon import Polygon, Polyline, Rectangle, RoundedRectangle
from janim.items.geometry.arc import Circle
from janim.utils.iterables import hash_obj
from janim.utils.directories import get_item_data_dir
from janim.logger import log

SVG_HASH_TO_MOB_MAP: dict[int, VItem] = {}

def _convert_point_to_3d(x: float, y: float) -> np.ndarray:
    return np.array([x, y, 0.0])


class SVGItem(VItem):
    def __init__(
        self,
        file_path: str | None = None,
        should_center: bool = True,
        width: Optional[float] = None,
        height: Optional[float] = 2,
        color: Optional[JAnimColor] = None,
        opacity: Optional[float] = None,
        fill_color: Optional[JAnimColor] = None,
        fill_opacity: Optional[float] = None,
        stroke_width: Optional[float] = None,
        svg_default: dict = dict(
            color=None,
            opacity=None,
            fill_color=WHITE,
            fill_opacity=None,
            stroke_width=None,
            stroke_color=None,
            stroke_opacity=None,
        ),
        path_string_config: dict = dict(),
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.file_path = file_path
        self.should_center = should_center
        self.width = width
        self.height = height
        self.svg_default = svg_default
        self.path_string_config = path_string_config

        self.init_svg_item()
        self.move_into_position()

        self.set_stroke(color, stroke_width, opacity)
        self.set_fill(fill_color, fill_opacity)

    def init_svg_item(self) -> None:
        hash_val = hash_obj(self.hash_seed)
        if hash_val in SVG_HASH_TO_MOB_MAP:
            item = SVG_HASH_TO_MOB_MAP[hash_val].copy()
            self.add(*item)
            return

        self.generate_item()
        SVG_HASH_TO_MOB_MAP[hash_val] = self.copy()

    @property
    def hash_seed(self) -> tuple:
        return (
            self.__class__.__name__,
            self.file_path,
            self.svg_default
        )

    def generate_item(self) -> None:
        file_path = self.get_file_path()
        element_tree = ET.parse(file_path)
        new_tree = self.modify_xml_tree(element_tree)
        # Create a temporary svg file to dump modified svg to be parsed
        root, ext = os.path.splitext(file_path)
        modified_file_path = root + "_" + ext
        new_tree.write(modified_file_path)

        svg = se.SVG.parse(modified_file_path)
        os.remove(modified_file_path)

        items = self.get_items_from(svg)
        self.add(*items)
        self.flip(RIGHT)  # Flip y

    def get_file_path(self) -> str:
        if self.file_path is None:
            raise Exception("Must specify file for SVGMobject")
        # TODO: get_full_vector_image_path
        return self.file_path

    def modify_xml_tree(self, element_tree: ET.ElementTree) -> ET.ElementTree:
        config_style_dict = self.generate_config_style_dict()
        style_keys = (
            "fill",
            "fill-opacity",
            "stroke",
            "stroke-opacity",
            "stroke-width",
            "style"
        )
        root = element_tree.getroot()
        root_style_dict = {
            k: v for k, v in root.attrib.items()
            if k in style_keys
        }

        new_root = ET.Element("svg", {})
        config_style_node = ET.SubElement(new_root, "g", config_style_dict)
        root_style_node = ET.SubElement(config_style_node, "g", root_style_dict)
        root_style_node.extend(root)
        return ET.ElementTree(new_root)

    def generate_config_style_dict(self) -> dict[str, str]:
        keys_converting_dict = {
            "fill": ("color", "fill_color"),
            "fill-opacity": ("opacity", "fill_opacity"),
            "stroke": ("color", "stroke_color"),
            "stroke-opacity": ("opacity", "stroke_opacity"),
            "stroke-width": ("stroke_width",)
        }
        svg_default_dict = self.svg_default
        result = {}
        for svg_key, style_keys in keys_converting_dict.items():
            for style_key in style_keys:
                if svg_default_dict[style_key] is None:
                    continue
                result[svg_key] = str(svg_default_dict[style_key])
        return result

    def get_items_from(self, svg: se.SVG) -> list[VItem]:
        result = []
        for shape in svg.elements():
            if isinstance(shape, se.Group):
                continue
            elif isinstance(shape, se.Path):
                item = self.path_to_item(shape)
            elif isinstance(shape, se.SimpleLine):
                item = self.line_to_item(shape)
            elif isinstance(shape, se.Rect):
                item = self.rect_to_item(shape)
            elif isinstance(shape, se.Circle):
                item = self.circle_to_item(shape)
            elif isinstance(shape, se.Ellipse):
                item = self.ellipse_to_item(shape)
            elif isinstance(shape, se.Polygon):
                item = self.polygon_to_item(shape)
            elif isinstance(shape, se.Polyline):
                item = self.polyline_to_item(shape)
            # elif isinstance(shape, se.Text):
            #     item = self.text_to_item(shape)
            elif type(shape) == se.SVGElement:
                continue
            else:
                log.warning(f"Unsupported element type: {type(shape)}")
                continue
            if not item.has_points():
                continue
            self.apply_style_to_mobject(item, shape)
            if isinstance(shape, se.Transformable) and shape.apply:
                self.handle_transform(item, shape.transform)
            result.append(item)
        return result

    @staticmethod
    def handle_transform(item: VItem, matrix: se.Matrix) -> VItem:
        mat = np.array([
            [matrix.a, matrix.c],
            [matrix.b, matrix.d]
        ])
        vec = np.array([matrix.e, matrix.f, 0.0])
        item.apply_matrix(mat)
        item.shift(vec)
        return item

    @staticmethod
    def apply_style_to_mobject(
        item: VItem,
        shape: se.GraphicObject
    ) -> VItem:
        item.set_stroke(shape.stroke.hex, shape.stroke_width / 100, shape.stroke.opacity)
        item.set_fill(shape.fill.hex, shape.fill.opacity)
        return item

    @staticmethod
    def handle_transform(item: VItem, matrix: se.Matrix):
        mat = np.array([
            [matrix.a, matrix.c],
            [matrix.b, matrix.d]
        ])
        vec = np.array([matrix.e, matrix.f, 0.0])
        item.apply_matrix(mat)
        item.shift(vec)
        return item

    def path_to_item(self, path: se.Path) -> VItemFromSVGPath:
        return VItemFromSVGPath(path, **self.path_string_config)

    def line_to_item(self, line: se.Line) -> Line:
        return Line(
            start=_convert_point_to_3d(line.x1, line.y1),
            end=_convert_point_to_3d(line.x2, line.y2)
        )

    def rect_to_item(self, rect: se.Rect) -> Rectangle:
        if rect.rx == 0 or rect.ry == 0:
            item = Rectangle(
                width=rect.width,
                height=rect.height,
            )
        else:
            item = RoundedRectangle(
                width=rect.width,
                height=rect.height * rect.rx / rect.ry,
                corner_radius=rect.rx
            )
            item.set_height(rect.height, stretch=True)
        item.shift(_convert_point_to_3d(
            rect.x + rect.width / 2,
            rect.y + rect.height / 2
        ))
        return item

    def circle_to_item(self, circle: se.Circle) -> Circle:
        # svgelements supports `rx` & `ry` but `r`
        item = Circle(radius=circle.rx)
        item.shift(_convert_point_to_3d(
            circle.cx, circle.cy
        ))
        return item

    def ellipse_to_item(self, ellipse: se.Ellipse) -> Circle:
        item = Circle(radius=ellipse.rx)
        item.set_height(2 * ellipse.ry, stretch=True)
        item.shift(_convert_point_to_3d(
            ellipse.cx, ellipse.cy
        ))
        return item

    def polygon_to_item(self, polygon: se.Polygon) -> Polygon:
        points = [
            _convert_point_to_3d(*point)
            for point in polygon
        ]
        return Polygon(*points)

    def polyline_to_item(self, polyline: se.Polyline) -> Polyline:
        points = [
            _convert_point_to_3d(*point)
            for point in polyline
        ]
        return Polyline(*points)

    def text_to_item(self, text: se.Text):
        pass

    def move_into_position(self) -> None:
        if self.should_center:
            self.to_center()
        if self.height is not None:
            self.set_height(self.height)
        if self.width is not None:
            self.set_width(self.width)


class VItemFromSVGPath(VItem):
    def __init__(
        self,
        path_obj: se.Path,
        long_lines: bool = False,
        should_subdivide_sharp_curves: bool = False,
        should_remove_null_curves: bool = False,
        **kwargs
    ) -> None:
        # Get rid of arcs
        path_obj.approximate_arcs_with_quads()
        self.path_obj = path_obj
        self.long_lines = long_lines
        self.should_subdivide_sharp_curves = should_subdivide_sharp_curves
        self.should_remove_null_curves = should_remove_null_curves
        super().__init__(**kwargs)
        self.init_points()

    def init_points(self) -> None:
        # After a given svg_path has been converted into points, the result
        # will be saved to a file so that future calls for the same path
        # don't need to retrace the same computation.
        path_string = self.path_obj.d()
        hasher = hashlib.sha256(path_string.encode())
        path_hash = hasher.hexdigest()[:16]
        points_filepath = os.path.join(get_item_data_dir(), f"{path_hash}_points.npy")
        tris_filepath = os.path.join(get_item_data_dir(), f"{path_hash}_tris.npy")

        if os.path.exists(points_filepath) and os.path.exists(tris_filepath):
            self.set_points(np.load(points_filepath))
            self.triangulation = np.load(tris_filepath)
            self.needs_new_triangulation = False
        else:
            self.handle_commands()
            if self.should_subdivide_sharp_curves:
                # For a healthy triangulation later
                self.subdivide_sharp_curves()
            if self.should_remove_null_curves:
                # Get rid of any null curves
                self.set_points(self.get_points_without_null_curves())
            # Save to a file for future use
            np.save(points_filepath, self.get_points())
            np.save(tris_filepath, self.get_triangulation())

    def handle_commands(self) -> None:
        segment_class_to_func_map = {
            se.Move: (self.path_move_to, ("end",)),
            se.Close: (self.close_path, ()),
            se.Line: (self.add_line_to, ("end",)),
            se.QuadraticBezier: (self.add_conic_to, ("control", "end")),
            se.CubicBezier: (self.add_cubic_to, ("control1", "control2", "end"))
        }
        for segment in self.path_obj:
            segment_class = segment.__class__
            func, attr_names = segment_class_to_func_map[segment_class]
            points = [
                _convert_point_to_3d(*segment.__getattribute__(attr_name))
                for attr_name in attr_names
            ]
            func(*points)

        # Get rid of the side effect of trailing "Z M" commands.
        if self.has_new_path_started():
            self.resize_points(self.points_count() - 1)
