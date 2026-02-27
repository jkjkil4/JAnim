"""Profile the merged rendering path to find bottlenecks."""

import sys, os, time, cProfile, pstats, io

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from janim.imports import *
from janim.utils.config import Config

# Import a benchmark scene
from bench_gpu_driven import BenchCircleGrid, BenchStressTest


def profile_scene(name, cls, n_frames=10):
    print(f"\n=== Profiling {name} ===")
    with Config(pixel_width=384, pixel_height=216, fps=cls.CONFIG.fps or 5):
        built = cls().build(quiet=True)

    # Warmup
    with Config(gpu_driven_rendering=True):
        built.capture(0.0)

    # Profile
    pr = cProfile.Profile()
    with Config(gpu_driven_rendering=True):
        pr.enable()
        for _ in range(n_frames):
            built.capture(0.5)
        pr.disable()

    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps.print_stats(25)
    print(s.getvalue())


if __name__ == "__main__":
    profile_scene("CircleGrid (500)", BenchCircleGrid)
    profile_scene("StressTest (2000)", BenchStressTest, n_frames=3)
