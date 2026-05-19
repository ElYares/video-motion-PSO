from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from rich.console import Console
from rich.table import Table

from core.motion.comparator import SUPPORTED_OBJECTIVES, compare_optimizers


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare manual profiles, random search and seeded PSO results."
    )

    parser.add_argument(
        "--reports-dir",
        default="outputs/reports",
        help="Directory where optimizer report JSON files are stored.",
    )

    parser.add_argument(
        "--objectives",
        nargs="+",
        default=SUPPORTED_OBJECTIVES,
        choices=SUPPORTED_OBJECTIVES,
        help="Objectives to compare.",
    )

    parser.add_argument(
        "--output-json",
        default="outputs/reports/optimizer_comparison.json",
        help="Output JSON comparison path.",
    )

    parser.add_argument(
        "--output-csv",
        default="outputs/reports/optimizer_comparison.csv",
        help="Output CSV comparison path.",
    )

    return parser.parse_args()


def render_comparison_table(console: Console, payload: dict) -> None:
    """
    Render the optimizer comparison table.
    """

    table = Table(title="Optimizer Comparison")

    table.add_column("Objective")
    table.add_column("Rank", justify="right")
    table.add_column("Method")
    table.add_column("Name")
    table.add_column("Score", justify="right")
    table.add_column("Motion Ratio", justify="right")
    table.add_column("Avg ms", justify="right")
    table.add_column("Resource", justify="right")
    table.add_column("Eff FPS", justify="right")
    table.add_column("Frame Ratio", justify="right")
    table.add_column("Resolution", justify="right")
    table.add_column("FPS", justify="right")
    table.add_column("Threshold", justify="right")

    comparison = payload["comparison"]

    for objective in payload["objectives"]:
        objective_result = comparison.get(objective, {})
        results = objective_result.get("results", [])

        for item in results:
            score = item["score"]
            metrics = item["metrics"]
            config = item["config"]

            table.add_row(
                objective,
                str(item["rank"]),
                item["method"],
                item["name"],
                str(score["final_score"]),
                str(score["motion_ratio"]),
                str(metrics["avg_processing_ms"]),
                str(score.get("resource_score", "")),
                str(score.get("effective_processed_fps", "")),
                str(score.get("processed_frame_ratio", "")),
                str(config["resolution_width"]),
                str(config["fps_sample"]),
                str(config["motion_threshold"]),
            )

    console.print(table)


def render_best_summary(console: Console, payload: dict) -> None:
    """
    Render compact best-method summary per objective.
    """

    summary_table = Table(title="Best Optimizer Per Objective")

    summary_table.add_column("Objective")
    summary_table.add_column("Best Method")
    summary_table.add_column("Name")
    summary_table.add_column("Score", justify="right")
    summary_table.add_column("Resource", justify="right")
    summary_table.add_column("Eff FPS", justify="right")
    summary_table.add_column("Config")

    comparison = payload["comparison"]

    for objective in payload["objectives"]:
        best = comparison[objective]["best"]

        if best is None:
            summary_table.add_row(
                objective,
                "N/A",
                "N/A",
                "N/A",
                "N/A",
                "N/A",
                "No reports found",
            )
            continue

        score = best["score"]
        config = best["config"]

        compact_config = {
            "w": config["resolution_width"],
            "fps": config["fps_sample"],
            "thr": config["motion_threshold"],
            "blur": config["blur_kernel"],
            "area": config["min_contour_area"],
            "dilate": config["dilate_iterations"],
            "gap": config["event_merge_gap_seconds"],
        }

        summary_table.add_row(
            objective,
            best["method"],
            best["name"],
            str(score["final_score"]),
            str(score.get("resource_score", "")),
            str(score.get("effective_processed_fps", "")),
            json.dumps(compact_config),
        )

    console.print(summary_table)


def main() -> None:
    args = parse_args()
    console = Console()

    payload = compare_optimizers(
        reports_dir=args.reports_dir,
        objectives=args.objectives,
        output_json=args.output_json,
        output_csv=args.output_csv,
    )

    render_best_summary(
        console=console,
        payload=payload,
    )

    render_comparison_table(
        console=console,
        payload=payload,
    )

    output_files = payload["output_files"]

    console.print("\nFiles saved:")
    console.print(f"JSON: {output_files['summary_json']}")
    console.print(f"CSV:  {output_files['ranking_csv']}")


if __name__ == "__main__":
    main()
