"""
Meta Ray-Bans Live Streaming Demo

This script demonstrates how to use the Ray-Bans integration for live streaming
with real-time price comparisons and sustainability announcements.
"""

import os
import time
import json
from dotenv import load_dotenv
from ray_ban_integration import RayBanLiveStreamer

# Load environment variables
load_dotenv('/Users/ethanwang/hackharvard/google-gemini/backend/.env')

def demo_live_shopping_session():
    """
    Demo a live shopping session with Ray-Bans
    """
    print("🥽 META RAY-BANS LIVE STREAMING DEMO")
    print("=" * 50)
    
    # Initialize Ray-Bans streamer
    try:
        streamer = RayBanLiveStreamer()
        print("✅ Ray-Bans streamer initialized")
    except Exception as e:
        print(f"❌ Error initializing Ray-Bans streamer: {e}")
        return
    
    # Start live streaming session
    print("\n📹 Starting live streaming session...")
    success = streamer.start_live_stream("Whole Foods Market - Downtown")
    
    if not success:
        print("❌ Failed to start live streaming session")
        return
    
    print("✅ Live streaming session started")
    
    # Demo products to analyze
    demo_products = [
        {"name": "Organic Apples", "store_price": "$4.99"},
        {"name": "Coca Cola", "store_price": "$2.49"},
        {"name": "Whole Milk", "store_price": "$3.99"},
        {"name": "Fair Trade Coffee", "store_price": "$12.99"},
        {"name": "Organic Bananas", "store_price": "$1.99"}
    ]
    
    print(f"\n🛒 Analyzing {len(demo_products)} products live...")
    
    for i, product in enumerate(demo_products, 1):
        print(f"\n🔍 Product {i}/{len(demo_products)}: {product['name']}")
        print(f"   Store Price: {product['store_price']}")
        
        # Analyze product in real-time
        result = streamer.analyze_product_live(
            product['name'], 
            product['store_price']
        )
        
        if 'error' in result:
            print(f"   ❌ Analysis failed: {result['error']}")
            continue
        
        # Display results
        print(f"   📊 Analysis Results:")
        print(f"      Online Price: {result['online_price']}")
        print(f"      Price Difference: ${result['price_difference']:.2f}")
        print(f"      Cheaper Online: {'Yes' if result['is_cheaper_online'] else 'No'}")
        print(f"      Sustainability Score: {result['sustainability_score']:.1f}/10")
        
        # Show audio files generated
        if result['audio_files']:
            print(f"      🎤 Audio Files Generated:")
            for audio_type, filename in result['audio_files'].items():
                print(f"         {audio_type}: {filename}")
        
        # Generate quick alerts
        print(f"   🚨 Generating quick alerts...")
        
        price_alert = streamer.generate_quick_alert(product['name'], "price")
        if price_alert:
            print(f"      Price alert: {price_alert}")
        
        sustainability_alert = streamer.generate_quick_alert(product['name'], "sustainability")
        if sustainability_alert:
            print(f"      Sustainability alert: {sustainability_alert}")
        
        # Simulate real-time delay
        time.sleep(2)
    
    # Stop live streaming session
    print(f"\n📹 Stopping live streaming session...")
    success = streamer.stop_live_stream()
    
    if success:
        print("✅ Live streaming session stopped")
    else:
        print("❌ Failed to stop live streaming session")
    
    # Show final status
    status = streamer.get_streaming_status()
    print(f"\n📊 Final Status:")
    print(f"   Streaming: {status['is_streaming']}")
    print(f"   Store Location: {status['store_location']}")
    print(f"   Last Product: {status['current_product']['product_name'] if status['current_product'] else 'None'}")


