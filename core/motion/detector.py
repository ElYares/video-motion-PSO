from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

import cv2


@dataclass
class MotionConfig:
    """
    Configuration used by the motion detector.

    method:
        frame_diff -> compares current frame against previous frame.
        mog2       -> OpenCV background subtraction using MOG2.
    """

    method: str = "frame_diff"

    resolution_width: int = 640
    fps_sample: float = 12.0
    motion_threshold: int = 35
    blur_kernel: int = 5
    min_contour_area: int = 800
    dilate_iterations: int = 2
    event_merge_gap_seconds: float = 0.5

    # MOG2-specific parameters.
    mog2_history: int = 120
    mog2_var_threshold: float = 25.0
    mog2_detect_shadows: bool = True
    mog2_learning_rate: float = -1.0
    mog2_warmup_frames: int = 5


def _ensure_odd_kernel(kernel_size: int) -> int:
    """
    OpenCV GaussianBlur requires an odd kernel size.
    """

    if kernel_size < 1:
        return 1

    if kernel_size % 2 == 0:
        return kernel_size + 1

    return kernel_size


def _resize_frame(frame, target_width: int):
    """
    Resize frame preserving aspect ratio.
    """

    original_height, original_width = frame.shape[:2]

    if target_width <= 0 or target_width >= original_width:
        return frame

    ratio = target_width / original_width
    target_height = int(original_height * ratio)

    return cv2.resize(frame, (target_width, target_height))


