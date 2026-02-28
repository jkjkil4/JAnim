"""
Detailed scaling benchmark: GPU-driven vs legacy rendering.

Tests how rendering time scales with item count across different scenarios.

Usage:
    .venv/bin/python examples/bench_scaling.py
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
from janim.imports import *
from janim.utils.config import Config


# ---------------------------------------------------------------------------
# Dynamic scene factories — create Timeline classes with parameterized N
# ---------------------------------------------------------------------------


def make_circle_scene(n: int):
    """N circles in a grid, static."""

    class _Scene(Timeline):
        CONFIG = Config(fps=5)

        def construct(self_):
            cols = max(int(n**0.5), 1)
            items = []
            for i in range(n):
                c = Circle(radius=0.1, color=BLUE)
                row, col = divmod(i, cols)
                c.points.shift(
                    RIGHT * (col - cols / 2) * 0.4 + UP * (row - n / cols / 2) * 0.4
                )
                items.append(c)
            Group(*items).show()
            self_.forward(1)

    _Scene.__name__ = f"Circles_{n}"
    return _Scene


def make_rect_filled_scene(n: int):
    """N filled rectangles, static."""

    class _Scene(Timeline):
        CONFIG = Config(fps=5)

        def construct(self_):
            cols = max(int(n**0.5), 1)
            colors = [RED, GREEN, BLUE, YELLOW, PURPLE, ORANGE]
            items = []
            for i in range(n):
                r = Rect(0.3, 0.2, color=colors[i % len(colors)], fill_alpha=0.5)
                row, col = divmod(i, cols)
                r.points.shift(
                    RIGHT * (col - cols / 2) * 0.5 + UP * (row - n / cols / 2) * 0.4
                )
                items.append(r)
            Group(*items).show()
            self_.forward(1)

    _Scene.__name__ = f"FilledRects_{n}"
    return _Scene


def make_dot_scene(n: int):
    """N dots (simplest VItem), static."""

    class _Scene(Timeline):
        CONFIG = Config(fps=5)

        def construct(self_):
            rng = np.random.default_rng(42)
            items = []
            for i in range(n):
                d = Dot(radius=0.03, color=BLUE)
                d.points.shift(RIGHT * rng.uniform(-6, 6) + UP * rng.uniform(-3.5, 3.5))
                items.append(d)
            Group(*items).show()
            self_.forward(1)

    _Scene.__name__ = f"Dots_{n}"
    return _Scene


def make_mixed_scene(n: int):
    """N items: 1/3 circles, 1/3 rects, 1/3 hexagons."""

    class _Scene(Timeline):
        CONFIG = Config(fps=5)

        def construct(self_):
            cols = max(int(n**0.5), 1)
            items = []
            for i in range(n):
                kind = i % 3
                if kind == 0:
                    item = Circle(radius=0.1, color=BLUE, fill_alpha=0.3)
                elif kind == 1:
                    item = Rect(0.2, 0.15, color=RED, fill_alpha=0.4)
                else:
                    item = RegularPolygon(n=6, radius=0.1, color=GREEN, fill_alpha=0.3)
                row, col = divmod(i, cols)
                item.points.shift(
                    RIGHT * (col - cols / 2) * 0.4 + UP * (row - n / cols / 2) * 0.4
                )
                items.append(item)
            Group(*items).show()
            self_.forward(1)

    _Scene.__name__ = f"Mixed_{n}"
    return _Scene


def make_animated_color_scene(n: int):
    """N circles with color animation."""

    class _Scene(Timeline):
        CONFIG = Config(fps=30)

        def construct(self_):
            cols = max(int(n**0.5), 1)
            items = []
            for i in range(n):
                c = Circle(radius=0.15, color=BLUE, fill_alpha=0.3)
                row, col = divmod(i, cols)
                c.points.shift(
                    RIGHT * (col - cols / 2) * 0.8 + UP * (row - n / cols / 2) * 0.8
                )
                items.append(c)
            g = Group(*items)
            g.show()
            self_.forward(0.2)
            self_.play(g(VItem).anim.color.set(RED), duration=1)
            self_.forward(0.2)

    _Scene.__name__ = f"AnimColor_{n}"
    return _Scene


def make_animated_move_scene(n: int):
    """N circles with position animation."""

    class _Scene(Timeline):
        CONFIG = Config(fps=30)

        def construct(self_):
            cols = max(int(n**0.5), 1)
            items = []
            for i in range(n):
                c = Circle(radius=0.1, color=GREEN)
                row, col = divmod(i, cols)
                c.points.shift(
                    RIGHT * (col - cols / 2) * 0.5 + UP * (row - n / cols / 2) * 0.5
                )
                items.append(c)
            g = Group(*items)
            g.show()
            self_.forward(0.2)
            self_.play(g.anim.points.shift(RIGHT * 2), duration=1)
            self_.forward(0.2)

    _Scene.__name__ = f"AnimMove_{n}"
    return _Scene


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

N_FRAMES = 30
BASE_CFG = dict(pixel_width=1920, pixel_height=1080)


def bench_one(cls, n_frames=N_FRAMES):
    """Build, warmup, and time n_frames captures. Returns (build_time, render_time)."""
    fps = cls.CONFIG.fps or 5
    cfg = dict(**BASE_CFG, fps=fps, gpu_driven_rendering=cls._gpu_driven)

    t0 = time.perf_counter()
    with Config(**cfg):
        built = cls().build(quiet=True)
    build_time = time.perf_counter() - t0

    # warmup
    built.capture(0.0)

    duration = built.duration
    times = np.linspace(0, min(duration, 5.0), n_frames, endpoint=False)

    t0 = time.perf_counter()
    for t in times:
        built.capture(t)
    render_time = time.perf_counter() - t0

    return build_time, render_time


def run_scaling_test(label, factory, counts):
    """Run a scaling test for a given scene factory across item counts."""
    print(f"\n{'=' * 78}")
    print(f"  {label}")
    print(f"{'=' * 78}")
    print(
        f"  {'N':>6}  {'Legacy':>10} {'Merged':>10} {'Speedup':>8}  "
        f"{'Legacy/item':>12} {'Merged/item':>12}"
    )
    print(f"  {'-' * 72}")

    results = []
    for n in counts:
        cls = factory(n)

        # Legacy
        cls._gpu_driven = False
        _, t_legacy = bench_one(cls)

        # Merged
        cls._gpu_driven = True
        _, t_merged = bench_one(cls)

        speedup = t_legacy / t_merged if t_merged > 0 else float("inf")
        per_item_legacy = t_legacy / n * 1000  # ms per item
        per_item_merged = t_merged / n * 1000

        print(
            f"  {n:>6}  {t_legacy:>8.3f}s  {t_merged:>8.3f}s  {speedup:>7.2f}x"
            f"  {per_item_legacy:>10.3f}ms  {per_item_merged:>10.3f}ms"
        )
        results.append((n, t_legacy, t_merged, speedup))

    return results


def main():
    print("GPU-driven rendering — detailed scaling benchmark")
    print(
        f"Frames per test: {N_FRAMES}, Resolution: {BASE_CFG['pixel_width']}x{BASE_CFG['pixel_height']}"
    )

    all_results = {}

    counts = [10, 50, 100, 200, 500, 1000, 2000, 5000]

    all_results["circles"] = run_scaling_test(
        "Static Circles (stroke only)", make_circle_scene, counts
    )
    all_results["filled_rects"] = run_scaling_test(
        "Static Filled Rects (stroke + fill)", make_rect_filled_scene, counts
    )
    all_results["dots"] = run_scaling_test(
        "Static Dots (simplest VItem)", make_dot_scene, counts
    )
    all_results["mixed"] = run_scaling_test(
        "Static Mixed (circle/rect/hexagon)", make_mixed_scene, counts
    )
    all_results["anim_color"] = run_scaling_test(
        "Animated Color Change", make_animated_color_scene, counts
    )
    all_results["anim_move"] = run_scaling_test(
        "Animated Position Shift", make_animated_move_scene, counts
    )

    # --- Summary ---
    print(f"\n{'=' * 78}")
    print("  Summary: speedup at each scale")
    print(f"{'=' * 78}")
    print(f"  {'N':>6}", end="")
    for label in all_results:
        print(f"  {label:>14}", end="")
    print()
    print(f"  {'-' * (6 + 16 * len(all_results))}")

    # Collect all unique N values
    all_ns = sorted(set(n for results in all_results.values() for n, *_ in results))
    for n in all_ns:
        print(f"  {n:>6}", end="")
        for label, results in all_results.items():
            match = [r for r in results if r[0] == n]
            if match:
                print(f"  {match[0][3]:>13.2f}x", end="")
            else:
                print(f"  {'—':>14}", end="")
        print()

    print()


if __name__ == "__main__":
    main()
