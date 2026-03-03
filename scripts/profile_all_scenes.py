"""
Profile all example scenes and output a summary comparison.

This script runs the legacy vs merged rendering comparison across all
available Timeline classes and outputs a summary table.

Usage:
    python scripts/profile_all_scenes.py
    python scripts/profile_all_scenes.py --frames 20
    python scripts/profile_all_scenes.py --filter Transform
    python scripts/profile_all_scenes.py --quick  # Lower resolution for faster testing
"""

import argparse
import os
import sys
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from janim import examples as janim_examples
from janim.cli import get_all_timelines_from_module
from janim.utils.config import Config

# Import test examples
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "test"))
import examples.examples_of_animations as anim_examples
import examples.examples_of_bugs as bug_examples

from profile_compared import compare_paths, ComparisonResult

if TYPE_CHECKING:
    from janim.anims.timeline import Timeline


# Resolution presets
RESOLUTION_PRESETS = {
    "full": dict(pixel_width=1920, pixel_height=1080),
    "quick": dict(pixel_width=640, pixel_height=360),
    "tiny": dict(pixel_width=320, pixel_height=180),
}


@dataclass
class SummaryEntry:
    """Summary entry for a single scene comparison."""
    name: str
    legacy_time: float
    merged_time: float
    speedup: float
    error: str | None = None

    @property
    def is_faster(self) -> bool:
        return self.speedup > 1.0

    @property
    def ms_per_frame_legacy(self) -> float:
        return self.legacy_time  # Already per-frame in summary

    @property
    def ms_per_frame_merged(self) -> float:
        return self.merged_time


@dataclass
class SummaryReport:
    """Complete summary report for all scenes."""
    entries: list[SummaryEntry] = field(default_factory=list)
    total_legacy_time: float = 0.0
    total_merged_time: float = 0.0
    n_frames: int = 30

    @property
    def overall_speedup(self) -> float:
        return self.total_legacy_time / self.total_merged_time if self.total_merged_time > 0 else float("inf")

    @property
    def faster_count(self) -> int:
        return sum(1 for e in self.entries if e.is_faster and e.error is None)

    @property
    def slower_count(self) -> int:
        return sum(1 for e in self.entries if not e.is_faster and e.error is None)

    @property
    def error_count(self) -> int:
        return sum(1 for e in self.entries if e.error is not None)


def get_all_scenes() -> list[type["Timeline"]]:
    """Collect all Timeline classes from example modules."""
    timelines: list[type["Timeline"]] = []
    timelines += get_all_timelines_from_module(janim_examples)
    timelines += get_all_timelines_from_module(anim_examples)
    timelines += get_all_timelines_from_module(bug_examples)
    return timelines


def profile_scene(cls: type["Timeline"], n_frames: int, base_cfg: dict) -> SummaryEntry:
    """Profile a single scene and return a summary entry."""
    name = cls.__name__
    try:
        result = compare_paths(cls, n_frames=n_frames, base_cfg=base_cfg)
        return SummaryEntry(
            name=name,
            legacy_time=result.legacy.ms_per_frame,
            merged_time=result.merged.ms_per_frame,
            speedup=result.speedup,
        )
    except Exception as e:
        return SummaryEntry(
            name=name,
            legacy_time=0,
            merged_time=0,
            speedup=0,
            error=str(e),
        )


def print_summary_table(report: SummaryReport) -> None:
    """Print a formatted summary table."""
    print(f"\n{'=' * 80}")
    print(f"  GPU-Driven Merged Rendering Performance Summary")
    print(f"  Resolution: {RESOLUTION_PRESETS.get(args.resolution, args.resolution)} | Frames per scene: {report.n_frames}")
    print(f"{'=' * 80}")

    # Header
    print(f"  {'Scene':<40} {'Legacy':>10} {'Merged':>10} {'Speedup':>10} {'Status':<8}")
    print(f"  {'-' * 76}")

    # Sort by speedup (fastest first)
    sorted_entries = sorted(
        [e for e in report.entries if e.error is None],
        key=lambda e: e.speedup,
        reverse=True
    )
    error_entries = [e for e in report.entries if e.error is not None]

    # Print entries
    for entry in sorted_entries:
        status = "FASTER" if entry.is_faster else "SLOWER"
        speedup_str = f"{entry.speedup:.2f}x"
        print(
            f"  {entry.name:<40} {entry.legacy_time:>8.1f}ms {entry.merged_time:>8.1f}ms {speedup_str:>10} {status:<8}"
        )

    # Print errors
    if error_entries:
        print(f"\n  Errors:")
        for entry in error_entries:
            print(f"    {entry.name}: {entry.error[:60]}...")

    # Summary
    print(f"\n{'=' * 80}")
    print(f"  Summary")
    print(f"{'=' * 80}")
    print(f"  Total scenes tested: {len(report.entries)}")
    print(f"  Merged faster: {report.faster_count}")
    print(f"  Merged slower: {report.slower_count}")
    print(f"  Errors: {report.error_count}")
    print(f"\n  Overall speedup (total time): {report.overall_speedup:.2f}x")
    print(f"  Total legacy time: {report.total_legacy_time:.1f}ms")
    print(f"  Total merged time: {report.total_merged_time:.1f}ms")
    print()

    # Speedup distribution
    if sorted_entries:
        print(f"  Speedup distribution:")
        speedups = [e.speedup for e in sorted_entries]
        print(f"    Min: {min(speedups):.2f}x | Max: {max(speedups):.2f}x | Avg: {sum(speedups)/len(speedups):.2f}x")
        print()


