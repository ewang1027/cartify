import argparse
import os
import time
from pathlib import Path
from typing import Any, Dict, List

import cv2
from dotenv import load_dotenv
from inference_sdk import InferenceHTTPClient

load_dotenv()

parser: argparse.ArgumentParser = argparse.ArgumentParser(
    description="Run Roboflow workflow on an input image."
)
parser.add_argument(
    "input_path",
    type=Path,
    help="Path to the input image file",
)
parser.add_argument(
    "--output-path",
    dest="output_path",
    type=Path,
    help="Optional path for the annotated output image",
)

args: argparse.Namespace = parser.parse_args()

input_image_path: Path = args.input_path
output_image_path: Path
if args.output_path is not None:
    output_image_path = args.output_path
else:
    output_image_path = input_image_path.with_name(
        f"{input_image_path.stem}_annotated{input_image_path.suffix}"
    )

roboflow_api_key: str | None = os.environ.get("ROBOFLOW_API_KEY")

if roboflow_api_key is None:
    raise EnvironmentError("ROBOFLOW_API_KEY environment variable is not set")

client = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key=roboflow_api_key
)

start_time: float = time.perf_counter()

result: Any = client.run_workflow(
    workspace_name="orbifold-ai",
    workflow_id="detect-count-and-visualize-3",
    images={
        "image": str(input_image_path)
    },
    use_cache=True # cache workflow definition for 15 minutes
)

print(result)

end_time: float = time.perf_counter()
processing_time: float = end_time - start_time

print(f"Processing time: {processing_time:.4f} seconds")
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


def draw_bounding_boxes(image_path: str, detections: List[Dict[str, Any]], output_path: str) -> None:
    image = cv2.imread(image_path)

    if image is None:
        raise FileNotFoundError(f"Failed to load image at {image_path}")

    image_height: int = int(image.shape[0])
    image_width: int = int(image.shape[1])

    for detection in detections:
        width: float = float(detection.get("width", 0.0))
        height: float = float(detection.get("height", 0.0))
        x_center: float = float(detection.get("x", detection.get("left", 0.0)))
        y_center: float = float(detection.get("y", detection.get("top", 0.0)))

        if "left" in detection and "right" in detection and "top" in detection and "bottom" in detection:
            left: int = int(detection.get("left", 0))
            top: int = int(detection.get("top", 0))
            right: int = int(detection.get("right", 0))
            bottom: int = int(detection.get("bottom", 0))
        else:
            left = int(round(x_center - (width / 2)))
            top = int(round(y_center - (height / 2)))
            right = int(round(x_center + (width / 2)))
            bottom = int(round(y_center + (height / 2)))

        left = max(0, min(left, image_width - 1))
        right = max(0, min(right, image_width - 1))
        top = max(0, min(top, image_height - 1))
        bottom = max(0, min(bottom, image_height - 1))

        if right <= left or bottom <= top:
            continue

        pt1: tuple[int, int] = (left, top)
        pt2: tuple[int, int] = (right, bottom)
        color: tuple[int, int, int] = (0, 255, 0)
        thickness: int = 2

        cv2.rectangle(image, pt1, pt2, color, thickness)

        label: str = str(detection.get("class", detection.get("label", "")))
        confidence: float = float(detection.get("confidence", 0.0))
        label_parts: List[str] = []
        if label:
            label_parts.append(label)
        label_parts.append(f"{confidence:.2f}")
        label_text: str = " ".join(label_parts)
        text_org: tuple[int, int] = (left, max(top - 10, 0))
        font: int = cv2.FONT_HERSHEY_SIMPLEX
        font_scale: float = 0.5
        font_thickness: int = 1

        cv2.putText(image, label_text, text_org, font, font_scale, color, font_thickness, cv2.LINE_AA)

    cv2.imwrite(output_path, image)


boxes: List[Dict[str, Any]] = extract_bounding_boxes(result)

if boxes:
    draw_bounding_boxes(str(input_image_path), boxes, str(output_image_path))

    print(f"Annotated image saved to: {output_image_path}")
else:
    print("No bounding boxes found in the workflow result.")