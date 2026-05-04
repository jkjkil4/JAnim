from typing import Callable

import numpy as np

from janim.constants import ORIGIN, OUT, PI, TAU
from janim.items.three_d.types import SurfaceGeometry
from janim.typing import Vect
from janim.utils.space_ops import z_to_vector


class ParametricSurface(SurfaceGeometry):
    """
    参数曲面

    :param uv_func: 参数方程，输入 ``(u, v)``，输出对应的三维坐标
    :param u_range: ``u`` 变量的取值范围
    :param v_range: ``v`` 变量的取值范围

    示例：

    .. code-block:: python

        ParametricSurface(
            lambda u, v: [np.cos(u) * np.cos(v), np.cos(u) * np.sin(v), -u],
            u_range=[-PI, PI],
            v_range=[0, TAU],
            resolution=16,
        ).into('checker')
    """

    def __init__(
        self,
        uv_func: Callable[[float, float], Vect],
        u_range: tuple[float, float] = (0, 1),
        v_range: tuple[float, float] = (0, 1),
        **kwargs,
    ):
        super().__init__(uv_func, u_range, v_range, **kwargs)


class Sphere(SurfaceGeometry):
    """
    三维球体

    :param center: 球体中心
    :param radius: 球体半径
    :param u_range: ``u`` 变量的范围（即绕纬线的取值，从 ``0`` 到 ``TAU``）
    :param v_range: ``v`` 变量的范围（即沿经线的取值，最底端为 ``0``，最顶端为 ``PI``）


    示例：

    .. code-block:: python

        Sphere(radius=2).into('checker')
    """

    RESOLUTIONS = {
        'face': (24, 12),
        'smooth': (101, 51),
    }

    def __init__(
        self,
        center: Vect = ORIGIN,
        radius: float = 1,
        u_range: tuple[float, float] = (0, TAU),
        v_range: tuple[float, float] = (0, PI),
        **kwargs,
    ):
        center = np.array(center)

        def uv_func(u: float, v: float) -> np.ndarray:
            return (
                radius * np.array([np.cos(u) * np.sin(v), np.sin(u) * np.sin(v), -np.cos(v)])
                + center
            )

        super().__init__(uv_func, u_range, v_range, **kwargs)


class Torus(SurfaceGeometry):
    """
    三维圆环面

    :param major_radius: 主半径（圆环中心到管道中心的距离）
    :param minor_radius: 次半径（管道半径）
    :param u_range: ``u`` 变量的范围（沿圆环主方向）
    :param v_range: ``v`` 变量的范围（沿管道截面方向）


    示例：

    .. code-block:: python

        Torus(2.5, 0.6).into('checker')
    """

    RESOLUTIONS = {
        'face': 24,
        'smooth': 101,
    }

    def __init__(
        self,
        major_radius: float = 3,
        minor_radius: float = 1,
        u_range: tuple[float, float] = (0, TAU),
        v_range: tuple[float, float] = (0, TAU),
        **kwargs,
    ):
        R = major_radius
        r = minor_radius

        def uv_func(u: float, v: float) -> np.ndarray:
            P = np.array([np.cos(u), np.sin(u), 0])
            return (R - r * np.cos(v)) * P - r * np.sin(v) * OUT

        super().__init__(uv_func, u_range, v_range, **kwargs)


class Cylinder(SurfaceGeometry):
    """
    三维圆柱面

    :param radius: 圆柱半径
    :param height: 圆柱高度
    :param axis: 圆柱轴线方向向量（默认沿 ``OUT``）
    :param u_range: ``u`` 变量的范围（绕圆柱侧面的角度）
    :param v_range: ``v`` 变量的范围（沿轴线方向的归一化取值）


    示例：

    .. code-block:: python

        Cylinder(1, 3).into('checker')
    """

    RESOLUTIONS = {
        'face': (24, 12),
        'smooth': (101, 11),
    }

    def __init__(
        self,
        radius: float = 1,
        height: float = 2,
        axis: Vect = OUT,
        # TODO: show_cap,
        u_range: tuple[float, float] = (0, TAU),
        v_range: tuple[float, float] = (-1 / 2, 1 / 2),
        **kwargs,
    ):
        rotT = z_to_vector(axis).T

        def uv_func(u: float, v: float) -> np.ndarray:
            # v @ rotT == rot @ v.T
            return [radius * np.cos(u), radius * np.sin(u), v * height] @ rotT

        super().__init__(uv_func, u_range, v_range, **kwargs)


class Cone(SurfaceGeometry):
    """
    三维圆锥面

    :param radius: 圆锥底面半径
    :param height: 圆锥高度
    :param axis: 圆锥轴线方向向量（默认沿 ``OUT``）
    :param u_range: ``u`` 变量的范围（绕圆锥侧面的角度）
    :param v_min: ``v`` 变量的最小值（用于裁剪锥面，``0`` 表示从锥尖开始）


    示例：

    .. code-block:: python

        Cone(1, 2).into('checker')
    """

    RESOLUTIONS = {
        'face': (24, 12),
        'smooth': (101, 11),
    }

    def __init__(
        self,
        radius: float = 1,
        height: float = 1,
        axis: Vect = OUT,
        # TODO: show_cap,
        u_range: tuple[float, float] = (0, TAU),
        v_min: float = 0,
        **kwargs,
    ):
        rotT = z_to_vector(axis).T
        theta = PI - np.arctan(radius / height)

        v_max = np.sqrt(radius**2 + height**2)
        v_range = (v_min, v_max)

        def uv_func(u: float, v: float) -> np.ndarray:
            phi = u
            r = v_max - (v - v_min)  # 反转 v 的取值使得法线朝向正常
            # v @ rotT == rot @ v.T
            return [
                r * np.sin(theta) * np.cos(phi),
                r * np.sin(theta) * np.sin(phi),
                r * np.cos(theta),
            ] @ rotT

        super().__init__(uv_func, u_range, v_range, **kwargs)
