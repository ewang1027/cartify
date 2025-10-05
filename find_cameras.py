#!/usr/bin/env python3
"""
Quick script to find all available cameras and their indices
This will help identify which camera ID is the OBS Virtual Camera
"""

import cv2

def list_available_cameras(max_cameras=10):
    """List all available cameras"""
    print("Scanning for available cameras...\n")
    print("=" * 60)
    
    available_cameras = []
    
    for i in range(max_cameras):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            # Try to read a frame to confirm it's working
            ret, frame = cap.read()
            
            # Get camera properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            backend = cap.getBackendName()
            
            status = "✅ Working" if ret and frame is not None else "⚠️ Opens but no frame"
            
            print(f"Camera ID {i}:")
            print(f"  Status: {status}")
            print(f"  Resolution: {width}x{height}")
            print(f"  FPS: {fps}")
            print(f"  Backend: {backend}")
            print(f"  Frame received: {'Yes' if ret else 'No'}")
            print()
            
            available_cameras.append({
                'id': i,
                'width': width,
                'height': height,
                'fps': fps,
                'backend': backend,
                'working': ret
            })
            
            cap.release()
    
    print("=" * 60)
    print(f"\nFound {len(available_cameras)} camera(s)")
    
    if available_cameras:
        print("\nWorking cameras:")
        for cam in available_cameras:
            if cam['working']:
                print(f"  - Camera ID {cam['id']}: {cam['width']}x{cam['height']} @ {cam['fps']}fps")
    else:
        print("No cameras found!")
    
    print("\n💡 TIP: OBS Virtual Camera typically shows up as one of these cameras.")
    print("   Look for a camera with 1920x1080 or 1280x720 resolution.")
    
    return available_cameras

if __name__ == "__main__":
    print("🎥 Camera Detection Tool\n")
    cameras = list_available_cameras(max_cameras=10)
    
    if cameras:
        print("\n" + "=" * 60)
        print("Test each camera by running:")
        for cam in cameras:
            if cam['working']:
                print(f"  python3 center_object_classifier.py --camera {cam['id']}")