def _find_motion_boxes_from_binary_mask(
    binary_mask,
    config: MotionConfig,
) -> list[tuple[int, int, int, int]]:
    """
    Find bounding boxes from a binary motion mask.
    """

    binary_mask = cv2.dilate(
        binary_mask,
        None,
        iterations=config.dilate_iterations,
    )

    contours, _ = cv2.findContours(
        binary_mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    bounding_boxes: list[tuple[int, int, int, int]] = []

    for contour in contours:
        area = cv2.contourArea(contour)

        if area < config.min_contour_area:
            continue

        x, y, w, h = cv2.boundingRect(contour)
        bounding_boxes.append((x, y, w, h))

    return bounding_boxes


def _build_frame_diff_motion_boxes(
    gray,
    previous_gray,
    config: MotionConfig,
) -> list[tuple[int, int, int, int]]:
    """
    Compare the current grayscale frame against the previous one and return
    bounding boxes for relevant motion areas.
    """

    frame_delta = cv2.absdiff(previous_gray, gray)

    _, threshold = cv2.threshold(
        frame_delta,
        config.motion_threshold,
        255,
        cv2.THRESH_BINARY,
    )

    return _find_motion_boxes_from_binary_mask(
        binary_mask=threshold,
        config=config,
    )


def _build_mog2_motion_boxes(
    gray,
    background_subtractor,
    config: MotionConfig,
) -> list[tuple[int, int, int, int]]:
    """
    Use MOG2 background subtraction to detect foreground/motion areas.

    MOG2 can mark shadows as gray values around 127. We threshold at 200 to keep
    strong foreground pixels only.
    """

    foreground_mask = background_subtractor.apply(
        gray,
        learningRate=config.mog2_learning_rate,
    )

    _, foreground_mask = cv2.threshold(
        foreground_mask,
        200,
        255,
        cv2.THRESH_BINARY,
    )

    return _find_motion_boxes_from_binary_mask(
        binary_mask=foreground_mask,
        config=config,
    )


def _draw_motion_overlay(
    frame,
    bounding_boxes: list[tuple[int, int, int, int]],
    motion_detected: bool,
    method: str,
) -> None:
    """
    Draw bounding boxes and motion label over the output frame.
    """

    for x, y, w, h in bounding_boxes:
        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            (0, 255, 0),
            2,
        )

    label = "MOTION" if motion_detected else "NO MOTION"

    cv2.putText(
        frame,
        label,
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0) if motion_detected else (255, 255, 255),
        2,
    )

    cv2.putText(
        frame,
        f"method={method}",
        (20, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
    )


def _validate_config(config: MotionConfig) -> None:
    """
    Validate detector configuration.
    """

    valid_methods = {"frame_diff", "mog2"}

    if config.method not in valid_methods:
        raise ValueError(
            f"Invalid motion detection method: {config.method}. "
            f"Expected one of: {sorted(valid_methods)}"
        )

    if config.fps_sample <= 0:
        raise ValueError("fps_sample must be greater than 0")

    if config.resolution_width <= 0:
        raise ValueError("resolution_width must be greater than 0")


def detect_motion(
    video_path: str | Path,
    config: MotionConfig,
    output_video_path: str | Path | None = None,
) -> dict[str, Any]:
    """
    Detect motion in a video using classic computer vision.

    Supported methods:
    - frame_diff
    - mog2
    """

    _validate_config(config)

    video_path = Path(video_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    source_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    frame_interval = max(int(round(source_fps / config.fps_sample)), 1)
    effective_processed_fps = source_fps / frame_interval

    max_event_gap_frames = max(
        int(round(config.event_merge_gap_seconds * effective_processed_fps)),
        1,
    )

    previous_gray = None
    previous_motion = False

    in_motion_event = False
    no_motion_gap_frames = 0

    total_frames_read = 0
    processed_frames = 0
    motion_frames = 0

    raw_motion_events = 0
    motion_events = 0

    total_processing_ms = 0.0

    writer = None

    background_subtractor = None

    if config.method == "mog2":
        background_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=config.mog2_history,
            varThreshold=config.mog2_var_threshold,
            detectShadows=config.mog2_detect_shadows,
        )

    if output_video_path:
        output_video_path = Path(output_video_path)
        output_video_path.parent.mkdir(parents=True, exist_ok=True)

    while True:
        ok, frame = cap.read()

        if not ok:
            break

        total_frames_read += 1

        should_process = (total_frames_read - 1) % frame_interval == 0

        if not should_process:
            continue

        start_time = perf_counter()

        resized = _resize_frame(frame, config.resolution_width)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

        blur_kernel = _ensure_odd_kernel(config.blur_kernel)
        gray = cv2.GaussianBlur(gray, (blur_kernel, blur_kernel), 0)

        bounding_boxes: list[tuple[int, int, int, int]] = []

        if config.method == "frame_diff":
            if previous_gray is not None:
                bounding_boxes = _build_frame_diff_motion_boxes(
                    gray=gray,
                    previous_gray=previous_gray,
                    config=config,
                )

        elif config.method == "mog2":
            if background_subtractor is None:
                raise RuntimeError("MOG2 background subtractor was not initialized.")

            bounding_boxes = _build_mog2_motion_boxes(
                gray=gray,
                background_subtractor=background_subtractor,
                config=config,
            )

            # MOG2 needs a few frames to learn the background.
            if processed_frames < config.mog2_warmup_frames:
                bounding_boxes = []

        motion_detected = len(bounding_boxes) > 0

        if motion_detected:
            motion_frames += 1

            # Raw events: every transition from NO MOTION to MOTION.
            if not previous_motion:
                raw_motion_events += 1

            # Smoothed events: merge motion events separated by a short gap.
            if not in_motion_event:
                motion_events += 1
                in_motion_event = True

            no_motion_gap_frames = 0

        else:
            if in_motion_event:
                no_motion_gap_frames += 1

                if no_motion_gap_frames > max_event_gap_frames:
                    in_motion_event = False
                    no_motion_gap_frames = 0

        previous_motion = motion_detected
        previous_gray = gray
        processed_frames += 1

        elapsed_ms = (perf_counter() - start_time) * 1000
        total_processing_ms += elapsed_ms

        if output_video_path:
            if writer is None:
                height, width = resized.shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                writer = cv2.VideoWriter(
                    str(output_video_path),
                    fourcc,
                    max(effective_processed_fps, 1),
                    (width, height),
                )

            _draw_motion_overlay(
                frame=resized,
                bounding_boxes=bounding_boxes,
                motion_detected=motion_detected,
                method=config.method,
            )

            writer.write(resized)

    cap.release()

    if writer is not None:
        writer.release()

    avg_processing_ms = (
        total_processing_ms / processed_frames if processed_frames > 0 else 0.0
    )

    estimated_processing_fps = (
        1000 / avg_processing_ms if avg_processing_ms > 0 else 0.0
    )

    return {
        "video": {
            "path": str(video_path),
            "source_fps": source_fps,
            "source_frame_count": source_frame_count,
            "frames_read": total_frames_read,
            "frame_interval": frame_interval,
            "effective_processed_fps": round(effective_processed_fps, 4),
        },
        "config": asdict(config),
        "metrics": {
            "processed_frames": processed_frames,
            "motion_frames": motion_frames,
            "raw_motion_events": raw_motion_events,
            "motion_events": motion_events,
            "avg_processing_ms": round(avg_processing_ms, 4),
            "estimated_processing_fps": round(estimated_processing_fps, 2),
        },
        "output": {
            "video_path": str(output_video_path) if output_video_path else None,
        },
    }
