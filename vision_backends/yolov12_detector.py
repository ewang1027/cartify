"""Track phones, mice, and bottles in a video using an Ultralytics YOLOv12 model."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence, Tuple, Union

import cv2
import numpy as np
from ultralytics import YOLO
from ultralytics.engine.results import Results

TARGET_CLASS_NAMES: Tuple[str, ...] = ("cell phone", "mouse", "bottle")
DEFAULT_OUTPUT_SUFFIX: str = "_tracked.mp4"
DEFAULT_TRACKER_CONFIG: str = "bytetrack.yaml"


@dataclass(frozen=True)
class TrackedDetection:
    """Structured representation of a tracked detection."""

    class_name: str
    confidence: float
    track_id: Optional[int]
    xyxy: Tuple[float, float, float, float]
    xywh: Tuple[float, float, float, float]
    mask: Optional[np.ndarray]
    mask_polygons: Optional[List[np.ndarray]]
    input_shape: Optional[Tuple[int, int]]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the tracking script."""

    parser = argparse.ArgumentParser(
        description="Run YOLOv12 tracking for cell phones, mice, and bottles on a video file.",
    )
    parser.add_argument(
        "video",
        nargs="?",
        type=Path,
        help="Path to the input video file.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="yolo11x-seg.pt",
        help="Path to the YOLOv12 checkpoint to load (default: %(default)s).",
    )
    parser.add_argument(
        "--output-video",
        type=Path,
        default=None,
        help="Optional path for the annotated output video (default: <video>_tracked.mp4).",
    )
    parser.add_argument(
        "--camera-index",
        type=int,
        default=0,
        help="Camera index to use when no video path is provided (default: %(default)s).",
    )
    parser.add_argument(
        "--tracker-config",
        type=str,
        default=None,
        help="Optional tracker configuration YAML (default: Ultralytics ByteTrack).",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.2,
        help="Confidence threshold for filtering predictions (default: %(default)s).",
    )
    parser.add_argument(
        "--device",
        type=str,
        default='mps',
        help="Torch device for inference (e.g., 'cpu', 'cuda:0').",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Optional cap on the number of frames to process.",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Display annotated frames during processing.",
    )
    parser.add_argument(
        "--line-thickness",
        type=int,
        default=5,
        help="Thickness of bounding box edges in pixels (default: %(default)s).",
    )
    parser.add_argument(
        "--retina-masks",
        dest="retina_masks",
        action="store_true",
        help="Enable high-resolution segmentation masks (Ultralytics retina masks).",
    )
    parser.add_argument(
        "--no-retina-masks",
        dest="retina_masks",
        action="store_false",
        help="Disable high-resolution segmentation masks.",
    )
    parser.set_defaults(retina_masks=True)
    return parser.parse_args()


def resolve_output_path(video_path: Optional[Path], output_path: Optional[Path]) -> Path:
    """Derive the output path for the annotated video."""

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path
    if video_path is None:
        raise ValueError("Unable to derive default output path without a video path.")
    default_path: Path = video_path.with_name(f"{video_path.stem}{DEFAULT_OUTPUT_SUFFIX}")
    default_path.parent.mkdir(parents=True, exist_ok=True)
    return default_path


def probe_video_geometry(video_path: Path) -> Tuple[float, Tuple[int, int]]:
    """Fetch FPS and frame dimensions for a video."""

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise FileNotFoundError(f"Failed to open video at {video_path}")

    fps: float = float(capture.get(cv2.CAP_PROP_FPS))
    width: int = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height: int = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    capture.release()

    if width <= 0 or height <= 0:
        raise ValueError("Unable to determine video frame size.")
    if fps <= 0.0:
        fps = 30.0
    return fps, (width, height)


def create_video_writer(output_path: Path, fps: float, frame_size: Tuple[int, int]) -> cv2.VideoWriter:
    """Instantiate an OpenCV video writer for MP4 output."""

    fourcc: int = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, frame_size)
    if not writer.isOpened():
        raise RuntimeError(f"Failed to open video writer at {output_path}")
    return writer


def color_for_track(track_id: Optional[int], class_index: int) -> Tuple[int, int, int]:
    """Produce a deterministic color for a track, falling back to class-based hues."""

    if track_id is None:
        base_colors: Tuple[Tuple[int, int, int], ...] = (
            (0, 165, 255),
            (0, 255, 0),
            (255, 0, 0),
        )
        return base_colors[class_index % len(base_colors)]
    unique_id: int = int(track_id)
    r: int = (37 * unique_id) % 256
    g: int = (17 * unique_id) % 256
    b: int = (29 * unique_id) % 256
    return (int((r + 96) % 256), int((g + 96) % 256), int((b + 96) % 256))


