from __future__ import annotations

import argparse
from typing import Sequence, Union

import cv2
import numpy as np
from ultralytics import YOLO
from ultralytics.engine.results import Results

DEFAULT_MODEL_PATH = "yolov8m-worldv2.pt"
CLASS_PROMPTS = ['phone', 'can', 'bottle', 'candy']
WINDOW_NAME = "YOLO-World Product"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a YOLO-World model on a video stream and display detections."
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
        help="Path to the YOLO-World weights file.",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.25,
        help="Confidence threshold for filtering detections (0.0 - 1.0).",
    )
    return parser.parse_args()


def resolve_source(source: str) -> Union[int, str]:
    if source.isdigit():
        return int(source)
    return source


def validate_confidence(confidence: float) -> float:
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("Confidence must be between 0.0 and 1.0.")
    return confidence


def annotate_frame(frame: np.ndarray, results: Sequence[Results]) -> np.ndarray:
    if not results:
        return frame
    annotated_frame: np.ndarray = results[0].plot()
    return annotated_frame


def run_stream(model_path: str, raw_source: str, confidence: float) -> None:
    validated_confidence = validate_confidence(confidence)
    video_source = resolve_source(raw_source)

    capture = cv2.VideoCapture(video_source)
    if not capture.isOpened():
        raise RuntimeError(f"Unable to open video source: {raw_source}")

    model = YOLO(model_path)
    model.set_classes(CLASS_PROMPTS)
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    print("Press 'q' to exit the stream window.")

    try:
        while True:
            success, frame = capture.read()
            if not success:
                print("[WARN] Failed to read frame from source; stopping stream.")
                break

            results = model.predict(frame, conf=validated_confidence, verbose=False)
            annotated_frame = annotate_frame(frame, results)

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
    run_stream(model_path=args.model, raw_source=args.source, confidence=args.confidence)


if __name__ == "__main__":
    main()