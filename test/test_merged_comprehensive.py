"""
Comprehensive test for GPU-driven merged VItem rendering.
Tests various VItem features: stroke, fill, glow, multiple subpaths, etc.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
from janim.imports import *
from janim.utils.config import Config


class TestComplex(Timeline):
    CONFIG = Config(pixel_width=384, pixel_height=216, fps=5)

    def construct(self) -> None:
        # Circles with different colors
        c1 = Circle(radius=1, color=BLUE, fill_alpha=0.3)
        c1.points.shift(LEFT * 3)

        # Rectangle with stroke and fill
        r1 = Rect(2, 1.5, color=RED, fill_alpha=0.5)

        # Arc
        a1 = Arc(start_angle=0, end_angle=PI, radius=1.5, color=GREEN)
        a1.points.shift(RIGHT * 3)

        # Line
        l1 = Line(LEFT * 4 + DOWN * 2, RIGHT * 4 + DOWN * 2, color=YELLOW)

        Group(c1, r1, a1, l1).show()
        self.forward(1)


class TestManyItems(Timeline):
    CONFIG = Config(pixel_width=384, pixel_height=216, fps=5)

    def construct(self) -> None:
        # 50 circles in a grid
        items = []
        for i in range(10):
            for j in range(5):
                c = Circle(radius=0.2, color=BLUE)
                c.points.shift(RIGHT * (i - 4.5) * 1.2 + UP * (j - 2) * 1.2)
                items.append(c)
        Group(*items).show()
        self.forward(1)


def compare(name, timeline_cls):
    print(f"\n--- {name} ---")
    base_cfg = dict(pixel_width=384, pixel_height=216, fps=5)
    t = 0.5

    # Build separately so gpu_driven_rendering is frozen into each build
    with Config(**base_cfg, gpu_driven_rendering=False):
        built_legacy = timeline_cls().build(quiet=True)
    img_legacy = np.array(built_legacy.capture(t))

    with Config(**base_cfg, gpu_driven_rendering=True):
        built_merged = timeline_cls().build(quiet=True)
    img_merged = np.array(built_merged.capture(t))

    diff = np.abs(img_legacy.astype(float) - img_merged.astype(float))
    max_diff = diff.max()
    mean_diff = diff.mean()

    print(f"  Max diff: {max_diff}, Mean diff: {mean_diff:.4f}")
    if max_diff == 0:
        print(f"  PASS: Identical")
    elif max_diff < 5:
        print(f"  PASS: Nearly identical")
    else:
        print(f"  FAIL: Significant differences")
        from PIL import Image

        Image.fromarray(img_legacy).save(f"/tmp/janim_{name}_legacy.png")
        Image.fromarray(img_merged).save(f"/tmp/janim_{name}_merged.png")
        print(f"  Saved to /tmp/janim_{name}_*.png")

    return max_diff


if __name__ == "__main__":
    results = []
    for name, cls in [
        ("complex", TestComplex),
        ("many_items", TestManyItems),
    ]:
        results.append((name, compare(name, cls)))

    print("\n=== Summary ===")
    all_pass = True
    for name, max_diff in results:
        status = "PASS" if max_diff < 5 else "FAIL"
        if max_diff >= 5:
            all_pass = False
        print(f"  {name}: {status} (max_diff={max_diff})")

    print(f"\nOverall: {'ALL PASS' if all_pass else 'SOME FAILED'}")
