
from typing import Callable

import numpy as np

from janim.constants import ORIGIN, OUT, PI, TAU
from janim.items.three_d.types import SurfaceGeometry
from janim.typing import Vect
from janim.utils.space_ops import z_to_vector


class ParametricSurface(SurfaceGeometry):
    def __init__(
        self,
        uv_func: Callable[[float, float], Vect],
        u_range: tuple[float, float] = (0, 1),
        v_range: tuple[float, float] = (0, 1),
        **kwargs
    ):
        super().__init__(uv_func, u_range, v_range, **kwargs)


class Sphere(SurfaceGeometry):
    # TODO: docstring

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
        **kwargs
    ):
        center = np.array(center)

        def uv_func(u: float, v: float) -> np.ndarray:
            return radius * np.array(
                [np.cos(u) * np.sin(v), np.sin(u) * np.sin(v), -np.cos(v)]
            ) + center

        super().__init__(uv_func, u_range, v_range, **kwargs)


class Torus(SurfaceGeometry):
    # TODO: docstring

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
        **kwargs
    ):
        R = major_radius
        r = minor_radius

        def uv_func(u: float, v: float) -> np.ndarray:
            P = np.array([np.cos(u), np.sin(u), 0])
            return (R - r * np.cos(v)) * P - r * np.sin(v) * OUT

        super().__init__(uv_func, u_range, v_range, **kwargs)


class Cylinder(SurfaceGeometry):
    # TODO: docstring

    RESOLUTIONS = {
        'face': (24, 12),
        'smooth': (101, 11)
    }

    def __init__(
        self,
        radius: float = 1,
        height: float = 2,
        axis: Vect = OUT,
        # TODO: show_cap,
        u_range: tuple[float, float] = (0, TAU),
        v_range: tuple[float, float] = (-1 / 2, 1 / 2),
        **kwargs
    ):
        rotT = z_to_vector(axis).T

        def uv_func(u: float, v: float) -> np.ndarray:
            # v @ rotT == rot @ v.T
            return [radius * np.cos(u), radius * np.sin(u), v * height] @ rotT

        super().__init__(uv_func, u_range, v_range, **kwargs)


class Cone(SurfaceGeometry):
    # TODO: docstring

    RESOLUTIONS = {
        'face': (24, 12),
        'smooth': (101, 11)
    }

    def __init__(
        self,
        radius: float = 1,
        height: float = 1,
        axis: Vect = OUT,
        # TODO: show_cap,
        u_range: tuple[float, float] = (0, TAU),
        v_min: float = 0,
        **kwargs
    ):
        rotT = z_to_vector(axis).T
        theta = PI - np.arctan(radius / height)

        def uv_func(u: float, v: float) -> np.ndarray:
            phi = u
            r = v
            # v @ rotT == rot @ v.T
            return [
                r * np.sin(theta) * np.sin(phi),
                r * np.sin(theta) * np.cos(phi),
                r * np.cos(theta)
            ] @ rotT

        v_range = (v_min, np.sqrt(radius**2 + height**2))

        super().__init__(uv_func, u_range, v_range)
