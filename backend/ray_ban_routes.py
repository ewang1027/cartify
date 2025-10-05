"""
Ray-Bans Flask Routes

This module contains the Flask route definitions for Ray-Bans integration.
Separated from the main integration class to avoid import scope issues.
"""

from flask import request, jsonify
from datetime import datetime


def create_ray_ban_routes(app, ray_ban_api):
    """
    Create Flask routes for Ray-Bans integration
    
    Args:
        app: Flask app instance
        ray_ban_api: RayBanAPI instance
    """
    
    @app.route('/ray-ban/start-stream', methods=['POST'])
    def start_stream():
        """Start live streaming session"""
        try:
            data = request.get_json() or {}
            store_location = data.get('store_location', 'Unknown Store')
            
            success = ray_ban_api.streamer.start_live_stream(store_location)
            
            if success:
                return jsonify({
                    'status': 'success',
                    'message': 'Live streaming started',
                    'store_location': store_location,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to start live streaming'
                }), 500
                
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/ray-ban/stop-stream', methods=['POST'])
    def stop_stream():
        """Stop live streaming session"""
        try:
            success = ray_ban_api.streamer.stop_live_stream()
            
            if success:
                return jsonify({
                    'status': 'success',
                    'message': 'Live streaming stopped',
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to stop live streaming'
                }), 500
                
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/ray-ban/analyze-product', methods=['POST'])
    def analyze_product():
        """Analyze product in real-time"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'status': 'error',
                    'message': 'No data provided'
                }), 400
            
            product_name = data.get('product_name')
            store_price = data.get('store_price')
            
            if not product_name or not store_price:
                return jsonify({
                    'status': 'error',
                    'message': 'product_name and store_price are required'
                }), 400
            
            result = ray_ban_api.streamer.analyze_product_live(product_name, store_price)
            
            return jsonify({
                'status': 'success',
                'data': result
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/ray-ban/quick-alert', methods=['POST'])
    def quick_alert():
        """Generate quick alert"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'status': 'error',
                    'message': 'No data provided'
                }), 400
            
            product_name = data.get('product_name')
            alert_type = data.get('alert_type', 'price')
            
            if not product_name:
                return jsonify({
                    'status': 'error',
                    'message': 'product_name is required'
                }), 400
            
            audio_filename = ray_ban_api.streamer.generate_quick_alert(product_name, alert_type)
            
            if audio_filename:
                return jsonify({
                    'status': 'success',
                    'audio_file': audio_filename,
                    'alert_type': alert_type
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to generate alert'
                }), 500
                
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/ray-ban/status', methods=['GET'])
    def get_status():
        """Get streaming status"""
        try:
            status = ray_ban_api.streamer.get_streaming_status()
            return jsonify({
                'status': 'success',
                'data': status
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
