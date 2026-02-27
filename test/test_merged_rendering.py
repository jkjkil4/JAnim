"""
Quick test for GPU-driven merged VItem rendering.
Renders a simple scene with multiple VItems and compares output
between legacy and merged rendering paths.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
from janim.imports import *
from janim.utils.config import Config


class TestMergedRendering(Timeline):
    CONFIG = Config(
        pixel_width=384,
        pixel_height=216,
        fps=5,
    )

    def construct(self) -> None:
        # Create several VItems
        circles = Group(
            *[
                Circle(radius=0.5, color=BLUE)
                .points.shift(RIGHT * (i - 2) * 1.5 + UP * (j - 1) * 1.5)
                .r
                for i in range(5)
                for j in range(3)
            ]
        )
        circles.show()
        self.forward(1)

        rect = Rect(2, 1, color=RED, fill_alpha=0.5)
        rect.show()
        self.forward(1)


def main():
    print("Building scene...")
    with Config(pixel_width=384, pixel_height=216, fps=5):
        built = TestMergedRendering().build(quiet=True)

    # Capture with legacy rendering
    print("Capturing with legacy rendering...")
    with Config(gpu_driven_rendering=False):
        img_legacy = np.array(built.capture(0.5))

    # Capture with merged rendering
    print("Capturing with GPU-driven rendering...")
    with Config(gpu_driven_rendering=True):
        img_merged = np.array(built.capture(0.5))

    # Compare
    diff = np.abs(img_legacy.astype(float) - img_merged.astype(float))
    max_diff = diff.max()
    mean_diff = diff.mean()

    print(f"Max pixel difference: {max_diff}")
    print(f"Mean pixel difference: {mean_diff:.4f}")

    if max_diff == 0:
        print("PASS: Identical output!")
    elif max_diff < 5:
        print("PASS: Nearly identical (rounding differences)")
    else:
        print(f"WARN: Significant differences detected (max={max_diff})")

    # Save images for visual inspection
    from PIL import Image

    Image.fromarray(img_legacy).save("/tmp/janim_legacy.png")
    Image.fromarray(img_merged).save("/tmp/janim_merged.png")
    print("Saved /tmp/janim_legacy.png and /tmp/janim_merged.png")


if __name__ == "__main__":
    main()
