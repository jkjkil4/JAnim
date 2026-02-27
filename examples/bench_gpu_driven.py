"""
GPU-driven rendering performance benchmark scenes.

Usage:
    # Compare legacy vs merged rendering:
    .venv/bin/python examples/bench_gpu_driven.py

    # Preview a specific scene:
    .venv/bin/python -m janim run examples/bench_gpu_driven.py BenchCircleGrid
"""

import time

from janim.imports import *


# ---------------------------------------------------------------------------
# Benchmark scenes — static (measure single-frame overhead)
# ---------------------------------------------------------------------------


class BenchCircleGrid(Timeline):
    """500 circles in a grid. Tests basic instanced draw overhead."""

    CONFIG = Config(fps=5)

    def construct(self):
        N = 500
        cols = 25
        items = []
        for i in range(N):
            c = Circle(radius=0.12, color=BLUE)
            row, col = divmod(i, cols)
            c.points.shift(
                RIGHT * (col - cols / 2) * 0.5 + UP * (row - N / cols / 2) * 0.5
            )
            items.append(c)
        Group(*items).show()
        self.forward(1)


class BenchFilledRects(Timeline):
    """300 filled rectangles with varying colors. Tests fill + stroke."""

    CONFIG = Config(fps=5)

    def construct(self):
        N = 300
        cols = 20
        items = []
        colors = [RED, GREEN, BLUE, YELLOW, PURPLE, ORANGE, TEAL, MAROON, GOLD]
        for i in range(N):
            r = Rect(0.4, 0.3, color=colors[i % len(colors)], fill_alpha=0.5)
            row, col = divmod(i, cols)
            r.points.shift(
                RIGHT * (col - cols / 2) * 0.6 + UP * (row - N / cols / 2) * 0.5
            )
            items.append(r)
        Group(*items).show()
        self.forward(1)


class BenchMixedShapes(Timeline):
    """200 mixed shapes: circles, rects, polygons. Tests heterogeneous batching."""

    CONFIG = Config(fps=5)

    def construct(self):
        items = []
        for i in range(70):
            c = Circle(radius=0.15, color=BLUE, fill_alpha=0.3)
            c.points.shift(RIGHT * (i % 10 - 5) * 0.8 + UP * 2)
            items.append(c)
        for i in range(70):
            r = Rect(0.3, 0.2, color=RED, fill_alpha=0.4)
            r.points.shift(RIGHT * (i % 10 - 5) * 0.8)
            items.append(r)
        for i in range(60):
            p = RegularPolygon(n=6, radius=0.15, color=GREEN, fill_alpha=0.3)
            p.points.shift(RIGHT * (i % 10 - 5) * 0.8 + DOWN * 2)
            items.append(p)
        Group(*items).show()
        self.forward(1)


class BenchStressTest(Timeline):
    """2000 tiny circles. Stress test for draw call reduction."""

    CONFIG = Config(fps=5)

    def construct(self):
        N = 2000
        rng = np.random.default_rng(42)
        items = []
        for i in range(N):
            c = Dot(radius=0.04, color=BLUE)
            x = rng.uniform(-6, 6)
            y = rng.uniform(-3.5, 3.5)
            c.points.shift(RIGHT * x + UP * y)
            items.append(c)
        Group(*items).show()
        self.forward(1)


# ---------------------------------------------------------------------------
# Benchmark scenes — animated (measure per-frame overhead)
# ---------------------------------------------------------------------------


class BenchAnimatedCircles(Timeline):
    """100 circles with color animation. Tests per-frame data re-upload."""

    CONFIG = Config(fps=30)

    def construct(self):
        N = 100
        cols = 10
        items = []
        for i in range(N):
            c = Circle(radius=0.25, color=BLUE, fill_alpha=0.3)
            row, col = divmod(i, cols)
            c.points.shift(
                RIGHT * (col - cols / 2) * 1.2 + UP * (row - N / cols / 2) * 1.2
            )
            items.append(c)
        g = Group(*items)
        g.show()
        self.forward(0.5)
        self.play(g(VItem).anim.color.set(RED), duration=2)
        self.play(g(VItem).anim.color.set(YELLOW), duration=2)
        self.forward(0.5)


class BenchAnimatedMovement(Timeline):
    """200 circles shifting position. Tests point data re-upload."""

    CONFIG = Config(fps=30)

    def construct(self):
        N = 200
        cols = 20
        items = []
        for i in range(N):
            c = Circle(radius=0.12, color=GREEN)
            row, col = divmod(i, cols)
            c.points.shift(
                RIGHT * (col - cols / 2) * 0.6 + UP * (row - N / cols / 2) * 0.6
            )
            items.append(c)
        g = Group(*items)
        g.show()
        self.forward(0.5)
        self.play(g.anim.points.shift(RIGHT * 2), duration=2)
        self.play(g.anim.points.shift(LEFT * 4), duration=2)
        self.play(g.anim.points.shift(RIGHT * 2), duration=2)
        self.forward(0.5)


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

ALL_BENCHMARKS = [
    ("CircleGrid (500)", BenchCircleGrid),
    ("FilledRects (300)", BenchFilledRects),
    ("MixedShapes (200)", BenchMixedShapes),
    ("StressTest (2000)", BenchStressTest),
    ("AnimatedCircles (100)", BenchAnimatedCircles),
    ("AnimatedMovement (200)", BenchAnimatedMovement),
]


def bench_capture(built, n_frames=20):
    """Capture n_frames and return total time."""
    fps = built.cfg.fps
    duration = built.duration
    times = np.linspace(0, min(duration, 5.0), n_frames, endpoint=False)

    start = time.perf_counter()
    for t in times:
        built.capture(t)
    elapsed = time.perf_counter() - start
    return elapsed


def main():
    print("GPU-driven rendering benchmark")
    print("=" * 65)
    print(f"{'Scene':<28} {'Legacy':>10} {'Merged':>10} {'Speedup':>10}")
    print("-" * 65)

    for name, cls in ALL_BENCHMARKS:
        with Config(pixel_width=384, pixel_height=216, fps=cls.CONFIG.fps or 5):
            built = cls().build(quiet=True)

        n_frames = 30

        # Warmup
        with Config(gpu_driven_rendering=False):
            built.capture(0.0)
        with Config(gpu_driven_rendering=True):
            built.capture(0.0)

        # Legacy
        with Config(gpu_driven_rendering=False):
            t_legacy = bench_capture(built, n_frames)

        # Merged
        with Config(gpu_driven_rendering=True):
            t_merged = bench_capture(built, n_frames)

        speedup = t_legacy / t_merged if t_merged > 0 else float("inf")
        print(f"{name:<28} {t_legacy:>8.3f}s {t_merged:>8.3f}s {speedup:>9.2f}x")

    print("=" * 65)


if __name__ == "__main__":
    main()
