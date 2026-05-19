from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

SUPPORTED_OBJECTIVES = ["balanced", "sensitive", "low_cpu"]


def _load_json(path: Path) -> dict[str, Any] | None:
    """
    Load a JSON file if it exists.

    Returns None when the file does not exist so the comparator can continue
    even if one optimizer has not been executed yet.
    """

    if not path.exists():
        return None

    return json.loads(path.read_text(encoding="utf-8"))


def _extract_manual_profile_result(
    objective: str,
    payload: dict[str, Any],
    source_path: Path,
) -> dict[str, Any]:
    """
    Normalize the best result from evaluate_configs.py output.
    """

    best_profile = payload["best_profile"]

    return {
        "objective": objective,
        "method": "manual_profiles",
        "name": best_profile["profile"]["name"],
        "description": best_profile["profile"].get("description"),
        "score": best_profile["score"],
        "metrics": best_profile["metrics"],
        "config": best_profile["profile"]["config"],
        "output": best_profile.get("output", {}),
        "source_file": str(source_path),
    }


def _extract_random_search_result(
    objective: str,
    payload: dict[str, Any],
    source_path: Path,
) -> dict[str, Any]:
    """
    Normalize the best result from random_search.py output.
    """

    best_result = payload["best_result"]

    return {
        "objective": objective,
        "method": "random_search",
        "name": "random_search_best",
        "description": "Best configuration found by random search.",
        "score": best_result["score"],
        "metrics": best_result["metrics"],
        "config": best_result["config"],
        "output": best_result.get("output", {}),
        "source_file": str(source_path),
    }


def _extract_pso_result(
    objective: str,
    payload: dict[str, Any],
    source_path: Path,
) -> dict[str, Any]:
    """
    Normalize the best result from pso_search.py output.
    """

    best_result = payload["best_result"]

    return {
        "objective": objective,
        "method": "seeded_pso",
        "name": "pso_best",
        "description": "Best configuration found by seeded PSO.",
        "score": best_result["score"],
        "metrics": best_result["metrics"],
        "config": best_result["config"],
        "output": best_result.get("output", {}),
        "source_file": str(source_path),
    }


def _collect_objective_results(
    reports_dir: Path,
    objective: str,
) -> list[dict[str, Any]]:
    """
    Collect all available optimizer results for a single objective.
    """

    results: list[dict[str, Any]] = []

    manual_path = reports_dir / f"evaluation_summary_{objective}.json"
    random_path = reports_dir / f"random_search_{objective}.json"
    pso_path = reports_dir / f"pso_search_{objective}.json"

    manual_payload = _load_json(manual_path)
    random_payload = _load_json(random_path)
    pso_payload = _load_json(pso_path)

    if manual_payload:
        results.append(
            _extract_manual_profile_result(
                objective=objective,
                payload=manual_payload,
                source_path=manual_path,
            )
        )

    if random_payload:
        results.append(
            _extract_random_search_result(
                objective=objective,
                payload=random_payload,
                source_path=random_path,
            )
        )

    if pso_payload:
        results.append(
            _extract_pso_result(
                objective=objective,
                payload=pso_payload,
                source_path=pso_path,
            )
        )

    results.sort(
        key=lambda item: item["score"]["final_score"],
        reverse=True,
    )

    return results


def _flatten_result_for_csv(
    rank: int,
    item: dict[str, Any],
) -> dict[str, Any]:
    """
    Flatten a normalized optimizer result into a CSV-friendly row.
    """

    score = item["score"]
    metrics = item["metrics"]
    config = item["config"]

    return {
        "objective": item["objective"],
        "rank": rank,
        "method": item["method"],
        "name": item["name"],
        "final_score": score["final_score"],
        "ratio_score": score["ratio_score"],
        "stability_score": score["stability_score"],
        "performance_score": score["performance_score"],
        "motion_frames": metrics["motion_frames"],
        "raw_motion_events": metrics.get(
            "raw_motion_events",
            metrics["motion_events"],
        ),
        "motion_events": metrics["motion_events"],
        "avg_processing_ms": metrics["avg_processing_ms"],
        "estimated_processing_fps": metrics["estimated_processing_fps"],
        "motion_ratio": score["motion_ratio"],
        "events_per_minute": score["events_per_minute"],
        "fragmentation": score["fragmentation"],
        "resolution_width": config["resolution_width"],
        "fps_sample": config["fps_sample"],
        "motion_threshold": config["motion_threshold"],
        "blur_kernel": config["blur_kernel"],
        "min_contour_area": config["min_contour_area"],
        "dilate_iterations": config["dilate_iterations"],
        "event_merge_gap_seconds": config["event_merge_gap_seconds"],
        "source_file": item["source_file"],
    }


def _write_comparison_json(
    output_path: Path,
    payload: dict[str, Any],
) -> None:
    """
    Write optimizer comparison as JSON.
    """

    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _write_comparison_csv(
    output_path: Path,
    rows: list[dict[str, Any]],
) -> None:
    """
    Write optimizer comparison as CSV.
    """

    fieldnames = [
        "objective",
        "rank",
        "method",
        "name",
        "final_score",
        "ratio_score",
        "stability_score",
        "performance_score",
        "motion_frames",
        "raw_motion_events",
        "motion_events",
        "avg_processing_ms",
        "estimated_processing_fps",
        "motion_ratio",
        "events_per_minute",
        "fragmentation",
        "resolution_width",
        "fps_sample",
        "motion_threshold",
        "blur_kernel",
        "min_contour_area",
        "dilate_iterations",
        "event_merge_gap_seconds",
        "source_file",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)


def compare_optimizers(
    reports_dir: str | Path = "outputs/reports",
    objectives: list[str] | None = None,
    output_json: str | Path = "outputs/reports/optimizer_comparison.json",
    output_csv: str | Path = "outputs/reports/optimizer_comparison.csv",
) -> dict[str, Any]:
    """
    Compare manual profiles, random search and seeded PSO results.

    This function does not run video processing again. It reads existing JSON
    reports produced by previous CLI commands and generates a unified ranking.
    """

    reports_dir = Path(reports_dir)
    output_json = Path(output_json)
    output_csv = Path(output_csv)

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    selected_objectives = objectives or SUPPORTED_OBJECTIVES

    comparison_by_objective: dict[str, Any] = {}
    csv_rows: list[dict[str, Any]] = []

    for objective in selected_objectives:
        results = _collect_objective_results(
            reports_dir=reports_dir,
            objective=objective,
        )

        ranked_results = []

        for rank, item in enumerate(results, start=1):
            ranked_item = {
                "rank": rank,
                **item,
            }

            ranked_results.append(ranked_item)
            csv_rows.append(
                _flatten_result_for_csv(
                    rank=rank,
                    item=item,
                )
            )

        comparison_by_objective[objective] = {
            "best": ranked_results[0] if ranked_results else None,
            "results": ranked_results,
        }

    payload = {
        "reports_dir": str(reports_dir),
        "objectives": selected_objectives,
        "comparison": comparison_by_objective,
        "output_files": {
            "summary_json": str(output_json),
            "ranking_csv": str(output_csv),
        },
    }

    _write_comparison_json(
        output_path=output_json,
        payload=payload,
    )

    _write_comparison_csv(
        output_path=output_csv,
        rows=csv_rows,
    )

    return payload
