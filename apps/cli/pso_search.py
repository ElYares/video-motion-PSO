from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from rich.console import Console
from rich.table import Table

from core.motion.pso_optimizer import run_pso_search


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run PSO search for motion detection configurations."
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
        help="Optimization objective.",
    )

    parser.add_argument(
        "--particles",
        type=int,
        default=10,
        help="Number of particles in the swarm.",
    )

    parser.add_argument(
        "--iterations",
        type=int,
        default=8,
        help="Number of PSO iterations.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible results.",
    )

    parser.add_argument(
        "--inertia-weight",
        type=float,
        default=0.65,
        help="PSO inertia weight.",
    )

    parser.add_argument(
        "--cognitive-weight",
        type=float,
        default=1.5,
        help="PSO cognitive weight.",
    )

    parser.add_argument(
        "--social-weight",
        type=float,
        default=1.5,
        help="PSO social weight.",
    )

    parser.add_argument(
        "--write-best-video",
        action="store_true",
        help="Generate annotated video for the best PSO configuration.",
    )

    return parser.parse_args()


def render_history_table(console: Console, payload: dict) -> None:
    table = Table(title=f"PSO History - {payload['objective']}")

    table.add_column("Iteration", justify="right")
    table.add_column("Best Score", justify="right")
    table.add_column("Average Score", justify="right")
    table.add_column("Particles", justify="right")

    for item in payload["history"]:
        table.add_row(
            str(item["iteration"]),
            str(item["best_score"]),
            str(item["average_score"]),
            str(item["evaluated_particles"]),
        )

    console.print(table)


def render_results_table(console: Console, payload: dict) -> None:
    table = Table(title=f"Top PSO Results - {payload['objective']}")

    table.add_column("Rank", justify="right")
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

    for rank, item in enumerate(payload["results"][:10], start=1):
        config = item["config"]
        metrics = item["metrics"]
        score = item["score"]

        table.add_row(
            str(rank),
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
    best_result = payload["best_result"]

    console.print("\nBest PSO configuration:")
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

    payload = run_pso_search(
        video_path=args.input,
        objective=args.objective,
        particles_count=args.particles,
        iterations=args.iterations,
        seed=args.seed,
        inertia_weight=args.inertia_weight,
        cognitive_weight=args.cognitive_weight,
        social_weight=args.social_weight,
        write_best_video=args.write_best_video,
    )

    render_history_table(
        console=console,
        payload=payload,
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
