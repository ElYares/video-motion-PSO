from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from core.motion.detector import MotionConfig, detect_motion


@dataclass
class MotionProfile:
    """
    Represents a motion detection profile.

    Each profile contains a specific configuration that can be evaluated
    against the same input video.
    """

    name: str
    description: str
    config: MotionConfig


def get_default_profiles() -> list[MotionProfile]:
    """
    Return the default profiles used to compare motion detection behavior.
    """

    return [
        MotionProfile(
            name="baseline",
            description="Balanced initial configuration.",
            config=MotionConfig(
                resolution_width=640,
                fps_sample=12.0,
                motion_threshold=35,
                blur_kernel=5,
                min_contour_area=800,
                dilate_iterations=2,
                event_merge_gap_seconds=0.5,
            ),
        ),
        MotionProfile(
            name="random_balanced_best",
            description="Best balanced configuration found by random search.",
            config=MotionConfig(
                resolution_width=480,
                fps_sample=18.0,
                motion_threshold=32,
                blur_kernel=3,
                min_contour_area=300,
                dilate_iterations=3,
                event_merge_gap_seconds=0.5,
            ),
        ),
        MotionProfile(
            name="strict",
            description="More conservative profile to reduce false positives.",
            config=MotionConfig(
                resolution_width=640,
                fps_sample=12.0,
                motion_threshold=45,
                blur_kernel=5,
                min_contour_area=1200,
                dilate_iterations=2,
                event_merge_gap_seconds=0.5,
            ),
        ),
        MotionProfile(
            name="sensitive",
            description="More sensitive profile for small or subtle motion.",
            config=MotionConfig(
                resolution_width=640,
                fps_sample=12.0,
                motion_threshold=25,
                blur_kernel=5,
                min_contour_area=500,
                dilate_iterations=2,
                event_merge_gap_seconds=0.5,
            ),
        ),
        MotionProfile(
            name="low_cpu",
            description="Lower resolution and fewer sampled frames.",
            config=MotionConfig(
                resolution_width=320,
                fps_sample=8.0,
                motion_threshold=35,
                blur_kernel=5,
                min_contour_area=500,
                dilate_iterations=2,
                event_merge_gap_seconds=0.5,
            ),
        ),
        MotionProfile(
            name="back_person_sensitive",
            description="Sensitive profile that detected the first back-facing person better.",
            config=MotionConfig(
                resolution_width=640,
                fps_sample=25.0,
                motion_threshold=22,
                blur_kernel=3,
                min_contour_area=300,
                dilate_iterations=2,
                event_merge_gap_seconds=0.5,
            ),
        ),
    ]


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    """
    Clamp a numeric value into a fixed range.
    """

    return max(minimum, min(value, maximum))


def _calculate_effective_processed_fps(
    metrics: dict[str, Any],
    video: dict[str, Any],
) -> float:
    """
    Estimate the effective processed FPS based on processed frames and video duration.

    This is more reliable than requested fps_sample, because the real processed
    FPS depends on the source FPS and the frame interval used by the detector.
    """

    source_fps = video["source_fps"] or 25.0
    source_frame_count = video["source_frame_count"] or metrics["processed_frames"]

    duration_seconds = max(source_frame_count / source_fps, 1.0)

    return metrics["processed_frames"] / duration_seconds


def _calculate_resource_score(
    result: dict[str, Any],
) -> dict[str, float]:
    """
    Calculate how lightweight a configuration is.

    Higher resource_score means cheaper/lighter processing.

    Cost proxy:
    - resolution width
    - effective processed FPS
    - processed frame ratio
    """

    metrics = result["metrics"]
    video = result["video"]
    config = result["config"]

    source_frame_count = max(
        video["source_frame_count"] or metrics["processed_frames"],
        1,
    )

    processed_frames = metrics["processed_frames"]
    resolution_width = config["resolution_width"]

    effective_processed_fps = _calculate_effective_processed_fps(
        metrics=metrics,
        video=video,
    )

    width_ratio = _clamp(
        (resolution_width - 320) / (960 - 320),
        0.0,
        1.0,
    )

    fps_ratio = _clamp(
        (effective_processed_fps - 8) / (25 - 8),
        0.0,
        1.0,
    )

    processed_frame_ratio = _clamp(
        processed_frames / source_frame_count,
        0.0,
        1.0,
    )

    resource_cost = width_ratio * 0.45 + fps_ratio * 0.35 + processed_frame_ratio * 0.20

    resource_score = _clamp(100 - resource_cost * 100)

    return {
        "resource_score": round(resource_score, 4),
        "resource_cost": round(resource_cost, 4),
        "effective_processed_fps": round(effective_processed_fps, 4),
        "processed_frame_ratio": round(processed_frame_ratio, 4),
    }


