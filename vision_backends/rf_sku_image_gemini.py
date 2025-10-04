import argparse
import asyncio
import json
import math
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TypedDict

import cv2
from google import genai
from google.genai import types
from inference_sdk import InferenceHTTPClient

from apple_ocr import recognize_with_boxes

from dotenv import load_dotenv

load_dotenv()

ROBOFLOW_WORKSPACE: str = "orbifold-ai"
ROBOFLOW_WORKFLOW_ID: str = "detect-count-and-visualize-3"
MODEL_NAME: str = "gemini-flash-lite-latest"
DEFAULT_CROPS_DIR: Path = Path(__file__).resolve().parent / "crops"


class OCRWord(TypedDict):
    text: str
    left: float
    top: float
    right: float
    bottom: float


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

        is_normalized: bool = (
            0.0 <= x_center <= 1.0
            and 0.0 <= y_center <= 1.0
            and 0.0 < width <= 1.0
            and 0.0 < height <= 1.0
        )

        if is_normalized:
            x_center *= float(image_width)
            y_center *= float(image_height)
            width *= float(image_width)
            height *= float(image_height)

        left = int(round(x_center - (width / 2.0)))
        top = int(round(y_center - (height / 2.0)))
        right = int(round(x_center + (width / 2.0)))
        bottom = int(round(y_center + (height / 2.0)))

        if left == right:
            right = left + 1
        if top == bottom:
            bottom = top + 1

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


def load_ocr_words(image_path: Path) -> List[OCRWord]:
    try:
        ocr_result: Dict[str, Any] = recognize_with_boxes(str(image_path))
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Failed to run OCR: {exc}")
        return []

    words: List[OCRWord] = []

    for line in ocr_result.get("lines", []):
        for word in line.get("words", []):
            box: Dict[str, Any] = word.get("box", {})
            left: float = float(box.get("x", 0.0))
            top: float = float(box.get("y", 0.0))
            width: float = float(box.get("w", 0.0))
            height: float = float(box.get("h", 0.0))
            words.append(
                OCRWord(
                    text=str(word.get("text", "")),
                    left=left,
                    top=top,
                    right=left + width,
                    bottom=top + height,
                )
            )

    return words


def expand_bbox_with_text(
    bbox: Tuple[int, int, int, int],
    ocr_words: List[OCRWord],
    image_width: int,
    image_height: int,
) -> Tuple[Tuple[int, int, int, int], Optional[str]]:
    left, top, right, bottom = bbox

    best_word: Optional[OCRWord] = None
    best_gap: float = math.inf
    best_center_delta: float = math.inf
    product_center_x: float = (left + right) / 2.0

    for word in ocr_words:
        if word["top"] < top:
            continue

        gap: float = max(0.0, word["top"] - bottom)
        word_center_x: float = (word["left"] + word["right"]) / 2.0
        center_delta: float = abs(product_center_x - word_center_x)

        if gap < best_gap or (math.isclose(gap, best_gap) and center_delta < best_center_delta):
            best_word = word
            best_gap = gap
            best_center_delta = center_delta

    if best_word is None:
        return (left, top, right, bottom), None

    expanded_left: int = max(0, int(math.floor(min(left, best_word["left"]))))
    expanded_right: int = min(image_width - 1, int(math.ceil(max(right, best_word["right"]))))
    expanded_top: int = max(0, int(math.floor(min(top, best_word["top"]))))
    expanded_bottom: int = min(image_height - 1, int(math.ceil(max(bottom, best_word["bottom"]))))

    if expanded_right <= expanded_left or expanded_bottom <= expanded_top:
        return (left, top, right, bottom), best_word["text"]

    return (expanded_left, expanded_top, expanded_right, expanded_bottom), best_word["text"]


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


