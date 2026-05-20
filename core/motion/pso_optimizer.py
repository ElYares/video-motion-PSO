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
class PSOBounds:
    """
    Continuous bounds used by PSO.

    PSO works with floating-point vectors, then each vector is decoded into
    a valid MotionConfig.
    """

    resolution_width: tuple[float, float] = (320.0, 960.0)
    fps_sample: tuple[float, float] = (8.0, 25.0)
    motion_threshold: tuple[float, float] = (18.0, 50.0)
    blur_kernel: tuple[float, float] = (3.0, 7.0)
    min_contour_area: tuple[float, float] = (250.0, 1500.0)
    dilate_iterations: tuple[float, float] = (1.0, 3.0)
    event_merge_gap_seconds: tuple[float, float] = (0.3, 0.7)


@dataclass
class Particle:
    """
    A PSO particle.

    detector_method:
        The detector method assigned to this particle.

    position:
        Current candidate solution.

    velocity:
        Movement direction and magnitude.

    best_position:
        Best position found by this particle.

    best_score:
        Best score found by this particle.
    """

    position: list[float]
    velocity: list[float]
    best_position: list[float]
    best_score: float
    detector_method: str = "frame_diff"
    best_payload: dict[str, Any] | None = None


def _clamp(value: float, minimum: float, maximum: float) -> float:
    """
    Clamp a number between minimum and maximum.
    """

    return max(minimum, min(value, maximum))


def _nearest(value: float, options: list[float]) -> float:
    """
    Return the option closest to value.
    """

    return min(options, key=lambda option: abs(option - value))


def _round_to_step(value: float, step: int) -> int:
    """
    Round a number to a fixed integer step.
    """

    return int(round(value / step) * step)


def _get_bound_ranges(bounds: PSOBounds) -> list[tuple[float, float]]:
    """
    Return PSO bounds as an ordered list.
    """

    return [
        bounds.resolution_width,
        bounds.fps_sample,
        bounds.motion_threshold,
        bounds.blur_kernel,
        bounds.min_contour_area,
        bounds.dilate_iterations,
        bounds.event_merge_gap_seconds,
    ]


def _decode_position(
    position: list[float],
    bounds: PSOBounds,
    detector_method: str = "frame_diff",
) -> MotionConfig:
    """
    Convert a PSO continuous vector into a valid MotionConfig.

    The vector layout is:

    0. resolution_width
    1. fps_sample
    2. motion_threshold
    3. blur_kernel
    4. min_contour_area
    5. dilate_iterations
    6. event_merge_gap_seconds
    """

    resolution_options = [320.0, 480.0, 640.0, 800.0, 960.0]
    fps_options = [8.0, 10.0, 12.0, 15.0, 18.0, 20.0, 25.0]
    blur_options = [3.0, 5.0, 7.0]

    resolution_width = int(_nearest(position[0], resolution_options))
    fps_sample = float(_nearest(position[1], fps_options))

    motion_threshold = int(
        round(
            _clamp(
                position[2],
                bounds.motion_threshold[0],
                bounds.motion_threshold[1],
            )
        )
    )

    blur_kernel = int(_nearest(position[3], blur_options))

    min_contour_area = _round_to_step(
        _clamp(
            position[4],
            bounds.min_contour_area[0],
            bounds.min_contour_area[1],
        ),
        step=50,
    )

    min_contour_area = int(
        _clamp(
            min_contour_area,
            bounds.min_contour_area[0],
            bounds.min_contour_area[1],
        )
    )

    dilate_iterations = int(
        round(
            _clamp(
                position[5],
                bounds.dilate_iterations[0],
                bounds.dilate_iterations[1],
            )
        )
    )

    event_merge_gap_seconds = round(
        _clamp(
            position[6],
            bounds.event_merge_gap_seconds[0],
            bounds.event_merge_gap_seconds[1],
        ),
        1,
    )

    return MotionConfig(
        method=detector_method,
        resolution_width=resolution_width,
        fps_sample=fps_sample,
        motion_threshold=motion_threshold,
        blur_kernel=blur_kernel,
        min_contour_area=min_contour_area,
        dilate_iterations=dilate_iterations,
        event_merge_gap_seconds=event_merge_gap_seconds,
    )


