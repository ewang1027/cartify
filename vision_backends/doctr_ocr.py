import json
import re
import sys
import time
from typing import Any, Dict, List

import numpy as np
import torch
from PIL import Image, ImageDraw
from doctr.models import ocr_predictor

inp = sys.argv[1] if len(sys.argv) > 1 else "input.jpg"
out = sys.argv[2] if len(sys.argv) > 2 else "output.jpg"
max_dim = int(sys.argv[3]) if len(sys.argv) > 3 else 1280  # cap largest side for speed

device = "mps" if torch.backends.mps.is_available() else "cpu"
torch.set_float32_matmul_precision("high")

# Load model once
model = ocr_predictor(pretrained=True).to(device).eval()

def load_and_resize(path: str, max_side: int) -> Image.Image:
    img = Image.open(path).convert("RGB")
    w, h = img.size
    s = max(w, h)
    if s > max_side:
        scale = max_side / s
        img = img.resize((int(w * scale), int(h * scale)), Image.BILINEAR)
    return img

img = load_and_resize(inp, max_dim)
W, H = img.size

# Run OCR
t0 = time.time()
with torch.inference_mode():
    doc = model([np.array(img)])
latency = time.time() - t0

# Extract word boxes + text
results: List[Dict[str, Any]] = []
pattern = re.compile(r"[A-Za-z]")
page = doc.pages[0]
for block in page.blocks:
    for line in block.lines:
        for word in line.words:
            (x0, y0), (x1, y1) = word.geometry  # normalized [0..1]
            text = word.value
            if pattern.search(text):
                continue
            bx = [int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)]
            results.append({"text": text, "box_xyxy": bx})

# Draw overlays
draw = ImageDraw.Draw(img)
for r in results:
    x0, y0, x1, y1 = r["box_xyxy"]
    draw.rectangle((x0, y0, x1, y1), outline=(255, 0, 0), width=2)

img.save(out, quality=95)

# Emit simple JSON alongside the image
print(json.dumps({
    "device": device,
    "image_size": [W, H],
    "latency_sec": round(latency, 3),
    "num_words": len(results),
    "words": results
}, ensure_ascii=False, indent=2))
print(f"Saved: {out}")