def build_contents(image_bytes: bytes, context_text: Optional[str]) -> List[types.Content]:
    prompt: str = (
        "You are an assistant that identifies retail products. "
        "Look at this cropped product image and respond with a JSON object containing "
        "three keys: product_name, brand, and price. If any value is unknown, use null. "
        "Price should be a numeric string without currency symbols."
    )

    parts: List[types.Part] = [
        types.Part.from_text(text=prompt),
        types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
    ]

    if context_text:
        parts.append(
            types.Part.from_text(
                text=f"Text located directly beneath this product: {context_text}"
            )
        )

    return [types.Content(role="user", parts=parts)]


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
            "price": None,
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
    context_text: Optional[str],
) -> Dict[str, Any]:
    contents: List[types.Content] = build_contents(image_bytes, context_text)

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
    parsed.setdefault("price", None)
    parsed["detection_index"] = detection_index

    return parsed


async def process_detections(
    image_path: Path,
    detections: List[Dict[str, Any]],
    gemini_client: genai.Client,
    crops_dir: Path,
    ocr_words: List[OCRWord],
) -> List[Dict[str, Any]]:
    image = cv2.imread(str(image_path))

    if image is None:
        raise FileNotFoundError(f"Failed to load image at {image_path}")

    image_height: int = int(image.shape[0])
    image_width: int = int(image.shape[1])

    tasks: List[asyncio.Task[Dict[str, Any]]] = []
    crops: Dict[int, bytes] = {}
    context_by_index: Dict[int, Optional[str]] = {}

    for index, detection in enumerate(detections):
        bbox: Optional[Tuple[int, int, int, int]] = detection_to_bbox(
            detection,
            image_height,
            image_width,
        )

        if bbox is None:
            continue

        expanded_bbox, context_text = expand_bbox_with_text(
            bbox,
            ocr_words,
            image_width,
            image_height,
        )

        crop_bytes: Optional[bytes] = crop_detection(image, expanded_bbox)
        if crop_bytes is None:
            continue

        crops[index] = crop_bytes
        context_by_index[index] = context_text
        tasks.append(
            asyncio.create_task(
                call_gemini(
                    gemini_client,
                    crop_bytes,
                    index,
                    context_text,
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
                    "price": None,
                    "error": str(result),
                }
            )
            continue

        detection_index: Any = result.get("detection_index")
        if isinstance(detection_index, int) and detection_index in crops:
            product_name_raw: Any = result.get("product_name")
            brand_raw: Any = result.get("brand")
            price_raw: Any = result.get("price")
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
            result["price"] = price_raw if price_raw is not None else None

            context_text: Optional[str] = context_by_index.get(detection_index)
            if context_text:
                result.setdefault("context_text", context_text)

        parsed_results.append(result)

    return parsed_results


async def main(image_path: Path, crops_dir: Path) -> None:
    gemini_api_key: Optional[str] = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
        raise EnvironmentError("GOOGLE_API_KEY environment variable is not set")

    roboflow_api_key: str | None = os.environ.get("ROBOFLOW_API_KEY")
    if not roboflow_api_key:
        raise EnvironmentError("ROBOFLOW_API_KEY environment variable is not set")

    inference_client = InferenceHTTPClient(
        api_url="https://serverless.roboflow.com",
        api_key=roboflow_api_key,
    )

    gemini_client = genai.Client(api_key=gemini_api_key)

    start_time: float = time.perf_counter()

    workflow_task: asyncio.Future[Any] = asyncio.to_thread(
        inference_client.run_workflow,
        workspace_name=ROBOFLOW_WORKSPACE,
        workflow_id=ROBOFLOW_WORKFLOW_ID,
        images={"image": str(image_path)},
        use_cache=True,
    )
    ocr_task: asyncio.Future[List[OCRWord]] = asyncio.to_thread(load_ocr_words, image_path)

    workflow_result, ocr_words = await asyncio.gather(workflow_task, ocr_task)

    detections: List[Dict[str, Any]] = extract_bounding_boxes(workflow_result)

    if not detections:
        print("No bounding boxes found in the workflow result.")
        return

    results: List[Dict[str, Any]] = await process_detections(
        image_path,
        detections,
        gemini_client,
        crops_dir,
        ocr_words,
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

