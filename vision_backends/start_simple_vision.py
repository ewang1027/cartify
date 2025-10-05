#!/usr/bin/env python3
"""
Startup script for Simple Vision Sustainability App
This script loads API keys and starts the simplified vision app
"""

import os
import sys
from pathlib import Path

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

def main():
    """Start the simple vision app"""
    
    print("🥽 Starting Simple Vision Sustainability App...")
    print("📋 Loading API keys from .env file...")
    
    # Load from .env file
    env_loaded = load_environment_variables()
    
    if env_loaded:
        print("✅ Environment variables loaded from .env file")
    else:
        print("❌ No .env file found! Please create .env file with your API keys.")
        print("📋 Required keys: OXYLABS_USERNAME, OXYLABS_PASSWORD, GEMINI_API_KEY, NEWS_API_KEY, USDA_API_KEY, ELEVENLABS_API_KEY")
        sys.exit(1)
    
    print("\n🌱 Starting simple vision app...")
    print("📊 Features:")
    print("   - Live camera streaming")
    print("   - Real-time product detection")
    print("   - Separate nutrition and sustainability scoring")
    print("   - Price analysis (web vs in-store)")
    print("   - TTS announcements")
    print("🌐 Starting server on port 5005...")
    print("🔗 Open http://localhost:5005 in your browser")
    
    # Import and run the simple vision app
    from simple_vision_app import app, socketio
    
    print("✅ Simple Vision App started successfully!")
    print("📍 Available at: http://localhost:5005")
    print("🔗 Health check: http://localhost:5005/health")
    
    # Start the Flask app with SocketIO
    socketio.run(app, host='0.0.0.0', port=5005, debug=True, allow_unsafe_werkzeug=True)

if __name__ == "__main__":
    main()
