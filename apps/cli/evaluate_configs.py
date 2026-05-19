from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

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


def main() -> None:
    args = parse_args()
    console = Console()

    summary = evaluate_profiles(
        video_path=args.input,
        objective=args.objective,
        write_videos=args.write_videos,
    )

    table = Table(title=f"Motion Profile Evaluation - {args.objective}")

    table.add_column("Rank", justify="right")
    table.add_column("Profile")
    table.add_column("Score", justify="right")
    table.add_column("Motion Frames", justify="right")
    table.add_column("Events", justify="right")
    table.add_column("Avg ms", justify="right")
    table.add_column("Motion Ratio", justify="right")

    for index, item in enumerate(summary["evaluations"], start=1):
        table.add_row(
            str(index),
            item["profile"]["name"],
            str(item["score"]["final_score"]),
            str(item["metrics"]["motion_frames"]),
            str(item["metrics"]["motion_events"]),
            str(item["metrics"]["avg_processing_ms"]),
            str(item["score"]["motion_ratio"]),
        )

    console.print(table)

    console.print("\nBest profile:")
    console.print_json(
        json.dumps(
            {
                "name": summary["best_profile"]["profile"]["name"],
                "score": summary["best_profile"]["score"],
                "config": summary["best_profile"]["profile"]["config"],
            }
        )
    )

    console.print("\nSummary saved at:")
    console.print("outputs/reports/evaluation_summary.json")


if __name__ == "__main__":
    main()