def extract_tracked_detections(result: Results, target_names: Sequence[str]) -> List[TrackedDetection]:
    """Filter tracked detections to the requested class names."""

    boxes = result.boxes
    if boxes is None:
        return []

    target_set = set(target_names)
    class_indices: List[int] = boxes.cls.int().tolist() if boxes.cls is not None else []
    confidences: List[float] = boxes.conf.tolist() if boxes.conf is not None else []
    xyxy_list: List[List[float]] = boxes.xyxy.tolist() if boxes.xyxy is not None else []
    xywh_list: List[List[float]] = boxes.xywh.tolist() if boxes.xywh is not None else []

    track_ids: List[Optional[int]]
    if boxes.id is not None:
        track_ids = [int(identifier) for identifier in boxes.id.int().tolist()]
    else:
        track_ids = [None for _ in class_indices]

    mask_list: List[Optional[np.ndarray]] = [None for _ in class_indices]
    polygon_list: List[Optional[List[np.ndarray]]] = [None for _ in class_indices]
    mask_input_shapes: List[Optional[Tuple[int, int]]] = [None for _ in class_indices]
    masks = getattr(result, "masks", None)
    if masks is not None:
        mask_data = getattr(masks, "data", None)
        mask_xy = getattr(masks, "xy", None)
        mask_input_size = getattr(masks, "im", None)
        mask_input_shape: Optional[Tuple[int, int]]
        if mask_input_size is not None and len(mask_input_size) >= 2:
            mask_input_shape = (int(mask_input_size[0]), int(mask_input_size[1]))
        else:
            mask_input_shape = None

        if mask_data is not None:
            mask_count: int = min(len(mask_data), len(mask_list))
            for index in range(mask_count):
                mask_tensor = mask_data[index]
                mask_array = (
                    mask_tensor.detach().cpu().numpy()
                    if hasattr(mask_tensor, "detach")
                    else np.asarray(mask_tensor)
                )
                mask_list[index] = mask_array.astype(np.float32)
                mask_input_shapes[index] = mask_input_shape

        if mask_xy is not None:
            polygon_count: int = min(len(mask_xy), len(polygon_list))
            for index in range(polygon_count):
                polygons = mask_xy[index]
                polygon_arrays: List[np.ndarray] = []
                for polygon in polygons:
                    polygon_array = (
                        polygon.detach().cpu().numpy()
                        if hasattr(polygon, "detach")
                        else np.asarray(polygon)
                    )
                    if polygon_array.ndim == 2 and polygon_array.shape[1] == 2:
                        polygon_arrays.append(polygon_array.astype(np.float32))
                if polygon_arrays:
                    polygon_list[index] = polygon_arrays

    detections: List[TrackedDetection] = []
    for (
        cls_idx,
        confidence,
        xyxy_vals,
        xywh_vals,
        track_id,
        mask_array,
        mask_polygons,
        mask_shape,
    ) in zip(
        class_indices,
        confidences,
        xyxy_list,
        xywh_list,
        track_ids,
        mask_list,
        polygon_list,
        mask_input_shapes,
    ):
        class_name: str = result.names.get(int(cls_idx), str(cls_idx))
        if class_name not in target_set:
            continue
        detections.append(
            TrackedDetection(
                class_name=class_name,
                confidence=float(confidence),
                track_id=track_id,
                xyxy=tuple(float(value) for value in xyxy_vals),
                xywh=tuple(float(value) for value in xywh_vals),
                mask=mask_array,
                mask_polygons=mask_polygons,
                input_shape=mask_shape,
            ),
        )
    return detections


def annotate_frame(
    frame: np.ndarray,
    detections: Sequence[TrackedDetection],
    line_thickness: int,
) -> np.ndarray:
    """Draw tracked detections with labels onto a frame."""

    annotated: np.ndarray = frame.copy()
    frame_height: int = int(annotated.shape[0])
    frame_width: int = int(annotated.shape[1])

    for index, detection in enumerate(detections):
        color: Tuple[int, int, int] = color_for_track(
            track_id=detection.track_id,
            class_index=index,
        )
        x1, y1, x2, y2 = detection.xyxy

        if detection.mask_polygons:
            overlay: np.ndarray = annotated.copy()
            scaled_polygons: List[np.ndarray] = []
            for polygon in detection.mask_polygons:
                if polygon.size == 0:
                    continue
                polygon_int = polygon.astype(np.int32)
                cv2.fillPoly(overlay, [polygon_int], color)
                scaled_polygons.append(polygon_int)
            if scaled_polygons:
                alpha: float = 0.4
                annotated = cv2.addWeighted(annotated, 1.0 - alpha, overlay, alpha, 0)
                cv2.polylines(
                    annotated,
                    scaled_polygons,
                    isClosed=True,
                    color=color,
                    thickness=line_thickness,
                )
        elif detection.mask is not None and detection.mask.size > 0:
            mask_resized = cv2.resize(
                detection.mask,
                (frame_width, frame_height),
                interpolation=cv2.INTER_LINEAR,
            )
            mask_binary = mask_resized > 0.5
            if mask_binary.any():
                overlay = annotated.copy()
                overlay[mask_binary] = color
                alpha = 0.4
                annotated = cv2.addWeighted(annotated, 1.0 - alpha, overlay, alpha, 0)

                mask_uint8 = (mask_binary.astype(np.uint8) * 255)
                contours, _ = cv2.findContours(
                    mask_uint8,
                    cv2.RETR_EXTERNAL,
                    cv2.CHAIN_APPROX_SIMPLE,
                )
                cv2.drawContours(annotated, contours, -1, color, line_thickness)
        else:
            top_left = (int(round(x1)), int(round(y1)))
            bottom_right = (int(round(x2)), int(round(y2)))
            cv2.rectangle(annotated, top_left, bottom_right, color, thickness=line_thickness)

        track_label: str = (
            f"{detection.class_name}#{detection.track_id}"
            if detection.track_id is not None
            else detection.class_name
        )
        label: str = f"{track_label} {detection.confidence:.2f}"
        text_origin = (int(round(x1)), max(0, int(round(y1)) - 8))
        cv2.putText(
            annotated,
            label,
            text_origin,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            1,
            cv2.LINE_AA,
        )
    return annotated


