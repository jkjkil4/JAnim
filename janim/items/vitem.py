from __future__ import annotations
from typing import Iterable, Optional
import numpy as np

from janim.constants import *
from janim.items.item import Item
from janim.utils.iterables import resize_with_interpolation, resize_array
from janim.shaders.render import VItemRenderer
from janim.utils.math_functions import get_norm, get_unit_normal

class VItem(Item):
    tolerance_for_point_equality = 1e-8

    def __init__(
        self,
        stroke_width: Optional[float | Iterable[float]] = 0.1,
        joint_type: JointType = JointType.Auto,
        fill_color: Optional[JAnimColor | Iterable[float]] = None,
        fill_opacity = 0.0,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.joint_type = joint_type
        # self.fill_color = fill_color # TODO: 实现 fill_color 和 fill_opacity
        # self.fill_opacity = fill_opacity

        # 轮廓线粗细
        self.stroke_width = np.array([0.1], dtype=np.float32)   # stroke_width 在所有操作中都会保持 dtype=np.float32，以便传入 shader
        self.needs_new_stroke_width = True

        # 法向量
        self.unit_normal = OUT
        self.needs_new_unit_normal = True

        # TODO: triangulation
        # TODO: 精细化边界框
        
        # 默认值
        self.set_stroke_width(stroke_width)

    def points_changed(self) -> None:
        super().points_changed()
        self.needs_new_stroke_width = True
        self.needs_new_unit_normal = True
    
    def create_renderer(self) -> VItemRenderer:
        return VItemRenderer()
    
    #region 点坐标数据
    
    def set_points(self, points: Iterable):
        super().set_points(resize_array(np.array(points), len(points) // 3 * 3))
        return self
    
    def get_start_points(self):
        return self.get_points()[::3]

    def get_handles(self):
        return self.get_points()[1::3]
    
    def get_end_points(self):
        return self.get_points()[2::3]

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
    
    def consider_points_equal(self, p0: np.ndarray, p1: np.ndarray) -> bool:
        return get_norm(p1 - p0) < self.tolerance_for_point_equality
    
    def get_joint_info(self) -> np.ndarray:
        if self.points_count() < 3:
            return np.zeros((0, 3), np.float32)
        
        points = self.get_points()
        cnt = len(points)
        handles = self.get_handles()

        ''' 对于第n段曲线：
        joint_info[0] = 前一个控制点
        joint_info[1] = [是否与前一个曲线转接, 是否与后一个曲线转接, 0.0]
        joint_info[2] = 后一个控制点
        '''
        joint_info = np.zeros(self.points.shape, np.float32)
        joint_info[3::3] = handles[:-1]     # 设置前一个控制点
        joint_info[2:-1:3] = handles[1:]    # 设置后一个控制点
        joint_info[1::3] = [
            [
                False if idx == 0 else self.consider_points_equal(points[idx - 1], points[idx]),
                False if idx == cnt - 3 else self.consider_points_equal(points[idx + 2], points[idx + 3]),
                0
            ]
            for idx in range(0, cnt, 3)
        ]
        
        return joint_info
    
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