def calculate_score(
    result: dict[str, Any],
    objective: str = "balanced",
) -> dict[str, float]:
    """
    Calculate a heuristic score for a detection result.

    This is not a scientific accuracy metric yet because we do not have
    ground-truth labels. It helps compare profiles based on:

    - motion ratio
    - detection stability
    - processing speed
    - resource usage

    For low_cpu, resource usage is strongly weighted.
    """

    metrics = result["metrics"]
    video = result["video"]

    processed_frames = max(metrics["processed_frames"], 1)
    motion_frames = metrics["motion_frames"]
    motion_events = metrics["motion_events"]
    raw_motion_events = metrics.get("raw_motion_events", motion_events)
    avg_processing_ms = metrics["avg_processing_ms"]

    source_fps = video["source_fps"] or 25.0
    source_frame_count = video["source_frame_count"] or processed_frames
    duration_seconds = max(source_frame_count / source_fps, 1.0)

    motion_ratio = motion_frames / processed_frames

    # Smoothed events approximate visual/real events.
    events_per_minute = motion_events / (duration_seconds / 60)

    # Raw events help detect flickering/unstable detection.
    fragmentation = raw_motion_events / max(motion_frames, 1)

    resource_info = _calculate_resource_score(result)

    if objective == "low_cpu":
        target_motion_ratio = 0.20

        ratio_weight = 0.20
        stability_weight = 0.15
        performance_weight = 0.20
        resource_weight = 0.45

    elif objective == "sensitive":
        target_motion_ratio = 0.32

        ratio_weight = 0.50
        stability_weight = 0.15
        performance_weight = 0.30
        resource_weight = 0.05

    else:
        target_motion_ratio = 0.25

        ratio_weight = 0.45
        stability_weight = 0.25
        performance_weight = 0.20
        resource_weight = 0.10

    ratio_score = _clamp(100 - abs(motion_ratio - target_motion_ratio) * 250)
    stability_score = _clamp(100 - events_per_minute * 3 - fragmentation * 100)
    performance_score = _clamp(100 - avg_processing_ms * 20)
    resource_score = resource_info["resource_score"]

    final_score = (
        ratio_score * ratio_weight
        + stability_score * stability_weight
        + performance_score * performance_weight
        + resource_score * resource_weight
    )

    return {
        "final_score": round(final_score, 4),
        "ratio_score": round(ratio_score, 4),
        "stability_score": round(stability_score, 4),
        "performance_score": round(performance_score, 4),
        "resource_score": round(resource_score, 4),
        "resource_cost": resource_info["resource_cost"],
        "motion_ratio": round(motion_ratio, 4),
        "events_per_minute": round(events_per_minute, 4),
        "fragmentation": round(fragmentation, 4),
        "effective_processed_fps": resource_info["effective_processed_fps"],
        "processed_frame_ratio": resource_info["processed_frame_ratio"],
    }


def _write_profile_report(
    report_path: Path,
    profile_report: dict[str, Any],
) -> None:
    """
    Write an individual profile evaluation report as JSON.
    """

    report_path.write_text(
        json.dumps(profile_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _write_summary_report(
    summary_path: Path,
    summary: dict[str, Any],
) -> None:
    """
    Write the full evaluation summary as JSON.
    """

    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _write_ranking_csv(
    csv_path: Path,
    evaluations: list[dict[str, Any]],
) -> None:
    """
    Write the ranked evaluation results as CSV.
    """

    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "rank",
                "profile",
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

        for rank, item in enumerate(evaluations, start=1):
            config = item["profile"]["config"]
            metrics = item["metrics"]
            score = item["score"]

            writer.writerow(
                {
                    "rank": rank,
                    "profile": item["profile"]["name"],
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


def evaluate_profiles(
    video_path: str | Path,
    objective: str = "balanced",
    method: str = "frame_diff",
    write_videos: bool = False,
    reports_dir: str | Path = "outputs/reports",
    videos_dir: str | Path = "outputs/videos",
) -> dict[str, Any]:
    """
    Run multiple motion detection profiles against the same video and rank them.

    method:
        frame_diff -> previous-frame difference.
        mog2       -> background subtraction.
    """

    valid_methods = {"frame_diff", "mog2"}

    if method not in valid_methods:
        raise ValueError(
            f"Invalid method: {method}. Expected one of: {sorted(valid_methods)}"
        )

    video_path = Path(video_path)
    reports_dir = Path(reports_dir)
    videos_dir = Path(videos_dir)

    reports_dir.mkdir(parents=True, exist_ok=True)
    videos_dir.mkdir(parents=True, exist_ok=True)

    evaluations: list[dict[str, Any]] = []

    for profile in get_default_profiles():
        profile_config_data = asdict(profile.config)
        profile_config_data["method"] = method
        config = MotionConfig(**profile_config_data)

        output_video_path = None

        if write_videos:
            output_video_path = videos_dir / f"{method}_{profile.name}_evaluated.mp4"

        result = detect_motion(
            video_path=video_path,
            config=config,
            output_video_path=output_video_path,
        )

        score = calculate_score(
            result=result,
            objective=objective,
        )

        profile_report = {
            "profile": {
                "name": profile.name,
                "description": profile.description,
                "method": method,
                "config": asdict(config),
            },
            "score": score,
            "metrics": result["metrics"],
            "output": result["output"],
        }

        report_path = reports_dir / f"{method}_{profile.name}_evaluation.json"

        _write_profile_report(
            report_path=report_path,
            profile_report=profile_report,
        )

        evaluations.append(profile_report)

    evaluations.sort(
        key=lambda item: item["score"]["final_score"],
        reverse=True,
    )

    summary_path = reports_dir / f"evaluation_summary_{objective}_{method}.json"
    csv_path = reports_dir / f"evaluation_ranking_{objective}_{method}.csv"

    summary = {
        "video_path": str(video_path),
        "objective": objective,
        "method": method,
        "best_profile": evaluations[0],
        "evaluations": evaluations,
        "output_files": {
            "summary_json": str(summary_path),
            "ranking_csv": str(csv_path),
        },
    }

    _write_summary_report(
        summary_path=summary_path,
        summary=summary,
    )

    _write_ranking_csv(
        csv_path=csv_path,
        evaluations=evaluations,
    )

    return summary
