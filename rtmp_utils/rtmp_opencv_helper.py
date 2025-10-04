
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
