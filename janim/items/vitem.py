from __future__ import annotations
from typing import Iterable, Optional, Sequence
import numpy as np

from janim.constants import *
from janim.items.item import Item
from janim.utils.iterables import resize_with_interpolation, resize_array
from janim.utils.space_ops import (
    get_norm, get_unit_normal,
    z_to_vector, cross2d,
    earclip_triangulation
)
from janim.utils.bezier import (
    interpolate, 
    get_smooth_quadratic_bezier_handle_points,
    get_smooth_cubic_bezier_handle_points,
    get_quadratic_approximation_of_cubic
)
from janim.utils.functions import safe_call

from janim.shaders.render import VItemRenderer

class VItem(Item):
    tolerance_for_point_equality = 1e-8

    def __init__(
        self,
        stroke_width: Optional[float | Iterable[float]] = 0.05,
        joint_type: JointType = JointType.Auto,
        fill_color: Optional[JAnimColor | Iterable[float]] = WHITE,
        fill_opacity = 0.0,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.joint_type = joint_type

        # 法向量
        self.unit_normal = OUT
        self.needs_new_unit_normal = True

        # 轮廓线粗细
        self.stroke_width = np.array([0.1], dtype=np.float32)   # stroke_width 在所有操作中都会保持 dtype=np.float32，以便传入 shader
        self.needs_new_stroke_width = True

        # 填充色数据
        self.fill_rgbas = np.array([1, 1, 1, 1], dtype=np.float32).reshape((1, 4))  # fill_rgbas 在所有操作中都会保持 dtype=np.float32，以便传入 shader
        self.needs_new_fill_rgbas = True

        # triangulation
        self.needs_new_triangulation = True

        
        # TODO: 精细化边界框
        
        # 默认值
        self.set_stroke_width(stroke_width)
        self.set_fill(fill_color, fill_opacity)

    #region 响应

    def points_changed(self) -> None:
        super().points_changed()
        self.needs_new_unit_normal = True
        self.needs_new_stroke_width = True
        self.needs_new_fill_rgbas = True
        self.needs_new_triangulation = True
    
    def fill_rgbas_changed(self) -> None:
        self.renderer.needs_update = True

    #endregion
    
    def create_renderer(self) -> VItemRenderer:
        return VItemRenderer()
    
    #region 点坐标数据
    
    def set_points(self, points: Iterable):
        super().set_points(resize_array(np.array(points), len(points) // 3 * 3))
        return self
    
    def set_anchors_and_handles(
        self,
        anchors1: np.ndarray,
        handles: np.ndarray,
        anchors2: np.ndarray
    ):
        assert(len(anchors1) == len(handles) == len(anchors2))
        new_points = np.zeros((3 * len(anchors1), 3))
        arrays = [anchors1, handles, anchors2]
        for index, array in enumerate(arrays):
            new_points[index::3] = array
        self.set_points(new_points)
        return self
    
    def get_start_points(self):
        return self.get_points()[::3]

    def get_handles(self):
        return self.get_points()[1::3]
    
    def get_end_points(self):
        return self.get_points()[2::3]
    
    def has_new_path_started(self) -> bool:
        return self.points_count() % 3 == 1
    
    def add_line_to(self, point: np.ndarray):
        end = self.get_points()[-1]
        alphas = np.linspace(0, 1, 3)
        points = [
            interpolate(end, point, a)
            for a in alphas
        ]
        self.append_points(points)
        return self
    
    def add_points_as_corners(self, points: Iterable[np.ndarray]):
        for point in points:
            self.add_line_to(point)
        return points

    def set_points_as_corners(self, points: Iterable[np.ndarray]):
        points = np.array(points)
        self.set_anchors_and_handles(*[
            interpolate(points[:-1], points[1:], a)
            for a in np.linspace(0, 1, 3)
        ])
        return self
    
    def get_subpaths_from_points(
        self,
        points: Sequence[np.ndarray]
    ) -> list[Sequence[np.ndarray]]:
        nppc = 3
        diffs = points[nppc - 1:-1:nppc] - points[nppc::nppc]
        splits = (diffs * diffs).sum(1) > self.tolerance_for_point_equality
        split_indices = np.arange(nppc, len(points), nppc, dtype=int)[splits]

        # split_indices = filter(
        #     lambda n: not self.consider_points_equals(points[n - 1], points[n]),
        #     range(nppc, len(points), nppc)
        # )
        split_indices = [0, *split_indices, len(points)]
        return [
            points[i1:i2]
            for i1, i2 in zip(split_indices, split_indices[1:])
            if (i2 - i1) >= nppc
        ]

    def get_subpaths(self) -> list[Sequence[np.ndarray]]:
        return self.get_subpaths_from_points(self.get_points())
    
    def close_path(self):
        if not self.is_closed():
            self.add_line_to(self.get_subpaths()[-1][0])
        return self

    def is_closed(self) -> bool:
        return self.consider_points_equals(
            self.get_points()[0], self.get_points()[-1]
        )

    def get_area_vector(self) -> np.ndarray:
        # Returns a vector whose length is the area bound by
        # the polygon formed by the anchor points, pointing
        # in a direction perpendicular to the polygon according
        # to the right hand rule.
        if not self.has_points():
            return np.zeros(3)

        p0 = self.get_start_points()
        p1 = np.vstack([p0[1:], p0[0]])

        # Each term goes through all edges [(x0, y0, z0), (x1, y1, z1)]
        sums = p0 + p1
        diffs = p1 - p0
        return 0.5 * np.array([
            (sums[:, 1] * diffs[:, 2]).sum(),  # Add up (y0 + y1)*(z1 - z0)
            (sums[:, 2] * diffs[:, 0]).sum(),  # Add up (z0 + z1)*(x1 - x0)
            (sums[:, 0] * diffs[:, 1]).sum(),  # Add up (x0 + x1)*(y1 - y0)
        ])
    
    def get_unit_normal(self) -> np.ndarray:
        if not self.needs_new_unit_normal:
            return self.unit_normal
        
        self.needs_new_unit_normal = False
        
        if self.points_count() < 3:
            return OUT

        area_vect = self.get_area_vector()
        area = get_norm(area_vect)
        if area > 0:
            normal = area_vect / area
        else:
            points = self.get_points()
            normal = get_unit_normal(
                points[1] - points[0],
                points[2] - points[1],
            )
        self.unit_normal = normal
        return normal
    
    def consider_points_equals(self, p0: np.ndarray, p1: np.ndarray) -> bool:
        return get_norm(p1 - p0) < self.tolerance_for_point_equality
    
    def get_joint_info(self) -> np.ndarray:
        if self.points_count() < 3:
            return np.zeros((0, 3), np.float32)
        
        ''' 对于第n段曲线：
        joint_info[0] = 前一个控制点
        joint_info[1] = [是否与前一个曲线转接, 是否与后一个曲线转接, 0.0]
        joint_info[2] = 后一个控制点
        '''
        joint_info = np.zeros(self.points.shape, np.float32)

        offset = 0
        for subpath in self.get_subpaths():
            end = offset + len(subpath)
            handles = subpath[1::3]
            
            joint_info[offset:end:3] = np.roll(handles, 1, axis=0)
            joint_info[offset + 1:end:3] = [
                [
                    self.consider_points_equals(p_prev, p0),
                    self.consider_points_equals(p_next, p2),
                    0
                ]
                for p_prev, p0, p2, p_next in zip(
                    np.roll(subpath[2::3], 1, axis=0),
                    subpath[::3],
                    subpath[2::3],
                    np.roll(subpath[::3], -1, axis=0)
                )
            ]
            joint_info[offset + 2:end:3] = np.roll(handles, -1, axis=0)

            offset = end
        
        return joint_info
    
    #endregion

    #region 轮廓线数据

    def set_stroke_width(self, stroke_width: float | Iterable[float]):
        if not isinstance(stroke_width, Iterable):
            stroke_width = [stroke_width]
        stroke_width = resize_with_interpolation(np.array(stroke_width), max(1, self.points_count()))
        if len(stroke_width) == len(self.stroke_width):
            self.stroke_width[:] = stroke_width
        else:
            self.stroke_width = stroke_width.astype(np.float32)
        return self
    
    def get_stroke_width(self) -> np.ndarray:
        if self.needs_new_stroke_width:
            self.set_stroke_width(self.stroke_width)
            self.needs_new_stroke_width = False
        return self.stroke_width
    
    #endregion

    #region 填充色数据

    def set_fill_rgbas(self, rgbas: Iterable[Iterable[float, float, float, float]]):
        rgbas = resize_array(np.array(rgbas), max(1, self.points_count()))
        if len(rgbas) == len(self.fill_rgbas):
            self.fill_rgbas[:] = rgbas
        else:
            self.fill_rgbas = rgbas.astype(np.float32)
        self.fill_rgbas_changed()
        return self
    
    def set_fill(
        self, 
        color: JAnimColor | Iterable[JAnimColor], 
        opacity: float | Iterable[float] = 1,
        recurse: bool = True,
    ):
        color, opacity = self.format_color(color), self.format_opacity(opacity)

        if recurse:
            for item in self:
                safe_call(item, 'set_fill_color', None, color, opacity)

        color = resize_array(np.array(color), max(1, self.points_count()))
        opacity = resize_array(np.array(opacity), max(1, self.points_count()))
        self.set_fill_rgbas(
            np.hstack((
                color, 
                opacity.reshape((len(opacity), 1))
            ))
        )

        return self
    
    def set_fill_opacity(self, opacity: float | Iterable[float]):
        opacity = resize_array(np.array(self.format_opacity(opacity)), len(self.fill_rgbas))
        self.fill_rgbas[:, 3] = opacity
        self.fill_rgbas_changed()
        return self

    def get_fill_rgbas(self) -> np.ndarray:
        if self.needs_new_fill_rgbas:
            self.set_fill_rgbas(self.fill_rgbas)
            self.needs_new_fill_rgbas = False
        return self.fill_rgbas

    #endregion

    #region 三角剖分

    def compute_triangulation(self, normal_vector: np.ndarray | None = None) -> np.ndarray:
        # Figure out how to triangulate the interior to know
        # how to send the points as to the vertex shader.
        # First triangles come directly from the points
        if normal_vector is None:
            normal_vector = self.get_unit_normal()

        if not self.needs_new_triangulation:
            return self.triangulation

        points = self.get_points()

        if len(points) <= 1:
            self.triangulation = np.zeros(0, dtype='i4')
            self.needs_new_triangulation = False
            return self.triangulation

        if not np.isclose(normal_vector, OUT).all():
            # Rotate points such that unit normal vector is OUT
            points = np.dot(points, z_to_vector(normal_vector))
        indices = np.arange(len(points), dtype=int)

        b0s = points[0::3]
        b1s = points[1::3]
        b2s = points[2::3]
        v01s = b1s - b0s
        v12s = b2s - b1s

        crosses = cross2d(v01s, v12s)
        convexities = np.sign(crosses)

        atol = self.tolerance_for_point_equality
        end_of_loop = np.zeros(len(b0s), dtype=bool)
        end_of_loop[:-1] = (np.abs(b2s[:-1] - b0s[1:]) > atol).any(1)
        end_of_loop[-1] = True

        concave_parts = convexities < 0

        # These are the vertices to which we'll apply a polygon triangulation
        inner_vert_indices = np.hstack([
            indices[0::3],
            indices[1::3][concave_parts],
            indices[2::3][end_of_loop],
        ])
        inner_vert_indices.sort()
        rings = np.arange(1, len(inner_vert_indices) + 1)[inner_vert_indices % 3 == 2]

        # Triangulate
        inner_verts = points[inner_vert_indices]
        inner_tri_indices = inner_vert_indices[
            earclip_triangulation(inner_verts, rings)
        ]

        tri_indices = np.hstack([indices, inner_tri_indices])
        self.needs_new_triangulation = False
        return tri_indices.astype('uint')
    
    def get_triangulation(self) -> np.ndarray:
        if self.needs_new_triangulation:
            self.triangulation = self.compute_triangulation()
            self.needs_new_triangulation = False
        return self.triangulation

    #endregion

    #region 变换

    def scale(
        self, 
        scale_factor: float | Iterable, 
        scale_stroke_width: bool = True, 
        **kwargs
    ):
        if scale_stroke_width and not isinstance(scale_factor, Iterable):
            self.set_stroke_width(self.get_stroke_width() * scale_factor)
        super().scale(scale_factor, **kwargs)
        return self
    
    def change_anchor_mode(self, mode: str):
        assert(mode in ("jagged", "approx_smooth", "true_smooth"))
        nppc = 3
        for subitem in self.family_members_with_points():
            if isinstance(subitem, VItem):
                subpaths = subitem.get_subpaths()
                subitem.clear_points()
                for subpath in subpaths:
                    anchors = np.vstack([subpath[::nppc], subpath[-1:]])
                    new_subpath = np.array(subpath)
                    if mode == "approx_smooth":
                        new_subpath[1::nppc] = get_smooth_quadratic_bezier_handle_points(anchors)
                    elif mode == "true_smooth":
                        h1, h2 = get_smooth_cubic_bezier_handle_points(anchors)
                        new_subpath = get_quadratic_approximation_of_cubic(anchors[:-1], h1, h2, anchors[1:])
                    elif mode == "jagged":
                        new_subpath[1::nppc] = 0.5 * (anchors[:-1] + anchors[1:])
                    subitem.append_points(new_subpath)
        return self

    def make_smooth(self):
        """
        This will double the number of points in the mobject,
        so should not be called repeatedly.  It also means
        transforming between states before and after calling
        this might have strange artifacts
        """
        self.change_anchor_mode("true_smooth")
        return self

    def make_approximately_smooth(self):
        """
        Unlike make_smooth, this will not change the number of
        points, but it also does not result in a perfectly smooth
        curve.  It's most useful when the points have been
        sampled at a not-too-low rate from a continuous function,
        as in the case of ParametricCurve
        """
        self.change_anchor_mode("approx_smooth")
        return self

    def make_jagged(self):
        self.change_anchor_mode("jagged")
        return self

    #endregion

