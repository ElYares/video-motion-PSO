from __future__ import annotations

import csv
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from core.motion.detector import MotionConfig, detect_motion
from core.motion.evaluator import calculate_score


@dataclass
class SearchSpace:
    """
    Search space used by random search.

    Each list contains valid values that can be sampled to create a
    MotionConfig candidate.
    """

    resolution_widths: list[int]
    fps_samples: list[float]
    motion_thresholds: list[int]
    blur_kernels: list[int]
    min_contour_areas: list[int]
    dilate_iterations: list[int]
    event_merge_gap_seconds: list[float]


def get_default_search_space() -> SearchSpace:
    """
    Return a practical default search space for hallway/camera-like videos.
    """

    return SearchSpace(
        resolution_widths=[320, 480, 640, 800, 960],
        fps_samples=[8.0, 10.0, 12.0, 15.0, 18.0, 20.0, 25.0],
        motion_thresholds=[18, 22, 25, 28, 32, 35, 40, 45, 50],
        blur_kernels=[3, 5, 7],
        min_contour_areas=[250, 300, 400, 500, 650, 800, 1000, 1200, 1500],
        dilate_iterations=[1, 2, 3],
        event_merge_gap_seconds=[0.3, 0.5, 0.7],
    )


def generate_random_config(
    search_space: SearchSpace,
    random_generator: random.Random,
) -> MotionConfig:
    """
    Generate a random MotionConfig from the provided search space.
    """

    return MotionConfig(
        resolution_width=random_generator.choice(search_space.resolution_widths),
        fps_sample=random_generator.choice(search_space.fps_samples),
        motion_threshold=random_generator.choice(search_space.motion_thresholds),
        blur_kernel=random_generator.choice(search_space.blur_kernels),
        min_contour_area=random_generator.choice(search_space.min_contour_areas),
        dilate_iterations=random_generator.choice(search_space.dilate_iterations),
        event_merge_gap_seconds=random_generator.choice(
            search_space.event_merge_gap_seconds
        ),
    )


def _config_signature(config: MotionConfig) -> tuple[Any, ...]:
    """
    Build a hashable signature to avoid evaluating duplicated configurations.
    """

    return (
        config.resolution_width,
        config.fps_sample,
        config.motion_threshold,
        config.blur_kernel,
        config.min_contour_area,
        config.dilate_iterations,
        config.event_merge_gap_seconds,
    )


def _write_random_search_json(
    output_path: Path,
    payload: dict[str, Any],
) -> None:
    """
    Write random search result as JSON.
    """

    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _write_random_search_csv(
    output_path: Path,
    results: list[dict[str, Any]],
) -> None:
    """
    Write random search ranking as CSV.
    """

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "rank",
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
            ],
        )

        writer.writeheader()

        for rank, item in enumerate(results, start=1):
            config = item["config"]
            metrics = item["metrics"]
            score = item["score"]

            writer.writerow(
                {
                    "rank": rank,
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
                }
            )


def run_random_search(
    video_path: str | Path,
    objective: str = "balanced",
    iterations: int = 30,
    seed: int = 42,
    reports_dir: str | Path = "outputs/reports",
    videos_dir: str | Path = "outputs/videos",
    write_best_video: bool = False,
) -> dict[str, Any]:
    """
    Run random search over generated MotionConfig candidates.

    The algorithm:
    1. Generate a random configuration.
    2. Run motion detection.
    3. Score the result.
    4. Repeat N times.
    5. Sort by score.
    6. Save JSON and CSV reports.
    """

    video_path = Path(video_path)
    reports_dir = Path(reports_dir)
    videos_dir = Path(videos_dir)

    reports_dir.mkdir(parents=True, exist_ok=True)
    videos_dir.mkdir(parents=True, exist_ok=True)

    random_generator = random.Random(seed)
    search_space = get_default_search_space()

    results: list[dict[str, Any]] = []
    evaluated_signatures: set[tuple[Any, ...]] = set()

    attempts = 0
    max_attempts = iterations * 10

    while len(results) < iterations and attempts < max_attempts:
        attempts += 1

        config = generate_random_config(
            search_space=search_space,
            random_generator=random_generator,
        )

        signature = _config_signature(config)

        if signature in evaluated_signatures:
            continue

        evaluated_signatures.add(signature)

        result = detect_motion(
            video_path=video_path,
            config=config,
            output_video_path=None,
        )

        score = calculate_score(
            result=result,
            objective=objective,
        )

        results.append(
            {
                "iteration": len(results) + 1,
                "config": asdict(config),
                "score": score,
                "metrics": result["metrics"],
                "video": result["video"],
            }
        )

    results.sort(
        key=lambda item: item["score"]["final_score"],
        reverse=True,
    )

    best_result = results[0] if results else None

    best_video_path = None

    if write_best_video and best_result is not None:
        best_config = MotionConfig(**best_result["config"])
        best_video_path = videos_dir / f"random_search_best_{objective}.mp4"

        detect_motion(
            video_path=video_path,
            config=best_config,
            output_video_path=best_video_path,
        )

        best_result["output"] = {
            "video_path": str(best_video_path),
        }

    json_path = reports_dir / f"random_search_{objective}.json"
    csv_path = reports_dir / f"random_search_{objective}.csv"

    payload = {
        "video_path": str(video_path),
        "objective": objective,
        "iterations_requested": iterations,
        "iterations_evaluated": len(results),
        "seed": seed,
        "best_result": best_result,
        "results": results,
        "output_files": {
            "summary_json": str(json_path),
            "ranking_csv": str(csv_path),
            "best_video": str(best_video_path) if best_video_path else None,
        },
    }

    _write_random_search_json(
        output_path=json_path,
        payload=payload,
    )

    _write_random_search_csv(
        output_path=csv_path,
        results=results,
    )

    return payload
