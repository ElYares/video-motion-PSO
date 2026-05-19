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

    The objective is to keep these parameters simple because later PSO will
    optimize them automatically.
    """

    resolution_width: int = 640
    fps_sample: float = 12.0
    motion_threshold: int = 35
    blur_kernel: int = 5
    min_contour_area: int = 800
    dilate_iterations: int = 2


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


def detect_motion(
    video_path: str | Path,
    config: MotionConfig,
    output_video_path: str | Path | None = None,
) -> dict[str, Any]:
    """
    Detect motion in a video using classic computer vision.

    Pipeline:
    1. Read video.
    2. Sample frames based on fps_sample.
    3. Resize frame.
    4. Convert to grayscale.
    5. Apply blur.
    6. Compare current frame against previous frame.
    7. Threshold difference.
    8. Find contours.
    9. Count motion frames and motion events.
    """

    video_path = Path(video_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    source_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    frame_interval = max(int(round(source_fps / config.fps_sample)), 1)

    previous_gray = None
    previous_motion = False

    total_frames_read = 0
    processed_frames = 0
    motion_frames = 0
    motion_events = 0
    total_processing_ms = 0.0

    writer = None

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

        motion_detected = False
        bounding_boxes: list[tuple[int, int, int, int]] = []

        if previous_gray is not None:
            frame_delta = cv2.absdiff(previous_gray, gray)

            _, threshold = cv2.threshold(
                frame_delta,
                config.motion_threshold,
                255,
                cv2.THRESH_BINARY,
            )

            threshold = cv2.dilate(
                threshold,
                None,
                iterations=config.dilate_iterations,
            )

            contours, _ = cv2.findContours(
                threshold,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE,
            )

            for contour in contours:
                area = cv2.contourArea(contour)

                if area < config.min_contour_area:
                    continue

                x, y, w, h = cv2.boundingRect(contour)
                bounding_boxes.append((x, y, w, h))

            motion_detected = len(bounding_boxes) > 0

        if motion_detected:
            motion_frames += 1

            if not previous_motion:
                motion_events += 1

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
                    max(config.fps_sample, 1),
                    (width, height),
                )

            for x, y, w, h in bounding_boxes:
                cv2.rectangle(
                    resized,
                    (x, y),
                    (x + w, y + h),
                    (0, 255, 0),
                    2,
                )

            label = "MOTION" if motion_detected else "NO MOTION"
            cv2.putText(
                resized,
                label,
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0) if motion_detected else (255, 255, 255),
                2,
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
        },
        "config": asdict(config),
        "metrics": {
            "processed_frames": processed_frames,
            "motion_frames": motion_frames,
            "motion_events": motion_events,
            "avg_processing_ms": round(avg_processing_ms, 4),
            "estimated_processing_fps": round(estimated_processing_fps, 2),
        },
        "output": {
            "video_path": str(output_video_path) if output_video_path else None,
        },
    }
