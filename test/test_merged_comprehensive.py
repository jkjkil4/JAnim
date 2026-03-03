"""
Comprehensive test for GPU-driven merged VItem rendering consistency.
Tests ALL existing Timeline/Scene classes to ensure rendering results
are identical between legacy and merged rendering paths.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
from janim.imports import *
from janim.utils.config import Config
from janim.cli import get_all_timelines_from_module

import janim.examples as examples
import test.examples.examples_of_animations as anim_examples
import test.examples.examples_of_bugs as bug_examples

# Small resolution for faster testing
WIDTH = 192 * 2
HEIGHT = 108 * 2
FPS = 5


def get_all_timelines_for_test() -> list[type[Timeline]]:
    """Collect all Timeline classes from example modules."""
    timelines: list[type[Timeline]] = []
    timelines += get_all_timelines_from_module(examples)
    timelines += get_all_timelines_from_module(anim_examples)
    timelines += get_all_timelines_from_module(bug_examples)
    return timelines


def compare_render(name: str, timeline_cls: type[Timeline], t: float = 0.5) -> tuple[bool, float, str]:
    """
    Compare rendering results between legacy and merged paths.

    Returns:
        (passed, max_diff, error_message)
    """
    base_cfg = dict(pixel_width=WIDTH, pixel_height=HEIGHT, fps=FPS)

    try:
        # Build with legacy rendering
        with Config(**base_cfg, gpu_driven_rendering=False):
            built_legacy = timeline_cls().build(quiet=True)
        img_legacy = np.array(built_legacy.capture(t))

        # Build with merged (GPU-driven) rendering
        with Config(**base_cfg, gpu_driven_rendering=True):
            built_merged = timeline_cls().build(quiet=True)
        img_merged = np.array(built_merged.capture(t))

        # Calculate difference
        diff = np.abs(img_legacy.astype(float) - img_merged.astype(float))
        max_diff = diff.max()
        mean_diff = diff.mean()

        passed = max_diff < 50  # Allow small differences (anti-aliasing, etc.)

        if not passed:
            error = f"max_diff={max_diff:.1f}, mean_diff={mean_diff:.4f}"
            # Save images for debugging
            error_dir = os.path.join(os.path.dirname(__file__), '__test_errors__')
            os.makedirs(error_dir, exist_ok=True)
            from PIL import Image
            Image.fromarray(img_legacy).save(os.path.join(error_dir, f'{name}_legacy.png'))
            Image.fromarray(img_merged).save(os.path.join(error_dir, f'{name}_merged.png'))
            return (False, max_diff, f"{error} (saved to {error_dir})")

        return (True, max_diff, "")

    except Exception as e:
        return (False, 255, f"Exception: {e}")


def run_all_tests():
    """Run consistency tests on all Timeline classes."""
    timelines = get_all_timelines_for_test()

    print(f"\n{'='*60}")
    print(f"GPU-driven Merged Rendering Consistency Test")
    print(f"Testing {len(timelines)} Timeline classes")
    print(f"{'='*60}\n")

    results = []
    failed = []

    for timeline_cls in timelines:
        name = timeline_cls.__name__
        print(f"Testing: {name}...", end=" ", flush=True)

        passed, max_diff, error = compare_render(name, timeline_cls)

        if passed:
            print(f"PASS (diff={max_diff:.1f})")
            results.append((name, True, max_diff))
        else:
            print(f"FAIL - {error}")
            results.append((name, False, max_diff))
            failed.append((name, error))

    # Summary
    print(f"\n{'='*60}")
    print("Summary:")
    print(f"{'='*60}")

    passed_count = sum(1 for _, p, _ in results if p)
    total_count = len(results)

    for name, passed, max_diff in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status} (max_diff={max_diff:.1f})")

    print(f"\n{passed_count}/{total_count} tests passed")

    if failed:
        print(f"\nFailed tests:")
        for name, error in failed:
            print(f"  - {name}: {error}")
        return False

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test rendering consistency")
    parser.add_argument("--filter", "-f", type=str, default=None,
                        help="Only test timelines matching this pattern")
    parser.add_argument("--list", "-l", action="store_true",
                        help="List all available timelines")
    args = parser.parse_args()

    timelines = get_all_timelines_for_test()

    if args.list:
        print("Available Timeline classes:")
        for tl in timelines:
            print(f"  {tl.__name__}")
        sys.exit(0)

    if args.filter:
        timelines = [tl for tl in timelines if args.filter.lower() in tl.__name__.lower()]
        if not timelines:
            print(f"No timelines match filter: {args.filter}")
            sys.exit(1)
        print(f"Filtered to {len(timelines)} timelines")

    # Run tests
    success = run_all_tests()
    sys.exit(0 if success else 1)
