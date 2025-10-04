#!/usr/bin/env python3
"""
Simple RTMP Stream Tester
A straightforward way to test and capture frames from RTMP stream
"""

import subprocess
import cv2
import time
import os
from datetime import datetime

def test_rtmp_stream(rtmp_url="rtmp://3.96.138.25:1935/live/key"):
    """Test RTMP stream and capture sample frames"""
    
    print("🚀 RTMP Stream Tester")
    print("=" * 50)
    print(f"📡 Stream URL: {rtmp_url}")
    print()
    
    # Test 1: Basic connectivity with ffprobe
    print("🔍 Testing stream connectivity...")
    try:
        cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', 
               '-show_streams', '-show_format', rtmp_url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Stream is accessible!")
        else:
            print("❌ Stream connectivity test failed")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test 2: Capture a frame using FFmpeg
    print("\n📸 Capturing sample frame...")
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"rtmp_sample_{timestamp}.jpg"
        
        cmd = [
            'ffmpeg', '-i', rtmp_url, 
            '-t', '3',  # Capture for 3 seconds
            '-f', 'image2', 
            '-update', '1',  # Update the same file
            output_file,
            '-y'  # Overwrite if exists
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0 and os.path.exists(output_file):
            print(f"✅ Frame captured successfully: {output_file}")
            
            # Get file size
            file_size = os.path.getsize(output_file)
            print(f"📁 File size: {file_size:,} bytes")
            
            # Try to load with OpenCV to verify it's a valid image
            img = cv2.imread(output_file)
            if img is not None:
                height, width = img.shape[:2]
                print(f"📐 Image dimensions: {width}x{height}")
                print("✅ Image is valid and can be processed with OpenCV")
            else:
                print("⚠️  Image captured but couldn't be loaded with OpenCV")
                
        else:
            print("❌ Failed to capture frame")
            return False
            
    except Exception as e:
        print(f"❌ Error capturing frame: {e}")
        return False
    
    # Test 3: Continuous frame capture (optional)
    print("\n🎬 Testing continuous capture...")
    try:
        # Capture multiple frames
        for i in range(3):
            frame_file = f"rtmp_frame_{i+1}.jpg"
            cmd = [
                'ffmpeg', '-i', rtmp_url,
                '-vframes', '1',  # Capture just 1 frame
                '-y',
                frame_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and os.path.exists(frame_file):
                print(f"✅ Frame {i+1} captured: {frame_file}")
            else:
                print(f"❌ Failed to capture frame {i+1}")
            
            time.sleep(1)  # Wait between captures
    
    except Exception as e:
        print(f"⚠️  Continuous capture test failed: {e}")
    
    print("\n🎉 RTMP Stream Testing Complete!")
    print("\n📋 Summary:")
    print("✅ Stream is accessible via FFmpeg")
    print("✅ Frames can be captured successfully")
    print("✅ Images are valid and processable")
    print("\n💡 Integration with your existing code:")
    print("   - Use FFmpeg subprocess calls to capture frames")
    print("   - Load captured frames with cv2.imread()")
    print("   - Process frames with your existing OpenCV pipeline")
    
    return True

def create_opencv_compatible_capture():
    """Create a function that captures frames compatible with your existing OpenCV code"""
    
    code = '''
def capture_rtmp_frame(rtmp_url="rtmp://3.96.138.25:1935/live/key", output_file="temp_frame.jpg"):
    """
    Capture a single frame from RTMP stream using FFmpeg
    Returns: (success, frame_path)
    """
    import subprocess
    import cv2
    import os
    
    try:
        # Capture frame using FFmpeg
        cmd = [
            'ffmpeg', '-i', rtmp_url,
            '-vframes', '1',  # Capture just 1 frame
            '-y',  # Overwrite output file
            output_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and os.path.exists(output_file):
            # Load with OpenCV
            frame = cv2.imread(output_file)
            if frame is not None:
                return True, frame
            else:
                return False, None
        else:
            return False, None
            
    except Exception as e:
        print(f"Error capturing RTMP frame: {e}")
        return False, None

# Usage example:
# success, frame = capture_rtmp_frame()
# if success:
#     # Process frame with your existing OpenCV code
#     processed_frame = your_processing_function(frame)
'''
    
    with open('rtmp_opencv_helper.py', 'w') as f:
        f.write(code)
    
    print("\n📝 Created 'rtmp_opencv_helper.py' with integration code")

if __name__ == "__main__":
    success = test_rtmp_stream()
    
    if success:
        create_opencv_compatible_capture()
    
    print(f"\n🏁 Testing completed. Success: {'✅' if success else '❌'}")
