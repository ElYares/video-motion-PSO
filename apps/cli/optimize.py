from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from core.motion.detector import MotionConfig, detect_motion


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run motion detection over a video file."
    )

    parser.add_argument(
        "--method",
        default="frame_diff",
        choices=["frame_diff", "mog2"],
        help="Motion detection method.",
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to input video.",
    )

    parser.add_argument(
        "--output-report",
        default="outputs/reports/motion_report.json",
        help="Path to output JSON report.",
    )

    parser.add_argument(
        "--output-video",
        default="outputs/videos/motion_detected.mp4",
        help="Path to annotated output video.",
    )

    parser.add_argument(
        "--resolution-width",
        type=int,
        default=640,
        help="Target frame width used for processing.",
    )

    parser.add_argument(
        "--fps-sample",
        type=float,
        default=12.0,
        help="How many FPS to process from the original video.",
    )

    parser.add_argument(
        "--motion-threshold",
        type=int,
        default=35,
        help="Pixel difference threshold for motion detection.",
    )

    parser.add_argument(
        "--blur-kernel",
        type=int,
        default=5,
        help="Gaussian blur kernel size. It should be odd.",
    )

    parser.add_argument(
        "--min-contour-area",
        type=int,
        default=800,
        help="Minimum contour area to count as relevant motion.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    report_path = Path(args.output_report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    output_video_path = Path(args.output_video)
    output_video_path.parent.mkdir(parents=True, exist_ok=True)

    config = MotionConfig(
        method=args.method,
        resolution_width=args.resolution_width,
        fps_sample=args.fps_sample,
        motion_threshold=args.motion_threshold,
        blur_kernel=args.blur_kernel,
        min_contour_area=args.min_contour_area,
    )

    result = detect_motion(
        video_path=args.input,
        config=config,
        output_video_path=output_video_path,
    )

    report_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nMotion detection completed.")
    print(f"Report: {report_path}")
    print(f"Annotated video: {output_video_path}")

    print("\nMetrics:")
    print(json.dumps(result["metrics"], indent=2))


if __name__ == "__main__":
    main()
