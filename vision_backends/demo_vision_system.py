#!/usr/bin/env python3
"""
Demo script for the Vision Sustainability System
Shows how the integrated system works with sample product data
"""

import os
import sys
import asyncio
import time
from pathlib import Path

# Add backend to path
sys.path.append('/Users/ethanwang/hackharvard/google-gemini/backend')

def load_environment_variables():
    """Load environment variables from .env file"""
    backend_dir = Path(__file__).resolve().parent.parent / "backend"
    dotenv_path = backend_dir / '.env'
    
    if dotenv_path.exists():
        print(f"📁 Loading environment variables from: {dotenv_path}")
        from dotenv import load_dotenv
        load_dotenv(dotenv_path)
        return True
    else:
        print(f"⚠️ No .env file found at {dotenv_path}")
        return False

async def demo_vision_system():
    """Demo the vision sustainability system"""
    print("🥽 VISION SUSTAINABILITY SYSTEM DEMO")
    print("=" * 50)
    
    # Load environment variables
    if not load_environment_variables():
        print("❌ Cannot load environment variables. Please check your .env file.")
        return
    
    # Import the analyzer
    try:
        from vision_sustainability_backend import vision_analyzer
        print("✅ Vision analyzer imported successfully")
    except Exception as e:
        print(f"❌ Error importing vision analyzer: {e}")
        return
    
    # Demo product (simulating what would be detected by camera)
    demo_product = {
        'product_name': 'Organic Bananas',
        'brand': 'Chiquita',
        'detected_price': '1.99',
        'confidence': 0.88
    }
    
    print(f"\n📦 DEMO PRODUCT DETECTED:")
    print(f"   Product: {demo_product['product_name']}")
    print(f"   Brand: {demo_product['brand']}")
    print(f"   Price: ${demo_product['detected_price']}")
    print(f"   Confidence: {demo_product['confidence']:.1%}")
    
    print(f"\n🔍 ANALYZING PRODUCT...")
    print("=" * 30)
    
    try:
        start_time = time.time()
        result = await vision_analyzer.analyze_detected_product(demo_product)
        analysis_time = time.time() - start_time
        
        print(f"\n✅ ANALYSIS COMPLETE in {analysis_time:.2f}s")
        print("=" * 40)
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
            return
        
        # Display results in a nice format
        print(f"\n📊 PRODUCT ANALYSIS RESULTS")
        print(f"Product: {result.get('product_name', 'Unknown')}")
        print(f"Brand: {result.get('brand', 'Unknown')}")
        print(f"Detected Price: ${result.get('detected_price', 'N/A')}")
        print(f"Confidence: {result.get('confidence', 0):.1%}")
        
        # Nutrition Score (Separate)
        nutrition_data = result.get('nutrition_score', {})
        if isinstance(nutrition_data, dict):
            nutrition_score = nutrition_data.get('score', 0)
            print(f"\n🥗 NUTRITION SCORE: {nutrition_score:.1f}/10")
            print(f"   Data Source: {nutrition_data.get('data_source', 'Unknown')}")
            print(f"   Analysis: {nutrition_data.get('analysis', 'No analysis available')}")
        else:
            print(f"\n🥗 NUTRITION SCORE: {nutrition_data}/10 (raw value)")
        
        # Sustainability Score (Separate)
        sustainability_data = result.get('sustainability_score', {})
        if isinstance(sustainability_data, dict):
            sustainability_score = sustainability_data.get('score', 0)
            print(f"\n🌱 SUSTAINABILITY SCORE: {sustainability_score:.1f}/10")
            print(f"   Carbon Score: {sustainability_data.get('carbon_score', 0):.1f}/10")
            print(f"   Ethics Score: {sustainability_data.get('ethics_score', 0):.1f}/10")
            print(f"   Analysis: {sustainability_data.get('analysis', 'No analysis available')}")
        else:
            print(f"\n🌱 SUSTAINABILITY SCORE: {sustainability_data}/10 (raw value)")
        
        # Price Analysis
        price_data = result.get('price_analysis', {})
        if isinstance(price_data, dict):
            print(f"\n💰 PRICE ANALYSIS")
            print(f"   In-Store Price: ${price_data.get('detected_price', 0):.2f}")
            print(f"   Average Online Price: ${price_data.get('avg_online_price', 0):.2f}")
            print(f"   Price Difference: {price_data.get('price_difference_percent', 0):.1f}%")
            print(f"   Cheaper Online: {'Yes' if price_data.get('is_cheaper_online', False) else 'No'}")
            print(f"   Products Found: {price_data.get('products_found', 0)}")
            print(f"   Data Source: {price_data.get('data_source', 'Unknown')}")
        else:
            print(f"\n💰 PRICE ANALYSIS: {price_data} (raw value)")
        
        # Summary
        print(f"\n📈 SUMMARY SCORES")
        if isinstance(nutrition_data, dict):
            print(f"   🥗 Nutrition: {nutrition_data.get('score', 0):.1f}/10")
        else:
            print(f"   🥗 Nutrition: {nutrition_data}/10")
        if isinstance(sustainability_data, dict):
            print(f"   🌱 Sustainability: {sustainability_data.get('score', 0):.1f}/10")
        else:
            print(f"   🌱 Sustainability: {sustainability_data}/10")
        if isinstance(price_data, dict):
            print(f"   💰 Price Advantage: {price_data.get('price_difference_percent', 0):.1f}%")
        else:
            print(f"   💰 Price Advantage: {price_data}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS")
        nutrition_score_val = nutrition_data.get('score', 0) if isinstance(nutrition_data, dict) else nutrition_data
        if nutrition_score_val >= 7:
            print("   ✅ Good nutrition choice!")
        elif nutrition_score_val >= 5:
            print("   ⚠️ Moderate nutrition - consider alternatives")
        else:
            print("   ❌ Poor nutrition - look for healthier options")
        
        sustainability_score_val = sustainability_data.get('score', 0) if isinstance(sustainability_data, dict) else sustainability_data
        if sustainability_score_val >= 7:
            print("   ✅ Environmentally and socially responsible!")
        elif sustainability_score_val >= 5:
            print("   ⚠️ Moderate sustainability impact")
        else:
            print("   ❌ High environmental/social impact - consider alternatives")
        
        if isinstance(price_data, dict):
            if price_data.get('is_cheaper_online', False):
                savings = price_data.get('savings_opportunity', 0)
                print(f"   💰 Save ${savings:.2f} by buying online!")
            elif price_data.get('price_difference_percent', 0) < -5:
                print("   🏪 Good in-store price compared to online!")
            else:
                print("   ⚖️ Prices are similar online and in-store")
        else:
            print("   ⚖️ Price analysis not available")
        
        print(f"\n⏱️ Total Analysis Time: {analysis_time:.2f}s")
        print(f"🕐 Timestamp: {result.get('analysis_timestamp', 'Unknown')}")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

