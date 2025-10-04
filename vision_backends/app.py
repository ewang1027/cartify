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
import numpy as np

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# RTMP stream configuration
RTMP_URL = "rtmp://3.96.138.25:1935/live/key"

# Camera streaming variables
camera = None
streaming = False
stream_thread = None

def stream_camera():
    """Stream camera frames to connected clients"""
    global camera, streaming
    
    try:
        # Initialize camera with ID 2
        camera = cv2.VideoCapture(2)
        
        if not camera.isOpened():
            socketio.emit('stream_error', {'message': 'Failed to open camera ID 2'})
            return
        
        # Set camera properties for better performance
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        camera.set(cv2.CAP_PROP_FPS, 30)
        
        print("Camera ID 2 opened successfully")
        
        while streaming:
            ret, frame = camera.read()
            
            if not ret:
                print("Failed to read frame from camera")
                break
            
            # Convert frame to JPEG and encode as base64
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_data = base64.b64encode(buffer).decode('utf-8')
            
            # Emit frame to all connected clients
            socketio.emit('video_frame', {'frame': frame_data})
            
            # Control frame rate
            time.sleep(1/30)  # ~30 FPS
            
    except Exception as e:
        print(f"Error in camera stream: {str(e)}")
        socketio.emit('stream_error', {'message': f'Camera streaming error: {str(e)}'})
    
    finally:
        if camera:
            camera.release()
            print("Camera released")

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('start_stream')
def handle_start_stream():
    """Start camera streaming"""
    global streaming, stream_thread
    
    if not streaming:
        streaming = True
        stream_thread = threading.Thread(target=stream_camera)
        stream_thread.daemon = True
        stream_thread.start()
        
        print("Camera streaming started")
        emit('stream_started', {'message': 'Camera stream started successfully'})
    else:
        emit('stream_started', {'message': 'Camera stream already running'})

@socketio.on('stop_stream')
def handle_stop_stream():
    """Stop camera streaming"""
    global streaming, stream_thread
    
    if streaming:
        streaming = False
        
        # Wait for stream thread to finish
        if stream_thread and stream_thread.is_alive():
            stream_thread.join(timeout=2)
        
        print("Camera streaming stopped")
        emit('stream_stopped', {'message': 'Camera stream stopped'})
    else:
        emit('stream_stopped', {'message': 'Camera stream was not running'})

@app.route('/health')
def health_check():
    return {'status': 'healthy', 'camera_active': streaming}

if __name__ == '__main__':
    print(f"Starting video streaming server...")
    print(f"RTMP URL: {RTMP_URL}")
    print("Camera ID 2 will be used for streaming")
    socketio.run(app, host='0.0.0.0', port=5002, debug=True, allow_unsafe_werkzeug=True)
