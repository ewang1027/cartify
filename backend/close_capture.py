import os, time, cv2, numpy as np, torch
import ssl
import urllib.request
from ultralytics import YOLO

# Fix SSL certificate verification issues on macOS
ssl._create_default_https_context = ssl._create_unverified_context

# Fix PyTorch 2.6 weights_only issue for YOLO models
# Monkey patch torch.load to use weights_only=False for trusted YOLO models
original_torch_load = torch.load
def patched_torch_load(*args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return original_torch_load(*args, **kwargs)
torch.load = patched_torch_load

# ---------------- Config ----------------
MODEL_PATH = "weights/best.pt"   # Your custom PyTorch model for grocery items
CONF_THRES = 0.1  # Lowered from 0.25 to catch more detections
DEPTH_MODEL_NAME = "MiDaS_small"   # fast; or "DPT_Small" for nicer edges (slower)
DEPTH_INPUT_SHORT = 256            # 256–320 is a good range for realtime
DEPTH_CUTOFF = 15.0                # Raw depth value - save if median depth <= this (closer = lower values)
AREA_MIN_FRAC = 0.05               # also require box to be at least 5% of frame area
SAVE_COOLDOWN_SEC = 1.5            # avoid spamming saves
DISABLE_DEPTH_FILTER = True        # Set to True to show all detections regardless of depth (for debugging)
OUT_DIR = "captures"
os.makedirs(OUT_DIR, exist_ok=True)

# No need to exclude classes since we're using a custom grocery model
# EXCLUDE_CLASSES = ["person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat"]

# ---------------- Depth model ----------------
print("[init] loading MiDaS:", DEPTH_MODEL_NAME)
try:
    # Try to load with internet connection
    depth_model = torch.hub.load("intel-isl/MiDaS", DEPTH_MODEL_NAME, force_reload=False)
    depth_model.eval()
    transforms = torch.hub.load("intel-isl/MiDaS", "transforms", force_reload=False)
    depth_transform = transforms.small_transform  # good for MiDaS_small and DPT_Small
    print("[init] MiDaS model loaded successfully")
except Exception as e:
    print(f"[error] Failed to load MiDaS model: {e}")
    print("[info] This might be due to network issues or SSL certificate problems.")
    print("[info] Please check your internet connection and try again.")
    print("[info] You can also try running: /Applications/Python\\ 3.13/Install\\ Certificates.command")
    exit(1)

device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
depth_model.to(device)
try:
    depth_model.half()  # may speed up on MPS/CUDA
except Exception:
    pass

def depth_map_from_bgr(frame_bgr):
    """Returns depth map where lower values = closer objects."""
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    scale = DEPTH_INPUT_SHORT / min(h, w)
    resized = cv2.resize(rgb, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)
    inp = depth_transform(resized).to(device)
    if next(depth_model.parameters()).dtype == torch.float16:
        inp = inp.half()
    with torch.inference_mode():
        pred = depth_model(inp).squeeze().detach().cpu().numpy()
    
    d = pred - pred.min()
    d = d / (d.max() + 1e-8)
    
    # Ensure d is 2D for cv2.resize
    if len(d.shape) != 2:
        d = d.reshape(d.shape[-2], d.shape[-1])
    
    # Ensure d is the right dtype for OpenCV
    if d.dtype != np.uint8:
        d = (d * 255).astype(np.uint8)
    
    return cv2.resize(d, (w, h), interpolation=cv2.INTER_LINEAR)

def get_object_detections(frame):
    """Get YOLO object detections for grocery items."""
    y = detector(frame, conf=CONF_THRES, verbose=False)[0]
    dets = []
    
    # Debug: Print total detections found
    total_detections = len(y.boxes) if y.boxes is not None else 0
    print(f"[debug] YOLO found {total_detections} detections with conf >= {CONF_THRES}")
    
    for b in y.boxes:
        cls = int(b.cls[0].item())
        label = y.names[cls]
        conf = float(b.conf[0].item())
        x1, y1, x2, y2 = map(float, b.xyxy[0].tolist())
        
        # Keep boxes inside frame
        x1 = max(0, min(x1, frame.shape[1]-1))
        y1 = max(0, min(y1, frame.shape[0]-1))
        x2 = max(0, min(x2, frame.shape[1]-1))
        y2 = max(0, min(y2, frame.shape[0]-1))
        
        if x2 > x1 and y2 > y1:
            dets.append(([x1, y1, x2, y2], label, conf))
            print(f"[debug] Added detection: {label} conf={conf:.3f} bbox=({x1:.1f},{y1:.1f},{x2:.1f},{y2:.1f})")
    
    print(f"[debug] Returning {len(dets)} valid detections")
    return dets

def get_object_depth(detection, depth_map):
    """Get median depth value for a detection."""
    (bx, by, ex, ey), label, conf = detection
    x1i, y1i, x2i, y2i = map(int, [bx, by, ex, ey])
    patch = depth_map[y1i:y2i, x1i:x2i]
    
    if patch.size == 0:
        return None
    
    return float(np.median(patch))

def get_color_for_depth(depth):
    """Get color and thickness based on depth value."""
    if depth <= 8:  # Very close
        return (0, 255, 255), 3  # Yellow, thick
    elif depth <= 12:  # Close
        return (0, 165, 255), 2  # Orange, medium
    else:  # Moderately close
        return (0, 100, 255), 2  # Red, medium

def draw_detection_boxes(frame, detections, depth_map):
    """Draw colored bounding boxes for close objects."""
    print(f"[debug] Found {len(detections)} detections, DEPTH_CUTOFF={DEPTH_CUTOFF}")
    
    boxes_drawn = 0
    for detection in detections:
        depth = get_object_depth(detection, depth_map)
        if depth is None:
            print(f"[debug] Skipping detection due to invalid depth")
            continue
            
        (bx, by, ex, ey), label, conf = detection
        will_show = depth <= DEPTH_CUTOFF
        print(f"[debug] {label}: depth={depth:.1f}, conf={conf:.2f}, will_show={will_show}")
        
        # Only draw boxes for objects close enough (or all if debug mode)
        if will_show or DISABLE_DEPTH_FILTER:
            if DISABLE_DEPTH_FILTER:
                # Use blue color for all detections in debug mode
                color, thickness = (255, 0, 0), 2
            else:
                color, thickness = get_color_for_depth(depth)
            
            cv2.rectangle(frame, (int(bx), int(by)), (int(ex), int(ey)), color, thickness)
            cv2.putText(frame, f"{label} {conf:.2f} d:{depth:.1f}", 
                       (int(bx), max(12, int(by)-4)), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            boxes_drawn += 1
    
    print(f"[debug] Drew {boxes_drawn} bounding boxes")

def find_closest_object(detections, depth_map, frame_area):
    """Find the closest object that meets all criteria."""
    best = None
    best_score = -1.0
    
    for detection in detections:
        depth = get_object_depth(detection, depth_map)
        if depth is None:
            continue
            
        (bx, by, ex, ey), label, conf = detection
        area_frac = ((ex - bx) * (ey - by)) / frame_area
        
        # Only consider objects close enough
        if depth <= DEPTH_CUTOFF:
            # Score: prioritize closeness, then size (lower depth = closer = higher score)
            score = (100.0 - depth) + 0.5 * area_frac
            if score > best_score:
                best_score = score
                best = (detection, depth, area_frac)
    
    return best

def highlight_selected_object(frame, best_object):
    """Highlight the selected object with green box."""
    if best_object is None:
        return
        
    (detection, depth, area_frac) = best_object
    (bx, by, ex, ey), label, conf = detection
    
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (int(bx), int(by)), (int(ex), int(ey)), (0,255,0), 2)
    cv2.putText(frame, f"SELECTED [{label}] depth~{depth:.1f} area~{area_frac:.2f}",
                (int(bx), min(h-6, int(ey)+16)), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,255,0), 2)

