"""
Simple Vision App with Sustainability Analysis
A simplified version that focuses on core functionality
"""

from flask import Flask, render_template_string, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import cv2
import base64
import threading
import time
import os
import asyncio
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Camera streaming variables
camera = None
streaming = False
stream_thread = None

# Simple HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vision Sustainability Analyzer</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .main-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .video-section, .analysis-section {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
        }
        #videoStream {
            width: 100%;
            border-radius: 10px;
            max-height: 400px;
        }
        .controls {
            margin: 20px 0;
            text-align: center;
        }
        button {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 12px 24px;
            margin: 0 10px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s;
        }
        button:hover {
            background: #45a049;
            transform: translateY(-2px);
        }
        button:disabled {
            background: #666;
            cursor: not-allowed;
        }
        .status {
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
            text-align: center;
        }
        .status.connected { background: rgba(76, 175, 80, 0.3); }
        .status.disconnected { background: rgba(244, 67, 54, 0.3); }
        .product-analysis {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #4CAF50;
        }
        .score-display {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 15px;
            margin: 20px 0;
        }
        .score-card {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            padding: 15px;
            text-align: center;
        }
        .score-value {
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }
        .score-label {
            font-size: 0.9em;
            opacity: 0.8;
        }
        .nutrition-score { border-left: 4px solid #FF9800; }
        .sustainability-score { border-left: 4px solid #4CAF50; }
        .price-analysis { border-left: 4px solid #2196F3; }
        .loading {
            text-align: center;
            padding: 20px;
            color: #FF9800;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🥽 Vision Sustainability Analyzer</h1>
            <p>Real-time product analysis with nutrition, sustainability, and price scoring</p>
        </div>
        
        <div class="main-content">
            <div class="video-section">
                <h3>📹 Live Camera Feed</h3>
                <img id="videoStream" src="" alt="Camera Feed">
                <div class="controls">
                    <button id="startBtn" onclick="startStream()">Start Camera</button>
                    <button id="stopBtn" onclick="stopStream()" disabled>Stop Camera</button>
                </div>
                <div id="status" class="status disconnected">Disconnected</div>
            </div>
            
            <div class="analysis-section">
                <h3>📊 Product Analysis</h3>
                <div id="analysisResults">
                    <div class="loading">Waiting for product detection...</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        
        // Connection status
        socket.on('connect', function() {
            document.getElementById('status').textContent = 'Connected';
            document.getElementById('status').className = 'status connected';
        });
        
        socket.on('disconnect', function() {
            document.getElementById('status').textContent = 'Disconnected';
            document.getElementById('status').className = 'status disconnected';
        });
        
        // Video stream handling
        socket.on('video_frame', function(data) {
            document.getElementById('videoStream').src = 'data:image/jpeg;base64,' + data.frame;
        });
        
        socket.on('stream_started', function(data) {
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
            document.getElementById('status').textContent = 'Streaming';
            document.getElementById('status').className = 'status connected';
        });
        
        socket.on('stream_stopped', function(data) {
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
            document.getElementById('status').textContent = 'Stopped';
            document.getElementById('status').className = 'status disconnected';
        });
        
        // Product analysis results
        socket.on('product_analysis_result', function(data) {
            displayAnalysisResults(data);
        });
        
        socket.on('analysis_error', function(data) {
            document.getElementById('analysisResults').innerHTML = 
                '<div class="status disconnected">Analysis Error: ' + data.error + '</div>';
        });
        
        function startStream() {
            socket.emit('start_stream');
        }
        
        function stopStream() {
            socket.emit('stop_stream');
        }
        
        function displayAnalysisResults(data) {
            const resultsDiv = document.getElementById('analysisResults');
            
            if (data.error) {
                resultsDiv.innerHTML = '<div class="status disconnected">Error: ' + data.error + '</div>';
                return;
            }
            
            const nutritionScore = data.nutrition_score?.score || 0;
            const sustainabilityScore = data.sustainability_score?.score || 0;
            const priceAnalysis = data.price_analysis || {};
            
            resultsDiv.innerHTML = `
                <div class="product-analysis">
                    <h4>${data.product_name || 'Unknown Product'}</h4>
                    <p><strong>Brand:</strong> ${data.brand || 'Unknown'}</p>
                    <p><strong>Detected Price:</strong> $${data.detected_price || 'N/A'}</p>
                    <p><strong>Confidence:</strong> ${(data.confidence * 100).toFixed(1)}%</p>
                </div>
                
                <div class="score-display">
                    <div class="score-card nutrition-score">
                        <div class="score-label">Nutrition Score</div>
                        <div class="score-value">${nutritionScore.toFixed(1)}</div>
                        <div class="score-label">/ 10</div>
                    </div>
                    
                    <div class="score-card sustainability-score">
                        <div class="score-label">Sustainability Score</div>
                        <div class="score-value">${sustainabilityScore.toFixed(1)}</div>
                        <div class="score-label">/ 10</div>
                    </div>
                    
                    <div class="score-card price-analysis">
                        <div class="score-label">Price Analysis</div>
                        <div class="score-value">${priceAnalysis.price_difference_percent?.toFixed(1) || 'N/A'}</div>
                        <div class="score-label">% difference</div>
                    </div>
                </div>
                
                <div class="product-details">
                    <h4>Detailed Analysis:</h4>
                    <p><strong>Nutrition:</strong> ${data.nutrition_score?.analysis || 'No analysis available'}</p>
                    <p><strong>Sustainability:</strong> ${data.sustainability_score?.analysis || 'No analysis available'}</p>
                    
                    ${priceAnalysis.products_found > 0 ? `
                        <div class="price-comparison">
                            <h5>💰 Price Comparison</h5>
                            <p><strong>In-Store:</strong> $${priceAnalysis.detected_price?.toFixed(2) || 'N/A'}</p>
                            <p><strong>Average Online:</strong> $${priceAnalysis.avg_online_price?.toFixed(2) || 'N/A'}</p>
                            <p><strong>Savings Opportunity:</strong> $${priceAnalysis.savings_opportunity?.toFixed(2) || 'N/A'}</p>
                            <p><strong>Products Found:</strong> ${priceAnalysis.products_found}</p>
                        </div>
                    ` : '<p>No online price data available</p>'}
                </div>
                
                <div class="product-details">
                    <p><strong>Analysis Time:</strong> ${data.processing_time?.toFixed(2)}s</p>
                    <p><strong>Timestamp:</strong> ${new Date(data.analysis_timestamp).toLocaleString()}</p>
                </div>
            `;
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the main interface"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/health')
def health_check():
    return {'status': 'healthy', 'camera_active': streaming}

# Camera streaming functions
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
            
            # Simulate product detection every 10 seconds for demo
            if int(time.time()) % 10 == 0:
                simulate_product_detection()
            
            # Control frame rate
            time.sleep(1/30)  # ~30 FPS
            
    except Exception as e:
        print(f"Error in camera stream: {str(e)}")
        socketio.emit('stream_error', {'message': f'Camera streaming error: {str(e)}'})
    
    finally:
        if camera:
            camera.release()
            print("Camera released")

def simulate_product_detection():
    """Simulate product detection for testing"""
    # This is where you would integrate with your actual product detection
    # For now, we'll simulate detecting a product every 10 seconds
    
    # Simulate detected product data
    detected_product = {
        'product_name': 'Organic Apples',
        'brand': 'Whole Foods',
        'detected_price': '4.99',
        'confidence': 0.85
    }
    
    # Analyze the detected product using the vision analyzer
    try:
        # Import here to avoid circular imports
        from vision_sustainability_backend import vision_analyzer
        
        # Run async analysis
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(vision_analyzer.analyze_detected_product(detected_product))
        loop.close()
        
        # Emit results to all connected clients
        socketio.emit('product_analysis_result', result)
        
    except Exception as e:
        print(f"Error in product analysis: {e}")
        socketio.emit('analysis_error', {'error': str(e)})

# Socket.IO event handlers
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

@socketio.on('analyze_detected_product')
def handle_analyze_product(data):
    """Handle real-time product analysis via WebSocket"""
    try:
        # Import here to avoid circular imports
        from vision_sustainability_backend import vision_analyzer
        
        # Run async analysis
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(vision_analyzer.analyze_detected_product(data))
        loop.close()
        
        # Emit results to all connected clients
        emit('product_analysis_result', result)
        
    except Exception as e:
        emit('analysis_error', {'error': str(e)})

if __name__ == '__main__':
    print("🥽 Starting Simple Vision Sustainability App...")
    print("📊 Features:")
    print("   - Live camera streaming")
    print("   - Real-time product detection")
    print("   - Separate nutrition and sustainability scoring")
    print("   - Price analysis (web vs in-store)")
    print("   - TTS announcements")
    print("🌐 Starting server on port 5005...")
    print("🔗 Open http://localhost:5005 in your browser")
    
    socketio.run(app, host='0.0.0.0', port=5005, debug=True, allow_unsafe_werkzeug=True)
