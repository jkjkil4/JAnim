"""
Per-function cProfile profiling for legacy vs merged rendering paths.

Runs cProfile on the rendering loop for both paths and outputs structured
tables sorted by self time, plus a comparison summary.

Usage:
    python examples/bench_profile.py path/to/file.py MySceneClass
    python examples/bench_profile.py path/to/file.py MySceneClass --frames 60
    python examples/bench_profile.py path/to/file.py MySceneClass --top 30
    python examples/bench_profile.py path/to/file.py MySceneClass -o output
"""

import argparse
import cProfile
import importlib.util
import os
import pstats
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
from janim.utils.config import Config


BASE_CFG = dict(pixel_width=1920, pixel_height=1080)


def load_class(file_path: str, class_name: str):
    """Dynamically import a class from a Python source file."""
    abs_path = os.path.abspath(file_path)
    if not os.path.isfile(abs_path):
        print(f"Error: file not found: {abs_path}", file=sys.stderr)
        sys.exit(1)

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
        print(
            f"Error: class '{class_name}' not found in {file_path}",
            file=sys.stderr,
        )
        sys.exit(1)
    return cls


def _shorten_func(filename: str, lineno: int, func_name: str) -> str:
    """Format a pstats key into a readable short name."""
    base = os.path.basename(filename)
    # Strip .py extension
    if base.endswith(".py"):
        base = base[:-3]
    return f"{base}:{func_name}"


def profile_path(cls, *, gpu_driven: bool, n_frames: int):
    """Build scene, warmup, profile n_frames captures. Returns (Stats, total_time)."""
    fps = getattr(cls, "CONFIG", None)
    fps = fps.fps if fps else 30
    fps = fps or 30

    cfg = dict(**BASE_CFG, fps=fps, gpu_driven_rendering=gpu_driven)

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
    return pr, stats, total_time


def print_table(label: str, stats: pstats.Stats, total_time: float,
                n_frames: int, top_n: int):
    """Print a formatted top-N function table."""
    ms_per_frame = total_time / n_frames * 1000 if n_frames else 0

    print(f"\n{'=' * 72}")
    print(f"  {label} — Total: {total_time:.3f}s ({n_frames} frames, {ms_per_frame:.1f}ms/frame)")
    print(f"{'=' * 72}")
    print(f"  {'#':>3}  {'Function':<42} {'Self':>8} {'Calls':>7} {'Per-call':>10}")
    print(f"  {'-' * 68}")

    # stats.stats: dict[(filename, lineno, func_name)] -> (cc, nc, tt, ct, callers)
    # tt = total self time for this function
    entries = []
    for key, (cc, nc, tt, ct, callers) in stats.stats.items():
        entries.append((tt, nc, key))
    entries.sort(reverse=True)

    for rank, (tt, nc, key) in enumerate(entries[:top_n], 1):
        name = _shorten_func(*key)
        per_call_ms = tt / nc * 1000 if nc else 0
        print(
            f"  {rank:>3}  {name:<42} {tt:>7.3f}s {nc:>7} {per_call_ms:>8.2f}ms"
        )


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

    # --- Legacy path ---
    print("\n>>> Building & profiling legacy path ...")
    pr_legacy, stats_legacy, t_legacy = profile_path(
        cls, gpu_driven=False, n_frames=args.frames
    )
    print_table("Legacy path", stats_legacy, t_legacy, args.frames, args.top)

    # --- Merged path ---
    print("\n>>> Building & profiling merged path ...")
    pr_merged, stats_merged, t_merged = profile_path(
        cls, gpu_driven=True, n_frames=args.frames
    )
    print_table("Merged path", stats_merged, t_merged, args.frames, args.top)

    # --- Comparison ---
    speedup = t_legacy / t_merged if t_merged > 0 else float("inf")
    print(f"\n{'=' * 72}")
    print(f"  Comparison")
    print(f"{'=' * 72}")
    print(f"  Legacy: {t_legacy:.3f}s | Merged: {t_merged:.3f}s | Speedup: {speedup:.2f}x")
    print()

    # --- Optional .prof export ---
    if args.output:
        path_legacy = f"{args.output}_legacy.prof"
        path_merged = f"{args.output}_merged.prof"
        pr_legacy.dump_stats(path_legacy)
        pr_merged.dump_stats(path_merged)
        print(f"Exported: {path_legacy}")
        print(f"Exported: {path_merged}")
        print("  (open with: python -m snakeviz <file>.prof)")
        print()


if __name__ == "__main__":
    main()