def should_capture_object(best_object, last_save_time, last_saved_bbox):
    """Check if object should be captured based on all criteria."""
    if best_object is None:
        return False, "No object"
        
    (detection, depth, area_frac) = best_object
    (bx, by, ex, ey), label, conf = detection
    
    now = time.time()
    close_enough = (depth <= DEPTH_CUTOFF and area_frac >= AREA_MIN_FRAC)
    cool = (now - last_save_time) >= SAVE_COOLDOWN_SEC
    same_as_last = (last_saved_bbox is not None and 
                   iou_xyxy(last_saved_bbox, (bx,by,ex,ey)) > 0.5)
    
    print(f"[debug] SELECTED: {label} - close_enough={close_enough} "
          f"(depth={depth:.1f}<={DEPTH_CUTOFF}, area={area_frac:.3f}>={AREA_MIN_FRAC}), "
          f"cool={cool}, not_same={not same_as_last}")
    
    return (close_enough and cool and not same_as_last), "All conditions met"

def capture_object(frame, best_object):
    """Capture and save the object image."""
    (detection, depth, area_frac) = best_object
    (bx, by, ex, ey), label, conf = detection
    
    crop = frame[int(by):int(ey), int(bx):int(ex)].copy()
    ts = time.strftime("%Y%m%d-%H%M%S")
    out_path = os.path.join(OUT_DIR, f"{ts}_{label}.jpg")
    cv2.imwrite(out_path, crop)
    print(f"[save] {out_path}  (depth≈{depth:.1f}, area={area_frac:.2f})")
    
    return (bx, by, ex, ey)  # Return bbox for duplicate detection

