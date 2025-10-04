#!/usr/bin/env python3
"""
Startup script for Real Grocery Sustainability API
This script loads API keys from config.py and starts the API server
"""

import os
import sys
from load_env import load_environment_variables

def main():
    """Start the API server with keys from .env file"""
    
    print("🚀 Starting Real Grocery Sustainability API...")
    print("📋 Loading API keys from .env file...")
    
    # Load from .env file
    env_loaded = load_environment_variables()
    
    if env_loaded:
        print("✅ Environment variables loaded from .env file")
    else:
        print("❌ No .env file found! Please create .env file with your API keys.")
        print("📋 Required keys: OXYLABS_USERNAME, OXYLABS_PASSWORD, GEMINI_API_KEY, NEWS_API_KEY, USDA_API_KEY")
        sys.exit(1)
    
    print("\n🌱 Starting API server...")
    
    # Import and run the API
    from real_grocery_api_oxylabs import app
    
    print("✅ API server started successfully!")
    print("📍 Available at: http://localhost:5008")
    print("🔗 Health check: http://localhost:5008/health")
    
    # Start the Flask app
    app.run(debug=True, port=5008, use_reloader=False)

if __name__ == "__main__":
    main()
