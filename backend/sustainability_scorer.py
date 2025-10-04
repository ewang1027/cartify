"""
Sustainability Score Calculator for Grocery Products

This module provides functionality to calculate comprehensive sustainability scores
for grocery products based on carbon footprint, nutrition metrics, and social/ethical factors.
"""

import json
import re
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum


class ProcessedLevel(Enum):
    """Enum for processed food levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class NutritionMetrics:
    """Data class for nutrition metrics"""
    sugar_g: Optional[float] = None
    saturated_fat_g: Optional[float] = None
    processed_level: Optional[str] = None


@dataclass
class SustainabilityScore:
    """Data class for sustainability score results"""
    product_name: str
    sustainability_score: float
    breakdown: Dict[str, float]
    justification: str


class SustainabilityScorer:
    """
    Main class for calculating sustainability scores of grocery products.
    
    Features:
    - Configurable weights for different scoring components
    - Batch processing capability
    - Robust handling of missing data
    - Clear justification generation
    """
    
    def __init__(self, 
                 carbon_weight: float = 0.30,
                 nutrition_weight: float = 0.52,
                 social_ethics_weight: float = 0.18):
        """
        Initialize the sustainability scorer with configurable weights.
        
        Args:
            carbon_weight: Weight for carbon footprint component (default: 0.30)
            nutrition_weight: Weight for nutrition component (default: 0.52)
            social_ethics_weight: Weight for social/ethics component (default: 0.18)
        """
        self.carbon_weight = carbon_weight
        self.nutrition_weight = nutrition_weight
        self.social_ethics_weight = social_ethics_weight
        
        # Validate weights sum to 1.0
        total_weight = carbon_weight + nutrition_weight + social_ethics_weight
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")
        
        # Carbon footprint normalization parameters
        # Based on typical grocery product carbon footprints (kg CO2 per kg product)
        self.carbon_min = 0.1    # Very low carbon (organic, local)
        self.carbon_max = 10.0   # Very high carbon (air-freighted, processed)
        
        # Nutrition scoring parameters
        self.sugar_max = 50.0    # Maximum sugar per 100g for normalization
        self.saturated_fat_max = 20.0  # Maximum saturated fat per 100g
        
        # Social/ethical scoring parameters
        self.negative_keywords = [
            'exploitation', 'violation', 'abuse', 'unfair', 'discrimination',
            'sweatshop', 'child labor', 'forced labor', 'unsafe', 'toxic',
            'contamination', 'recall', 'lawsuit', 'fine', 'penalty'
        ]
        self.positive_keywords = [
            'fair trade', 'organic', 'sustainable', 'ethical', 'certified',
            'community', 'charity', 'donation', 'support', 'initiative',
            'renewable', 'carbon neutral', 'zero waste', 'local sourcing'
        ]
    
    def normalize_carbon_footprint(self, carbon_footprint: float) -> float:
        """
        Normalize carbon footprint to 0-10 scale where lower CO2 = higher score.
        
        Args:
            carbon_footprint: Carbon footprint in kg CO2 per unit/kg
            
        Returns:
            Normalized score (0-10)
        """
        if carbon_footprint is None:
            return 5.0  # Neutral score for missing data
        
        # Clamp to reasonable range
        carbon_footprint = max(0, min(carbon_footprint, self.carbon_max))
        
        # Linear normalization: lower CO2 = higher score
        if carbon_footprint <= self.carbon_min:
            return 10.0
        elif carbon_footprint >= self.carbon_max:
            return 0.0
        else:
            # Inverse linear mapping
            normalized = 10.0 - ((carbon_footprint - self.carbon_min) / 
                               (self.carbon_max - self.carbon_min)) * 10.0
            return round(normalized, 1)
    
    def calculate_nutrition_score(self, nutrition_metrics: Union[Dict, NutritionMetrics, None]) -> float:
        """
        Calculate nutrition score based on sugar, saturated fat, and processing level.
        
        Args:
            nutrition_metrics: Dictionary or NutritionMetrics object with nutrition data
            
        Returns:
            Nutrition score (0-10)
        """
        if nutrition_metrics is None:
            return 5.0  # Neutral score for missing data
            
        if isinstance(nutrition_metrics, dict):
            sugar_g = nutrition_metrics.get('sugar_g')
            saturated_fat_g = nutrition_metrics.get('saturated_fat_g')
            processed_level = nutrition_metrics.get('processed_level')
        else:
            sugar_g = nutrition_metrics.sugar_g
            saturated_fat_g = nutrition_metrics.saturated_fat_g
            processed_level = nutrition_metrics.processed_level
        
        # Handle missing data
        if sugar_g is None and saturated_fat_g is None and processed_level is None:
            return 5.0  # Neutral score for completely missing data
        
        scores = []
        
        # Sugar scoring (lower is better)
        if sugar_g is not None:
            sugar_score = max(0, 10 - (sugar_g / self.sugar_max) * 10)
            scores.append(sugar_score)
        
        # Saturated fat scoring (lower is better)
        if saturated_fat_g is not None:
            fat_score = max(0, 10 - (saturated_fat_g / self.saturated_fat_max) * 10)
            scores.append(fat_score)
        
        # Processing level scoring
        if processed_level is not None:
            processed_level = processed_level.lower()
            if processed_level == ProcessedLevel.LOW.value:
                processed_score = 10.0
            elif processed_level == ProcessedLevel.MEDIUM.value:
                processed_score = 6.0
            elif processed_level == ProcessedLevel.HIGH.value:
                processed_score = 2.0
            else:
                processed_score = 5.0  # Unknown level
            scores.append(processed_score)
        
        # Return average of available scores
        return round(sum(scores) / len(scores), 1) if scores else 5.0
    
    def analyze_news_sentiment(self, recent_news: List[str]) -> float:
        """
        Analyze sentiment of news articles and return social/ethical score.
        
        Args:
            recent_news: List of news article summaries
            
        Returns:
            Social/ethical score (0-10)
        """
        if not recent_news:
            return 5.0  # Neutral score for no news
        
        positive_count = 0
        negative_count = 0
        total_articles = len(recent_news)
        
        for article in recent_news:
            article_lower = article.lower()
            
            # Count positive keywords
            positive_matches = sum(1 for keyword in self.positive_keywords 
                                 if keyword in article_lower)
            positive_count += positive_matches
            
            # Count negative keywords
            negative_matches = sum(1 for keyword in self.negative_keywords 
                                 if keyword in article_lower)
            negative_count += negative_matches
        
        # Calculate base score
        if total_articles == 0:
            return 5.0
        
        # Weight the sentiment based on article count and keyword density
        positive_ratio = positive_count / (positive_count + negative_count + 1)
        negative_ratio = negative_count / (positive_count + negative_count + 1)
        
        # Base score starts at 5 (neutral)
        base_score = 5.0
        
        # Adjust based on sentiment
        if positive_ratio > negative_ratio:
            # More positive news
            score_adjustment = min(5.0, positive_ratio * 5.0)
            final_score = base_score + score_adjustment
        elif negative_ratio > positive_ratio:
            # More negative news
            score_adjustment = min(5.0, negative_ratio * 5.0)
            final_score = base_score - score_adjustment
        else:
            # Balanced or no clear sentiment
            final_score = base_score
        
        return round(max(0, min(10, final_score)), 1)
    
    def generate_justification(self, 
                             product_name: str,
                             carbon_score: float,
                             nutrition_score: float,
                             social_ethics_score: float,
                             carbon_footprint: Optional[float],
                             nutrition_metrics: Union[Dict, NutritionMetrics, None],
                             recent_news: List[str]) -> str:
        """
        Generate a human-readable justification for the sustainability score.
        
        Args:
            product_name: Name of the product
            carbon_score: Carbon footprint score
            nutrition_score: Nutrition score
            social_ethics_score: Social/ethics score
            carbon_footprint: Original carbon footprint value
            nutrition_metrics: Original nutrition metrics
            recent_news: Original news list
            
        Returns:
            Justification string
        """
        justifications = []
        
        # Carbon footprint justification
        if carbon_footprint is not None:
            if carbon_score >= 8:
                justifications.append("excellent carbon footprint")
            elif carbon_score >= 6:
                justifications.append("good carbon footprint")
            elif carbon_score >= 4:
                justifications.append("moderate carbon footprint")
            else:
                justifications.append("high carbon footprint")
        else:
            justifications.append("carbon footprint data unavailable")
        
        # Nutrition justification
        has_nutrition_data = False
        if nutrition_metrics:
            if isinstance(nutrition_metrics, dict):
                has_nutrition_data = any(nutrition_metrics.get(k) is not None for k in ['sugar_g', 'saturated_fat_g', 'processed_level'])
            elif hasattr(nutrition_metrics, 'sugar_g'):
                has_nutrition_data = any([nutrition_metrics.sugar_g, nutrition_metrics.saturated_fat_g, nutrition_metrics.processed_level])
        
        if has_nutrition_data:
            if nutrition_score >= 8:
                justifications.append("excellent nutritional profile")
            elif nutrition_score >= 6:
                justifications.append("good nutritional profile")
            elif nutrition_score >= 4:
                justifications.append("moderate nutritional profile")
            else:
                justifications.append("poor nutritional profile")
        else:
            justifications.append("nutritional data unavailable")
        
        # Social/ethics justification
        if recent_news:
            if social_ethics_score >= 8:
                justifications.append("positive social/ethical practices")
            elif social_ethics_score >= 6:
                justifications.append("generally positive social practices")
            elif social_ethics_score >= 4:
                justifications.append("mixed social/ethical news")
            else:
                justifications.append("concerning social/ethical issues")
        else:
            justifications.append("no recent social/ethical news available")
        
        # Combine justifications
        if len(justifications) == 1:
            return f"{product_name} shows {justifications[0]}."
        elif len(justifications) == 2:
            return f"{product_name} shows {justifications[0]} and {justifications[1]}."
        else:
            return f"{product_name} shows {', '.join(justifications[:-1])}, and {justifications[-1]}."
    
    def calculate_sustainability_score(self,
                                     product_name: str,
                                     carbon_footprint: Optional[float] = None,
                                     nutrition_metrics: Union[Dict, NutritionMetrics, None] = None,
                                     recent_news: Optional[List[str]] = None) -> SustainabilityScore:
        """
        Calculate comprehensive sustainability score for a single product.
        
        Args:
            product_name: Name of the grocery product
            carbon_footprint: Carbon footprint in kg CO2 per unit/kg
            nutrition_metrics: Nutrition metrics dictionary or NutritionMetrics object
            recent_news: List of recent news article summaries
            
        Returns:
            SustainabilityScore object with complete scoring breakdown
        """
        # Calculate individual component scores
        carbon_score = self.normalize_carbon_footprint(carbon_footprint)
        nutrition_score = self.calculate_nutrition_score(nutrition_metrics)
        social_ethics_score = self.analyze_news_sentiment(recent_news or [])
        
        # Calculate weighted final score
        final_score = (carbon_score * self.carbon_weight + 
                      nutrition_score * self.nutrition_weight + 
                      social_ethics_score * self.social_ethics_weight)
        
        # Generate justification
        justification = self.generate_justification(
            product_name, carbon_score, nutrition_score, social_ethics_score,
            carbon_footprint, nutrition_metrics, recent_news or []
        )
        
        return SustainabilityScore(
            product_name=product_name,
            sustainability_score=round(final_score, 1),
            breakdown={
                "carbon_footprint_score": carbon_score,
                "nutrition_score": nutrition_score,
                "social_ethics_score": social_ethics_score
            },
            justification=justification
        )
    
    def calculate_batch_sustainability_scores(self, products: List[Dict]) -> List[SustainabilityScore]:
        """
        Calculate sustainability scores for multiple products in batch.
        
        Args:
            products: List of product dictionaries, each containing:
                - product_name (str)
                - carbon_footprint (float, optional)
                - nutrition_metrics (dict, optional)
                - recent_news (list, optional)
        
        Returns:
            List of SustainabilityScore objects
        """
        results = []
        
        for product in products:
            try:
                score = self.calculate_sustainability_score(
                    product_name=product.get('product_name', 'Unknown Product'),
                    carbon_footprint=product.get('carbon_footprint'),
                    nutrition_metrics=product.get('nutrition_metrics'),
                    recent_news=product.get('recent_news')
                )
                results.append(score)
            except Exception as e:
                # Handle individual product errors gracefully
                error_score = SustainabilityScore(
                    product_name=product.get('product_name', 'Unknown Product'),
                    sustainability_score=0.0,
                    breakdown={
                        "carbon_footprint_score": 0.0,
                        "nutrition_score": 0.0,
                        "social_ethics_score": 0.0
                    },
                    justification=f"Error calculating score: {str(e)}"
                )
                results.append(error_score)
        
        return results
    
    def to_json(self, score: SustainabilityScore) -> Dict:
        """
        Convert SustainabilityScore to JSON-serializable dictionary.
        
        Args:
            score: SustainabilityScore object
            
        Returns:
            Dictionary representation
        """
        return {
            "product_name": score.product_name,
            "sustainability_score": score.sustainability_score,
            "breakdown": score.breakdown,
            "justification": score.justification
        }
    
    def batch_to_json(self, scores: List[SustainabilityScore]) -> List[Dict]:
        """
        Convert list of SustainabilityScore objects to JSON-serializable format.
        
        Args:
            scores: List of SustainabilityScore objects
            
        Returns:
            List of dictionary representations
        """
        return [self.to_json(score) for score in scores]


# Convenience functions for easy integration
def calculate_single_product_score(product_name: str,
                                 carbon_footprint: Optional[float] = None,
                                 nutrition_metrics: Union[Dict, NutritionMetrics, None] = None,
                                 recent_news: Optional[List[str]] = None,
                                 carbon_weight: float = 0.30,
                                 nutrition_weight: float = 0.52,
                                 social_ethics_weight: float = 0.18) -> Dict:
    """
    Convenience function to calculate sustainability score for a single product.
    
    Args:
        product_name: Name of the grocery product
        carbon_footprint: Carbon footprint in kg CO2 per unit/kg
        nutrition_metrics: Nutrition metrics dictionary
        recent_news: List of recent news article summaries
        carbon_weight: Weight for carbon footprint component
        nutrition_weight: Weight for nutrition component
        social_ethics_weight: Weight for social/ethics component
        
    Returns:
        JSON-serializable dictionary with sustainability score
    """
    scorer = SustainabilityScorer(carbon_weight, nutrition_weight, social_ethics_weight)
    score = scorer.calculate_sustainability_score(
        product_name, carbon_footprint, nutrition_metrics, recent_news
    )
    return scorer.to_json(score)


def calculate_batch_product_scores(products: List[Dict],
                                 carbon_weight: float = 0.30,
                                 nutrition_weight: float = 0.52,
                                 social_ethics_weight: float = 0.18) -> List[Dict]:
    """
    Convenience function to calculate sustainability scores for multiple products.
    
    Args:
        products: List of product dictionaries
        carbon_weight: Weight for carbon footprint component
        nutrition_weight: Weight for nutrition component
        social_ethics_weight: Weight for social/ethics component
        
    Returns:
        List of JSON-serializable dictionaries with sustainability scores
    """
    scorer = SustainabilityScorer(carbon_weight, nutrition_weight, social_ethics_weight)
    scores = scorer.calculate_batch_sustainability_scores(products)
    return scorer.batch_to_json(scores)


# Example usage and testing
if __name__ == "__main__":
    # Example single product calculation
    example_product = {
        "product_name": "Coke 6-pack",
        "carbon_footprint": 2.5,
        "nutrition_metrics": {
            "sugar_g": 12,
            "saturated_fat_g": 3,
            "processed_level": "high"
        },
        "recent_news": [
            "Coca-Cola announces new sustainability initiative for water conservation",
            "Minor labor dispute reported at bottling plant in Mexico"
        ]
    }
    
    # Calculate single product score
    single_score = calculate_single_product_score(
        product_name=example_product["product_name"],
        carbon_footprint=example_product["carbon_footprint"],
        nutrition_metrics=example_product["nutrition_metrics"],
        recent_news=example_product["recent_news"]
    )
    
    print("Single Product Score:")
    print(json.dumps(single_score, indent=2))
    
    # Example batch calculation
    batch_products = [
        {
            "product_name": "Organic Apples",
            "carbon_footprint": 0.5,
            "nutrition_metrics": {
                "sugar_g": 10,
                "saturated_fat_g": 0,
                "processed_level": "low"
            },
            "recent_news": [
                "Local organic farm receives fair trade certification",
                "Community garden initiative supports local farmers"
            ]
        },
        {
            "product_name": "Frozen Pizza",
            "carbon_footprint": 3.2,
            "nutrition_metrics": {
                "sugar_g": 8,
                "saturated_fat_g": 12,
                "processed_level": "high"
            },
            "recent_news": [
                "Food safety concerns raised about frozen food processing",
                "Company faces criticism for excessive packaging"
            ]
        }
    ]
    
    # Calculate batch scores
    batch_scores = calculate_batch_product_scores(batch_products)
    
    print("\nBatch Product Scores:")
    print(json.dumps(batch_scores, indent=2))
