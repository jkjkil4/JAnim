
import numpy as np
import svgelements as se

from janim.constants import ORIGIN, RIGHT
from janim.items.item import Group
from janim.items.vitem import VItem
from janim.logger import log
from janim.utils.bezier import PathBuilder
from janim.utils.config import Config

DEFAULT_SVGITEM_SCALE_FACTOR = 4.36
STROKE_WIDTH_CONVERSION = 0.01


def _convert_point_to_3d(x: float, y: float) -> np.ndarray:
    return np.array([x, y, 0])


def _convert_alpha_to_float(x: int | None) -> float:
    return None if x is None else x / 255


class SVGItem(Group[VItem]):
    svg_part_default_kwargs = dict(
        stroke_radius=1.0 * STROKE_WIDTH_CONVERSION / 2,
        stroke_color=None,
        stroke_alpha=0,
        fill_color=None,
        fill_alpha=0
    )

    def __init__(self, file_path: str, **kwargs):
        svg: se.SVG = se.SVG.parse(file_path)

        items = []
        for shape in svg.elements():
            if isinstance(shape, (se.Group, se.Use)):
                continue
            elif isinstance(shape, se.Path):
                items.append(self.convert_path_to_item(shape))
            elif type(shape) is se.SVGElement:
                continue
            else:
                log.warning(f'Unsupported element type: {type(shape)}')

        super().__init__(*items, **kwargs)

        # 这里的 4.36 是我手动试出来的
        self(VItem).points.scale(
            Config.get.pixel_to_frame_ratio * DEFAULT_SVGITEM_SCALE_FACTOR,
            about_point=ORIGIN
        ).flip(RIGHT)

    @staticmethod
    def convert_path_to_item(path: se.Path) -> VItem:
        builder = PathBuilder()
        segment_class_to_func_map = {
            se.Move: (builder.move_to, ('end',)),
            se.Close: (builder.close_path, ()),
            se.Line: (builder.line_to, ('end',)),
            se.QuadraticBezier: (builder.conic_to, ('control', 'end')),
            se.CubicBezier: (builder.cubic_to, ('control1', 'control2', 'end'))
        }
        for segment in path:
            segment_class = segment.__class__
            func, attr_names = segment_class_to_func_map[segment_class]
            points = [
                _convert_point_to_3d(*getattr(segment, attr_name))
                for attr_name in attr_names
            ]
            func(*points)

        vitem = VItem(**SVGItem.svg_part_default_kwargs)
        vitem.set_style(
            stroke_radius=path.stroke_width * STROKE_WIDTH_CONVERSION / 2,
            stroke_color=path.stroke.hex,
            stroke_alpha=_convert_alpha_to_float(path.stroke.alpha),
            fill_color=path.fill.hex,
            fill_alpha=_convert_alpha_to_float(path.fill.alpha)
        )
        vitem.points.set(builder.get())
        return vitem
