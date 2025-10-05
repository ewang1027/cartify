#!/usr/bin/env python3
"""
Video Stream Server for CV2 Feed
Streams CV2 video output to frontend via SocketIO
Works efficiently on localhost for same-machine setups
"""

from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import cv2
import base64
import threading
import time
import os
import sys
import asyncio

# Import your existing CV2 processing
from center_object_classifier import CenterObjectClassifier

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Camera streaming variables
camera = None
streaming = False
stream_thread = None
camera_lock = threading.Lock()

# CV2 Classifier instance
classifier = None

# Configuration
CAMERA_ID = 1  # Change this to your camera ID
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 30
JPEG_QUALITY = 85

def process_frame_with_classifier(frame):
    """
    Process frame using your CenterObjectClassifier
    This adds motion detection, scene change detection, and bounding boxes
    """
    global classifier
    
    try:
        if classifier is None:
            return frame
            
        # Process frame with your classifier (sync wrapper for async function)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        detection_data = loop.run_until_complete(classifier.process_frame(frame))
        loop.close()
        
        # Draw detections on the frame
        classifier.draw_detections(frame, detection_data)
        
        return frame
    except Exception as e:
        print(f"⚠️ Error processing frame: {e}")
        # Return original frame if processing fails
        return frame

def stream_camera():
    """Stream camera frames to connected clients"""
    global camera, streaming, classifier
    
    try:
        # Initialize classifier with your existing CV2 processing
        print("🔧 Initializing CenterObjectClassifier...")
        classifier = CenterObjectClassifier(enable_tts=False)  # Disable TTS for streaming
        print("✅ Classifier initialized")
        
        with camera_lock:
            camera = cv2.VideoCapture(CAMERA_ID)
            
            if not camera.isOpened():
                print(f"❌ Failed to open camera ID {CAMERA_ID}")
                socketio.emit('stream_error', {
                    'message': f'Failed to open camera ID {CAMERA_ID}'
                })
                return
            
            # Set camera properties
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
            camera.set(cv2.CAP_PROP_FPS, FPS)
        
        print(f"✅ Camera ID {CAMERA_ID} opened successfully")
        print(f"📹 Resolution: {FRAME_WIDTH}x{FRAME_HEIGHT} @ {FPS}fps")
        print(f"🎨 CV2 Processing: Motion Detection + Scene Change Detection")
        
        frame_count = 0
        start_time = time.time()
        
        while streaming:
            with camera_lock:
                if camera is None or not camera.isOpened():
                    break
                    
                ret, frame = camera.read()
            
            if not ret:
                print("⚠️  Failed to read frame from camera")
                time.sleep(0.1)
                continue
            
            # Process frame with your CenterObjectClassifier CV2 code
            processed_frame = process_frame_with_classifier(frame)
            
            # Encode frame as JPEG
            encode_param = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
            _, buffer = cv2.imencode('.jpg', processed_frame, encode_param)
            frame_data = base64.b64encode(buffer).decode('utf-8')
            
            # Emit frame to all connected clients
            socketio.emit('video_frame', {
                'frame': frame_data,
                'timestamp': time.time(),
                'frame_count': frame_count
            })
            
            frame_count += 1
            
            # Log FPS every 100 frames
            if frame_count % 100 == 0:
                elapsed = time.time() - start_time
                actual_fps = frame_count / elapsed
                print(f"📊 Streaming at {actual_fps:.1f} FPS (sent {frame_count} frames)")
            
            # Control frame rate
            time.sleep(1/FPS)
            
    except Exception as e:
        print(f"❌ Error in camera stream: {str(e)}")
        socketio.emit('stream_error', {'message': f'Camera streaming error: {str(e)}'})
    
    finally:
        with camera_lock:
            if camera:
                camera.release()
                camera = None
        print("🔴 Camera released")

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"✅ Client connected: {request.sid if 'request' in dir() else 'unknown'}")
    emit('connection_status', {'status': 'connected', 'streaming': streaming})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"🔌 Client disconnected")

@socketio.on('start_stream')
def handle_start_stream():
    """Start the camera stream"""
    global streaming, stream_thread
    
    if streaming:
        print("⚠️  Stream already running")
        emit('stream_started', {'message': 'Stream already active'})
        return
    
    print("🎬 Starting camera stream...")
    streaming = True
    stream_thread = threading.Thread(target=stream_camera, daemon=True)
    stream_thread.start()
    
    emit('stream_started', {
        'message': 'Stream started successfully',
        'camera_id': CAMERA_ID,
        'resolution': f"{FRAME_WIDTH}x{FRAME_HEIGHT}",
        'fps': FPS
    }, broadcast=True)

@socketio.on('stop_stream')
def handle_stop_stream():
    """Stop the camera stream"""
    global streaming, camera
    
    if not streaming:
        print("⚠️  Stream not running")
        emit('stream_stopped', {'message': 'Stream was not active'})
        return
    
    print("🛑 Stopping camera stream...")
    streaming = False
    
    # Wait for thread to finish
    if stream_thread and stream_thread.is_alive():
        stream_thread.join(timeout=2)
    
    with camera_lock:
        if camera:
            camera.release()
            camera = None
    
    emit('stream_stopped', {'message': 'Stream stopped successfully'}, broadcast=True)

@socketio.on('request_frame')
def handle_frame_request():
    """Client requesting single frame (for debugging)"""
    if not streaming:
        emit('stream_error', {'message': 'Stream not active'})

@app.route('/')
def index():
    """Health check endpoint"""
    return {
        'status': 'online',
        'service': 'CV2 Video Stream Server',
        'streaming': streaming,
        'camera_id': CAMERA_ID,
        'resolution': f"{FRAME_WIDTH}x{FRAME_HEIGHT}",
        'fps': FPS
    }

@app.route('/health')
def health():
    """Health check"""
    return {'status': 'healthy', 'streaming': streaming}

if __name__ == '__main__':
    print("=" * 70)
    print("🎥 CV2 Video Stream Server Starting...")
    print("=" * 70)
    print(f"📍 Server: http://localhost:5001")
    print(f"📹 Camera ID: {CAMERA_ID}")
    print(f"📐 Resolution: {FRAME_WIDTH}x{FRAME_HEIGHT}")
    print(f"🎞️  Target FPS: {FPS}")
    print(f"💾 JPEG Quality: {JPEG_QUALITY}%")
    print("=" * 70)
    print("\n✨ Connect your frontend to: http://localhost:5001")
    print("📡 SocketIO events:")
    print("   - emit 'start_stream' to start")
    print("   - emit 'stop_stream' to stop")
    print("   - listen for 'video_frame' to receive frames")
    print("\nPress Ctrl+C to stop\n")
    
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, allow_unsafe_werkzeug=True)
