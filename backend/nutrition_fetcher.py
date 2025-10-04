"""
USDA FoodData Central API Integration

This module fetches nutritional data from the USDA FoodData Central API
to enhance sustainability scoring with real nutritional information.
"""

import os
import requests
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class NutritionFetcher:
    """
    Fetches nutritional data from USDA FoodData Central API
    and processes it for sustainability scoring.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the nutrition fetcher.
        
        Args:
            api_key: USDA FoodData Central API key (optional, uses DEMO_KEY as fallback)
        """
        self.api_key = api_key or os.getenv('USDA_API_KEY', 'your_usda_api_key_here')
        self.base_url = "https://api.nal.usda.gov/fdc/v1"
        
        # Nutritional components we care about for sustainability scoring
        self.nutrition_components = {
            # Negative components (higher = worse for sustainability)
            'sugar': {
                'nutrient_id': 2000,  # Sugars, total (g)
                'weight': -0.3,  # Negative weight for sustainability
                'thresholds': [0, 2, 4, 6, 8, 10, 12, 15, 20, 25, 30]  # g per 100g (more realistic thresholds)
            },
            'saturated_fat': {
                'nutrient_id': 1258,  # Fatty acids, total saturated (g)
                'weight': -0.25,  # Negative weight for sustainability
                'thresholds': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]  # g per 100g
            },
            'sodium': {
                'nutrient_id': 1093,  # Sodium, Na (mg)
                'weight': -0.15,  # Negative weight for sustainability
                'thresholds': [0, 50, 100, 150, 200, 300, 400, 500, 600, 800, 1000]  # mg per 100g (more realistic thresholds)
            },
            'trans_fat': {
                'nutrient_id': 1257,  # Fatty acids, total trans (g)
                'weight': -0.2,  # Negative weight for sustainability
                'thresholds': [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]  # g per 100g
            },
            
            # Positive components (higher = better for sustainability)
            'protein': {
                'nutrient_id': 1003,  # Protein (g)
                'weight': 0.2,  # Positive weight for sustainability
                'thresholds': [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20]  # g per 100g
            },
            'fiber': {
                'nutrient_id': 1079,  # Fiber, total dietary (g)
                'weight': 0.15,  # Positive weight for sustainability
                'thresholds': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]  # g per 100g
            },
            'vitamins': {
                'nutrient_id': [1106, 1107, 1108, 1109, 1110],  # Various vitamins
                'weight': 0.1,  # Positive weight for sustainability
                'thresholds': [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50]  # % DV
            },
            'minerals': {
                'nutrient_id': [1087, 1089, 1090, 1091, 1092],  # Various minerals
                'weight': 0.1,  # Positive weight for sustainability
                'thresholds': [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50]  # % DV
            }
        }
    
    def search_food(self, query: str, data_type: str = "Branded", page_size: int = 10) -> List[Dict]:
        """
        Search for food items using the USDA FoodData Central API.
        
        Args:
            query: Search query (e.g., "apple", "chicken breast")
            data_type: Type of data to search ("Branded", "Foundation", "SR Legacy")
            page_size: Number of results to return
            
        Returns:
            List of food items with basic information
        """
        try:
            url = f"{self.base_url}/foods/search"
            params = {
                'api_key': self.api_key,
                'query': query,
                'dataType': [data_type],
                'pageSize': page_size,
                'sortBy': 'dataType.keyword',
                'sortOrder': 'asc'
            }
            
            print(f"🔍 Searching USDA FoodData Central for: {query}")
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            foods = data.get('foods', [])
            
            print(f"📊 Found {len(foods)} food items from USDA FoodData Central")
            
            return foods
            
        except Exception as e:
            print(f"❌ Error searching USDA FoodData Central: {e}")
            return []
    
    def get_food_details(self, fdc_id: int) -> Optional[Dict]:
        """
        Get detailed nutritional information for a specific food item.
        
        Args:
            fdc_id: FoodData Central ID
            
        Returns:
            Detailed food information with nutritional data
        """
        try:
            url = f"{self.base_url}/food/{fdc_id}"
            params = {'api_key': self.api_key}
            
            print(f"📋 Fetching detailed nutrition data for FDC ID: {fdc_id}")
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            food_data = response.json()
            
            print(f"✅ Retrieved nutrition data for: {food_data.get('description', 'Unknown')}")
            
            return food_data
            
        except Exception as e:
            print(f"❌ Error fetching food details: {e}")
            return None
    
    def extract_nutrition_data(self, food_data: Dict) -> Dict:
        """
        Extract relevant nutritional data from USDA food data.
        
        Args:
            food_data: Raw food data from USDA API
            
        Returns:
            Processed nutritional data for sustainability scoring
        """
        if not food_data:
            return {}
        
        nutrition_data = {}
        
        # First try to use labelNutrients (more accurate for branded foods)
        label_nutrients = food_data.get('labelNutrients', {})
        if label_nutrients:
            # Map label nutrients to our components
            label_mapping = {
                'sugar': ['sugars', 'sugar'],
                'sodium': ['sodium'],
                'protein': ['protein'],
                'saturated_fat': ['saturatedFat', 'saturated_fat'],
                'fiber': ['fiber', 'dietaryFiber']
            }
            
            for component, possible_keys in label_mapping.items():
                for key in possible_keys:
                    if key in label_nutrients and isinstance(label_nutrients[key], dict):
                        nutrition_data[component] = label_nutrients[key].get('value', 0)
                        break
                    elif key in label_nutrients:
                        nutrition_data[component] = label_nutrients[key]
                        break
        
        # Fallback to foodNutrients if labelNutrients not available
        if not nutrition_data and 'foodNutrients' in food_data:
            food_nutrients = food_data.get('foodNutrients', [])
            
            # Extract nutrient values
            for nutrient in food_nutrients:
                nutrient_info = nutrient.get('nutrient', {})
                nutrient_id = nutrient_info.get('id')
                amount = nutrient.get('amount', 0)
                
                # Map to our nutrition components
                for component, config in self.nutrition_components.items():
                    if isinstance(config['nutrient_id'], list):
                        # Handle multiple nutrient IDs (like vitamins/minerals)
                        if nutrient_id in config['nutrient_id']:
                            if component not in nutrition_data:
                                nutrition_data[component] = 0
                            nutrition_data[component] += amount
                    else:
                        # Handle single nutrient ID
                        if nutrient_id == config['nutrient_id']:
                            nutrition_data[component] = amount
                            break
        
        # USDA data is per serving, convert to per 100g for consistent scoring
        serving_size = food_data.get('servingSize', 100)
        serving_unit = food_data.get('servingSizeUnit', 'g')
        
        # Convert serving size to grams if needed
        if serving_unit in ['MLT', 'ml', 'mL']:
            # For beverages, assume density of ~1.0 g/ml (water-like)
            serving_size_grams = serving_size * 1.0
        elif serving_unit == 'g':
            serving_size_grams = serving_size
        else:
            # Default to 100g if unknown unit
            serving_size_grams = 100
        
        # Convert from per serving to per 100g
        if serving_size_grams != 100:
            for key, value in nutrition_data.items():
                if isinstance(value, (int, float)):
                    nutrition_data[key] = (value / serving_size_grams) * 100
        
        print(f"📊 Extracted nutrition data: {nutrition_data}")
        return nutrition_data
    
    def calculate_nutrition_score(self, nutrition_data: Dict) -> Tuple[float, Dict]:
        """
        Calculate nutrition-based sustainability score.
        
        Args:
            nutrition_data: Extracted nutritional data
            
        Returns:
            Tuple of (nutrition_score, score_breakdown)
        """
        if not nutrition_data:
            return 5.0, {"message": "No nutrition data available"}
        
        positive_score = 0.0
        negative_score = 0.0
        max_positive = 0.0
        max_negative = 0.0
        score_breakdown = {}
        
        for component, config in self.nutrition_components.items():
            if component not in nutrition_data:
                continue
            
            value = nutrition_data[component]
            weight = config['weight']
            thresholds = config['thresholds']
            
            # Calculate score based on thresholds
            score = self._calculate_component_score(value, thresholds)
            
            # Calculate contribution based on component type
            if weight > 0:  # Positive component (higher = better)
                if value > 0:
                    positive_score += score * weight
                    max_positive += 10 * weight
                contribution = score * weight if value > 0 else 0
            else:  # Negative component (higher = worse, so invert the logic)
                if value > 0:
                    # For negative components, high values get low scores, low values get high scores
                    # We want to penalize high values, so we use (10 - score) for contribution
                    inverted_score = 10 - score
                    negative_score += inverted_score * abs(weight)
                    max_negative += 10 * abs(weight)
                contribution = (10 - score) * abs(weight) if value > 0 else 0
            
            score_breakdown[component] = {
                'value': value,
                'score': score,
                'weight': weight,
                'contribution': contribution
            }
        
        # Calculate final score: positive components minus negative components
        if max_positive > 0:
            positive_contribution = (positive_score / max_positive) * 5  # Scale to 0-5
        else:
            positive_contribution = 2.5  # Neutral
            
        if max_negative > 0:
            negative_contribution = (negative_score / max_negative) * 5  # Scale to 0-5
        else:
            negative_contribution = 2.5  # Neutral
        
        # Final score: positive - negative + 5 (to center around 5)
        final_score = max(0, min(10, positive_contribution - negative_contribution + 5))
        
        print(f"📈 Nutrition Score: {final_score:.1f}/10")
        print(f"   Breakdown: {score_breakdown}")
        
        return round(final_score, 1), score_breakdown
    
    def _calculate_component_score(self, value: float, thresholds: List[float]) -> float:
        """
        Calculate score based on value and thresholds.
        
        Args:
            value: Nutritional value
            thresholds: List of threshold values
            
        Returns:
            Score from 0-10
        """
        if value <= thresholds[0]:
            return 10.0
        
        for i in range(1, len(thresholds)):
            if value <= thresholds[i]:
                # Linear interpolation between thresholds
                ratio = (value - thresholds[i-1]) / (thresholds[i] - thresholds[i-1])
                return 10.0 - (i - 1 + ratio)
        
        return 0.0  # Value exceeds all thresholds
    
    def get_processed_level(self, food_data: Dict) -> str:
        """
        Determine processing level based on food data.
        
        Args:
            food_data: Raw food data from USDA API
            
        Returns:
            Processing level: "low", "medium", or "high"
        """
        description = food_data.get('description', '').lower()
        ingredients = food_data.get('ingredients', '').lower()
        
        # High processing indicators
        high_processing_keywords = [
            'processed', 'canned', 'frozen', 'dried', 'dehydrated', 'powdered',
            'instant', 'ready-to-eat', 'pre-cooked', 'prepared', 'convenience',
            'artificial', 'synthetic', 'preservatives', 'additives'
        ]
        
        # Low processing indicators
        low_processing_keywords = [
            'fresh', 'raw', 'organic', 'natural', 'whole', 'unprocessed',
            'farm-fresh', 'local', 'seasonal'
        ]
        
        # Count processing indicators
        high_count = sum(1 for keyword in high_processing_keywords 
                        if keyword in description or keyword in ingredients)
        low_count = sum(1 for keyword in low_processing_keywords 
                       if keyword in description or keyword in ingredients)
        
        if high_count > low_count and high_count >= 2:
            return "high"
        elif low_count > high_count and low_count >= 2:
            return "low"
        else:
            return "medium"
    
    def fetch_nutrition_for_product(self, product_name: str) -> Dict:
        """
        Fetch comprehensive nutrition data for a product.
        
        Args:
            product_name: Name of the product to analyze
            
        Returns:
            Dictionary with nutrition data and scoring
        """
        print(f"\n🥗 Fetching nutrition data for: {product_name}")
        print("=" * 60)
        
        # Search for the product
        foods = self.search_food(product_name)
        
        if not foods:
            return {
                "product_name": product_name,
                "nutrition_score": 5.0,
                "nutrition_data": {},
                "processed_level": "medium",
                "message": "No nutrition data found",
                "source": "USDA FoodData Central"
            }
        
        # Get detailed data for the first result
        best_food = foods[0]
        fdc_id = best_food.get('fdcId')
        food_details = self.get_food_details(fdc_id)
        
        if not food_details:
            return {
                "product_name": product_name,
                "nutrition_score": 5.0,
                "nutrition_data": {},
                "processed_level": "medium",
                "message": "Could not fetch detailed nutrition data",
                "source": "USDA FoodData Central"
            }
        
        # Extract and process nutrition data
        nutrition_data = self.extract_nutrition_data(food_details)
        nutrition_score, score_breakdown = self.calculate_nutrition_score(nutrition_data)
        processed_level = self.get_processed_level(food_details)
        
        result = {
            "product_name": product_name,
            "fdc_id": fdc_id,
            "description": food_details.get('description', ''),
            "nutrition_score": nutrition_score,
            "nutrition_data": nutrition_data,
            "score_breakdown": score_breakdown,
            "processed_level": processed_level,
            "source": "USDA FoodData Central",
            "fetch_timestamp": datetime.now().isoformat()
        }
        
        print(f"✅ Nutrition analysis complete: {nutrition_score}/10")
        print(f"   Processed Level: {processed_level}")
        print(f"   Key Nutrients: {list(nutrition_data.keys())}")
        
        return result


