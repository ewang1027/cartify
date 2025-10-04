#!/usr/bin/env python3
"""
Simple YOLO object detection script - just detects objects and draws bounding boxes
No depth processing, no filtering - just pure object detection visualization
"""
import cv2
import torch
from ultralytics import YOLO

# Fix PyTorch 2.6 weights_only issue for YOLO models
original_torch_load = torch.load
def patched_torch_load(*args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return original_torch_load(*args, **kwargs)
torch.load = patched_torch_load

# Configuration
MODEL_PATH = "weights/best.pt"

def main():
    # Configuration
    CONF_THRESHOLD = 0.1  # Lower threshold to catch more detections
    print("Loading YOLO model...")
    try:
        model = YOLO(MODEL_PATH)
        print(f"Model loaded successfully!")
        print(f"Classes: {model.names}")
        print(f"Number of classes: {len(model.names)}")
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    print("Opening camera...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Could not open camera")
        return

    print("Camera opened successfully!")
    print("Press 'q' to quit, 's' to save current frame")
    
    frame_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to read frame")
                break
            
            frame_count += 1
            
            # Run detection
            results = model(frame, conf=CONF_THRESHOLD, verbose=False)
            
            # Process results
            if len(results) > 0:
                result = results[0]
                detections = len(result.boxes) if result.boxes is not None else 0
                
                # Print detection info every 30 frames to avoid spam
                if frame_count % 30 == 0:
                    print(f"Frame {frame_count}: Found {detections} detections")
                
                # Draw bounding boxes
                if result.boxes is not None and len(result.boxes) > 0:
                    for i, box in enumerate(result.boxes):
                        # Get detection info
                        conf = float(box.conf[0].item())
                        cls = int(box.cls[0].item())
                        label = result.names[cls]
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        
                        # Draw bounding box (green color)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        
                        # Draw label and confidence
                        label_text = f"{label} {conf:.2f}"
                        label_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                        
                        # Draw background rectangle for text
                        cv2.rectangle(frame, (x1, y1 - label_size[1] - 10), 
                                    (x1 + label_size[0], y1), (0, 255, 0), -1)
                        
                        # Draw text
                        cv2.putText(frame, label_text, (x1, y1 - 5), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            
            # Add frame counter to display
            cv2.putText(frame, f"Frame: {frame_count}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # Add detection count to display
            if len(results) > 0 and results[0].boxes is not None:
                detection_count = len(results[0].boxes)
                cv2.putText(frame, f"Detections: {detection_count}", (10, 70), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # Display frame
            cv2.imshow("Simple YOLO Detection", frame)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("Quitting...")
                break
            elif key == ord('s'):
                filename = f"detection_frame_{frame_count}.jpg"
                cv2.imwrite(filename, frame)
                print(f"Saved frame to {filename}")
            elif key == ord('c'):
                # Change confidence threshold
                CONF_THRESHOLD = max(0.01, CONF_THRESHOLD - 0.05)
                print(f"Lowered confidence threshold to {CONF_THRESHOLD:.2f}")
            elif key == ord('v'):
                # Change confidence threshold
                CONF_THRESHOLD = min(0.9, CONF_THRESHOLD + 0.05)
                print(f"Raised confidence threshold to {CONF_THRESHOLD:.2f}")

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("Camera released and windows closed")

if __name__ == "__main__":
    main()
