from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from rich.console import Console
from rich.table import Table

from core.motion.optimizer import run_random_search


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run random search for motion detection configurations."
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to input video.",
    )

    parser.add_argument(
        "--methods",
        nargs="+",
        default=["frame_diff"],
        choices=["frame_diff", "mog2"],
        help="Motion detection methods to include in random search.",
    )

    parser.add_argument(
        "--objective",
        default="balanced",
        choices=["balanced", "low_cpu", "sensitive"],
        help="Optimization objective.",
    )

    parser.add_argument(
        "--iterations",
        type=int,
        default=30,
        help="Number of random configurations to evaluate.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible results.",
    )

    parser.add_argument(
        "--write-best-video",
        action="store_true",
        help="Generate annotated video for the best configuration.",
    )

    return parser.parse_args()


def render_results_table(console: Console, payload: dict) -> None:
    """
    Render top random search results in the terminal.
    """

    table = Table(title=f"Random Search Results - {payload['objective']}")

    table.add_column("Rank", justify="right")
    table.add_column("Method")
    table.add_column("Score", justify="right")
    table.add_column("Resolution", justify="right")
    table.add_column("FPS", justify="right")
    table.add_column("Threshold", justify="right")
    table.add_column("Blur", justify="right")
    table.add_column("Min Area", justify="right")
    table.add_column("Motion Frames", justify="right")
    table.add_column("Raw Events", justify="right")
    table.add_column("Events", justify="right")
    table.add_column("Avg ms", justify="right")

    top_results = payload["results"][:10]

    for rank, item in enumerate(top_results, start=1):
        config = item["config"]
        metrics = item["metrics"]
        score = item["score"]

        table.add_row(
            str(rank),
            str(config.get("method", "frame_diff")),
            str(score["final_score"]),
            str(config["resolution_width"]),
            str(config["fps_sample"]),
            str(config["motion_threshold"]),
            str(config["blur_kernel"]),
            str(config["min_contour_area"]),
            str(metrics["motion_frames"]),
            str(metrics.get("raw_motion_events", metrics["motion_events"])),
            str(metrics["motion_events"]),
            str(metrics["avg_processing_ms"]),
        )

    console.print(table)


def render_best_result(console: Console, payload: dict) -> None:
    """
    Render the best random search result.
    """

    best_result = payload["best_result"]

    console.print("\nBest random configuration:")
    console.print_json(
        json.dumps(
            {
                "score": best_result["score"],
                "metrics": best_result["metrics"],
                "config": best_result["config"],
                "output": best_result.get("output"),
            }
        )
    )


def main() -> None:
    args = parse_args()
    console = Console()

    payload = run_random_search(
        video_path=args.input,
        objective=args.objective,
        iterations=args.iterations,
        seed=args.seed,
        methods=args.methods,
        write_best_video=args.write_best_video,
    )

    render_results_table(
        console=console,
        payload=payload,
    )

    render_best_result(
        console=console,
        payload=payload,
    )

    output_files = payload["output_files"]

    console.print("\nFiles saved:")
    console.print(f"JSON: {output_files['summary_json']}")
    console.print(f"CSV:  {output_files['ranking_csv']}")

    if output_files["best_video"]:
        console.print(f"Video: {output_files['best_video']}")


if __name__ == "__main__":
    main()
