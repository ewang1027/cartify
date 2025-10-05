"""
Real Grocery Product Sustainability Scorer (Oxylabs Version)

This module integrates Google Shopping scraping via Oxylabs with the sustainability scoring system
to analyze real grocery products and generate actual sustainability scores.
"""

import os
import json
import requests
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from simple_news_scorer import SimpleNewsScorer
from nutrition_fetcher import NutritionFetcher
from sustainability_scorer import SustainabilityScorer
from google_scrape import scrape_google_shopping_deals

# No config fallback needed - using .env file only


class RealGroceryScorerOxylabs:
    """
    Enhanced sustainability scorer that uses real grocery product data
    from Google Shopping via Oxylabs and generates actual sustainability scores.
    """
    
    def __init__(self, oxylabs_username: Optional[str] = None, oxylabs_password: Optional[str] = None, 
                 usda_api_key: Optional[str] = None, news_api_key: Optional[str] = None, 
                 gemini_api_key: Optional[str] = None):
        """
        Initialize the real grocery scorer with Oxylabs integration.
        
        Args:
            oxylabs_username: Oxylabs username
            oxylabs_password: Oxylabs password
            usda_api_key: USDA FoodData Central API key
            news_api_key: News API key
            gemini_api_key: Google Gemini API key
        """
        # Use environment variables from .env file
        self.oxylabs_username = oxylabs_username or os.getenv('OXYLABS_USERNAME')
        self.oxylabs_password = oxylabs_password or os.getenv('OXYLABS_PASSWORD')
        self.usda_api_key = usda_api_key or os.getenv('USDA_API_KEY')
        self.news_api_key = news_api_key or os.getenv('GNEWS_API_KEY') or os.getenv('NEWS_API_KEY')
        self.gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        
        # Initialize components with API keys
        self.news_scorer = SimpleNewsScorer(
            news_api_key=self.news_api_key,
            usda_api_key=self.usda_api_key,
            gemini_api_key=self.gemini_api_key
        )
        self.nutrition_fetcher = NutritionFetcher(self.usda_api_key)
        self.sustainability_scorer = SustainabilityScorer()
        
        print("🛒 Real Grocery Scorer (Oxylabs) initialized")
        print(f"   Oxylabs Username: {'✅ Set' if self.oxylabs_username else '❌ Missing'}")
        print(f"   Oxylabs Password: {'✅ Set' if self.oxylabs_password else '❌ Missing'}")
        print(f"   USDA API Key: {'✅ Set' if self.usda_api_key != 'DEMO_KEY' else '⚠️  Using DEMO_KEY'}")
    
    def scrape_grocery_products(self, query: str, num_results: int = 20) -> List[Dict[str, Any]]:
        """
        Scrape real grocery products from Google Shopping using Oxylabs.
        
        Args:
            query: Search query (e.g., "organic apples", "whole wheat bread")
            num_results: Number of products to return
            
        Returns:
            List of grocery products with details
        """
        print(f"🛒 Scraping grocery products for: {query}")
        
        try:
            # Use the existing google_scrape.py functionality
            raw_results = scrape_google_shopping_deals(query)
            
            # Transform the results to match our expected format
            products = []
            for i, item in enumerate(raw_results[:num_results]):
                # Extract and clean product information
                product = {
                    "title": item.get("title", ""),
                    "price": item.get("price", ""),
                    "currency": "USD",  # Default to USD
                    "seller": item.get("store", ""),
                    "url": "",  # Not available in current format
                    "image": "",  # Not available in current format
                    "rating": 0,  # Not available in current format
                    "reviews": 0,  # Not available in current format
                    "delivery": "",  # Not available in current format
                    "extracted_price": 0,
                    "raw_data": item  # Keep original data for debugging
                }
                
                # Clean up price formatting
                if product["price"]:
                    price_clean = re.sub(r'[^\d.,]', '', product["price"])
                    if price_clean:
                        try:
                            product["numeric_price"] = float(price_clean.replace(',', ''))
                        except ValueError:
                            product["numeric_price"] = 0
                    else:
                        product["numeric_price"] = 0
                else:
                    product["numeric_price"] = 0
                
                # Clean up seller name
                if product["seller"]:
                    product["seller"] = re.sub(r'\.(com|org|net|edu|gov|co\.uk|ca|de|fr|jp)$', '', product["seller"])
                    product["seller"] = product["seller"].replace('.', ' ').title()
                
                products.append(product)
            
            print(f"✅ Found {len(products)} grocery products")
            return products
            
        except Exception as e:
            print(f"❌ Error scraping products: {e}")
            return []
    
    def extract_brand_from_title(self, title: str) -> str:
        """
        Extract brand name from product title.
        
        Args:
            title: Product title
            
        Returns:
            Extracted brand name
        """
        # Common grocery brand patterns
        brand_patterns = [
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',  # Capitalized words at start
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+',  # Capitalized words followed by space
        ]
        
        for pattern in brand_patterns:
            match = re.search(pattern, title)
            if match:
                brand = match.group(1).strip()
                # Filter out common non-brand words
                if brand.lower() not in ['organic', 'natural', 'fresh', 'frozen', 'canned']:
                    return brand.lower()
        
        # Fallback: use first word
        first_word = title.split()[0] if title.split() else ""
        return first_word.lower()
    
    def analyze_grocery_product(self, product: Dict[str, Any], use_usda_nutrition: bool = True) -> Dict[str, Any]:
        """
        Analyze a single grocery product for sustainability.
        
        Args:
            product: Product data from Google Shopping
            use_usda_nutrition: Whether to use USDA nutrition data
            
        Returns:
            Comprehensive sustainability analysis
        """
        title = product.get("title", "")
        brand = self.extract_brand_from_title(title)
        
        print(f"\n🔍 Analyzing: {title}")
        print(f"   Brand: {brand}")
        print(f"   Price: {product.get('price', 'N/A')}")
        print(f"   Seller: {product.get('seller', 'N/A')}")
        
        # Calculate sustainability score
        try:
            sustainability_result = self.news_scorer.calculate_sustainability_score(
                product_name=title,
                carbon_footprint=None,  # Will be estimated
                nutrition_metrics=None,  # Will be fetched from USDA
                days_back=30,
                use_usda_nutrition=use_usda_nutrition
            )
        except Exception as e:
            print(f"❌ Error calculating sustainability score: {e}")
            sustainability_result = {
                "sustainability_score": 5.0,
                "base_score": 5.0,
                "news_score": 5.0,
                "justification": "Error in analysis",
                "brand_name": brand
            }
        
        # Combine product data with sustainability analysis
        result = {
            "product_info": {
                "title": title,
                "brand": brand,
                "price": product.get("price", ""),
                "currency": product.get("currency", "USD"),
                "numeric_price": product.get("numeric_price", 0),
                "seller": product.get("seller", ""),
                "url": product.get("url", ""),
                "image": product.get("image", ""),
                "rating": product.get("rating", 0),
                "reviews": product.get("reviews", 0),
                "delivery": product.get("delivery", "")
            },
            "sustainability_analysis": sustainability_result,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        return result
    
    def analyze_grocery_category(self, category: str, num_products: int = 10) -> Dict[str, Any]:
        """
        Analyze a category of grocery products.
        
        Args:
            category: Grocery category (e.g., "organic fruits", "whole grain bread")
            num_products: Number of products to analyze
            
        Returns:
            Category analysis with sustainability insights
        """
        print(f"\n🛒 ANALYZING GROCERY CATEGORY: {category.upper()}")
        print("=" * 60)
        
        # Scrape products
        products = self.scrape_grocery_products(category, num_products)
        
        if not products:
            return {
                "category": category,
                "error": "No products found",
                "products_analyzed": 0,
                "analysis_timestamp": datetime.now().isoformat()
            }
        
        # Analyze each product
        analyzed_products = []
        total_sustainability_score = 0
        total_news_score = 0
        total_base_score = 0
        
        for i, product in enumerate(products[:num_products]):
            print(f"\n--- Product {i+1}/{min(len(products), num_products)} ---")
            
            try:
                analysis = self.analyze_grocery_product(product)
                analyzed_products.append(analysis)
                
                # Accumulate scores
                sus_score = analysis["sustainability_analysis"].get("sustainability_score", 5.0)
                news_score = analysis["sustainability_analysis"].get("news_score", 5.0)
                base_score = analysis["sustainability_analysis"].get("base_score", 5.0)
                
                total_sustainability_score += sus_score
                total_news_score += news_score
                total_base_score += base_score
                
            except Exception as e:
                print(f"❌ Error analyzing product: {e}")
                continue
        
        # Calculate category averages
        num_analyzed = len(analyzed_products)
        if num_analyzed > 0:
            avg_sustainability = total_sustainability_score / num_analyzed
            avg_news_score = total_news_score / num_analyzed
            avg_base_score = total_base_score / num_analyzed
        else:
            avg_sustainability = avg_news_score = avg_base_score = 5.0
        
        # Find best and worst performers
        best_product = None
        worst_product = None
        
        if analyzed_products:
            best_product = max(analyzed_products, 
                             key=lambda x: x["sustainability_analysis"].get("sustainability_score", 0))
            worst_product = min(analyzed_products, 
                              key=lambda x: x["sustainability_analysis"].get("sustainability_score", 0))
        
        # Category insights
        insights = {
            "category": category,
            "products_found": len(products),
            "products_analyzed": num_analyzed,
            "average_sustainability_score": round(avg_sustainability, 2),
            "average_news_score": round(avg_news_score, 2),
            "average_base_score": round(avg_base_score, 2),
            "best_performer": {
                "title": best_product["product_info"]["title"] if best_product else "N/A",
                "score": best_product["sustainability_analysis"]["sustainability_score"] if best_product else 0,
                "price": best_product["product_info"]["price"] if best_product else "N/A"
            },
            "worst_performer": {
                "title": worst_product["product_info"]["title"] if worst_product else "N/A",
                "score": worst_product["sustainability_analysis"]["sustainability_score"] if worst_product else 0,
                "price": worst_product["product_info"]["price"] if worst_product else "N/A"
            },
            "products": analyzed_products,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        return insights
    
    def generate_grocery_report(self, categories: List[str], products_per_category: int = 5) -> Dict[str, Any]:
        """
        Generate a comprehensive grocery sustainability report.
        
        Args:
            categories: List of grocery categories to analyze
            products_per_category: Number of products per category
            
        Returns:
            Comprehensive grocery sustainability report
        """
        print(f"\n📊 GENERATING GROCERY SUSTAINABILITY REPORT")
        print("=" * 70)
        print(f"Categories: {', '.join(categories)}")
        print(f"Products per category: {products_per_category}")
        print("=" * 70)
        
        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "categories_analyzed": categories,
                "products_per_category": products_per_category,
                "total_categories": len(categories),
                "scraping_method": "Oxylabs Google Shopping"
            },
            "category_analyses": {},
            "overall_insights": {}
        }
        
        all_scores = []
        category_summaries = []
        
        # Analyze each category
        for category in categories:
            print(f"\n🛒 Analyzing category: {category}")
            category_analysis = self.analyze_grocery_category(category, products_per_category)
            report["category_analyses"][category] = category_analysis
            
            if "average_sustainability_score" in category_analysis:
                all_scores.append(category_analysis["average_sustainability_score"])
                category_summaries.append({
                    "category": category,
                    "average_score": category_analysis["average_sustainability_score"],
                    "products_analyzed": category_analysis["products_analyzed"]
                })
        
        # Calculate overall insights
        if all_scores:
            report["overall_insights"] = {
                "overall_average_score": round(sum(all_scores) / len(all_scores), 2),
                "best_category": max(category_summaries, key=lambda x: x["average_score"]),
                "worst_category": min(category_summaries, key=lambda x: x["average_score"]),
                "total_products_analyzed": sum(cat["products_analyzed"] for cat in category_summaries),
                "category_rankings": sorted(category_summaries, key=lambda x: x["average_score"], reverse=True)
            }
        
        return report