def print_markdown_report(report: SummaryReport) -> None:
    """Print a markdown-formatted report."""
    print("\n## GPU-Driven Merged Rendering Performance Report\n")
    print(f"**Resolution:** {RESOLUTION_PRESETS.get(args.resolution, args.resolution)}  ")
    print(f"**Frames per scene:** {report.n_frames}  \n")

    print("| Scene | Legacy (ms/frame) | Merged (ms/frame) | Speedup | Status |")
    print("|-------|-------------------|-------------------|---------|--------|")

    sorted_entries = sorted(
        [e for e in report.entries if e.error is None],
        key=lambda e: e.speedup,
        reverse=True
    )

    for entry in sorted_entries:
        status = "✅ Faster" if entry.is_faster else "⚠️ Slower"
        print(f"| {entry.name} | {entry.legacy_time:.1f} | {entry.merged_time:.1f} | {entry.speedup:.2f}x | {status} |")

    print(f"\n**Summary:** {report.faster_count} faster, {report.slower_count} slower, overall {report.overall_speedup:.2f}x\n")


def main():
    global args
    parser = argparse.ArgumentParser(
        description="Profile all example scenes and output a performance summary."
    )
    parser.add_argument(
        "--frames", type=int, default=20,
        help="Number of frames to profile per scene (default: 20)"
    )
    parser.add_argument(
        "--resolution", choices=list(RESOLUTION_PRESETS.keys()), default="quick",
        help="Resolution preset: full (1920x1080), quick (640x360), tiny (320x180) (default: quick)"
    )
    parser.add_argument(
        "--filter", type=str, default=None,
        help="Only profile scenes matching this pattern"
    )
    parser.add_argument(
        "--markdown", action="store_true",
        help="Output in markdown format"
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List all available scenes without profiling"
    )
    args = parser.parse_args()

    # Get all scenes
    scenes = get_all_scenes()

    if args.list:
        print(f"Available scenes ({len(scenes)}):")
        for cls in scenes:
            print(f"  {cls.__name__}")
        return

    # Filter scenes
    if args.filter:
        scenes = [cls for cls in scenes if args.filter.lower() in cls.__name__.lower()]
        if not scenes:
            print(f"No scenes match filter: {args.filter}")
            return
        print(f"Filtered to {len(scenes)} scenes")

    # Get resolution config
    base_cfg = RESOLUTION_PRESETS.get(args.resolution, RESOLUTION_PRESETS["quick"])

    print(f"\nProfiling {len(scenes)} scenes...")
    print(f"Resolution: {base_cfg['pixel_width']}x{base_cfg['pixel_height']}, Frames: {args.frames}")
    print()

    # Profile all scenes
    report = SummaryReport(n_frames=args.frames)
    start_time = time.time()

    for i, cls in enumerate(scenes, 1):
        name = cls.__name__
        print(f"[{i}/{len(scenes)}] Profiling: {name}...", end=" ", flush=True)
        entry = profile_scene(cls, args.frames, base_cfg)
        report.entries.append(entry)
        report.total_legacy_time += entry.legacy_time
        report.total_merged_time += entry.merged_time

        if entry.error:
            print(f"ERROR ({entry.error[:40]}...)")
        else:
            status = "FASTER" if entry.is_faster else "SLOWER"
            print(f"{status} ({entry.speedup:.2f}x)")

    elapsed = time.time() - start_time
    print(f"\nTotal profiling time: {elapsed:.1f}s")

    # Output report
    if args.markdown:
        print_markdown_report(report)
    else:
        print_summary_table(report)


if __name__ == "__main__":
    main()
