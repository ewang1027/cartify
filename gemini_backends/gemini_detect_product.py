"""
Capture one-second webcam clips and summarize them with Gemini.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import tempfile
import time
from typing import Dict, List, Optional, Tuple

import cv2
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MODEL = "gemini-flash-latest"
DEFAULT_CAMERA_INDEX = 0
TARGET_FPS = 24
CLIP_DURATION_SECONDS = 1.0


class VideoClipSummarizer:
    """Continuously captures one-second clips and asks Gemini to describe them."""

    def __init__(
        self,
        camera_index: int = DEFAULT_CAMERA_INDEX,
        clip_duration: float = CLIP_DURATION_SECONDS,
        target_fps: int = TARGET_FPS,
    ) -> None:
        self.camera_index = camera_index
        self.clip_duration = clip_duration
        self.target_fps = target_fps
        self.sequence_counter: int = 0
        self.next_sequence_to_print: int = 0
        self.pending_results: Dict[int, Tuple[str, str]] = {}
        self.print_lock = asyncio.Lock()
        self.processing_tasks: set[asyncio.Task[None]] = set()

        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable is required")

        self.client = genai.Client(api_key=api_key)
        self.generate_config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            safety_settings=[
                types.SafetySetting(
                    category="HARM_CATEGORY_HARASSMENT",
                    threshold="BLOCK_NONE",
                )
            ],
        )

    def capture_clip(self, capture: cv2.VideoCapture) -> Optional[bytes]:
        """Record approximately one second of video and return it as MP4 bytes."""

        frames: List[np.ndarray] = []
        start_time = time.monotonic()
        frame_interval = 1.0 / float(self.target_fps)
        next_frame_time = start_time

        while time.monotonic() - start_time < self.clip_duration:
            ret, frame = capture.read()
            if not ret:
                break
            frames.append(frame)

            next_frame_time += frame_interval
            sleep_duration = next_frame_time - time.monotonic()
            if sleep_duration > 0:
                time.sleep(sleep_duration)

        if not frames:
            return None

        return self._encode_frames(frames)

    def _encode_frames(self, frames: List[np.ndarray]) -> bytes:
        """Encode a sequence of frames into an MP4 held in memory."""

        height, width = frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        writer = cv2.VideoWriter(tmp_path, fourcc, float(self.target_fps), (width, height))
        try:
            for frame in frames:
                writer.write(frame)
        finally:
            writer.release()

        with open(tmp_path, "rb") as clip_file:
            clip_bytes = clip_file.read()
        os.remove(tmp_path)
        return clip_bytes

    async def request_description(self, clip_bytes: bytes) -> str:
        """Send the clip to Gemini and return structured product JSON."""

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        inline_data=types.Blob(mime_type="video/mp4", data=clip_bytes)
                    ),
                    types.Part.from_text(
                        text=(
                            "If the center of this one-second video clearly shows a retail product, "
                            "respond with a single JSON object containing keys product_brand, product_name, and price. "
                            "The prodctu_brand is the name of the company that makes the product. product_name is the name of this specific product."
                            "Each value must be either a string (when confidently observed) or null. "
                            "If no product is visible, respond with {\"product_brand\": null, \"product_name\": null, \"price\": null}."
                        )
                    ),
                ],
            )
        ]

        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=MODEL,
            contents=contents,
            config=self.generate_config,
        )

        if response.text:
            return response.text.strip()

        for candidate in response.candidates or []:
            parts = getattr(candidate, "content", None)
            if parts:
                for part in parts.parts or []:
                    if part.text:
                        return part.text.strip()

        return ""

    async def _process_clip(self, clip_bytes: bytes, sequence: int, timestamp: str) -> None:
        try:
            description = await self.request_description(clip_bytes)
        except Exception as exc:  # pylint: disable=broad-except
            description = json.dumps({"error": str(exc)}, ensure_ascii=False)

        async with self.print_lock:
            self.pending_results[sequence] = (timestamp, description or "(no description received)")
            await self._emit_ready_results()

    async def _emit_ready_results(self) -> None:
        while self.next_sequence_to_print in self.pending_results:
            timestamp, description = self.pending_results.pop(self.next_sequence_to_print)
            print(f"[{timestamp}] {description}")
            self.next_sequence_to_print += 1

    async def run(self) -> None:
        """Continuously capture clips and print Gemini's descriptions."""

        capture = cv2.VideoCapture(self.camera_index)
        if not capture.isOpened():
            raise RuntimeError(f"Unable to open camera index {self.camera_index}")

        print("Press Ctrl+C to stop.")

        try:
            while True:
                loop_start = time.monotonic()
                clip_bytes = await asyncio.to_thread(self.capture_clip, capture)
                if clip_bytes is None:
                    print("[WARN] Failed to capture clip; retrying...")
                else:
                    timestamp = time.strftime("%H:%M:%S")
                    sequence = self.sequence_counter
                    self.sequence_counter += 1

                    task = asyncio.create_task(self._process_clip(clip_bytes, sequence, timestamp))
                    self.processing_tasks.add(task)
                    task.add_done_callback(self.processing_tasks.discard)

                elapsed = time.monotonic() - loop_start
                sleep_duration = max(0.0, self.clip_duration - elapsed)
                if sleep_duration > 0:
                    await asyncio.sleep(sleep_duration)
        except KeyboardInterrupt:
            print("\nStopping summarizer.")
        finally:
            capture.release()
            if self.processing_tasks:
                await asyncio.gather(*self.processing_tasks, return_exceptions=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize one-second webcam clips with Gemini")
    parser.add_argument(
        "--camera-index",
        type=int,
        default=DEFAULT_CAMERA_INDEX,
        help="Webcam index to open (default: 0)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=CLIP_DURATION_SECONDS,
        help="Seconds of footage to capture per request (default: 1.0)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=TARGET_FPS,
        help="Target frames per second for captured clips (default: 24)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summarizer = VideoClipSummarizer(
        camera_index=args.camera_index,
        clip_duration=args.duration,
        target_fps=args.fps,
    )
    asyncio.run(summarizer.run())


if __name__ == "__main__":
    main()