def main():
    """Main function for testing the real grocery scorer with Oxylabs."""
    print("🛒 REAL GROCERY SUSTAINABILITY SCORER (OXYLABS)")
    print("=" * 60)
    
    # Initialize scorer
    scorer = RealGroceryScorerOxylabs()
    
    # Test categories
    test_categories = [
        "organic fruits",
        "whole grain bread",
        "organic vegetables",
        "sustainable seafood",
        "plant-based milk"
    ]
    
    # Generate report
    report = scorer.generate_grocery_report(test_categories, products_per_category=3)
    
    # Print summary
    print(f"\n📊 REPORT SUMMARY")
    print("=" * 30)
    print(f"Overall Average Score: {report['overall_insights']['overall_average_score']}/10")
    print(f"Total Products Analyzed: {report['overall_insights']['total_products_analyzed']}")
    print(f"Best Category: {report['overall_insights']['best_category']['category']} ({report['overall_insights']['best_category']['average_score']}/10)")
    print(f"Worst Category: {report['overall_insights']['worst_category']['category']} ({report['overall_insights']['worst_category']['average_score']}/10)")
    
    # Save report
    report_file = f"grocery_sustainability_report_oxylabs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Report saved to: {report_file}")
    print("🎉 Grocery sustainability analysis complete!")


if __name__ == "__main__":
    main()
