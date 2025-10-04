#!/usr/bin/env python3
"""Process a video at 1 FPS with Roboflow detections, OCR, hand keypoints, depth, and Gemini extraction."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import coremltools as ct
import cv2
import numpy as np
from PIL import Image

from google import genai
from inference_sdk import InferenceHTTPClient
from mp_hand import (
    DEFAULT_MODEL_PATH as HAND_DEFAULT_MODEL_PATH,
    draw_landmarks,
    ensure_model as ensure_hand_model,
    mp_image_from_bgr,
)
from rf_sku_image_gemini import (
    DEFAULT_CROPS_DIR,
    ROBOFLOW_WORKFLOW_ID,
    ROBOFLOW_WORKSPACE,
    OCRWord,
    detection_to_bbox,
    extract_bounding_boxes,
    load_ocr_words,
    process_detections,
)


@dataclass(frozen=True)
class FrameTaskResult:
    """Container for the parallel tasks tied to a single frame."""

    workflow_result: Any
    ocr_words: List[OCRWord]
    hand_landmarks: Any
    depth_map: np.ndarray


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Process video frames at 1 FPS with detections, hands, depth, and Gemini extraction.",
    )
    parser.add_argument("video", type=Path, help="Path to the source video file.")
    parser.add_argument(
        "--output-video",
        type=Path,
        default='output.mp4',
        help="Output path for the annotated 1 FPS video (default: <video>_annotated.mp4)",
    )
    parser.add_argument(
        "--crops-dir",
        type=Path,
        default=DEFAULT_CROPS_DIR,
        help="Directory to store cropped product images (default: %(default)s)",
    )
    parser.add_argument(
        "--depth-model",
        type=Path,
        default=Path("models/DepthAnythingV2SmallF16.mlpackage"),
        help="Path to the Core ML depth model package.",
    )
    parser.add_argument(
        "--hand-model",
        type=Path,
        default=Path(HAND_DEFAULT_MODEL_PATH),
        help="Path to the MediaPipe hand landmark model file.",
    )
    return parser.parse_args()


def load_depth_model(model_path: Path) -> ct.models.MLModel:
    """Load the Core ML depth model once."""

    if not model_path.exists():
        raise FileNotFoundError(f"Depth model not found at {model_path}")
    return ct.models.MLModel(str(model_path))


def infer_depth_map(mlmodel: ct.models.MLModel, frame_bgr: np.ndarray) -> np.ndarray:
    """Run depth inference on a BGR frame and return a float32 depth array."""

    image_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    input_spec = mlmodel.get_spec().description.input[0]
    image_type = input_spec.type.imageType
    width = int(image_type.width) if image_type.width else image_rgb.shape[1]
    height = int(image_type.height) if image_type.height else image_rgb.shape[0]
    pil_image = Image.fromarray(image_rgb).resize((width, height), Image.BILINEAR)
    input_name = input_spec.name
    prediction = mlmodel.predict({input_name: pil_image})
    output_name = mlmodel.get_spec().description.output[0].name
    depth_array = np.array(prediction[output_name], dtype=np.float32)
    if depth_array.size != width * height:
        depth_array = np.squeeze(depth_array)
    depth_array = depth_array.reshape((height, width))
    return depth_array


def resize_depth_map(depth_map: np.ndarray, target_shape: Tuple[int, int]) -> np.ndarray:
    """Resize the depth map to match the video frame size using bilinear interpolation."""

    target_width, target_height = target_shape
    depth_resized = cv2.resize(depth_map, (target_width, target_height), interpolation=cv2.INTER_LINEAR)
    return depth_resized


def depth_to_green_red_overlay(depth_map: np.ndarray) -> np.ndarray:
    """Convert a depth map to a perceptually richer BGR overlay using percentile stretching."""

    finite_mask = np.isfinite(depth_map)
    if not np.any(finite_mask):
        normalized = np.zeros_like(depth_map, dtype=np.float32)
    else:
        finite_values = depth_map[finite_mask]
        lower = float(np.percentile(finite_values, 5.0))
        upper = float(np.percentile(finite_values, 95.0))

        if math.isclose(lower, upper, rel_tol=1e-6, abs_tol=1e-6):
            lower = float(np.min(finite_values))
            upper = float(np.max(finite_values))

        if math.isclose(lower, upper, rel_tol=1e-6, abs_tol=1e-6):
            normalized = np.zeros_like(depth_map, dtype=np.float32)
        else:
            clipped = np.clip(depth_map, lower, upper)
            normalized = (clipped - lower) / (upper - lower)

    normalized = np.nan_to_num(np.clip(normalized, 0.0, 1.0), copy=False)
    colormap_input = np.round(normalized * 255.0).astype(np.uint8)
    overlay = cv2.applyColorMap(colormap_input, cv2.COLORMAP_INFERNO)
    if not np.all(finite_mask):
        overlay[~finite_mask] = 0
    return overlay


def draw_roboflow_boxes(frame: np.ndarray, detections: Sequence[Dict[str, Any]]) -> None:
    """Draw Roboflow detections on the frame."""

    height, width = frame.shape[:2]
    for detection in detections:
        bbox = detection_to_bbox(detection, height, width)
        if bbox is None:
            continue
        left, top, right, bottom = bbox
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 255), 2)
        label = str(detection.get("class", "product"))
        confidence = detection.get("confidence")
        if isinstance(confidence, (int, float)):
            label = f"{label} {confidence:.2f}"
        cv2.putText(
            frame,
            label,
            (left, max(0, top - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )


def draw_ocr_boxes(frame: np.ndarray, words: Sequence[OCRWord]) -> None:
    """Draw OCR word bounding boxes and labels on the frame."""

    for word in words:
        left = int(word["left"])
        top = int(word["top"])
        right = int(word["right"])
        bottom = int(word["bottom"])
        cv2.rectangle(frame, (left, top), (right, bottom), (255, 255, 0), 1)
        text = str(word.get("text", ""))
        if text:
            cv2.putText(
                frame,
                text,
                (left, max(0, top - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (255, 255, 0),
                1,
                cv2.LINE_AA,
            )


def detect_hands(frame_bgr: np.ndarray, hand_model_path: Path) -> Any:
    """Detect hand landmarks using MediaPipe HandLandmarker."""

    model_path = ensure_hand_model(str(hand_model_path))
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    mp_image = mp_image_from_bgr(frame_bgr)
    options = vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=model_path),
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        running_mode=vision.RunningMode.IMAGE,
    )
    with vision.HandLandmarker.create_from_options(options) as landmarker:
        return landmarker.detect(mp_image)


async def run_parallel_tasks(
    inference_client: InferenceHTTPClient,
    temp_image_path: Path,
    frame_bgr: np.ndarray,
    hand_model_path: Path,
    depth_model: ct.models.MLModel,
) -> FrameTaskResult:
    """Run Roboflow, OCR, hand detection, and depth inference in parallel."""

    workflow_task = asyncio.to_thread(
        inference_client.run_workflow,
        workspace_name=ROBOFLOW_WORKSPACE,
        workflow_id=ROBOFLOW_WORKFLOW_ID,
        images={"image": str(temp_image_path)},
        use_cache=True,
    )
    ocr_task = asyncio.to_thread(load_ocr_words, temp_image_path)
    hand_task = asyncio.to_thread(detect_hands, frame_bgr.copy(), hand_model_path)
    depth_task = asyncio.to_thread(infer_depth_map, depth_model, frame_bgr.copy())

    workflow_result, ocr_words, hand_result, depth_map = await asyncio.gather(
        workflow_task,
        ocr_task,
        hand_task,
        depth_task,
    )

    return FrameTaskResult(
        workflow_result=workflow_result,
        ocr_words=ocr_words,
        hand_landmarks=hand_result,
        depth_map=depth_map,
    )


def overlay_results_on_frame(
    frame_bgr: np.ndarray,
    detections: Sequence[Dict[str, Any]],
    ocr_words: Sequence[OCRWord],
    hand_result: Any,
    depth_map: np.ndarray,
) -> np.ndarray:
    """Create the annotated frame with all overlays applied."""

    overlay_frame = frame_bgr.copy()
    depth_resized = resize_depth_map(depth_map, (overlay_frame.shape[1], overlay_frame.shape[0]))
    depth_overlay = depth_to_green_red_overlay(depth_resized)
    overlay_frame = cv2.addWeighted(overlay_frame, 0.8, depth_overlay, 0.2, 0.0)
    draw_roboflow_boxes(overlay_frame, detections)
    draw_ocr_boxes(overlay_frame, ocr_words)
    if hand_result and getattr(hand_result, "hand_landmarks", None):
        draw_landmarks(
            overlay_frame,
            hand_result.hand_landmarks,
            getattr(hand_result, "handedness", []),
        )
    return overlay_frame


def compute_sampled_frame_indices(total_frames: int, fps: float) -> List[int]:
    """Compute frame indices corresponding to one frame per second."""

    if fps <= 0.0:
        return list(range(0, total_frames, 1))
    total_seconds = int(math.floor(total_frames / fps))
    indices = {min(int(round(second * fps)), total_frames - 1) for second in range(total_seconds + 1)}
    return sorted(indices)


async def process_frame(
    frame_bgr: np.ndarray,
    frame_index: int,
    timestamp_s: float,
    inference_client: InferenceHTTPClient,
    gemini_client: Any,
    crops_dir: Path,
    depth_model: ct.models.MLModel,
    hand_model_path: Path,
) -> np.ndarray:
    """Process a single sampled frame and return the annotated image."""

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        temp_path = Path(tmp.name)
        success = cv2.imwrite(str(temp_path), frame_bgr)
    if not success:
        temp_path.unlink(missing_ok=True)
        raise RuntimeError("Failed to write temporary frame image")

    try:
        task_result = await run_parallel_tasks(
            inference_client,
            temp_path,
            frame_bgr,
            hand_model_path,
            depth_model,
        )
        depth_map_raw = task_result.depth_map
        finite_mask = np.isfinite(depth_map_raw)
        if np.any(finite_mask):
            finite_depth = depth_map_raw[finite_mask]
            depth_stats = {
                "frame_index": frame_index,
                "timestamp_seconds": timestamp_s,
                "depth_min": float(np.min(finite_depth)),
                "depth_max": float(np.max(finite_depth)),
                "depth_mean": float(np.mean(finite_depth)),
                "depth_p05": float(np.percentile(finite_depth, 5.0)),
                "depth_p95": float(np.percentile(finite_depth, 95.0)),
            }
        else:
            depth_stats = {
                "frame_index": frame_index,
                "timestamp_seconds": timestamp_s,
                "depth_all_nan": True,
            }
        print(json.dumps({"depth_stats": depth_stats}, ensure_ascii=False))
        detections = extract_bounding_boxes(task_result.workflow_result)
        annotated_frame = overlay_results_on_frame(
            frame_bgr,
            detections,
            task_result.ocr_words,
            task_result.hand_landmarks,
            task_result.depth_map,
        )

        gemini_results = await process_detections(
            temp_path,
            detections,
            gemini_client,
            crops_dir,
            task_result.ocr_words,
        )
        for result in gemini_results:
            enriched = dict(result)
            enriched.setdefault("frame_index", frame_index)
            enriched.setdefault("timestamp_seconds", timestamp_s)
            print(json.dumps(enriched, ensure_ascii=False))

        return annotated_frame
    finally:
        temp_path.unlink(missing_ok=True)


async def process_video(
    video_path: Path,
    output_video_path: Path,
    crops_dir: Path,
    depth_model_path: Path,
    hand_model_path: Path,
) -> None:
    """Main video processing coroutine."""

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    gemini_api_key = (
        os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
    )
    if not gemini_api_key:
        raise EnvironmentError("GOOGLE_API_KEY or GEMINI_API_KEY environment variable must be set")
    roboflow_api_key = os.environ.get("ROBOFLOW_API_KEY")
    if not roboflow_api_key:
        raise EnvironmentError("ROBOFLOW_API_KEY environment variable must be set")

    inference_client = InferenceHTTPClient(
        api_url="https://serverless.roboflow.com",
        api_key=roboflow_api_key,
    )
    gemini_client = genai.Client(api_key=gemini_api_key)
    depth_model = load_depth_model(depth_model_path)

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Failed to open video: {video_path}")

    fps = float(capture.get(cv2.CAP_PROP_FPS)) or 30.0
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    sampled_indices = compute_sampled_frame_indices(total_frames, fps)
    sampled_set = set(sampled_indices)

    _, first_frame = capture.read()
    if first_frame is None:
        capture.release()
        raise RuntimeError("Video has no frames")

    frame_height, frame_width = first_frame.shape[:2]
    video_writer = cv2.VideoWriter(
        str(output_video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        1.0,
        (frame_width, frame_height),
    )
    capture.set(cv2.CAP_PROP_POS_FRAMES, 0)

    try:
        for frame_index in range(total_frames):
            success, frame = capture.read()
            if not success or frame is None:
                break
            if frame_index not in sampled_set:
                continue
            timestamp_seconds = frame_index / fps if fps > 0 else 0.0
            annotated = await process_frame(
                frame,
                frame_index,
                timestamp_seconds,
                inference_client,
                gemini_client,
                crops_dir,
                depth_model,
                hand_model_path,
            )
            video_writer.write(annotated)
    finally:
        capture.release()
        video_writer.release()


def resolve_output_path(video_path: Path, output_arg: Optional[Path]) -> Path:
    """Resolve the output video path given an optional argument."""

    if output_arg is not None:
        return output_arg
    return video_path.with_name(f"{video_path.stem}_annotated.mp4")


def main() -> None:
    args = parse_args()
    output_video_path = resolve_output_path(args.video, args.output_video)
    args.crops_dir.mkdir(parents=True, exist_ok=True)
    asyncio.run(
        process_video(
            args.video.resolve(),
            output_video_path.resolve(),
            args.crops_dir.resolve(),
            args.depth_model.resolve(),
            args.hand_model.resolve(),
        )
    )


if __name__ == "__main__":
    import os
    from google import genai

    main()

