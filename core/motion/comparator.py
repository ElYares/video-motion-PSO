from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

SUPPORTED_OBJECTIVES = ["balanced", "sensitive", "low_cpu"]
SUPPORTED_DETECTOR_METHODS = ["frame_diff", "mog2"]
DEFAULT_DETECTOR_METHODS = ["frame_diff"]


def _load_json(path: Path) -> dict[str, Any] | None:
    """
    Load a JSON file if it exists.

    Returns None when the file does not exist so the comparator can continue
    even if one optimizer has not been executed yet.
    """

    if not path.exists():
        return None

    return json.loads(path.read_text(encoding="utf-8"))


def _load_first_existing_json(
    paths: list[Path],
) -> tuple[dict[str, Any], Path] | tuple[None, None]:
    """
    Load the first existing JSON from a list of candidate paths.
    """

    for path in paths:
        payload = _load_json(path)

        if payload is not None:
            return payload, path

    return None, None


def _candidate_report_paths(
    reports_dir: Path,
    report_name: str,
    objective: str,
    detector_method: str,
) -> list[Path]:
    """
    Return report paths for the requested detector method.

    Newer reports include the detector method in the filename. Legacy
    frame-difference reports did not, so frame_diff keeps a fallback path.
    """

    paths = [
        reports_dir / f"{report_name}_{objective}_{detector_method}.json",
    ]

    if detector_method == "frame_diff":
        paths.append(reports_dir / f"{report_name}_{objective}.json")

    return paths


def _extract_manual_profile_result(
    objective: str,
    detector_method: str,
    payload: dict[str, Any],
    source_path: Path,
) -> dict[str, Any]:
    """
    Normalize the best result from evaluate_configs.py output.
    """

    best_profile = payload["best_profile"]

    return {
        "objective": objective,
        "detector_method": (
            best_profile["profile"].get("method")
            or best_profile["profile"].get("config", {}).get("method")
            or payload.get("method")
            or detector_method
        ),
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
    detector_method: str,
    payload: dict[str, Any],
    source_path: Path,
) -> dict[str, Any]:
    """
    Normalize the best result from random_search.py output.
    """

    best_result = payload["best_result"]

    return {
        "objective": objective,
        "detector_method": best_result["config"].get("method", detector_method),
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
    detector_method: str,
    payload: dict[str, Any],
    source_path: Path,
) -> dict[str, Any]:
    """
    Normalize the best result from pso_search.py output.
    """

    best_result = payload["best_result"]

    return {
        "objective": objective,
        "detector_method": best_result["config"].get("method", detector_method),
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
    detector_method: str,
) -> list[dict[str, Any]]:
    """
    Collect all available optimizer results for an objective and detector method.
    """

    results: list[dict[str, Any]] = []

    manual_payload, manual_path = _load_first_existing_json(
        _candidate_report_paths(
            reports_dir=reports_dir,
            report_name="evaluation_summary",
            objective=objective,
            detector_method=detector_method,
        )
    )

    random_payload, random_path = _load_first_existing_json(
        _candidate_report_paths(
            reports_dir=reports_dir,
            report_name="random_search",
            objective=objective,
            detector_method=detector_method,
        )
    )

    pso_payload, pso_path = _load_first_existing_json(
        _candidate_report_paths(
            reports_dir=reports_dir,
            report_name="pso_search",
            objective=objective,
            detector_method=detector_method,
        )
    )

    if manual_payload is not None and manual_path is not None:
        results.append(
            _extract_manual_profile_result(
                objective=objective,
                detector_method=detector_method,
                payload=manual_payload,
                source_path=manual_path,
            )
        )

    if random_payload is not None and random_path is not None:
        results.append(
            _extract_random_search_result(
                objective=objective,
                detector_method=detector_method,
                payload=random_payload,
                source_path=random_path,
            )
        )

    if pso_payload is not None and pso_path is not None:
        results.append(
            _extract_pso_result(
                objective=objective,
                detector_method=detector_method,
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
    method_rank: int | None,
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
        "detector_method": item["detector_method"],
        "method_rank": method_rank,
        "method": item["method"],
        "name": item["name"],
        "final_score": score["final_score"],
        "ratio_score": score["ratio_score"],
        "stability_score": score["stability_score"],
        "performance_score": score["performance_score"],
        "resource_score": score.get("resource_score"),
        "resource_cost": score.get("resource_cost"),
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
        "effective_processed_fps": score.get("effective_processed_fps"),
        "processed_frame_ratio": score.get("processed_frame_ratio"),
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
        "detector_method",
        "method_rank",
        "method",
        "name",
        "final_score",
        "ratio_score",
        "stability_score",
        "performance_score",
        "resource_score",
        "resource_cost",
        "motion_frames",
        "raw_motion_events",
        "motion_events",
        "avg_processing_ms",
        "estimated_processing_fps",
        "motion_ratio",
        "events_per_minute",
        "fragmentation",
        "effective_processed_fps",
        "processed_frame_ratio",
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
    methods: list[str] | None = None,
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
    selected_methods = methods or DEFAULT_DETECTOR_METHODS

    invalid_methods = [
        method
        for method in selected_methods
        if method not in SUPPORTED_DETECTOR_METHODS
    ]

    if invalid_methods:
        raise ValueError(
            f"Invalid detector methods: {invalid_methods}. "
            f"Expected one of: {SUPPORTED_DETECTOR_METHODS}"
        )

    comparison_by_objective: dict[str, Any] = {}
    csv_rows: list[dict[str, Any]] = []

    for objective in selected_objectives:
        method_comparison: dict[str, Any] = {}
        objective_results: list[dict[str, Any]] = []

        for detector_method in selected_methods:
            method_results = _collect_objective_results(
                reports_dir=reports_dir,
                objective=objective,
                detector_method=detector_method,
            )

            ranked_method_results = []

            for method_rank, item in enumerate(method_results, start=1):
                ranked_item = {
                    "rank": method_rank,
                    **item,
                }

                ranked_method_results.append(ranked_item)

                objective_results.append(
                    {
                        "method_rank": method_rank,
                        **item,
                    }
                )

            method_comparison[detector_method] = {
                "best": ranked_method_results[0] if ranked_method_results else None,
                "results": ranked_method_results,
            }

        objective_results.sort(
            key=lambda item: item["score"]["final_score"],
            reverse=True,
        )

        ranked_results = []

        for rank, item in enumerate(objective_results, start=1):
            ranked_item = {
                "rank": rank,
                **item,
            }

            ranked_results.append(ranked_item)
            csv_rows.append(
                _flatten_result_for_csv(
                    rank=rank,
                    method_rank=item.get("method_rank"),
                    item=item,
                )
            )

        comparison_by_objective[objective] = {
            "best": ranked_results[0] if ranked_results else None,
            "results": ranked_results,
            "methods": method_comparison,
        }

    payload = {
        "reports_dir": str(reports_dir),
        "objectives": selected_objectives,
        "methods": selected_methods,
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
