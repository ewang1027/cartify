#!/usr/bin/env python3
"""
Startup script for Integrated Vision Sustainability App
This script loads API keys from .env file and starts the vision app
"""

import os
import sys
from pathlib import Path

def load_environment_variables():
    """
    Loads environment variables from a .env file in the backend directory.
    Returns True if .env was loaded, False otherwise.
    """
    # Try to load from backend .env file first
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

def verify_environment_variables():
    """
    Verifies if required environment variables are set.
    """
    required_keys = [
        'OXYLABS_USERNAME',
        'OXYLABS_PASSWORD', 
        'GEMINI_API_KEY',
        'NEWS_API_KEY',
        'USDA_API_KEY',
        'ELEVENLABS_API_KEY'
    ]
    
    status = {}
    for key in required_keys:
        status[key] = os.getenv(key) is not None
    
    return status

def main():
    """Start the integrated vision app with environment variables"""
    
    print("🥽 Starting Integrated Vision Sustainability App...")
    print("📋 Loading API keys from .env file...")
    
    # Load from .env file
    env_loaded = load_environment_variables()
    
    if env_loaded:
        print("✅ Environment variables loaded from .env file")
    else:
        print("❌ No .env file found! Please create .env file with your API keys.")
        print("📋 Required keys: OXYLABS_USERNAME, OXYLABS_PASSWORD, GEMINI_API_KEY, NEWS_API_KEY, USDA_API_KEY, ELEVENLABS_API_KEY")
        sys.exit(1)
    
    # Verify environment variables
    print("\n🔧 Verifying environment variables:")
    status = verify_environment_variables()
    all_loaded = True
    
    for key, is_set in status.items():
        value = os.getenv(key)
        if is_set and value:
            print(f"   {key}: ✅ Set ({value[:10]}...)")
        else:
            print(f"   {key}: ❌ Not set")
            all_loaded = False
    
    if not all_loaded:
        print("\n❌ Some required environment variables are missing!")
        print("Please check your .env file and ensure all keys are set.")
        sys.exit(1)
    
    print("\n🌱 Starting integrated vision app...")
    print("📊 Features:")
    print("   - Live camera streaming")
    print("   - Real-time product detection")
    print("   - Separate nutrition and sustainability scoring")
    print("   - Price analysis (web vs in-store)")
    print("   - TTS announcements")
    print("🌐 Starting server on port 5004...")
    print("🔗 Open http://localhost:5004 in your browser")
    
    # Import and run the integrated vision app
    from integrated_vision_app import app, socketio
    
    print("✅ Integrated Vision App started successfully!")
    print("📍 Available at: http://localhost:5004")
    print("🔗 Health check: http://localhost:5004/health")
    
    # Start the Flask app with SocketIO
    socketio.run(app, host='0.0.0.0', port=5004, debug=True, allow_unsafe_werkzeug=True)

if __name__ == "__main__":
    main()
