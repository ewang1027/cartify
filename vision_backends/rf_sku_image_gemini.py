import argparse
import asyncio
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
from google import genai
from google.genai import types
from inference_sdk import InferenceHTTPClient

from dotenv import load_dotenv

load_dotenv()

ROBOFLOW_WORKSPACE: str = "orbifold-ai"
ROBOFLOW_WORKFLOW_ID: str = "detect-count-and-visualize-3"
MODEL_NAME: str = "gemini-flash-lite-latest"
DEFAULT_CROPS_DIR: Path = Path(__file__).resolve().parent / "crops"


def extract_bounding_boxes(workflow_result: Any) -> List[Dict[str, Any]]:
    boxes: List[Dict[str, Any]] = []
    items: List[Any] = workflow_result if isinstance(workflow_result, list) else [workflow_result]

    for item in items:
        if not isinstance(item, Dict):
            continue

        direct_predictions: Any = item.get("predictions")

        if isinstance(direct_predictions, dict):
            inner_predictions: Any = direct_predictions.get("predictions")
            if isinstance(inner_predictions, list):
                boxes.extend(det for det in inner_predictions if isinstance(det, dict))
        elif isinstance(direct_predictions, list):
            boxes.extend(det for det in direct_predictions if isinstance(det, dict))

        nodes: Any = item.get("nodes")
        if isinstance(nodes, list):
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                node_output: Any = node.get("output")
                if not isinstance(node_output, dict):
                    continue
                node_predictions: Any = node_output.get("predictions")
                if isinstance(node_predictions, list):
                    boxes.extend(det for det in node_predictions if isinstance(det, dict))

    return boxes


def detection_to_bbox(
    detection: Dict[str, Any],
    image_height: int,
    image_width: int,
) -> Optional[Tuple[int, int, int, int]]:
    if {
        "left",
        "right",
        "top",
        "bottom",
    }.issubset(detection.keys()):
        left: int = int(detection.get("left", 0))
        top: int = int(detection.get("top", 0))
        right: int = int(detection.get("right", 0))
        bottom: int = int(detection.get("bottom", 0))
    else:
        width: float = float(detection.get("width", 0.0))
        height: float = float(detection.get("height", 0.0))
        x_center: float = float(detection.get("x", detection.get("left", 0.0)))
        y_center: float = float(detection.get("y", detection.get("top", 0.0)))

        left = int(round(x_center - (width / 2)))
        top = int(round(y_center - (height / 2)))
        right = int(round(x_center + (width / 2)))
        bottom = int(round(y_center + (height / 2)))

    left = max(0, min(left, image_width - 1))
    right = max(0, min(right, image_width - 1))
    top = max(0, min(top, image_height - 1))
    bottom = max(0, min(bottom, image_height - 1))

    if right <= left or bottom <= top:
        return None

    box_width: int = right - left
    box_height: int = bottom - top

    expand_x: int = int(round(box_width * 0.1))
    expand_y: int = int(round(box_height * 0.1))

    left = max(0, left - expand_x)
    right = min(image_width - 1, right + expand_x)
    top = max(0, top - expand_y)
    bottom = min(image_height - 1, bottom + expand_y)

    return left, top, right, bottom


def crop_detection(
    image: Any,
    bbox: Tuple[int, int, int, int],
) -> Optional[bytes]:
    left, top, right, bottom = bbox
    crop = image[top:bottom, left:right]

    if crop.size == 0:
        return None

    success, buffer = cv2.imencode(".png", crop)
    if not success:
        return None

    return buffer.tobytes()


def build_contents(image_bytes: bytes) -> List[types.Content]:
    prompt: str = (
        "You are an assistant that identifies retail products. "
        "Look at this cropped product image and respond with a JSON object containing "
        "two keys: product_name and brand."
    )

    return [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
            ],
        )
    ]


def parse_response_text(text: str) -> Dict[str, Any]:
    cleaned_text: str = text.strip()

    if cleaned_text.startswith("```"):
        cleaned_lines: List[str] = cleaned_text.splitlines()
        if len(cleaned_lines) >= 3:
            cleaned_lines = cleaned_lines[1:-1]
        cleaned_text = "\n".join(cleaned_lines).strip()

    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        return {
            "product_name": None,
            "brand": None,
            "raw_response": cleaned_text,
        }


def sanitize_filename_component(value: Any, fallback: str) -> str:
    raw_value: str = "" if value is None else str(value)
    sanitized: str = re.sub(r"[^A-Za-z0-9._ -]", "_", raw_value)
    sanitized = re.sub(r"\s+", " ", sanitized).strip(" ._-")
    return sanitized if sanitized else fallback


def build_unique_crop_path(brand: str, product_name: str, crops_dir: Path) -> Path:
    base_name: str = f"{brand} - {product_name}"
    candidate: Path = crops_dir / f"{base_name}.png"
    if not candidate.exists():
        return candidate

    counter: int = 1
    while True:
        candidate = crops_dir / f"{base_name} ({counter}).png"
        if not candidate.exists():
            return candidate
        counter += 1


