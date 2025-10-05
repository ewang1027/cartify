"""
Meta Ray-Bans Integration for Live Streaming with TTS

This module provides integration between the sustainability scoring system
and Meta Ray-Bans for real-time price comparisons and sustainability announcements.
"""

import os
import json
import time
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
from flask import request, jsonify
from tts_service import PriceComparisonTTS
from real_grocery_scorer_oxylabs import RealGroceryScorerOxylabs


class RayBanLiveStreamer:
    """
    Meta Ray-Bans live streaming integration with TTS announcements
    """
    
    def __init__(self, elevenlabs_api_key: Optional[str] = None):
        """
        Initialize Ray-Bans live streaming service
        
        Args:
            elevenlabs_api_key: ElevenLabs API key for TTS
        """
        try:
            self.tts_service = PriceComparisonTTS(elevenlabs_api_key)
            self.tts_available = True
        except Exception as e:
            print(f"⚠️ TTS service not available: {e}")
            self.tts_service = None
            self.tts_available = False
            
        self.grocery_scorer = RealGroceryScorerOxylabs()
        self.is_streaming = False
        self.current_product = None
        self.price_comparison_data = {}
        
    def start_live_stream(self, store_location: str = "Unknown Store") -> bool:
        """
        Start live streaming session
        
        Args:
            store_location: Physical store location
            
        Returns:
            True if started successfully
        """
        try:
            self.is_streaming = True
            self.store_location = store_location
            
            # Generate welcome announcement
            if self.tts_available:
                welcome_text = f"""
                Live sustainability shopping session started at {store_location}. 
                I'll help you compare prices and analyze product sustainability in real-time.
                """
                
                welcome_audio = self.tts_service.tts.text_to_speech(welcome_text.strip())
                if welcome_audio:
                    self.tts_service.tts.save_audio(welcome_audio, "welcome_announcement.mp3")
                    print("🎤 Welcome announcement generated")
            else:
                print("⚠️ TTS not available - welcome announcement skipped")
            
            print(f"📹 Live streaming started at {store_location}")
            return True
            
        except Exception as e:
            print(f"❌ Error starting live stream: {e}")
            return False
    
    def stop_live_stream(self) -> bool:
        """
        Stop live streaming session
        
        Returns:
            True if stopped successfully
        """
        try:
            self.is_streaming = False
            
            # Generate closing announcement
            if self.tts_available:
                closing_text = """
                Live sustainability shopping session ended. 
                Thank you for using our real-time price and sustainability analysis.
                """
                
                closing_audio = self.tts_service.tts.text_to_speech(closing_text.strip())
                if closing_audio:
                    self.tts_service.tts.save_audio(closing_audio, "closing_announcement.mp3")
                    print("🎤 Closing announcement generated")
            else:
                print("⚠️ TTS not available - closing announcement skipped")
            
            print("📹 Live streaming stopped")
            return True
            
        except Exception as e:
            print(f"❌ Error stopping live stream: {e}")
            return False
    
    def analyze_product_live(self, product_name: str, store_price: str) -> Dict[str, Any]:
        """
        Analyze product in real-time during live streaming
        
        Args:
            product_name: Name of the product being analyzed
            store_price: Price observed in store (e.g., "$4.99")
            
        Returns:
            Dictionary containing analysis results and TTS audio
        """
        try:
            print(f"🔍 Analyzing {product_name} live...")
            
            # Get online price and sustainability data
            online_data = self.grocery_scorer.scrape_grocery_products(product_name, num_results=5)
            
            if not online_data.get('products'):
                return {
                    'error': 'No online data found',
                    'product_name': product_name,
                    'store_price': store_price
                }
            
            # Find best online price
            best_online_product = min(online_data['products'], 
                                    key=lambda x: float(x.get('price', '$999').replace('$', '').replace(',', '')))
            online_price = best_online_product.get('price', '$0')
            
            # Get sustainability analysis
            sustainability_data = self.grocery_scorer.analyze_product_sustainability(
                best_online_product, use_usda_nutrition=True
            )
            
            sustainability_score = sustainability_data.get('sustainability_analysis', {}).get('sustainability_score', 0)
            
            # Generate TTS announcements
            price_announcement = None
            sustainability_announcement = None
            
            if self.tts_available:
                price_announcement = self.tts_service.generate_price_comparison_announcement(
                    product_name, online_price, store_price, sustainability_score
                )
                
                sustainability_announcement = self.tts_service.generate_sustainability_announcement(
                    product_name, sustainability_data.get('sustainability_analysis', {})
                )
            
            # Save audio files
            audio_files = {}
            if price_announcement:
                price_filename = f"price_announcement_{int(time.time())}.mp3"
                self.tts_service.tts.save_audio(price_announcement, price_filename)
                audio_files['price_announcement'] = price_filename
            
            if sustainability_announcement:
                sustainability_filename = f"sustainability_announcement_{int(time.time())}.mp3"
                self.tts_service.tts.save_audio(sustainability_announcement, sustainability_filename)
                audio_files['sustainability_announcement'] = sustainability_filename
            
            # Calculate price difference
            try:
                online_val = float(online_price.replace('$', '').replace(',', ''))
                store_val = float(store_price.replace('$', '').replace(',', ''))
                price_difference = store_val - online_val
                is_cheaper_online = price_difference > 0
            except:
                price_difference = 0
                is_cheaper_online = False
            
            result = {
                'product_name': product_name,
                'store_price': store_price,
                'online_price': online_price,
                'price_difference': price_difference,
                'is_cheaper_online': is_cheaper_online,
                'sustainability_score': sustainability_score,
                'sustainability_analysis': sustainability_data.get('sustainability_analysis', {}),
                'audio_files': audio_files,
                'timestamp': datetime.now().isoformat(),
                'store_location': getattr(self, 'store_location', 'Unknown')
            }
            
            self.current_product = result
            return result
            
        except Exception as e:
            print(f"❌ Error analyzing product live: {e}")
            return {
                'error': str(e),
                'product_name': product_name,
                'store_price': store_price
            }
    
    def generate_quick_alert(self, product_name: str, alert_type: str = "price") -> Optional[str]:
        """
        Generate quick alert for live streaming
        
        Args:
            product_name: Name of the product
            alert_type: Type of alert ("price" or "sustainability")
            
        Returns:
            Filename of generated audio file
        """
        try:
            if not self.current_product or not self.tts_available:
                return None
            
            if alert_type == "price":
                price_diff = self.current_product.get('price_difference', 0)
                is_cheaper = self.current_product.get('is_cheaper_online', False)
                audio_data = self.tts_service.generate_quick_price_alert(
                    product_name, abs(price_diff), is_cheaper
                )
            elif alert_type == "sustainability":
                score = self.current_product.get('sustainability_score', 0)
                audio_data = self.tts_service.generate_sustainability_quick_alert(
                    product_name, score
                )
            else:
                return None
            
            if audio_data:
                filename = f"quick_alert_{alert_type}_{int(time.time())}.mp3"
                self.tts_service.tts.save_audio(audio_data, filename)
                return filename
            
            return None
            
        except Exception as e:
            print(f"❌ Error generating quick alert: {e}")
            return None
    
    def get_streaming_status(self) -> Dict[str, Any]:
        """
        Get current streaming status
        
        Returns:
            Dictionary containing streaming status
        """
        return {
            'is_streaming': self.is_streaming,
            'current_product': self.current_product,
            'store_location': getattr(self, 'store_location', 'Unknown'),
            'timestamp': datetime.now().isoformat()
        }


