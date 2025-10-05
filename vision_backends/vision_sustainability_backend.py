"""
Vision-Integrated Sustainability Backend

This module integrates the sustainability scoring system with the vision detection pipeline.
It processes detected products in real-time and provides separate scores for:
- Sustainability Score
- Nutrition Score  
- Price Analysis (web vs in-store comparison)
"""

import os
import json
import asyncio
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# Import your existing sustainability components
import sys
sys.path.append('/Users/ethanwang/hackharvard/google-gemini/backend')

from real_grocery_scorer_oxylabs import RealGroceryScorerOxylabs
from nutrition_fetcher import NutritionFetcher
from simple_news_scorer import SimpleNewsScorer
from sustainability_scorer import SustainabilityScorer
from tts_service import PriceComparisonTTS

class VisionSustainabilityAnalyzer:
    """
    Real-time sustainability analyzer for vision-detected products
    """
    
    def __init__(self):
        """Initialize the vision sustainability analyzer"""
        # Initialize all scoring components
        self.grocery_scorer = RealGroceryScorerOxylabs(
            usda_api_key=os.getenv('USDA_API_KEY'),
            news_api_key=os.getenv('GNEWS_API_KEY') or os.getenv('NEWS_API_KEY'),
            gemini_api_key=os.getenv('GEMINI_API_KEY'),
            oxylabs_username=os.getenv('OXYLABS_USERNAME'),
            oxylabs_password=os.getenv('OXYLABS_PASSWORD')
        )
        
        self.nutrition_fetcher = NutritionFetcher(os.getenv('USDA_API_KEY'))
        self.news_scorer = SimpleNewsScorer(
            news_api_key=os.getenv('GNEWS_API_KEY') or os.getenv('NEWS_API_KEY'),
            usda_api_key=os.getenv('USDA_API_KEY'),
            gemini_api_key=os.getenv('GEMINI_API_KEY')
        )
        self.sustainability_scorer = SustainabilityScorer()
        
        # Initialize TTS for announcements (bonus feature)
        try:
            self.tts_service = PriceComparisonTTS(os.getenv('ELEVENLABS_API_KEY'))
            self.tts_available = True
            print("✅ TTS service initialized successfully")
        except Exception as e:
            print(f"⚠️ TTS service not available: {e}")
            self.tts_service = None
            self.tts_available = False
    
    async def analyze_detected_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a detected product for sustainability, nutrition, and price
        
        Args:
            product_data: Dictionary containing detected product info
                - product_name: str
                - brand: str  
                - detected_price: str (from price tag)
                - confidence: float
        
        Returns:
            Dictionary with all analysis results
        """
        start_time = time.time()
        
        try:
            product_name = product_data.get('product_name', '')
            brand = product_data.get('brand', '')
            detected_price = product_data.get('detected_price', '')
            confidence = product_data.get('confidence', 0.0)
            
            print(f"🔍 Analyzing detected product: {product_name} by {brand}")
            
            # Initialize results
            results = {
                'product_name': product_name,
                'brand': brand,
                'detected_price': detected_price,
                'confidence': confidence,
                'analysis_timestamp': datetime.now().isoformat(),
                'processing_time': 0,
                'sustainability_score': 0,
                'nutrition_score': 0,
                'price_analysis': {},
                'errors': []
            }
            
            # 1. NUTRITION SCORE (Separate from sustainability)
            nutrition_score = await self._analyze_nutrition(product_name, brand)
            results['nutrition_score'] = nutrition_score
            
            # 2. SUSTAINABILITY SCORE (Environmental and social impact)
            sustainability_score = await self._analyze_sustainability(product_name, brand)
            results['sustainability_score'] = sustainability_score
            
            # 3. PRICE ANALYSIS (Web vs In-Store comparison)
            price_analysis = await self._analyze_pricing(product_name, detected_price)
            results['price_analysis'] = price_analysis
            
            # 4. BONUS: TTS Announcement (if available)
            if self.tts_available and self.tts_service:
                await self._generate_tts_announcement(results)
            
            results['processing_time'] = time.time() - start_time
            
            print(f"✅ Analysis complete in {results['processing_time']:.2f}s")
            nutrition_score_data = results.get('nutrition_score', {})
            sustainability_score_data = results.get('sustainability_score', {})
            nutrition_score_value = nutrition_score_data.get('score', nutrition_score_data if isinstance(nutrition_score_data, (int, float)) else 0)
            sustainability_score_value = sustainability_score_data.get('score', sustainability_score_data if isinstance(sustainability_score_data, (int, float)) else 0)
            print(f"   Nutrition: {nutrition_score_value:.1f}/10")
            print(f"   Sustainability: {sustainability_score_value:.1f}/10")
            price_diff = price_analysis.get('price_difference_percent', 0) if isinstance(price_analysis, dict) else 0
            print(f"   Price Analysis: {price_diff:.1f}% difference")
            
            return results
            
        except Exception as e:
            print(f"❌ Error analyzing product: {e}")
            return {
                'product_name': product_data.get('product_name', ''),
                'brand': product_data.get('brand', ''),
                'error': str(e),
                'analysis_timestamp': datetime.now().isoformat()
            }
    
    async def _analyze_nutrition(self, product_name: str, brand: str) -> Dict[str, Any]:
        """
        Analyze nutrition score separately from sustainability
        
        Returns:
            Dictionary with nutrition analysis
        """
        try:
            # Use USDA API to get nutrition data
            from nutrition_fetcher import fetch_nutrition_data
            nutrition_data = fetch_nutrition_data(product_name, self.nutrition_fetcher.api_key)
            
            if nutrition_data and nutrition_data.get('nutrition_data'):
                # Calculate nutrition score
                nutrition_score, score_breakdown = self.nutrition_fetcher.calculate_nutrition_score(
                    nutrition_data['nutrition_data']
                )
                
                return {
                    'score': nutrition_score,
                    'breakdown': score_breakdown,
                    'data_source': 'USDA',
                    'nutrition_data': nutrition_data['nutrition_data'],
                    'analysis': nutrition_data.get('analysis', 'Nutrition data analyzed')
                }
            else:
                # Fallback: basic nutrition estimation
                return {
                    'score': 5.0,  # Neutral score
                    'breakdown': {},
                    'data_source': 'estimated',
                    'analysis': 'No detailed nutrition data available'
                }
                
        except Exception as e:
            print(f"⚠️ Nutrition analysis error: {e}")
            return {
                'score': 5.0,
                'breakdown': {},
                'data_source': 'error',
                'analysis': f'Nutrition analysis failed: {str(e)}'
            }
    
    async def _analyze_sustainability(self, product_name: str, brand: str) -> Dict[str, Any]:
        """
        Analyze sustainability score (environmental and social impact)
        
        Returns:
            Dictionary with sustainability analysis
        """
        try:
            # Create a mock product for analysis
            mock_product = {
                'title': product_name,
                'price': '$0.00',  # Price not needed for sustainability
                'seller': brand,
                'url': '',
                'image': ''
            }
            
            # Get sustainability analysis
            sustainability_analysis = self.grocery_scorer.analyze_grocery_product(
                mock_product, use_usda_nutrition=False  # We already have nutrition separately
            )
            
            if sustainability_analysis and 'sustainability_analysis' in sustainability_analysis:
                analysis = sustainability_analysis['sustainability_analysis']
                
                return {
                    'score': analysis.get('sustainability_score', 5.0),
                    'carbon_score': analysis.get('breakdown', {}).get('carbon_footprint_score', 5.0),
                    'ethics_score': analysis.get('breakdown', {}).get('social_ethics_score', 5.0),
                    'analysis': analysis.get('justification', 'Sustainability analysis completed'),
                    'data_source': 'AI Analysis'
                }
            else:
                return {
                    'score': 5.0,
                    'carbon_score': 5.0,
                    'ethics_score': 5.0,
                    'analysis': 'Sustainability analysis not available',
                    'data_source': 'fallback'
                }
                
        except Exception as e:
            print(f"⚠️ Sustainability analysis error: {e}")
            return {
                'score': 5.0,
                'carbon_score': 5.0,
                'ethics_score': 5.0,
                'analysis': f'Sustainability analysis failed: {str(e)}',
                'data_source': 'error'
            }
    
    async def _analyze_pricing(self, product_name: str, detected_price: str) -> Dict[str, Any]:
        """
        Analyze pricing by comparing web prices to in-store price
        
        Returns:
            Dictionary with price analysis
        """
        try:
            # Clean detected price
            detected_price_clean = detected_price.replace('$', '').replace(',', '').strip()
            try:
                detected_price_float = float(detected_price_clean)
            except:
                detected_price_float = 0.0
            
            # Search for online prices
            online_products = self.grocery_scorer.scrape_grocery_products(product_name, num_results=5)
            
            if online_products and 'products' in online_products and online_products['products']:
                products = online_products['products']
                
                # Calculate average online price
                online_prices = []
                for product in products:
                    try:
                        price_str = product.get('price', '$0').replace('$', '').replace(',', '').strip()
                        price_float = float(price_str)
                        online_prices.append(price_float)
                    except:
                        continue
                
                if online_prices:
                    avg_online_price = sum(online_prices) / len(online_prices)
                    min_online_price = min(online_prices)
                    max_online_price = max(online_prices)
                    
                    # Calculate differences
                    price_difference = detected_price_float - avg_online_price
                    price_difference_percent = (price_difference / avg_online_price) * 100 if avg_online_price > 0 else 0
                    
                    return {
                        'detected_price': detected_price_float,
                        'avg_online_price': avg_online_price,
                        'min_online_price': min_online_price,
                        'max_online_price': max_online_price,
                        'price_difference': price_difference,
                        'price_difference_percent': price_difference_percent,
                        'is_cheaper_online': price_difference > 0,
                        'savings_opportunity': max(0, price_difference),
                        'data_source': 'Web Search',
                        'products_found': len(online_prices)
                    }
            
            return {
                'detected_price': detected_price_float,
                'avg_online_price': 0,
                'price_difference': 0,
                'price_difference_percent': 0,
                'is_cheaper_online': False,
                'data_source': 'No online data found',
                'products_found': 0
            }
            
        except Exception as e:
            print(f"⚠️ Price analysis error: {e}")
            return {
                'detected_price': 0,
                'avg_online_price': 0,
                'price_difference': 0,
                'price_difference_percent': 0,
                'is_cheaper_online': False,
                'data_source': f'Price analysis failed: {str(e)}',
                'products_found': 0
            }
    
    async def _generate_tts_announcement(self, results: Dict[str, Any]) -> Optional[str]:
        """
        Generate TTS announcement for the analysis results (bonus feature)
        
        Returns:
            Filename of generated audio file, or None
        """
        try:
            if not self.tts_available or not self.tts_service:
                return None
            
            product_name = results.get('product_name', 'Product')
            nutrition_data = results.get('nutrition_score', {})
            sustainability_data = results.get('sustainability_score', {})
            price_analysis = results.get('price_analysis', {})
            
            # Extract actual scores from the data structures
            if isinstance(nutrition_data, dict):
                nutrition_score = nutrition_data.get('score', 5)
            elif isinstance(nutrition_data, tuple):
                nutrition_score = nutrition_data[0]  # First element is the score
            else:
                nutrition_score = 5
            
            if isinstance(sustainability_data, dict):
                sustainability_score = sustainability_data.get('score', 5)
            else:
                sustainability_score = sustainability_data if sustainability_data else 5
            
            # Format scores with one decimal place for clearer announcements
            try:
                nutrition_score = round(float(nutrition_score), 1) if nutrition_score is not None else 5.0
                sustainability_score = round(float(sustainability_score), 1) if sustainability_score is not None else 5.0
            except (ValueError, TypeError):
                nutrition_score = 5.0
                sustainability_score = 5.0
            
            # Create announcement text
            announcement = f"""
            {product_name} detected. 
            Nutrition score: {nutrition_score:.1f} out of 10. 
            Sustainability score: {sustainability_score:.1f} out of 10.
            """
            
            if isinstance(price_analysis, dict) and price_analysis.get('products_found', 0) > 0:
                price_diff = price_analysis.get('price_difference_percent', 0)
                try:
                    price_diff = int(float(price_diff)) if price_diff else 0
                except (ValueError, TypeError):
                    price_diff = 0
                
                if price_diff > 0:
                    announcement += f" Online price is {abs(price_diff):.1f} percent cheaper."
                elif price_diff < 0:
                    announcement += f" Store price is {abs(price_diff):.1f} percent cheaper."
                else:
                    announcement += " Prices are similar online and in store."
            
            # Generate audio
            audio_data = self.tts_service.tts.text_to_speech(announcement.strip())
            if audio_data:
                filename = f"product_announcement_{int(time.time())}.mp3"
                self.tts_service.tts.save_audio(audio_data, filename)
                return filename
            
            return None
            
        except Exception as e:
            print(f"⚠️ TTS announcement error: {e}")
            return None


# Initialize the analyzer
vision_analyzer = VisionSustainabilityAnalyzer()

# Flask app for API endpoints
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Vision Sustainability Analyzer',
        'timestamp': datetime.now().isoformat(),
        'tts_available': vision_analyzer.tts_available
    })

@app.route('/analyze-product', methods=['POST'])
def analyze_product_endpoint():
    """Analyze a detected product"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Run async analysis
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(vision_analyzer.analyze_detected_product(data))
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@socketio.on('analyze_detected_product')
def handle_analyze_product(data):
    """Handle real-time product analysis via WebSocket"""
    try:
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
    print("🔬 Starting Vision Sustainability Analyzer...")
    print("📊 Features:")
    print("   - Real-time product analysis")
    print("   - Separate nutrition and sustainability scoring")
    print("   - Price analysis (web vs in-store)")
    print("   - TTS announcements")
    print("🌐 Starting server on port 5003...")
    
    socketio.run(app, host='0.0.0.0', port=5003, debug=True, allow_unsafe_werkzeug=True)
