#!/usr/bin/env python3
"""
Quick test script to verify YOLO detection is working with the new settings
"""
import cv2
import torch
from ultralytics import YOLO

# Load model
print("Loading YOLO model...")
model = YOLO('weights/best.pt')
print(f"Model loaded successfully. Classes: {model.names}")

# Test with webcam
print("Opening camera...")
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Could not open camera")
    exit(1)

print("Camera opened. Press 'q' to quit, 's' to save frame")
frame_count = 0

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_count += 1
        
        # Run detection every 10 frames to avoid spam
        if frame_count % 10 == 0:
            print(f"\n--- Frame {frame_count} ---")
            results = model(frame, conf=0.1, verbose=False)
            
            if len(results) > 0:
                result = results[0]
                num_detections = len(result.boxes) if result.boxes is not None else 0
                print(f"Found {num_detections} detections")
                
                if result.boxes is not None and len(result.boxes) > 0:
                    for i, box in enumerate(result.boxes):
                        conf = float(box.conf[0].item())
                        cls = int(box.cls[0].item())
                        label = result.names[cls]
                        x1, y1, x2, y2 = map(float, box.xyxy[0].tolist())
                        
                        # Draw bounding box
                        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                        cv2.putText(frame, f"{label} {conf:.2f}", 
                                   (int(x1), max(12, int(y1)-4)), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        print(f"  Detection {i}: {label} conf={conf:.3f}")
            else:
                print("No detections found")
        
        # Display frame
        cv2.imshow("YOLO Detection Test", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            cv2.imwrite(f"test_frame_{frame_count}.jpg", frame)
            print(f"Saved frame {frame_count}")

finally:
    cap.release()
    cv2.destroyAllWindows()
    print("Test completed")