def demo_tts_functionality():
    """
    Demo TTS functionality
    """
    print("\n🎤 TEXT-TO-SPEECH DEMO")
    print("=" * 30)
    
    try:
        from tts_service import PriceComparisonTTS
        
        # Initialize TTS service
        tts_service = PriceComparisonTTS()
        print("✅ TTS service initialized")
        
        # Test basic TTS
        print("\n🔊 Testing basic TTS...")
        test_text = "Hello, this is a test of the ElevenLabs text-to-speech service for Meta Ray-Bans."
        audio_data = tts_service.tts.text_to_speech(test_text)
        
        if audio_data:
            tts_service.tts.save_audio(audio_data, "basic_tts_test.mp3")
            print("✅ Basic TTS test completed - saved to basic_tts_test.mp3")
        else:
            print("❌ Basic TTS test failed")
        
        # Test price comparison TTS
        print("\n💰 Testing price comparison TTS...")
        price_audio = tts_service.generate_price_comparison_announcement(
            "Organic Apples",
            "$4.99",
            "$5.49",
            7.5
        )
        
        if price_audio:
            tts_service.tts.save_audio(price_audio, "price_comparison_test.mp3")
            print("✅ Price comparison TTS test completed - saved to price_comparison_test.mp3")
        else:
            print("❌ Price comparison TTS test failed")
        
        # Test sustainability TTS
        print("\n🌱 Testing sustainability TTS...")
        sustainability_data = {
            'sustainability_score': 7.5,
            'breakdown': {
                'nutrition_score': 8.0,
                'carbon_footprint_score': 6.5,
                'social_ethics_score': 8.0
            }
        }
        
        sustainability_audio = tts_service.generate_sustainability_announcement(
            "Organic Apples",
            sustainability_data
        )
        
        if sustainability_audio:
            tts_service.tts.save_audio(sustainability_audio, "sustainability_test.mp3")
            print("✅ Sustainability TTS test completed - saved to sustainability_test.mp3")
        else:
            print("❌ Sustainability TTS test failed")
            
    except Exception as e:
        print(f"❌ TTS Demo Error: {e}")


def demo_api_endpoints():
    """
    Demo API endpoints for Ray-Bans integration
    """
    print("\n🌐 API ENDPOINTS DEMO")
    print("=" * 30)
    
    print("Available Ray-Bans API endpoints:")
    print("  POST /ray-ban/start-stream - Start live streaming session")
    print("  POST /ray-ban/stop-stream - Stop live streaming session")
    print("  POST /ray-ban/analyze-product - Analyze product in real-time")
    print("  POST /ray-ban/quick-alert - Generate quick TTS alert")
    print("  GET  /ray-ban/status - Get streaming status")
    
    print("\nExample API calls:")
    print("""
    # Start streaming session
    curl -X POST http://localhost:5008/ray-ban/start-stream \\
         -H "Content-Type: application/json" \\
         -d '{"store_location": "Whole Foods Market"}'
    
    # Analyze product
    curl -X POST http://localhost:5008/ray-ban/analyze-product \\
         -H "Content-Type: application/json" \\
         -d '{"product_name": "Organic Apples", "store_price": "$4.99"}'
    
    # Generate quick alert
    curl -X POST http://localhost:5008/ray-ban/quick-alert \\
         -H "Content-Type: application/json" \\
         -d '{"product_name": "Organic Apples", "alert_type": "price"}'
    
    # Get status
    curl http://localhost:5008/ray-ban/status
    """)


if __name__ == "__main__":
    print("🥽 META RAY-BANS INTEGRATION DEMO")
    print("=" * 50)
    
    # Check if ElevenLabs API key is set
    if not os.getenv('ELEVENLABS_API_KEY') or os.getenv('ELEVENLABS_API_KEY') == 'your_elevenlabs_api_key_here':
        print("⚠️  ElevenLabs API key not set!")
        print("   Please set ELEVENLABS_API_KEY in your .env file")
        print("   Get your API key from: https://elevenlabs.io/")
        print()
        print("Demo will show functionality without actual TTS...")
    else:
        print("✅ ElevenLabs API key found")
    
    # Run demos
    demo_tts_functionality()
    demo_live_shopping_session()
    demo_api_endpoints()
    
    print("\n🎉 Demo completed!")
    print("Your Meta Ray-Bans integration is ready for live streaming!")
