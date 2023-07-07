from __future__ import annotations
from typing import Iterable

import numpy as np

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
