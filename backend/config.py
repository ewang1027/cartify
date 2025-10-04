"""
Configuration file for Real Grocery Sustainability Scorer
Store your API keys here for easy management
"""

import os

# Use environment variables as primary source, with fallback to hardcoded values
API_KEYS = {
    'OXYLABS_USERNAME': os.getenv('OXYLABS_USERNAME', 'your_oxylabs_username'),
    'OXYLABS_PASSWORD': os.getenv('OXYLABS_PASSWORD', 'your_oxylabs_password'),
    'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY', 'your_gemini_api_key_here'),
    'NEWS_API_KEY': os.getenv('NEWS_API_KEY', 'your_news_api_key_here'),
    'USDA_API_KEY': os.getenv('USDA_API_KEY', 'your_usda_api_key_here')
}

# Alternative: You can also set these as environment variables
# The code will check environment variables first, then fall back to this config
