from __future__ import annotations
from typing import Iterable, Optional, Sequence, Callable
from janim.typing import Self
import numpy as np
import math

from janim.constants import *
from janim.items.item import Item, NonParentGroup
from janim.utils.iterables import resize_with_interpolation, resize_array
from janim.utils.space_ops import (
    get_norm, get_unit_normal,
    z_to_vector, cross2d,
    earclip_triangulation,
    angle_between_vectors
)
from janim.utils.bezier import (
    bezier, interpolate, 
    integer_interpolate, inverse_interpolate,
    get_smooth_quadratic_bezier_handle_points,
    get_smooth_cubic_bezier_handle_points,
    get_quadratic_approximation_of_cubic,
    partial_quadratic_bezier_points
)
from janim.utils.simple_functions import clip
from janim.utils.functions import safe_call_same
from janim.logger import log

DEFAULT_STROKE_WIDTH = 0.04

class VItem(Item):
    tolerance_for_point_equality = 1e-8

    def __init__(
        self,
        stroke_width: Optional[float | Iterable[float]] = DEFAULT_STROKE_WIDTH,
        stroke_behind_fill: bool = False,
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

        # 轮廓线数据
        self.stroke_width = np.array([DEFAULT_STROKE_WIDTH], dtype=np.float32)   # stroke_width 在所有操作中都会保持 dtype=np.float32，以便传入 shader
        self.stroke_behind_fill = stroke_behind_fill
        self.needs_new_stroke_width = True

        # 填充色数据
        self.fill_rgbas = np.array([1, 1, 1, 1], dtype=np.float32).reshape((1, 4))  # fill_rgbas 在所有操作中都会保持 dtype=np.float32，以便传入 shader
        self.needs_new_fill_rgbas = True

        self.fill_rgbas_visible = True
        self.needs_new_fill_rgbas_visible = True

        # triangulation
        self.needs_new_triangulation = True

        self.npdata_to_copy_and_interpolate.update((
            ('stroke_width', 'get_stroke_width', 'set_self_stroke_width'), 
            ('fill_rgbas', 'get_fill_rgbas', 'set_fill_rgbas')
        ))
        
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
        self.needs_new_fill_rgbas_visible = True
        self.renderer.needs_update = True
    
    def stroke_width_changed(self) -> None:
        self.renderer.needs_update = True

    #endregion

    def create_renderer(self):
        from janim.gl.render import VItemRenderer
        return VItemRenderer()
    
    def __mul__(self, times: int) -> VGroup:
        assert(isinstance(times, int))
        return VGroup(
            *(self.copy() for _ in range(times))
        )
    
    #region 点坐标数据
    
    #region 简单判断
    
    def curves_count(self) -> int:
        return self.points_count() // 3
    
    def consider_points_equals(self, p0: np.ndarray, p1: np.ndarray) -> bool:
        return get_norm(p1 - p0) < self.tolerance_for_point_equality
    
    #endregion
    
    #region ::3 操作

    def set_anchors_and_handles(
        self,
        anchors1: np.ndarray,
        handles: np.ndarray,
        anchors2: np.ndarray
    ) -> Self:
        assert(len(anchors1) == len(handles) == len(anchors2))
        new_points = np.zeros((3 * len(anchors1), 3))
        arrays = [anchors1, handles, anchors2]
        for index, array in enumerate(arrays):
            new_points[index::3] = array
        self.set_points(new_points)
        return self
    
    def get_start_points(self) -> np.ndarray:
        return self.get_points()[::3]

    def get_handles(self) -> np.ndarray:
        return self.get_points()[1::3]
    
    def get_end_points(self) -> np.ndarray:
        return self.get_points()[2::3]
    
    #endregion
        
    #region 链式创建路径操作

    def has_new_path_started(self) -> bool:
        return self.points_count() % 3 == 1
    
    def path_move_to(self, point: np.ndarray) -> Self:
        if self.has_new_path_started():
            self.points[-1] = point
            self.points_changed()
        else:
            self.append_points([point])
        
        return self
    
    def add_line_to(self, point: np.ndarray) -> Self:
        end = self.get_points()[-1]
        alphas = np.linspace(0, 1, 3)
        points = [
            interpolate(end, point, a)
            for a in alphas
        ]
        if self.has_new_path_started():
            self.append_points(points[1:])
        else:
            self.append_points(points)
        
        return self
    
    def add_conic_to(self, handle: np.ndarray, point: np.ndarray) -> Self:
        end = self.get_points()[-1]
        if self.consider_points_equals(end, handle):
            handle = (end + point) / 2
        
        if self.has_new_path_started():
            self.append_points([handle, point])
        else:
            self.append_points([end, handle, point])

        return self
    
    #endregion
    
    #region _as_corners 操作

    def add_points_as_corners(self, points: Iterable[np.ndarray]) -> Self:
        for point in points:
            self.add_line_to(point)
        return self

    def set_points_as_corners(self, points: Iterable[np.ndarray]) -> Self:
        points = np.array(points)
        self.set_anchors_and_handles(*[
            interpolate(points[:-1], points[1:], a)
            for a in np.linspace(0, 1, 3)
        ])
        return self
    
    #endregion
    
    #region subpaths

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
    
    def close_path(self) -> Self:
        if not self.is_closed():
            self.add_line_to(self.get_subpaths()[-1][0])
        return self

    def is_closed(self) -> bool:
        return self.consider_points_equals(
            self.get_points()[0], self.get_points()[-1]
        )
    
    #endregion
    
    #region pfp

    def get_nth_curve_points(self, n: int) -> np.ndarray:
        assert(n < self.curves_count())
        nppc = 3
        return self.get_points()[nppc * n:nppc * (n + 1)]

    def get_nth_curve_function(self, n: int) -> Callable[[float], np.ndarray]:
        return bezier(self.get_nth_curve_points(n))

    def quick_point_from_proportion(self, alpha: float) -> np.ndarray:
        # Assumes all curves have the same length, so is inaccurate
        num_curves = self.curves_count()
        n, residue = integer_interpolate(0, num_curves, alpha)
        curve_func = self.get_nth_curve_function(n)
        return curve_func(residue)

    def point_from_proportion(self, alpha: float) -> np.ndarray:
        if alpha <= 0:
            return self.get_start()
        elif alpha >= 1:
            return self.get_end()

        partials = [0]
        for tup in self.get_bezier_tuples():
            # Approximate length with straight line from start to end
            arclen = get_norm(tup[0] - tup[-1])
            partials.append(partials[-1] + arclen)
        full = partials[-1]
        if full == 0:
            return self.get_start()
        # First index where the partial lenth is more alpha times the full length
        i = next(
            (i for i, x in enumerate(partials) if x >= full * alpha),
            len(partials)  # Default
        )
        residue = inverse_interpolate(partials[i - 1] / full, partials[i] / full, alpha)
        return self.get_nth_curve_function(i - 1)(residue)

    #endregion

    #region 计算法向量

    def get_area_vector(self) -> np.ndarray:
        # Returns a vector whose length is the area bound by
        # the polygon formed by the anchor points, pointing
        # in a direction perpendicular to the polygon according
        # to the right hand rule.
        if not self.has_points():
            return np.zeros(3)

        points = self.get_points()
        p0 = points[0::3]
        p1 = points[2::3]

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
    
    #endregion
    
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
            joint_info[offset + 1:end:3, 0] = np.all(
                np.isclose(
                    np.roll(subpath[2::3], 1, axis=0),
                    subpath[::3]
                ), 
                axis=1
            )
            joint_info[offset + 1:end:3, 1] = np.all(
                np.isclose(
                    subpath[2::3],
                    np.roll(subpath[::3], -1, axis=0)
                ),
                axis=1
            )
            joint_info[offset + 2:end:3] = np.roll(handles, -1, axis=0)

            offset = end
        
        return joint_info
    
    #endregion

    #region 颜色数据

    def set_color(
        self,
        color: Optional[JAnimColor | Iterable[JAnimColor]] = None,
        opacity: Optional[float | Iterable[float]] = None,
        recurse: bool = True,
    ) -> Self:
        self.set_stroke(color, opacity, recurse=recurse)
        self.set_fill(color, opacity, recurse=recurse)
        return self
    
    def is_transparent(self) -> bool:
        data = self.get_fill_rgbas()[:, 3]
        return super().is_transparent() \
            or np.any((0 < data) & (data < 1))

    #region 轮廓线数据

    def set_stroke(
        self, 
        color: Optional[JAnimColor | Iterable[JAnimColor]] = None, 
        opacity: Optional[float | Iterable[float]] = None,
        width: Optional[float | Iterable[float]] = None,
        background: Optional[bool] = None,
        recurse: bool = True,
    ) -> Self:
        if color is not None or opacity is not None:
            self.set_points_color(color, opacity, recurse)
        if width is not None:
            self.set_stroke_width(width, recurse)
        if background is not None:
            self.set_stroke_behind_fill(background)
        return self

    def set_stroke_width(
        self, 
        stroke_width: float | Iterable[float], 
        recurse: bool = True
    ) -> Self:
        if not isinstance(stroke_width, Iterable):
            stroke_width = [stroke_width]

        if recurse:
            for item in self.get_family()[1:]:
                safe_call_same(
                    item, None, 
                    stroke_width=stroke_width, 
                    recurse=False
                )

        stroke_width = resize_with_interpolation(
            np.array(stroke_width, dtype=np.float32), 
            max(1, self.points_count())
        )
        if len(stroke_width) == len(self.stroke_width):
            self.stroke_width[:] = stroke_width
        else:
            self.stroke_width = stroke_width
        self.stroke_width_changed()
        return self

    def set_self_stroke_width(self, stroke_width) -> Self:
        return self.set_stroke_width(stroke_width, recurse=False)
    
    def get_stroke_width(self) -> np.ndarray:
        if self.needs_new_stroke_width:
            self.set_self_stroke_width(self.stroke_width)
            self.needs_new_stroke_width = False
        return self.stroke_width
    
    def set_stroke_behind_fill(self, flag: bool = True) -> Self:
        self.stroke_behind_fill = flag
        return self
    
    def set_opacity(self, opacity: float) -> Self:
        super().set_opacity(opacity)
        self.set_fill(opacity=opacity)
        return self
    
    def compute_rgbas_visible(self) -> bool:
        return super().compute_rgbas_visible() \
            and np.any(self.get_stroke_width() > 0)

    #endregion

    #region 填充色数据

    def set_fill_rgbas(self, rgbas: Iterable[Iterable[float, float, float, float]]) -> Self:
        rgbas = np.array(rgbas, dtype=np.float32)
        assert(rgbas.ndim == 2)
        assert(rgbas.shape[1] == 4)

        rgbas = resize_array(rgbas, max(1, self.points_count()))
        if len(rgbas) == len(self.fill_rgbas):
            self.fill_rgbas[:] = rgbas
        else:
            self.fill_rgbas = rgbas
        self.fill_rgbas_changed()
        return self
    
    def set_fill(
        self, 
        color: Optional[JAnimColor | Iterable[JAnimColor]] = None, 
        opacity: Optional[float | Iterable[float]] = None,
        recurse: bool = True,
    ) -> Self:
        color, opacity = self.format_color(color), self.format_opacity(opacity)

        if recurse:
            for item in self.get_family()[1:]:
                safe_call_same(
                    item, None, 
                    color=color, 
                    opacity=opacity, 
                    recurse=False
                )
        
        if color is None:
            color = self.get_fill_rgbas()[:, :3]
        if opacity is None:
            opacity = self.get_fill_rgbas()[:, 3]

        color = resize_array(np.array(color), max(1, self.points_count()))
        opacity = resize_array(np.array(opacity), max(1, self.points_count()))
        self.set_fill_rgbas(
            np.hstack((
                color, 
                opacity.reshape((len(opacity), 1))
            ))
        )

        return self

    def get_fill_rgbas(self) -> np.ndarray:
        if self.needs_new_fill_rgbas:
            self.set_fill_rgbas(self.fill_rgbas)
            self.needs_new_fill_rgbas = False
        return self.fill_rgbas
    
    def get_fill_rgbas_visible(self) -> bool:
        if self.needs_new_fill_rgbas_visible:
            self.fill_rgbas_visible = self.compute_fill_rgbas_visible()
            self.needs_new_fill_rgbas_visible = False
        return self.fill_rgbas_visible

    def compute_fill_rgbas_visible(self) -> bool:
        return np.any(self.get_fill_rgbas()[:, 3] > 0)

    #endregion

    #endregion

    #region 三角剖分

    def compute_triangulation(self, normal_vector: np.ndarray | None = None) -> np.ndarray:
        # Figure out how to triangulate the interior to know
        # how to send the points as to the vertex shader.
        # First triangles come directly from the points
        if normal_vector is None:
            normal_vector = self.get_unit_normal()

        points = self.get_points()

        if len(points) <= 1:
            return np.zeros(0, dtype='uint')

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
        scale_stroke_width: bool = False, 
        **kwargs
    ) -> Self:
        if scale_stroke_width and not isinstance(scale_factor, Iterable):
            self.set_stroke_width(self.get_stroke_width() * scale_factor)
        super().scale(scale_factor, **kwargs)
        return self
    
    def change_anchor_mode(self, mode: AnchorMode) -> Self:
        assert(isinstance(mode, AnchorMode))
        nppc = 3
        for subitem in self.family_members_with_points():
            if isinstance(subitem, VItem):
                subpaths = subitem.get_subpaths()
                subitem.clear_points()
                for subpath in subpaths:
                    anchors = np.vstack([subpath[::nppc], subpath[-1:]])
                    new_subpath = np.array(subpath)
                    if mode == AnchorMode.ApproxSmooth:
                        new_subpath[1::nppc] = get_smooth_quadratic_bezier_handle_points(anchors)
                    elif mode == AnchorMode.TrueSmooth:
                        h1, h2 = get_smooth_cubic_bezier_handle_points(anchors)
                        new_subpath = get_quadratic_approximation_of_cubic(anchors[:-1], h1, h2, anchors[1:])
                    elif mode == AnchorMode.Jagged:
                        new_subpath[1::nppc] = 0.5 * (anchors[:-1] + anchors[1:])
                    subitem.append_points(new_subpath)
        return self

    def make_smooth(self) -> Self:
        """
        This will double the number of points in the mobject,
        so should not be called repeatedly.  It also means
        transforming between states before and after calling
        this might have strange artifacts
        """
        self.change_anchor_mode(AnchorMode.TrueSmooth)
        return self

    def make_approximately_smooth(self) -> Self:
        """
        Unlike make_smooth, this will not change the number of
        points, but it also does not result in a perfectly smooth
        curve.  It's most useful when the points have been
        sampled at a not-too-low rate from a continuous function,
        as in the case of ParametricCurve
        """
        self.change_anchor_mode(AnchorMode.ApproxSmooth)
        return self

    def make_jagged(self) -> Self:
        self.change_anchor_mode(AnchorMode.Jagged)
        return self
    
    # Information about the curve
    @staticmethod
    def get_bezier_tuples_from_points(points: Sequence[np.ndarray]):
        nppc = 3
        remainder = len(points) % nppc
        points = points[:len(points) - remainder]
        return (
            points[i:i + nppc]
            for i in range(0, len(points), nppc)
        )

    def get_bezier_tuples(self):
        return self.get_bezier_tuples_from_points(self.get_points())

    @staticmethod
    def insert_n_curves_to_point_list(n: int, points: np.ndarray):
        nppc = 3
        if len(points) == 1:
            return np.repeat(points, nppc * n, 0)

        bezier_groups = list(VItem.get_bezier_tuples_from_points(points))
        norms = np.array([
            get_norm(bg[nppc - 1] - bg[0])
            for bg in bezier_groups
        ])
        total_norm = sum(norms)
        # Calculate insertions per curve (ipc)
        if total_norm < 1e-6:
            ipc = [n] + [0] * (len(bezier_groups) - 1)
        else:
            ipc = np.round(n * norms / sum(norms)).astype(int)

        diff = n - sum(ipc)
        for x in range(diff):
            ipc[np.argmin(ipc)] += 1
        for x in range(-diff):
            ipc[np.argmax(ipc)] -= 1

        new_points = []
        for group, n_inserts in zip(bezier_groups, ipc):
            # What was once a single quadratic curve defined
            # by "group" will now be broken into n_inserts + 1
            # smaller quadratic curves
            alphas = np.linspace(0, 1, n_inserts + 2)
            for a1, a2 in zip(alphas, alphas[1:]):
                new_points += partial_quadratic_bezier_points(group, a1, a2)
        return np.vstack(new_points)

    def insert_n_curves(self, n: int, recurse: bool = True) -> Self:
        if self.curves_count() > 0:
            new_points = self.insert_n_curves_to_point_list(n, self.get_points())
            # TODO: [L] this should happen in insert_n_curves_to_point_list
            if self.has_new_path_started():
                new_points = np.vstack([new_points, self.get_points()[-1]])
            self.set_points(new_points)

        if recurse:
            for item in self.get_family()[1:]:
                safe_call_same(
                    item, None, 
                    n=n, 
                    recurse=False
                )
        
        return self
    
    @staticmethod
    def subdivide_sharp_curves_from_points(
        points: np.ndarray,
        angle_threshold: float = 30 * DEGREES
    ) -> np.ndarray:
        new_points = []
        for tup in VItem.get_bezier_tuples_from_points(points):
            angle = angle_between_vectors(tup[1] - tup[0], tup[2] - tup[1])
            if angle > angle_threshold:
                n = int(np.ceil(angle / angle_threshold))
                alphas = np.linspace(0, 1, n + 1)
                new_points.extend([
                    partial_quadratic_bezier_points(tup, a1, a2)
                    for a1, a2 in zip(alphas, alphas[1:])
                ])
            else:
                new_points.append(tup)
        return np.vstack(new_points)

    def subdivide_sharp_curves(
        self,
        angle_threshold: float = 30 * DEGREES,
        recurse: bool = True
    ) -> Self:
        if self.curves_count() > 0:
            self.set_points(VItem.subdivide_sharp_curves_from_points(self.get_points(), angle_threshold))

        if recurse:
            for item in self.get_family()[1:]:
                safe_call_same(
                    item, None, 
                    angle_threshold=angle_threshold, 
                    recurse=False
                )

        return self
    
    def pointwise_become_partial(self, vitem: VItem, a: float, b: float):
        assert(isinstance(vitem, VItem))
        if a <= 0 and b >= 1:
            self.become(vitem)
            return self
        num_curves = vitem.curves_count()
        nppc = 3

        # Partial curve includes three portions:
        # - A middle section, which matches the curve exactly
        # - A start, which is some ending portion of an inner quadratic
        # - An end, which is the starting portion of a later inner quadratic

        lower_index, lower_residue = integer_interpolate(0, num_curves, a)
        upper_index, upper_residue = integer_interpolate(0, num_curves, b)
        i1 = nppc * lower_index
        i2 = nppc * (lower_index + 1)
        i3 = nppc * upper_index
        i4 = nppc * (upper_index + 1)

        vm_points = vitem.get_points()
        new_points = vm_points.copy()
        if num_curves == 0:
            new_points[:] = 0
            return self
        if lower_index == upper_index:
            tup = partial_quadratic_bezier_points(vm_points[i1:i2], lower_residue, upper_residue)
            new_points[:i1] = tup[0]
            new_points[i1:i4] = tup
            new_points[i4:] = tup[2]
            new_points[nppc:] = new_points[nppc - 1]
        else:
            low_tup = partial_quadratic_bezier_points(vm_points[i1:i2], lower_residue, 1)
            high_tup = partial_quadratic_bezier_points(vm_points[i3:i4], 0, upper_residue)
            new_points[0:i1] = low_tup[0]
            new_points[i1:i2] = low_tup
            # Keep new_points i2:i3 as they are
            new_points[i3:i4] = high_tup
            new_points[i4:] = high_tup[2]
        self.set_points(new_points)
        return self

    #endregion

    #region Alignment

    def align_points(self, vitem: VItem) -> Self:
        if self.points_count() == vitem.points_count():
            return

        for item in self, vitem:
            # If there are no points, add one to
            # where the "center" is
            if not item.has_points():
                item.path_move_to(item.get_center())
            # If there's only one point, turn it into
            # a null curve
            if item.has_new_path_started():
                item.add_line_to(item.get_points()[0])

        # Figure out what the subpaths are, and align
        subpaths1 = self.get_subpaths()
        subpaths2 = vitem.get_subpaths()
        n_subpaths = max(len(subpaths1), len(subpaths2))
        # Start building new ones
        new_subpaths1 = []
        new_subpaths2 = []

        nppc = 3

        def get_nth_subpath(path_list, n):
            if n >= len(path_list):
                # Create a null path at the very end
                return [path_list[-1][-1]] * nppc
            return path_list[n]

        for n in range(n_subpaths):
            sp1 = get_nth_subpath(subpaths1, n)
            sp2 = get_nth_subpath(subpaths2, n)
            diff1 = max(0, (len(sp2) - len(sp1)) // nppc)
            diff2 = max(0, (len(sp1) - len(sp2)) // nppc)
            sp1 = self.insert_n_curves_to_point_list(diff1, sp1)
            sp2 = self.insert_n_curves_to_point_list(diff2, sp2)
            new_subpaths1.append(sp1)
            new_subpaths2.append(sp2)
        self.set_points(np.vstack(new_subpaths1))
        vitem.set_points(np.vstack(new_subpaths2))
        return self

    #endregion

    def add_tip(
        self, 
        alpha: float = 1.0, 
        reverse: bool = False, 
        colorize: bool = True,
        angle: Optional[float] = None,
        fill_color: JAnimColor = None,
        color: JAnimColor = None,
        d_alpha: float = 1e-6,
        **tip_kwargs
    ):
        '''
        在 `alpha` 处创建一个箭头

        - 默认情况下，箭头与路径方向同向；若传入 `reverse=True` 则反向
        - 若传入 `colorize=True`（默认），则会使箭头的颜色与路径的颜色相同
        - 其余参数请参考 `ArrowTip`
        '''
        if alpha >= 1.0:
            pos = self.get_points()[-1]
            angle_vert = self.get_points()[-1] - self.get_points()[-2]
        elif alpha <= 0.0:
            pos = self.get_points()[0]
            angle_vert = self.get_points()[1] - self.get_points()[0]
        else:
            pos = self.pfp(alpha)
            angle_vert = self.pfp(clip(alpha + d_alpha, 0, 1)) - self.pfp(clip(alpha - d_alpha, 0, 1))

        if angle is None:
            angle = math.atan2(angle_vert[1], angle_vert[0])
        if reverse:
            angle += PI

        if colorize:
            if fill_color is None:
                fill_color = self.get_rgbas()[0][:3]
            if color is None:
                color = self.get_rgbas()[0][:3]

        from janim.items.geometry.arrow import ArrowTip
        tip = ArrowTip(angle=angle, fill_color=fill_color, color=color, **tip_kwargs).move_anchor_to(pos)
        self.add(tip)

        return tip

class VGroup(VItem):
    def __init__(self, *items: VItem, **kwargs) -> None:
        if not all(isinstance(item, VItem) for item in items):
            raise Exception('All subitems of VGroup must be VItem')
        super().__init__(**kwargs)
        self.add(*items)
    
    def __getitem__(self, value) -> VItem | NonParentVGroup:
        if isinstance(value, slice):
            return NonParentVGroup(*self.items[value])
        return self.items[value]

class NonParentVGroup(NonParentGroup, VGroup):
    pass

