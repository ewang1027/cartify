#!/usr/bin/env python3
"""
Startup script for Real Grocery Sustainability API
This script loads API keys from config.py and starts the API server
"""

import os
import sys
from config import API_KEYS

def main():
    """Start the API server with keys from config.py"""
    
    print("🚀 Starting Real Grocery Sustainability API...")
    print("📋 Loading API keys from config.py...")
    
    # Set environment variables from config
    for key, value in API_KEYS.items():
        os.environ[key] = value
        print(f"   {key}: {'✅ Set' if value else '❌ Missing'}")
    
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
