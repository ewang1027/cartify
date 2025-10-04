# Real Grocery Sustainability Scorer

A production-ready system that analyzes real grocery products and generates sustainability scores using Google Shopping data, USDA nutrition data, and news analysis.

## 🚀 **Quick Start**

### Option 1: Using Config File (Recommended)
```bash
# Edit config.py with your API keys, then:
python3 start_api.py
```

### Option 2: Using Environment Variables
```bash
export OXYLABS_USERNAME="your_username"
export OXYLABS_PASSWORD="your_password"
export GEMINI_API_KEY="your_gemini_key"
export NEWS_API_KEY="your_news_key"
export USDA_API_KEY="your_usda_key"
python3 real_grocery_api_oxylabs.py
```

### Option 3: Direct API Start
```bash
python3 real_grocery_api_oxylabs.py
```
Server runs on: http://localhost:5008

## 📁 **Core Files**

- `real_grocery_api_oxylabs.py` - Main API server (Port 5008)
- `real_grocery_scorer_oxylabs.py` - Core scoring engine
- `google_scrape.py` - Google Shopping integration via Oxylabs
- `nutrition_fetcher.py` - USDA nutrition data integration
- `simple_news_scorer.py` - News analysis and sentiment scoring
- `sustainability_scorer.py` - Base sustainability scoring engine
- `config.py` - API keys configuration file
- `start_api.py` - Easy startup script

## 🔌 **API Endpoints**

- `GET /health` - Health check
- `POST /grocery/search` - Search for grocery products
- `POST /grocery/analyze` - Analyze single product sustainability
- `POST /grocery/category` - Analyze grocery category
- `POST /grocery/report` - Generate comprehensive report

## 📊 **Example Usage**

```bash
# Search for products
curl -X POST http://localhost:5008/grocery/search \
  -H "Content-Type: application/json" \
  -d '{"query": "organic apples", "num_results": 5}'

# Analyze a category
curl -X POST http://localhost:5008/grocery/category \
  -H "Content-Type: application/json" \
  -d '{"category": "organic fruits", "num_products": 3}'
```

## ✅ **System Status: PRODUCTION READY**

The system successfully:
- ✅ Scrapes real grocery products from Google Shopping
- ✅ Fetches real nutritional data from USDA FoodData Central
- ✅ Analyzes news sentiment for sustainability factors
- ✅ Generates comprehensive sustainability scores
- ✅ Provides RESTful API for web applications
