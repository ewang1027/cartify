# RTMP Stream Utilities

This directory contains utilities for working with RTMP streams, specifically for the stream at `rtmp://3.96.138.25:1935/live/key`.

## Files

- **`rtmp_stream_tester.py`** - Comprehensive testing script for RTMP streams
- **`rtmp_opencv_helper.py`** - Helper functions for capturing RTMP frames with OpenCV

## Usage

### Testing the Stream

```bash
cd rtmp_utils
python rtmp_stream_tester.py
```

### Capturing Frames in Your Code

```python
from rtmp_opencv_helper import capture_rtmp_frame

# Capture a single frame
success, frame = capture_rtmp_frame()
if success:
    # frame is a numpy array ready for OpenCV processing
    # Your existing OpenCV code here
    pass
```

### Stream Information

- **URL**: `rtmp://3.96.138.25:1935/live/key`
- **Server**: NGINX RTMP
- **Resolution**: 3024x1964
- **Frame Rate**: 30 fps
- **Audio**: AAC, 48kHz, stereo
- **Video**: H.264/AVC

## Requirements

- FFmpeg (for RTMP stream access)
- OpenCV (for image processing)
- Python subprocess module

## Notes

- OpenCV cannot directly read RTMP streams, so we use FFmpeg as a bridge
- The stream is live and accessible 24/7
- Frame capture is done via FFmpeg subprocess calls
- Captured frames are returned as OpenCV-compatible numpy arrays