def _encode_config_to_position(config: MotionConfig) -> list[float]:
    """
    Convert a MotionConfig into a PSO position vector.
    """

    return [
        float(config.resolution_width),
        float(config.fps_sample),
        float(config.motion_threshold),
        float(config.blur_kernel),
        float(config.min_contour_area),
        float(config.dilate_iterations),
        float(config.event_merge_gap_seconds),
    ]


def get_seed_configs(
    objective: str,
    detector_methods: list[str],
) -> list[MotionConfig]:
    """
    Return known good configurations used to seed PSO.

    The same seed parameter sets are expanded across each selected detector
    method, so PSO can compare frame_diff and mog2 fairly.
    """

    random_balanced_best = MotionConfig(
        method="frame_diff",
        resolution_width=480,
        fps_sample=18.0,
        motion_threshold=32,
        blur_kernel=3,
        min_contour_area=300,
        dilate_iterations=3,
        event_merge_gap_seconds=0.5,
    )

    back_person_sensitive = MotionConfig(
        method="frame_diff",
        resolution_width=640,
        fps_sample=25.0,
        motion_threshold=22,
        blur_kernel=3,
        min_contour_area=300,
        dilate_iterations=2,
        event_merge_gap_seconds=0.5,
    )

    low_cpu = MotionConfig(
        method="frame_diff",
        resolution_width=320,
        fps_sample=8.0,
        motion_threshold=35,
        blur_kernel=5,
        min_contour_area=500,
        dilate_iterations=2,
        event_merge_gap_seconds=0.5,
    )

    baseline = MotionConfig(
        method="frame_diff",
        resolution_width=640,
        fps_sample=12.0,
        motion_threshold=35,
        blur_kernel=5,
        min_contour_area=800,
        dilate_iterations=2,
        event_merge_gap_seconds=0.5,
    )

    if objective == "sensitive":
        base_seeds = [
            back_person_sensitive,
            random_balanced_best,
            baseline,
        ]

    elif objective == "low_cpu":
        base_seeds = [
            low_cpu,
            random_balanced_best,
            baseline,
        ]

    else:
        base_seeds = [
            random_balanced_best,
            baseline,
            back_person_sensitive,
        ]

    expanded_seeds: list[MotionConfig] = []

    for detector_method in detector_methods:
        for seed_config in base_seeds:
            config_data = asdict(seed_config)
            config_data["method"] = detector_method
            expanded_seeds.append(MotionConfig(**config_data))

    return expanded_seeds


def _create_seed_particle(
    config: MotionConfig,
    bounds: PSOBounds,
    random_generator: random.Random,
) -> Particle:
    """
    Create a PSO particle from a known good MotionConfig.

    The position starts exactly from the known config, while velocity gets
    a small random value so PSO can explore around it.
    """

    position = _encode_config_to_position(config)
    velocity: list[float] = []

    for minimum, maximum in _get_bound_ranges(bounds):
        value_range = maximum - minimum
        velocity.append(random_generator.uniform(-value_range, value_range) * 0.03)

    return Particle(
        position=position,
        velocity=velocity,
        best_position=position.copy(),
        best_score=float("-inf"),
        detector_method=config.method,
    )


def _config_signature(config: MotionConfig) -> tuple[Any, ...]:
    """
    Build a hashable signature to cache repeated evaluations.
    """

    return (
        config.method,
        config.resolution_width,
        config.fps_sample,
        config.motion_threshold,
        config.blur_kernel,
        config.min_contour_area,
        config.dilate_iterations,
        config.event_merge_gap_seconds,
    )


def _create_particle(
    bounds: PSOBounds,
    random_generator: random.Random,
    detector_method: str = "frame_diff",
) -> Particle:
    """
    Create a random particle inside the PSO search bounds.
    """

    position: list[float] = []
    velocity: list[float] = []

    for minimum, maximum in _get_bound_ranges(bounds):
        value = random_generator.uniform(minimum, maximum)
        value_range = maximum - minimum

        position.append(value)
        velocity.append(random_generator.uniform(-value_range, value_range) * 0.1)

    return Particle(
        position=position,
        velocity=velocity,
        best_position=position.copy(),
        best_score=float("-inf"),
        detector_method=detector_method,
    )


