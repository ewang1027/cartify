#!/usr/bin/env python3
import sys, json, re, time
import objc
from Foundation import NSMakeRange
from PIL import Image, ImageDraw
from Cocoa import NSURL
from Quartz import (
    VNImageRequestHandler,
    VNRecognizeTextRequest,
)

def vision_box_to_pixels(bbox, img_w, img_h):
    """
    Convert Vision's normalized bbox (origin at bottom-left) to pixel coords:
    returns (x, y, w, h) with y measured from top (image coords).
    """
    x_norm = bbox.origin.x
    y_norm = bbox.origin.y
    w_norm = bbox.size.width
    h_norm = bbox.size.height

    x = x_norm * img_w
    # Vision origin is bottom-left; PIL expects top-left:
    y = (1.0 - y_norm - h_norm) * img_h
    w = w_norm * img_w
    h = h_norm * img_h
    return (float(x), float(y), float(w), float(h))

def word_spans(text):
    """
    Return list of (start, end, word) index spans for words in 'text'.
    Uses regex to avoid merging punctuation.
    """
    spans = []
    for m in re.finditer(r"\S+", text):
        spans.append((m.start(), m.end(), m.group(0)))
    return spans

def recognize_with_boxes(image_path, annotate_out=None, level="accurate"):
    # Load image to get size for pixel conversion
    img = Image.open(image_path).convert("RGB")
    W, H = img.size

    # Configure Vision request
    req = VNRecognizeTextRequest.alloc().init()
    # Optional: limit to English; comment out to let system auto-detect
    # req.recognitionLanguages = ["en-US"]

    url = NSURL.fileURLWithPath_(image_path)
    handler = VNImageRequestHandler.alloc().initWithURL_options_(url, None)

    success = handler.performRequests_error_([req], None)
    if not success:
        raise RuntimeError("Vision request failed")

    out = {
        "image": image_path,
        "width": W,
        "height": H,
        "lines": []  # each: {text, confidence, box:{x,y,w,h}, words:[{text,conf,box}]}
    }

    draw = ImageDraw.Draw(img) if annotate_out else None

    results = req.results() or []
    for obs in results:
        # obs: VNRecognizedTextObservation
        candidates = obs.topCandidates_(1)
        if not candidates or len(candidates) == 0:
            continue
        best = candidates[0]  # VNRecognizedText
        line_text = str(best.string())
        line_conf = float(best.confidence())

        # Skip lines containing any English alphabet characters
        if re.search(r"[A-Za-z]", line_text):
            continue

        # Line-level box
        lbox = vision_box_to_pixels(obs.boundingBox(), W, H)

        line_rec = {
            "text": line_text,
            "confidence": line_conf,
            "box": {"x": lbox[0], "y": lbox[1], "w": lbox[2], "h": lbox[3]},
            "words": []
        }

        # Word-level boxes (approx): map each token to its character span
        for s, e, tok in word_spans(line_text):
            if re.search(r"[A-Za-z]", tok):
                continue
            rng = NSMakeRange(s, e - s)
            # boundingBoxForRange_ returns a CGRect in the observation's space (normalized)
            okptr = objc.nil
            rect = best.boundingBoxForRange_error_(rng, None)
            if rect is None:
                continue
            bbox = rect.boundingBox()
            # boundingBoxForRange_error_ can return zero-sized rects; skip them
            if bbox.size.width == 0.0 or bbox.size.height == 0.0:
                continue
            wbox = vision_box_to_pixels(bbox, W, H)
            word_rec = {
                "text": tok,
                "confidence": line_conf,  # Vision gives confidence per line candidate; use same here
                "box": {"x": wbox[0], "y": wbox[1], "w": wbox[2], "h": wbox[3]},
            }
            line_rec["words"].append(word_rec)

        if not line_rec["words"]:
            continue

        out["lines"].append(line_rec)

        if draw:
            # draw line box
            x, y, w, h = lbox
            draw.rectangle([x, y, x + w, y + h], outline=(255, 0, 0), width=2)
            # draw word boxes
            for wrec in line_rec["words"]:
                bx = wrec["box"]["x"]
                by = wrec["box"]["y"]
                bw = wrec["box"]["w"]
                bh = wrec["box"]["h"]
                draw.rectangle([bx, by, bx + bw, by + bh], outline=(0, 255, 0), width=2)

    if annotate_out:
        img.save(annotate_out)

    return out

def main():
    if len(sys.argv) < 2:
        print("Usage: python apple_vision_ocr_boxes.py <image_path> [annotated_output.png] [fast|accurate]")
        sys.exit(1)
    image_path = sys.argv[1]
    annotate = sys.argv[2] if len(sys.argv) >= 3 else None
    level = sys.argv[3] if len(sys.argv) >= 4 else "accurate"

    start_time: float = time.perf_counter()
    result = recognize_with_boxes(image_path, annotate_out=annotate, level=level)
    latency_sec: float = time.perf_counter() - start_time
    result["latency_sec"] = latency_sec
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"latency_sec: {latency_sec:.3f}s")

if __name__ == "__main__":
    main()
