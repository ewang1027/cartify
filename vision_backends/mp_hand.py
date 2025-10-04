#!/usr/bin/env python3
"""
Overlay MediaPipe Hand Landmarker keypoints on an input image.

Requirements:
  pip install mediapipe opencv-python

Example:
  python hand_overlay.py --image path/to/photo.jpg
"""
import argparse
import os
import sys
import urllib.request
from pathlib import Path

import cv2
import numpy as np

from mediapipe import Image, ImageFormat

# MediaPipe Tasks (Hand Landmarker)
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode

# We'll reuse the canonical hand connections from the Solutions API.
from mediapipe.python.solutions.hands import HAND_CONNECTIONS


DEFAULT_MODEL_URL = (
    # Public model asset published by MediaPipe (float16 variant).
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
DEFAULT_MODEL_PATH = "hand_landmarker.task"


def ensure_model(model_path: str, model_url: str = DEFAULT_MODEL_URL) -> str:
    """Ensure the model file exists locally; download if missing."""
    p = Path(model_path)
    if p.exists():
        return str(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    print(f"[info] downloading Hand Landmarker model to {p} ...", file=sys.stderr)
    urllib.request.urlretrieve(model_url, p)
    return str(p)


def mp_image_from_bgr(bgr: np.ndarray):
    """Convert OpenCV BGR image to MediaPipe Image (SRGB)."""
    # MediaPipe Tasks expect SRGB (i.e., RGB byte array).
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return Image(image_format=ImageFormat.SRGB, data=rgb)


def draw_landmarks(
    bgr: np.ndarray,
    hand_landmarks_list,
    handedness_list,
    circle_radius: int = 3,
    thickness: int = 2,
):
    """
    Draw 21 keypoints and connections for each detected hand.
    Uses pixel coordinates (scaled from normalized landmarks).
    """
    h, w = bgr.shape[:2]

    # Convert connections (set of pairs) to list for iteration
    connections = list(HAND_CONNECTIONS)

    for hand_idx, landmarks in enumerate(hand_landmarks_list):
        # Choose a per-hand color in BGR (rotate through a small palette)
        palette = [(0, 255, 0), (255, 0, 0), (0, 200, 255), (200, 0, 255)]
        color = palette[hand_idx % len(palette)]

        # Scale normalized landmarks to image coordinates
        points = []
        for lm in landmarks:
            x = min(max(int(round(lm.x * w)), 0), w - 1)
            y = min(max(int(round(lm.y * h)), 0), h - 1)
            points.append((x, y))

        # Draw connections (the "skeleton")
        for a, b in connections:
            pa, pb = points[a], points[b]
            cv2.line(bgr, pa, pb, color, thickness, lineType=cv2.LINE_AA)

        # Draw keypoints
        for (x, y) in points:
            cv2.circle(bgr, (x, y), circle_radius, color, -1, lineType=cv2.LINE_AA)

        # Add handedness label near the wrist (landmark 0)
        label = ""
        if handedness_list and hand_idx < len(handedness_list):
            # Each handedness entry is a list of Classification; take top one.
            classif = handedness_list[hand_idx]
            if classif and len(classif) > 0:
                cat = classif[0]
                label = f"{cat.category_name} ({cat.score:.2f})"
        if label:
            x0, y0 = points[0]
            y_lbl = max(0, y0 - 10)
            cv2.putText(
                bgr, label, (x0 + 6, y_lbl),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA
            )

    return bgr


def run(image_path: str, model_path: str, output_path: str | None):
    # Load image
    bgr = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(f"Failed to read image: {image_path}")

    mp_img = mp_image_from_bgr(bgr)

    # Ensure model available
    model_path = ensure_model(model_path)

    # Configure landmarker
    options = HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=model_path),
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        running_mode=RunningMode.IMAGE,
    )

    with HandLandmarker.create_from_options(options) as landmarker:
        result = landmarker.detect(mp_img)

    # Draw results
    bgr_out = bgr.copy()
    bgr_out = draw_landmarks(
        bgr_out,
        hand_landmarks_list=result.hand_landmarks,
        handedness_list=result.handedness,
    )

    # Determine output path
    if not output_path:
        stem = Path(image_path).stem
        parent = Path(image_path).parent
        output_path = str(parent / f"{stem}_keypoints.png")

    ok = cv2.imwrite(output_path, bgr_out)
    if not ok:
        raise RuntimeError(f"Failed to write output image: {output_path}")

    print(f"[ok] saved: {output_path}")


def parse_args():
    ap = argparse.ArgumentParser(description="Overlay MediaPipe hand keypoints on an image.")
    ap.add_argument("--image", required=True, help="Path to input image")
    ap.add_argument("--model", default=DEFAULT_MODEL_PATH, help="Path to hand_landmarker.task")
    ap.add_argument("--output", default=None, help="Path to save output (default: <image>_keypoints.png)")
    return ap.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.image, args.model, args.output)
