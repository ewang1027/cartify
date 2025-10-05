from __future__ import annotations

import argparse
from typing import Sequence, Tuple, Union

import cv2
import numpy as np
from ultralytics import SAM
from ultralytics.engine.results import Results

DEFAULT_MODEL_PATH = "mobile_sam.pt"
WINDOW_NAME = "SAM Center Point"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a SAM model on a video stream using the frame center as the prompt."
    )
    parser.add_argument(
        "--source",
        type=str,
        default="0",
        help=(
            "Video source to open. Use an integer index for webcams (e.g. '0') or a "
            "file path / URL for prerecorded streams."
        ),
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL_PATH,
        help="Path to the SAM weights file.",
    )
    return parser.parse_args()


def resolve_source(source: str) -> Union[int, str]:
    if source.isdigit():
        return int(source)
    return source


def compute_center_point(frame: np.ndarray) -> Tuple[int, int]:
    height, width = frame.shape[:2]
    return width // 2, height // 2


def annotate_frame(frame: np.ndarray, results: Sequence[Results]) -> np.ndarray:
    output = frame.copy()
    if results:
        output = results[0].plot()
    return output


def run_stream(model_path: str, raw_source: str) -> None:
    video_source = resolve_source(raw_source)

    capture = cv2.VideoCapture(video_source)
    if not capture.isOpened():
        raise RuntimeError(f"Unable to open video source: {raw_source}")

    model = SAM(model_path)
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    print("Press 'q' to exit the stream window.")

    try:
        while True:
            success, frame = capture.read()
            if not success:
                print("[WARN] Failed to read frame from source; stopping stream.")
                break

            center_point = compute_center_point(frame)
            results = model.predict(
                frame,
                points=[list(center_point)],
                labels=[1],
                verbose=False,
            )

            annotated_frame = annotate_frame(frame, results)
            cv2.circle(annotated_frame, center_point, 5, (0, 255, 0), -1)

            cv2.imshow(WINDOW_NAME, annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    except KeyboardInterrupt:
        print("\nStream interrupted by user.")
    finally:
        capture.release()
        cv2.destroyAllWindows()


def main() -> None:
    args = parse_arguments()
    run_stream(model_path=args.model, raw_source=args.source)


if __name__ == "__main__":
    main()