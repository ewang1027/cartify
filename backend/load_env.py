"""
Environment variable loader for Real Grocery Sustainability Scorer
This script loads environment variables from .env file if it exists
"""

import os
from dotenv import load_dotenv

def load_environment_variables():
    """
    Load environment variables from .env file if it exists
    """
    # Look for .env file in the current directory
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    
    if os.path.exists(env_path):
        print(f"📁 Loading environment variables from: {env_path}")
        load_dotenv(env_path)
        return True
    else:
        print("⚠️ No .env file found, using system environment variables or config.py fallback")
        return False

def get_api_keys():
    """
    Get API keys from environment variables or config.py fallback
    """
    # Try to load from .env file first
    load_environment_variables()
    
    # Import config as fallback
    try:
        from config import API_KEYS
        return API_KEYS
    except ImportError:
        return {}

if __name__ == "__main__":
    # Test the environment loading
    print("🔧 Testing environment variable loading...")
    load_environment_variables()
    
    # Check if environment variables are set
    keys = ['OXYLABS_USERNAME', 'OXYLABS_PASSWORD', 'GEMINI_API_KEY', 'NEWS_API_KEY', 'USDA_API_KEY']
    for key in keys:
        value = os.getenv(key)
        if value:
            print(f"   {key}: ✅ Set ({value[:10]}...)")
        else:
            print(f"   {key}: ❌ Not set")