# ---------------- Custom YOLO Model ----------------
print("[init] loading custom YOLO model:", MODEL_PATH)
try:
    # Load your custom fine-tuned YOLO model for grocery items
    detector = YOLO(MODEL_PATH)
    print("[init] Custom YOLO model loaded successfully")
    
    # Print model info
    print(f"[info] Model classes: {detector.names}")
    print(f"[info] Number of classes: {len(detector.names)}")
    
except Exception as e:
    print(f"[error] Failed to load custom YOLO model: {e}")
    print("[info] Make sure the model path is correct and the model is valid")
    exit(1)

# ---------------- Helpers ----------------
def iou_xyxy(a, b):
    ax1, ay1, ax2, ay2 = a; bx1, by1, bx2, by2 = b
    inter_x1 = max(ax1, bx1); inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2); inter_y2 = min(ay2, by2)
    iw = max(0, inter_x2 - inter_x1); ih = max(0, inter_y2 - inter_y1)
    inter = iw * ih
    area_a = max(0, (ax2-ax1)) * max(0, (ay2-ay1))
    area_b = max(0, (bx2-bx1)) * max(0, (by2-by1))
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0

def visualize_depth_overlay(frame, depth_map):
    """Add small depth visualization overlay to frame."""
    h, w = frame.shape[:2]
    depth_vis = (depth_map * 255).astype(np.uint8)
    depth_vis = cv2.applyColorMap(depth_vis, cv2.COLORMAP_MAGMA)
    depth_vis = cv2.resize(depth_vis, (int(w*0.3), int(h*0.3)))
    frame[0:depth_vis.shape[0], 0:depth_vis.shape[1]] = depth_vis

def process_frame(frame, last_save_time, last_saved_bbox):
    """Process a single frame and return updated state."""
    h, w = frame.shape[:2]
    frame_area = float(h * w)
    
    # 1) Generate depth map
    depth_map = depth_map_from_bgr(frame)
    # 2) Get object detections
    detections = get_object_detections(frame)
    # 3) Draw colored bounding boxes for close objects
    draw_detection_boxes(frame, detections, depth_map)
    # 4) Find the closest object
    best_object = find_closest_object(detections, depth_map, frame_area)
    # 5) Highlight selected object
    highlight_selected_object(frame, best_object)
    
    # 6) Check if we should capture
    should_capture, reason = should_capture_object(best_object, last_save_time, last_saved_bbox)
    
    new_last_save_time = last_save_time
    new_last_saved_bbox = last_saved_bbox
    
    if should_capture:
        new_last_saved_bbox = capture_object(frame, best_object)
        new_last_save_time = time.time()
    
    # 7) Add depth visualization overlay
    visualize_depth_overlay(frame, depth_map)
    
    return new_last_save_time, new_last_saved_bbox

def main():
    """Main application loop."""
    # Initialize camera
    cap = cv2.VideoCapture(0)
    
    # State variables
    last_save_time = 0.0
    last_saved_bbox = None
    
    print("[run] press ESC to quit")
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            
            # Process frame and update state
            last_save_time, last_saved_bbox = process_frame(frame, last_save_time, last_saved_bbox)
            
            # Display frame
            cv2.imshow("closest-capture (ESC to quit)", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break
                
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("[done]")

if __name__ == "__main__":
    main()