def show_system_features():
    """Show the system features"""
    print("\n🎯 VISION SUSTAINABILITY SYSTEM FEATURES")
    print("=" * 50)
    print("📹 Real-time Camera Detection")
    print("   - Live video streaming")
    print("   - Product detection and recognition")
    print("   - Price tag detection")
    print("   - Brand identification")
    
    print("\n📊 Comprehensive Analysis")
    print("   - 🥗 Separate Nutrition Scoring (0-10)")
    print("   - 🌱 Separate Sustainability Scoring (0-10)")
    print("   - 💰 Real-time Price Analysis")
    print("   - 🔍 Web vs In-Store Comparison")
    
    print("\n🤖 AI-Powered Analysis")
    print("   - USDA nutrition data integration")
    print("   - Google Gemini AI for sustainability")
    print("   - News-based social ethics scoring")
    print("   - Dynamic carbon footprint calculation")
    
    print("\n🎤 Bonus Features")
    print("   - ElevenLabs text-to-speech announcements")
    print("   - Real-time voice feedback")
    print("   - Meta Ray-Bans integration ready")
    
    print("\n🌐 Web Interface")
    print("   - Live camera feed display")
    print("   - Real-time score updates")
    print("   - Detailed analysis breakdown")
    print("   - Price comparison charts")

async def main():
    """Run the demo"""
    show_system_features()
    await demo_vision_system()
    
    print("\n🚀 SYSTEM READY FOR PRODUCTION!")
    print("=" * 40)
    print("To start the full system:")
    print("1. Run: python3 start_vision_app.py")
    print("2. Open: http://localhost:5004")
    print("3. Start camera streaming")
    print("4. Point camera at products for real-time analysis!")

if __name__ == "__main__":
    asyncio.run(main())
