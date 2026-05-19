from __future__ import annotations

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
    Default profiles used to compare motion detection behavior.
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
            ),
        ),
    ]


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    """
    Clamp a numeric value into a fixed range.
    """

    return max(minimum, min(value, maximum))


def calculate_score(
    result: dict[str, Any], objective: str = "balanced"
) -> dict[str, float]:
    """
    Calculate a heuristic score for a detection result.

    This score is not a scientific accuracy metric yet because we do not have
    ground-truth labels. It helps compare profiles based on motion ratio,
    stability and processing cost.
    """

    metrics = result["metrics"]
    video = result["video"]

    processed_frames = max(metrics["processed_frames"], 1)
    motion_frames = metrics["motion_frames"]
    motion_events = metrics["motion_events"]
    avg_processing_ms = metrics["avg_processing_ms"]

    source_fps = video["source_fps"] or 25.0
    source_frame_count = video["source_frame_count"] or processed_frames
    duration_seconds = max(source_frame_count / source_fps, 1.0)

    motion_ratio = motion_frames / processed_frames
    events_per_minute = motion_events / (duration_seconds / 60)
    fragmentation = motion_events / max(motion_frames, 1)

    if objective == "low_cpu":
        target_motion_ratio = 0.20
        ratio_weight = 0.30
        stability_weight = 0.20
        performance_weight = 0.50
    elif objective == "sensitive":
        target_motion_ratio = 0.32
        ratio_weight = 0.50
        stability_weight = 0.15
        performance_weight = 0.35
    else:
        target_motion_ratio = 0.25
        ratio_weight = 0.45
        stability_weight = 0.30
        performance_weight = 0.25

    ratio_score = _clamp(100 - abs(motion_ratio - target_motion_ratio) * 250)
    stability_score = _clamp(100 - events_per_minute * 3 - fragmentation * 100)
    performance_score = _clamp(100 - avg_processing_ms * 20)

    final_score = (
        ratio_score * ratio_weight
        + stability_score * stability_weight
        + performance_score * performance_weight
    )

    return {
        "final_score": round(final_score, 4),
        "ratio_score": round(ratio_score, 4),
        "stability_score": round(stability_score, 4),
        "performance_score": round(performance_score, 4),
        "motion_ratio": round(motion_ratio, 4),
        "events_per_minute": round(events_per_minute, 4),
        "fragmentation": round(fragmentation, 4),
    }


def evaluate_profiles(
    video_path: str | Path,
    objective: str = "balanced",
    write_videos: bool = False,
    reports_dir: str | Path = "outputs/reports",
    videos_dir: str | Path = "outputs/videos",
) -> dict[str, Any]:
    """
    Run multiple motion detection profiles against the same video and rank them.
    """

    video_path = Path(video_path)
    reports_dir = Path(reports_dir)
    videos_dir = Path(videos_dir)

    reports_dir.mkdir(parents=True, exist_ok=True)
    videos_dir.mkdir(parents=True, exist_ok=True)

    evaluations: list[dict[str, Any]] = []

    for profile in get_default_profiles():
        output_video_path = None

        if write_videos:
            output_video_path = videos_dir / f"{profile.name}_evaluated.mp4"

        result = detect_motion(
            video_path=video_path,
            config=profile.config,
            output_video_path=output_video_path,
        )

        score = calculate_score(result, objective=objective)

        profile_report = {
            "profile": {
                "name": profile.name,
                "description": profile.description,
                "config": asdict(profile.config),
            },
            "score": score,
            "metrics": result["metrics"],
            "output": result["output"],
        }

        report_path = reports_dir / f"{profile.name}_evaluation.json"
        report_path.write_text(
            json.dumps(profile_report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        evaluations.append(profile_report)

    evaluations.sort(
        key=lambda item: item["score"]["final_score"],
        reverse=True,
    )

    summary = {
        "video_path": str(video_path),
        "objective": objective,
        "best_profile": evaluations[0],
        "evaluations": evaluations,
    }

    summary_path = reports_dir / "evaluation_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return summary
