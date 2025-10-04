import cv2
import time
import json
import numpy as np
from flask import Flask, Response, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app, resources={r"/*": {"origins": "*"}})

def generate_frames():
    global stream
    while True:
        frame_data = stream.get_frame()
        if frame_data:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
        else:
            # If no frame, send a blank image
            blank = np.zeros((480, 640, 3), np.uint8)
            ret, buffer = cv2.imencode('.jpg', blank)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        # Control the MJPEG stream rate
        time.sleep(0.03)  # ~30fps

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@socketio.on('connect')
def handle_connect():
    print('Client connected to WebSocket')
    # Send initial embedding visualization on connect
    global stream
    if stream:
        viz_data = stream.embedding_visualizer.generate_visualization_data()
        socketio.emit('embedding_visualization', viz_data)

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected from WebSocket')


if __name__ == '__main__':
    app.run(debug=True)