def iter_tracking_results(
    model: YOLO,
    source: Union[int, Path, str],
    conf: float,
    device: Optional[str],
    tracker_config: Optional[str],
    retina_masks: bool,
) -> Iterator[Results]:
    """Yield tracking results for each frame in the video."""

    yield from model.track(
        source=str(source) if isinstance(source, Path) else source,
        conf=conf,
        device=device,
        tracker=tracker_config or DEFAULT_TRACKER_CONFIG,
        stream=True,
        persist=True,
        verbose=False,
        retina_masks=retina_masks,
    )


def main() -> None:
    """Entry point for YOLOv12 tracking."""

    args = parse_args()
    video_path: Optional[Path] = args.video
    camera_index: int = int(args.camera_index)

    if video_path is not None and not video_path.exists():
        raise FileNotFoundError(f"Input video not found at {video_path}")

    output_path: Optional[Path]
    fps: Optional[float]
    frame_size: Optional[Tuple[int, int]]
    writer: Optional[cv2.VideoWriter]

    if video_path is not None:
        output_path = resolve_output_path(video_path=video_path, output_path=args.output_video)
        fps, frame_size = probe_video_geometry(video_path=video_path)
        writer = create_video_writer(output_path=output_path, fps=fps, frame_size=frame_size)
        source: Union[int, Path] = video_path
    else:
        source = camera_index
        output_path = (
            resolve_output_path(video_path=None, output_path=args.output_video)
            if args.output_video is not None
            else None
        )
        fps = None
        frame_size = None
        writer = None

    print(f"Loading YOLOv12 model from {args.model}")
    model = YOLO(args.model)

    try:
        for frame_index, result in enumerate(
            iter_tracking_results(
                model=model,
                source=source,
                conf=args.conf,
                device=args.device,
                tracker_config=args.tracker_config,
                retina_masks=bool(args.retina_masks),
            ),
        ):
            if args.max_frames is not None and frame_index >= args.max_frames:
                print("Reached max frame limit; stopping early.")
                break

            if result.orig_img is None:
                continue

            detections: List[TrackedDetection] = extract_tracked_detections(
                result=result,
                target_names=TARGET_CLASS_NAMES,
            )

            default_identity: str = (
                str(video_path)
                if video_path is not None
                else f"camera:{camera_index}"
            )
            frame_identity: str = result.path or default_identity
            if detections:
                print(f"Frame {frame_index} ({frame_identity}): {len(detections)} target tracks")
                for detection in detections:
                    x_center, y_center, width, height = detection.xywh
                    print(
                        f"  - {detection.class_name}"
                        f" track_id={detection.track_id if detection.track_id is not None else 'N/A'}"
                        f" conf={detection.confidence:.3f}"
                        f" xyxy={detection.xyxy}"
                        f" xywh=({x_center:.1f}, {y_center:.1f}, {width:.1f}, {height:.1f})",
                    )
            else:
                print(f"Frame {frame_index} ({frame_identity}): no target tracks")

            annotated: np.ndarray = annotate_frame(
                frame=result.orig_img,
                detections=detections,
                line_thickness=args.line_thickness,
            )
            if output_path is not None:
                if writer is None:
                    if frame_size is None:
                        height: int = int(annotated.shape[0])
                        width: int = int(annotated.shape[1])
                        frame_size = (width, height)
                    fps = fps or 30.0
                    writer = create_video_writer(
                        output_path=output_path,
                        fps=fps,
                        frame_size=frame_size,
                    )
                writer.write(annotated)

            if args.show:
                cv2.imshow("YOLOv12 Tracking", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    print("Stopping due to 'q' keypress.")
                    break
    finally:
        if writer is not None:
            writer.release()
        if args.show:
            cv2.destroyAllWindows()

    if output_path is not None:
        print(f"Annotated video saved to {output_path}")


if __name__ == "__main__":
    main()


