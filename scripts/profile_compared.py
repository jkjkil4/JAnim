"""
Per-function cProfile profiling for legacy vs merged rendering paths.

Runs cProfile on the rendering loop for both paths and outputs structured
tables sorted by self time, plus a comparison summary.

Usage:
    python scripts/profile_compared.py path/to/file.py MySceneClass
    python scripts/profile_compared.py path/to/file.py MySceneClass --frames 60
    python scripts/profile_compared.py path/to/file.py MySceneClass --top 30
    python scripts/profile_compared.py path/to/file.py MySceneClass -o output
"""

import argparse
import cProfile
import importlib.util
import os
import pstats
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
from janim.utils.config import Config

if TYPE_CHECKING:
    from janim.anims.timeline import Timeline


BASE_CFG = dict(pixel_width=1920, pixel_height=1080)


@dataclass
class ProfileResult:
    """Result of profiling a single rendering path."""
    profiler: cProfile.Profile
    stats: pstats.Stats
    total_time: float
    n_frames: int

    @property
    def ms_per_frame(self) -> float:
        return self.total_time / self.n_frames * 1000 if self.n_frames else 0


@dataclass
class ComparisonResult:
    """Result of comparing legacy vs merged rendering paths."""
    name: str
    legacy: ProfileResult
    merged: ProfileResult

    @property
    def speedup(self) -> float:
        return self.legacy.total_time / self.merged.total_time if self.merged.total_time > 0 else float("inf")

    @property
    def is_faster(self) -> bool:
        return self.speedup > 1.0


def load_class(file_path: str, class_name: str) -> type["Timeline"]:
    """Dynamically import a class from a Python source file."""
    abs_path = os.path.abspath(file_path)
    if not os.path.isfile(abs_path):
        raise FileNotFoundError(f"file not found: {abs_path}")

    mod_name = os.path.splitext(os.path.basename(abs_path))[0]
    spec = importlib.util.spec_from_file_location(mod_name, abs_path)
    mod = importlib.util.module_from_spec(spec)
    # Ensure the file's directory is on sys.path so its own imports work.
    mod_dir = os.path.dirname(abs_path)
    if mod_dir not in sys.path:
        sys.path.insert(0, mod_dir)
    # Register so inspect.getfile() can resolve classes from this module.
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)

    cls = getattr(mod, class_name, None)
    if cls is None:
        raise AttributeError(f"class '{class_name}' not found in {file_path}")
    return cls


def _shorten_func(filename: str, lineno: int, func_name: str) -> str:
    """Format a pstats key into a readable short name."""
    base = os.path.basename(filename)
    # Strip .py extension
    if base.endswith(".py"):
        base = base[:-3]
    return f"{base}:{func_name}"


def profile_path(cls: type["Timeline"], *, gpu_driven: bool, n_frames: int,
                 base_cfg: dict | None = None) -> ProfileResult:
    """
    Build scene, warmup, profile n_frames captures.

    Args:
        cls: Timeline subclass to profile
        gpu_driven: Whether to use GPU-driven merged rendering
        n_frames: Number of frames to profile
        base_cfg: Optional base config overrides

    Returns:
        ProfileResult with profiler, stats, and timing info
    """
    if base_cfg is None:
        base_cfg = BASE_CFG

    fps = getattr(cls, "CONFIG", None)
    fps = fps.fps if fps else 30
    fps = fps or 30

    cfg = dict(**base_cfg, fps=fps, gpu_driven_rendering=gpu_driven)

    with Config(**cfg):
        built = cls().build(quiet=True)

    # warmup
    built.capture(0.0)

    duration = built.duration
    times = np.linspace(0, min(duration, 5.0), n_frames, endpoint=False)

    pr = cProfile.Profile()
    pr.enable()
    for t in times:
        built.capture(t)
    pr.disable()

    stats = pstats.Stats(pr)
    total_time = stats.total_tt
    return ProfileResult(profiler=pr, stats=stats, total_time=total_time, n_frames=n_frames)


