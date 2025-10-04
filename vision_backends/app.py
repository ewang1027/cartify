from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import cv2
import base64
import threading
import time
import os
import subprocess
import tempfile

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# RTMP stream configuration
RTMP_URL = "rtmp://3.96.138.25:1935/live/key"
streaming_active = False
stream_thread = None

def capture_rtmp_frame():
    """
    Capture a single frame from RTMP stream using FFmpeg
    Returns: (success, frame_data)
    """
    try:
        # Create temporary file for frame capture
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Capture frame using FFmpeg
        cmd = [
            'ffmpeg', '-i', RTMP_URL,
            '-vframes', '1',  # Capture just 1 frame
            '-y',  # Overwrite output file
            temp_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0 and os.path.exists(temp_path):
            # Read frame and encode as base64
            with open(temp_path, 'rb') as f:
                frame_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Clean up temporary file
            os.unlink(temp_path)
            return True, frame_data
        else:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return False, None
            
    except Exception as e:
        print(f"Error capturing RTMP frame: {e}")
        return False, None

def stream_video():
    """
    Continuous video streaming function
    """
    global streaming_active
    while streaming_active:
        try:
            success, frame_data = capture_rtmp_frame()
            if success:
                socketio.emit('video_frame', {'frame': frame_data})
            else:
                socketio.emit('stream_error', {'message': 'Failed to capture frame'})
            
            # Control frame rate (adjust as needed)
            time.sleep(0.033)  # ~30 FPS
            
        except Exception as e:
            print(f"Streaming error: {e}")
            socketio.emit('stream_error', {'message': str(e)})
            break

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connected', {'message': 'Connected to video stream'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('start_stream')
def handle_start_stream():
    """
    Start video streaming from RTMP source
    """
    global streaming_active, stream_thread
    
    if not streaming_active:
        streaming_active = True
        stream_thread = threading.Thread(target=stream_video)
        stream_thread.daemon = True
        stream_thread.start()
        emit('stream_started', {'message': 'Video stream started'})
    else:
        emit('stream_error', {'message': 'Stream already active'})

@socketio.on('stop_stream')
def handle_stop_stream():
    """
    Stop video streaming
    """
    global streaming_active, stream_thread
    
    if streaming_active:
        streaming_active = False
        if stream_thread:
            stream_thread.join(timeout=2)
        emit('stream_stopped', {'message': 'Video stream stopped'})
    else:
        emit('stream_error', {'message': 'No active stream to stop'})

@socketio.on('get_frame')
def handle_get_frame():
    """
    Get a single frame from the RTMP stream
    """
    success, frame_data = capture_rtmp_frame()
    if success:
        emit('frame_data', {'frame': frame_data})
    else:
        emit('stream_error', {'message': 'Failed to capture frame'})

@app.route('/')
def index():
    return {
        'message': 'Video streaming server is running',
        'rtmp_url': RTMP_URL,
        'endpoints': {
            'start_stream': 'Start continuous video streaming',
            'stop_stream': 'Stop video streaming',
            'get_frame': 'Get single frame'
        }
    }

if __name__ == '__main__':
    print(f"Starting video streaming server...")
    print(f"RTMP URL: {RTMP_URL}")
    socketio.run(app, host='0.0.0.0', port=5002, debug=True, allow_unsafe_werkzeug=True)