# Convenience function for easy use
def fetch_nutrition_data(product_name: str, api_key: Optional[str] = None) -> Dict:
    """
    Convenience function to fetch nutrition data for a product.
    
    Args:
        product_name: Name of the product
        api_key: Optional USDA API key
        
    Returns:
        Dictionary with nutrition data and scoring
    """
    fetcher = NutritionFetcher(api_key)
    return fetcher.fetch_nutrition_for_product(product_name)


# Example usage and testing
if __name__ == "__main__":
    print("🥗 USDA FoodData Central Nutrition Fetcher")
    print("=" * 50)
    
    # Test with various food products
    test_products = [
        "apple",
        "chicken breast",
        "whole wheat bread",
        "coca cola",
        "organic spinach"
    ]
    
    fetcher = NutritionFetcher()
    
    for product in test_products:
        print(f"\n{'='*60}")
        try:
            result = fetcher.fetch_nutrition_for_product(product)
            print(f"\n✅ Analysis complete for {product}")
            print(f"   Nutrition Score: {result['nutrition_score']}/10")
            print(f"   Processed Level: {result['processed_level']}")
            print(f"   Key Nutrients: {list(result['nutrition_data'].keys())}")
        except Exception as e:
            print(f"❌ Error analyzing {product}: {e}")
    
    print(f"\n{'='*60}")
    print("🎉 Nutrition data fetching complete!")