async def call_gemini(
    client: genai.Client,
    image_bytes: bytes,
    detection_index: int,
) -> Dict[str, Any]:
    contents: List[types.Content] = build_contents(image_bytes)

    generate_content_config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=0),
        safety_settings=[
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="BLOCK_NONE",
            )
        ],
    )

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=MODEL_NAME,
        contents=contents,
        config=generate_content_config,
    )

    response_text: str = getattr(response, "text", "")

    if not response_text and hasattr(response, "candidates"):
        candidates: Any = getattr(response, "candidates", [])
        if candidates:
            first_candidate: Any = candidates[0]
            content: Any = getattr(first_candidate, "content", None)
            if content is not None:
                parts: Any = getattr(content, "parts", None)
                if isinstance(parts, list):
                    response_text = "".join(
                        part.text for part in parts if hasattr(part, "text")
                    )

    parsed: Dict[str, Any] = parse_response_text(response_text)
    parsed.setdefault("product_name", None)
    parsed.setdefault("brand", None)
    parsed["detection_index"] = detection_index

    return parsed


async def process_detections(
    image_path: Path,
    detections: List[Dict[str, Any]],
    gemini_client: genai.Client,
    crops_dir: Path,
) -> List[Dict[str, Any]]:
    image = cv2.imread(str(image_path))

    if image is None:
        raise FileNotFoundError(f"Failed to load image at {image_path}")

    image_height: int = int(image.shape[0])
    image_width: int = int(image.shape[1])

    tasks: List[asyncio.Task[Dict[str, Any]]] = []
    crops: Dict[int, bytes] = {}

    for index, detection in enumerate(detections):
        bbox: Optional[Tuple[int, int, int, int]] = detection_to_bbox(
            detection,
            image_height,
            image_width,
        )

        if bbox is None:
            continue

        crop_bytes: Optional[bytes] = crop_detection(image, bbox)
        if crop_bytes is None:
            continue

        crops[index] = crop_bytes
        tasks.append(
            asyncio.create_task(
                call_gemini(
                    gemini_client,
                    crop_bytes,
                    index,
                )
            )
        )

    if not tasks:
        return []

    results = await asyncio.gather(*tasks, return_exceptions=True)

    parsed_results: List[Dict[str, Any]] = []
    for result in results:
        if isinstance(result, Exception):
            parsed_results.append(
                {
                    "product_name": None,
                    "brand": None,
                    "error": str(result),
                }
            )
            continue

        detection_index: Any = result.get("detection_index")
        if isinstance(detection_index, int) and detection_index in crops:
            product_name_raw: Any = result.get("product_name")
            brand_raw: Any = result.get("brand")
            product_name: str = sanitize_filename_component(
                product_name_raw,
                fallback=f"Product {detection_index}",
            )
            brand: str = sanitize_filename_component(
                brand_raw,
                fallback=f"Brand {detection_index}",
            )

            crops_dir.mkdir(parents=True, exist_ok=True)
            crop_path: Path = build_unique_crop_path(brand, product_name, crops_dir)
            crop_bytes: bytes = crops[detection_index]
            crop_path.write_bytes(crop_bytes)

            result["crop_path"] = str(crop_path)

        parsed_results.append(result)

    return parsed_results


async def main(image_path: Path, crops_dir: Path) -> None:
    gemini_api_key: Optional[str] = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
        raise EnvironmentError("GOOGLE_API_KEY environment variable is not set")

    inference_client = InferenceHTTPClient(
        api_url="https://serverless.roboflow.com",
        api_key="your_roboflow_api_key",
    )

    gemini_client = genai.Client(api_key=gemini_api_key)

    start_time: float = time.perf_counter()

    workflow_result: Any = inference_client.run_workflow(
        workspace_name=ROBOFLOW_WORKSPACE,
        workflow_id=ROBOFLOW_WORKFLOW_ID,
        images={"image": str(image_path)},
        use_cache=True,
    )

    detections: List[Dict[str, Any]] = extract_bounding_boxes(workflow_result)

    if not detections:
        print("No bounding boxes found in the workflow result.")
        return

    results: List[Dict[str, Any]] = await process_detections(
        image_path,
        detections,
        gemini_client,
        crops_dir,
    )

    end_time: float = time.perf_counter()
    processing_time: float = end_time - start_time

    print(f"Processing time: {processing_time:.4f} seconds")

    for result in results:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process detections with Gemini and save cropped products.")
    parser.add_argument("image", type=Path, help="Path to the source image to process.")
    parser.add_argument(
        "--crops-dir",
        type=Path,
        default=DEFAULT_CROPS_DIR,
        help="Directory where cropped images will be stored (default: %(default)s).",
    )

    parsed_args = parser.parse_args()

    asyncio.run(main(parsed_args.image.resolve(), parsed_args.crops_dir.resolve()))

