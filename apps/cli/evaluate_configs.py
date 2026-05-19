from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from rich.console import Console
from rich.table import Table

from core.motion.evaluator import evaluate_profiles


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate multiple motion detection profiles."
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to input video.",
    )

    parser.add_argument(
        "--objective",
        default="balanced",
        choices=["balanced", "low_cpu", "sensitive"],
        help="Evaluation objective.",
    )

    parser.add_argument(
        "--write-videos",
        action="store_true",
        help="Generate annotated videos for each profile.",
    )

    return parser.parse_args()


def render_results_table(console: Console, summary: dict, objective: str) -> None:
    """
    Render a ranking table in the terminal.
    """

    table = Table(title=f"Motion Profile Evaluation - {objective}")

    table.add_column("Rank", justify="right")
    table.add_column("Profile")
    table.add_column("Score", justify="right")
    table.add_column("Motion Frames", justify="right")
    table.add_column("Raw Events", justify="right")
    table.add_column("Events", justify="right")
    table.add_column("Avg ms", justify="right")
    table.add_column("Motion Ratio", justify="right")

    for index, item in enumerate(summary["evaluations"], start=1):
        metrics = item["metrics"]
        score = item["score"]

        table.add_row(
            str(index),
            item["profile"]["name"],
            str(score["final_score"]),
            str(metrics["motion_frames"]),
            str(metrics.get("raw_motion_events", metrics["motion_events"])),
            str(metrics["motion_events"]),
            str(metrics["avg_processing_ms"]),
            str(score["motion_ratio"]),
        )

    console.print(table)


def render_best_profile(console: Console, summary: dict) -> None:
    """
    Render the best profile details as JSON.
    """

    best_profile = summary["best_profile"]

    console.print("\nBest profile:")
    console.print_json(
        json.dumps(
            {
                "name": best_profile["profile"]["name"],
                "score": best_profile["score"],
                "metrics": best_profile["metrics"],
                "config": best_profile["profile"]["config"],
            }
        )
    )


def main() -> None:
    args = parse_args()
    console = Console()

    summary = evaluate_profiles(
        video_path=args.input,
        objective=args.objective,
        write_videos=args.write_videos,
    )

    render_results_table(
        console=console,
        summary=summary,
        objective=args.objective,
    )

    render_best_profile(
        console=console,
        summary=summary,
    )

    output_files = summary["output_files"]

    console.print("\nFiles saved:")
    console.print(f"JSON: {output_files['summary_json']}")
    console.print(f"CSV:  {output_files['ranking_csv']}")


if __name__ == "__main__":
    main()
