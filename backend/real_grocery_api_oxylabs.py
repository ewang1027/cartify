"""
Real Grocery Sustainability API (Oxylabs Version)

Flask API server for analyzing real grocery products with sustainability scoring.
Integrates Google Shopping data via Oxylabs with comprehensive sustainability analysis.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime
from real_grocery_scorer_oxylabs import RealGroceryScorerOxylabs

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize the real grocery scorer with Oxylabs
# Uses environment variables from .env file
grocery_scorer = RealGroceryScorerOxylabs(
    usda_api_key=os.getenv('USDA_API_KEY'),
    news_api_key=os.getenv('NEWS_API_KEY'),
    gemini_api_key=os.getenv('GEMINI_API_KEY'),
    oxylabs_username=os.getenv('OXYLABS_USERNAME'),
    oxylabs_password=os.getenv('OXYLABS_PASSWORD')
)

print("🛒 Starting Real Grocery Sustainability API (Oxylabs)...")
print("Available endpoints:")
print("  GET  /health - Health check")
print("  POST /grocery/search - Search for grocery products")
print("  POST /grocery/analyze - Analyze single grocery product")
print("  POST /grocery/category - Analyze grocery category")
print("  POST /grocery/report - Generate comprehensive report")
print("Features:")
print("  - Real Google Shopping product data via Oxylabs")
print("  - USDA nutrition data integration")
print("  - News-based sustainability analysis")
print("  - Comprehensive grocery category insights")


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Real Grocery Sustainability API (Oxylabs)",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "scraping_method": "Oxylabs Google Shopping",
        "features": [
            "Google Shopping integration via Oxylabs",
            "USDA nutrition data",
            "News-based sustainability scoring",
            "Real grocery product analysis"
        ]
    })


@app.route('/grocery/search', methods=['POST'])
def search_grocery_products():
    """
    Search for real grocery products using Google Shopping via Oxylabs.
    
    Expected JSON payload:
    {
        "query": "string",
        "num_results": int (optional, default 20)
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        query = data.get('query')
        if not query:
            return jsonify({"error": "query is required"}), 400
        
        num_results = data.get('num_results', 20)
        
        # Search for products
        products = grocery_scorer.scrape_grocery_products(query, num_results)
        
        return jsonify({
            "query": query,
            "products_found": len(products),
            "products": products,
            "search_timestamp": datetime.now().isoformat(),
            "scraping_method": "Oxylabs Google Shopping"
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Internal server error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/grocery/analyze', methods=['POST'])
def analyze_grocery_product():
    """
    Analyze a single grocery product for sustainability.
    
    Expected JSON payload:
    {
        "product": {
            "title": "string",
            "price": "string",
            "seller": "string",
            "url": "string",
            "image": "string"
        },
        "use_usda_nutrition": bool (optional, default true)
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        product = data.get('product')
        if not product:
            return jsonify({"error": "product is required"}), 400
        
        use_usda_nutrition = data.get('use_usda_nutrition', True)
        
        # Analyze the product
        analysis = grocery_scorer.analyze_grocery_product(product, use_usda_nutrition)
        
        return jsonify(analysis)
        
    except Exception as e:
        return jsonify({
            "error": f"Internal server error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/grocery/category', methods=['POST'])
def analyze_grocery_category():
    """
    Analyze a category of grocery products.
    
    Expected JSON payload:
    {
        "category": "string",
        "num_products": int (optional, default 10)
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        category = data.get('category')
        if not category:
            return jsonify({"error": "category is required"}), 400
        
        num_products = data.get('num_products', 10)
        
        # Analyze the category
        analysis = grocery_scorer.analyze_grocery_category(category, num_products)
        
        return jsonify(analysis)
        
    except Exception as e:
        return jsonify({
            "error": f"Internal server error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/grocery/report', methods=['POST'])
def generate_grocery_report():
    """
    Generate a comprehensive grocery sustainability report.
    
    Expected JSON payload:
    {
        "categories": ["string"],
        "products_per_category": int (optional, default 5)
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        categories = data.get('categories')
        if not categories or not isinstance(categories, list):
            return jsonify({"error": "categories must be a list"}), 400
        
        products_per_category = data.get('products_per_category', 5)
        
        # Generate report
        report = grocery_scorer.generate_grocery_report(categories, products_per_category)
        
        return jsonify(report)
        
    except Exception as e:
        return jsonify({
            "error": f"Internal server error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/grocery/quick-test', methods=['GET'])
def quick_test():
    """
    Quick test endpoint to verify the system is working.
    """
    try:
        # Test with a simple category
        test_category = "organic apples"
        analysis = grocery_scorer.analyze_grocery_category(test_category, 3)
        
        return jsonify({
            "status": "success",
            "test_category": test_category,
            "products_found": analysis.get("products_found", 0),
            "products_analyzed": analysis.get("products_analyzed", 0),
            "average_score": analysis.get("average_sustainability_score", 0),
            "scraping_method": "Oxylabs Google Shopping",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


if __name__ == '__main__':
    # Run the Flask app
    app.run(host='0.0.0.0', port=5008, debug=True)
