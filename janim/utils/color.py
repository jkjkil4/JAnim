from __future__ import annotations
from typing import Iterable

from colour import Color
import numpy as np

from janim.constants import WHITE
from janim.utils.bezier import interpolate

def color_to_rgb(color):
    if isinstance(color, str):
        return hex_to_rgb(color)
    if isinstance(color, Color):
        return np.array(color.get_rgb())
    raise Exception("Invalid color type")

def rgb_to_color(rgb):
    try:
        return Color(rgb=rgb)
    except ValueError:
        return Color(WHITE)

def rgb_to_hex(rgba: Iterable[float]) -> str:
    return '#' + ''.join(
        hex(int_x // 16)[2] + hex(int_x % 16)[2]
        for x in rgba
        for int_x in [int(255 * x)]
    )

def hex_to_rgb(hex_code: str) -> np.ndarray:
    hex_part = hex_code[1:]
    if len(hex_part) == 3:
        hex_part = ''.join([2 * c for c in hex_part])
    return np.array([
        int(hex_part[i:i+2], 16) / 255
        for i in range(0, 6, 2)
    ])

def color_gradient(reference_colors, length_of_output):
    if length_of_output == 0:
        return reference_colors[0]
    rgbs = list(map(color_to_rgb, reference_colors))
    alphas = np.linspace(0, (len(rgbs) - 1), length_of_output)
    floors = alphas.astype('int')
    alphas_mod1 = alphas % 1
    # End edge case
    alphas_mod1[-1] = 1
    floors[-1] = len(rgbs) - 2
    return [
        rgb_to_color(interpolate(rgbs[i], rgbs[i + 1], alpha))
        for i, alpha in zip(floors, alphas_mod1)
    ]