def compare_paths(cls: type["Timeline"], n_frames: int = 30,
                  base_cfg: dict | None = None) -> ComparisonResult:
    """
    Compare legacy vs merged rendering paths for a single scene.

    Args:
        cls: Timeline subclass to profile
        n_frames: Number of frames to profile for each path
        base_cfg: Optional base config overrides

    Returns:
        ComparisonResult with both profile results
    """
    legacy = profile_path(cls, gpu_driven=False, n_frames=n_frames, base_cfg=base_cfg)
    merged = profile_path(cls, gpu_driven=True, n_frames=n_frames, base_cfg=base_cfg)
    return ComparisonResult(name=cls.__name__, legacy=legacy, merged=merged)


def print_table(label: str, result: ProfileResult, top_n: int = 20) -> None:
    """Print a formatted top-N function table."""
    print(f"\n{'=' * 72}")
    print(f"  {label} — Total: {result.total_time:.3f}s ({result.n_frames} frames, {result.ms_per_frame:.1f}ms/frame)")
    print(f"{'=' * 72}")
    print(f"  {'#':>3}  {'Function':<42} {'Self':>8} {'Calls':>7} {'Per-call':>10}")
    print(f"  {'-' * 68}")

    # stats.stats: dict[(filename, lineno, func_name)] -> (cc, nc, tt, ct, callers)
    # tt = total self time for this function
    entries = []
    for key, (cc, nc, tt, ct, callers) in result.stats.stats.items():
        entries.append((tt, nc, key))
    entries.sort(reverse=True)

    for rank, (tt, nc, key) in enumerate(entries[:top_n], 1):
        name = _shorten_func(*key)
        per_call_ms = tt / nc * 1000 if nc else 0
        print(
            f"  {rank:>3}  {name:<42} {tt:>7.3f}s {nc:>7} {per_call_ms:>8.2f}ms"
        )


def print_comparison(result: ComparisonResult) -> None:
    """Print a comparison summary between legacy and merged paths."""
    print(f"\n{'=' * 72}")
    print(f"  Comparison: {result.name}")
    print(f"{'=' * 72}")
    print(f"  Legacy: {result.legacy.total_time:.3f}s ({result.legacy.ms_per_frame:.1f}ms/frame)")
    print(f"  Merged: {result.merged.total_time:.3f}s ({result.merged.ms_per_frame:.1f}ms/frame)")
    speedup_str = f"{result.speedup:.2f}x" if result.speedup != float("inf") else "inf"
    status = "FASTER" if result.is_faster else "SLOWER"
    print(f"  Speedup: {speedup_str} ({status})")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="cProfile-based rendering profiler for legacy vs merged paths."
    )
    parser.add_argument("file", help="Python source file containing the scene class")
    parser.add_argument("class_name", help="Timeline subclass name to profile")
    parser.add_argument(
        "--frames", type=int, default=30, help="Number of frames to profile (default: 30)"
    )
    parser.add_argument(
        "--top", type=int, default=20, help="Show top N functions (default: 20)"
    )
    parser.add_argument(
        "-o", "--output", default=None,
        help="Export .prof files with this prefix (e.g. -o result -> result_legacy.prof, result_merged.prof)"
    )
    args = parser.parse_args()

    cls = load_class(args.file, args.class_name)

    print(f"Profiling: {args.class_name} from {args.file}")
    print(f"Frames: {args.frames}, Resolution: {BASE_CFG['pixel_width']}x{BASE_CFG['pixel_height']}")

    # Run comparison
    result = compare_paths(cls, n_frames=args.frames)

    # Print detailed tables
    print_table("Legacy path", result.legacy, args.top)
    print_table("Merged path", result.merged, args.top)

    # Print comparison summary
    print_comparison(result)

    # Optional .prof export
    if args.output:
        path_legacy = f"{args.output}_legacy.prof"
        path_merged = f"{args.output}_merged.prof"
        result.legacy.profiler.dump_stats(path_legacy)
        result.merged.profiler.dump_stats(path_merged)
        print(f"Exported: {path_legacy}")
        print(f"Exported: {path_merged}")
        print("  (open with: python -m snakeviz <file>.prof)")
        print()


if __name__ == "__main__":
    main()