def _evaluate_position(
    video_path: Path,
    position: list[float],
    bounds: PSOBounds,
    objective: str,
    detector_method: str,
    cache: dict[tuple[Any, ...], dict[str, Any]],
) -> dict[str, Any]:
    """
    Decode and evaluate a PSO position.
    """

    config = _decode_position(
        position=position,
        bounds=bounds,
        detector_method=detector_method,
    )

    signature = _config_signature(config)

    if signature in cache:
        return cache[signature]

    detection_result = detect_motion(
        video_path=video_path,
        config=config,
        output_video_path=None,
    )

    score = calculate_score(
        result=detection_result,
        objective=objective,
    )

    payload = {
        "config": asdict(config),
        "score": score,
        "metrics": detection_result["metrics"],
        "video": detection_result["video"],
    }

    cache[signature] = payload

    return payload


def _update_particle_velocity_and_position(
    particle: Particle,
    global_best_position: list[float],
    bounds: PSOBounds,
    random_generator: random.Random,
    inertia_weight: float,
    cognitive_weight: float,
    social_weight: float,
) -> None:
    """
    Update a particle using the standard PSO formula.

    velocity =
        inertia
        + cognitive component toward personal best
        + social component toward global best
    """

    bound_ranges = _get_bound_ranges(bounds)

    for index, (minimum, maximum) in enumerate(bound_ranges):
        r1 = random_generator.random()
        r2 = random_generator.random()

        inertia = inertia_weight * particle.velocity[index]

        cognitive = (
            cognitive_weight
            * r1
            * (particle.best_position[index] - particle.position[index])
        )

        social = (
            social_weight
            * r2
            * (global_best_position[index] - particle.position[index])
        )

        new_velocity = inertia + cognitive + social

        value_range = maximum - minimum
        max_velocity = value_range * 0.3

        new_velocity = _clamp(
            new_velocity,
            -max_velocity,
            max_velocity,
        )

        new_position = particle.position[index] + new_velocity
        new_position = _clamp(new_position, minimum, maximum)

        particle.velocity[index] = new_velocity
        particle.position[index] = new_position


def _write_pso_json(output_path: Path, payload: dict[str, Any]) -> None:
    """
    Write PSO result as JSON.
    """

    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _write_pso_csv(output_path: Path, results: list[dict[str, Any]]) -> None:
    """
    Write PSO evaluated configurations as CSV.
    """

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "rank",
                "source",
                "detector_method",
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
                    "source": item.get("source", "pso"),
                    "detector_method": config.get("method", "frame_diff"),
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