class RayBanAPI:
    """
    Flask API for Ray-Bans integration
    """
    
    def __init__(self, elevenlabs_api_key: Optional[str] = None):
        """
        Initialize Ray-Bans API
        
        Args:
            elevenlabs_api_key: ElevenLabs API key
        """
        self.streamer = RayBanLiveStreamer(elevenlabs_api_key)
    
    def create_flask_routes(self, app):
        """
        Create Flask routes for Ray-Bans integration
        
        Args:
            app: Flask app instance
        """
        
        @app.route('/ray-ban/start-stream', methods=['POST'])
        def start_stream():
            """Start live streaming session"""
            try:
                data = request.get_json() or {}
                store_location = data.get('store_location', 'Unknown Store')
                
                success = self.streamer.start_live_stream(store_location)
                
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
                success = self.streamer.stop_live_stream()
                
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
                
                result = self.streamer.analyze_product_live(product_name, store_price)
                
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
                
                audio_filename = self.streamer.generate_quick_alert(product_name, alert_type)
                
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
                status = self.streamer.get_streaming_status()
                return jsonify({
                    'status': 'success',
                    'data': status
                })
                
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500


def test_ray_ban_integration():
    """
    Test Ray-Bans integration functionality
    """
    print("🥽 Testing Ray-Bans Integration...")
    
    try:
        # Initialize Ray-Bans streamer
        streamer = RayBanLiveStreamer()
        
        # Test starting stream
        print("📹 Starting live stream...")
        success = streamer.start_live_stream("Whole Foods Market")
        if success:
            print("✅ Live stream started")
        else:
            print("❌ Failed to start live stream")
            return
        
        # Test product analysis
        print("🔍 Analyzing product live...")
        result = streamer.analyze_product_live("Organic Apples", "$4.99")
        
        if 'error' not in result:
            print("✅ Product analysis successful")
            print(f"   Product: {result['product_name']}")
            print(f"   Store Price: {result['store_price']}")
            print(f"   Online Price: {result['online_price']}")
            print(f"   Sustainability Score: {result['sustainability_score']}/10")
            print(f"   Audio Files: {result['audio_files']}")
        else:
            print(f"❌ Product analysis failed: {result['error']}")
        
        # Test quick alert
        print("🚨 Testing quick alert...")
        alert_file = streamer.generate_quick_alert("Organic Apples", "price")
        if alert_file:
            print(f"✅ Quick alert generated: {alert_file}")
        else:
            print("❌ Quick alert failed")
        
        # Test stopping stream
        print("📹 Stopping live stream...")
        success = streamer.stop_live_stream()
        if success:
            print("✅ Live stream stopped")
        else:
            print("❌ Failed to stop live stream")
            
    except Exception as e:
        print(f"❌ Ray-Bans Integration Test Error: {e}")


if __name__ == "__main__":
    test_ray_ban_integration()