def run_pso_search(
    video_path: str | Path,
    objective: str = "balanced",
    particles_count: int = 10,
    iterations: int = 8,
    seed: int = 42,
    inertia_weight: float = 0.65,
    cognitive_weight: float = 1.5,
    social_weight: float = 1.5,
    reports_dir: str | Path = "outputs/reports",
    videos_dir: str | Path = "outputs/videos",
    write_best_video: bool = False,
    use_seed_configs: bool = True,
    detector_methods: list[str] | None = None,
) -> dict[str, Any]:
    """
    Run Particle Swarm Optimization for motion detection configuration.

    The algorithm:
    1. Create seeded and random particles.
    2. Each particle represents a candidate MotionConfig.
    3. Each particle keeps its detector method fixed.
    4. Evaluate each particle.
    5. Update personal best and global best.
    6. Move particles toward better numeric configurations.
    7. Save JSON, CSV and optional best annotated video.
    """

    if particles_count < 1:
        raise ValueError("particles_count must be greater than 0")

    if iterations < 1:
        raise ValueError("iterations must be greater than 0")

    valid_methods = {"frame_diff", "mog2"}
    selected_methods = detector_methods or ["frame_diff"]

    invalid_methods = set(selected_methods) - valid_methods

    if invalid_methods:
        raise ValueError(
            f"Invalid detector methods: {sorted(invalid_methods)}. "
            f"Expected one of: {sorted(valid_methods)}"
        )

    video_path = Path(video_path)
    reports_dir = Path(reports_dir)
    videos_dir = Path(videos_dir)

    reports_dir.mkdir(parents=True, exist_ok=True)
    videos_dir.mkdir(parents=True, exist_ok=True)

    random_generator = random.Random(seed)
    bounds = PSOBounds()

    particles: list[Particle] = []

    if use_seed_configs:
        seed_configs = get_seed_configs(
            objective=objective,
            detector_methods=selected_methods,
        )

        for seed_config in seed_configs:
            if len(particles) >= particles_count:
                break

            particles.append(
                _create_seed_particle(
                    config=seed_config,
                    bounds=bounds,
                    random_generator=random_generator,
                )
            )

    while len(particles) < particles_count:
        particles.append(
            _create_particle(
                bounds=bounds,
                random_generator=random_generator,
                detector_method=random_generator.choice(selected_methods),
            )
        )

    cache: dict[tuple[Any, ...], dict[str, Any]] = {}

    global_best_position: list[float] | None = None
    global_best_score = float("-inf")
    global_best_payload: dict[str, Any] | None = None

    history: list[dict[str, Any]] = []

    for iteration in range(1, iterations + 1):
        iteration_scores: list[float] = []

        for particle in particles:
            payload = _evaluate_position(
                video_path=video_path,
                position=particle.position,
                bounds=bounds,
                objective=objective,
                detector_method=particle.detector_method,
                cache=cache,
            )

            score = payload["score"]["final_score"]
            iteration_scores.append(score)

            if score > particle.best_score:
                particle.best_score = score
                particle.best_position = particle.position.copy()
                particle.best_payload = payload

            if score > global_best_score:
                global_best_score = score
                global_best_position = particle.position.copy()
                global_best_payload = payload

        if global_best_position is None:
            raise RuntimeError("PSO could not evaluate any particle.")

        average_score = sum(iteration_scores) / len(iteration_scores)

        history.append(
            {
                "iteration": iteration,
                "best_score": round(global_best_score, 4),
                "average_score": round(average_score, 4),
                "evaluated_particles": len(iteration_scores),
            }
        )

        for particle in particles:
            _update_particle_velocity_and_position(
                particle=particle,
                global_best_position=global_best_position,
                bounds=bounds,
                random_generator=random_generator,
                inertia_weight=inertia_weight,
                cognitive_weight=cognitive_weight,
                social_weight=social_weight,
            )

    all_results = list(cache.values())

    for item in all_results:
        item["source"] = "pso"

    all_results.sort(
        key=lambda item: item["score"]["final_score"],
        reverse=True,
    )

    best_result = global_best_payload

    best_video_path = None

    if write_best_video and best_result is not None:
        best_config = MotionConfig(**best_result["config"])
        best_method = best_config.method
        best_video_path = videos_dir / f"pso_best_{objective}_{best_method}.mp4"

        detect_motion(
            video_path=video_path,
            config=best_config,
            output_video_path=best_video_path,
        )

        best_result["output"] = {
            "video_path": str(best_video_path),
        }

    methods_suffix = "_".join(selected_methods)

    json_path = reports_dir / f"pso_search_{objective}.json"
    csv_path = reports_dir / f"pso_search_{objective}.csv"

    # Keep the classic output names for compatibility. Also include the method
    # list in the payload so the comparator can read the detector method from
    # each result.
    payload = {
        "video_path": str(video_path),
        "objective": objective,
        "detector_methods": selected_methods,
        "methods_suffix": methods_suffix,
        "particles_count": particles_count,
        "iterations": iterations,
        "seed": seed,
        "parameters": {
            "inertia_weight": inertia_weight,
            "cognitive_weight": cognitive_weight,
            "social_weight": social_weight,
            "use_seed_configs": use_seed_configs,
            "detector_methods": selected_methods,
        },
        "best_result": best_result,
        "history": history,
        "results": all_results,
        "output_files": {
            "summary_json": str(json_path),
            "ranking_csv": str(csv_path),
            "best_video": str(best_video_path) if best_video_path else None,
        },
    }

    _write_pso_json(
        output_path=json_path,
        payload=payload,
    )

    _write_pso_csv(
        output_path=csv_path,
        results=all_results,
    )

    return payload
