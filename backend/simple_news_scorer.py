"""
Simple News-Based Sustainability Scorer

This module focuses on using the product name to search for news first,
then calculating sustainability scores based on the news analysis.
"""

import os
import json
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sustainability_scorer import SustainabilityScorer
from nutrition_fetcher import NutritionFetcher


class SimpleNewsScorer:
    """
    Simple news-based sustainability scorer that:
    1. Takes a product name
    2. Searches for news about the product/brand
    3. Analyzes the news for sustainability factors
    4. Calculates a sustainability score
    """
    
    def __init__(self, news_api_key: Optional[str] = None, usda_api_key: Optional[str] = None, gemini_api_key: Optional[str] = None):
        """
        Initialize the simple news scorer.
        
        Args:
            news_api_key: News API key (optional, uses Google News RSS as fallback)
            usda_api_key: USDA FoodData Central API key (optional, uses DEMO_KEY as fallback)
            gemini_api_key: Google Gemini API key for AI analysis
        """
        self.news_api_key = news_api_key or os.getenv('GNEWS_API_KEY') 
        self.gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        self.news_base_url = "https://gnews.io/api/v4/search"
        self.news_api_name = "GNews API"
        self.gemini_api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        
        # Initialize base sustainability scorer
        self.sustainability_scorer = SustainabilityScorer()
        
        # Initialize nutrition fetcher
        self.nutrition_fetcher = NutritionFetcher(usda_api_key)
        
        # Sustainability keywords for news filtering
        self.sustainability_keywords = [
            'sustainability', 'environmental', 'carbon', 'emissions', 'climate',
            'renewable', 'organic', 'fair trade', 'ethical', 'labor', 'workers',
            'safety', 'health', 'pollution', 'waste', 'recycling', 'green',
            'eco-friendly', 'sustainable', 'social responsibility', 'CSR',
            'human rights', 'working conditions', 'supply chain', 'transparency'
        ]
    
    def extract_brand_name(self, product_name: str) -> str:
        """
        Extract brand name from product name for news search.
        
        Args:
            product_name: Full product name
            
        Returns:
            Extracted brand name
        """
        # Simple brand extraction - remove common product descriptors
        descriptors = ['organic', 'premium', 'fresh', 'frozen', 'dried', 'canned', 'bottled', 'classic']
        brand_name = product_name.lower()
        
        for descriptor in descriptors:
            brand_name = brand_name.replace(descriptor, '').strip()
        
        # Remove common product types
        product_types = ['apples', 'bananas', 'pizza', 'cereal', 'milk', 'bread', 'juice', 'burger', 't-shirt', 'model']
        for product_type in product_types:
            brand_name = brand_name.replace(product_type, '').strip()
        
        # Clean up and return
        brand_name = ' '.join(brand_name.split())
        
        # If we can't extract a meaningful brand, use the full product name
        if len(brand_name) < 3:
            brand_name = product_name
        
        return brand_name
    
    def search_news(self, brand_name: str, days_back: int = 60) -> List[Dict]:
        """
        Search for news articles about a brand.
        
        Args:
            brand_name: Name of the brand to search for
            days_back: Number of days to look back for news
            
        Returns:
            List of news articles with metadata
        """
        print(f"🔍 Searching for news about: {brand_name}")
        
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Prepare search query with sustainability focus
            query = f'"{brand_name}" AND (sustainability OR environmental OR "social responsibility" OR ethical OR labor OR "fair trade" OR organic OR "carbon footprint")'
            
            if self.news_api_key:
                # Use GNews API
                print("📰 Using GNews API for news search...")
                return self._search_news_api(query, start_date, end_date)
            else:
                # Use Google News RSS
                print("📰 Using Google News RSS for news search...")
                return self._search_google_news_rss(brand_name)
                
        except Exception as e:
            print(f"❌ Error searching for news: {e}")
            return []
    
    def _search_news_api(self, query: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Search using GNews API"""
        try:
            params = {
                'q': query,
                'from': start_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'to': end_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'sortby': 'publishedAt',
                'lang': 'en',
                'max': 25,
                'token': self.news_api_key
            }
            
            response = requests.get(self.news_base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            articles = data.get('articles', [])
            
            print(f"📊 Found {len(articles)} articles from {self.news_api_name}")
            
            # Filter and enhance articles
            filtered_articles = []
            for article in articles:
                if self._is_sustainability_relevant(article):
                    enhanced_article = {
                        'title': article.get('title', ''),
                        'description': article.get('description', ''),
                        'content': article.get('content', ''),
                        'url': article.get('url', ''),
                        'publishedAt': article.get('publishedAt', ''),
                        'source': article.get('source', {}).get('name', ''),
                        'relevance_score': self._calculate_relevance_score(article)
                    }
                    filtered_articles.append(enhanced_article)
            
            # Sort by relevance
            filtered_articles.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            print(f"✅ {len(filtered_articles)} relevant articles found")
            return filtered_articles[:5]  # Return top 5 most relevant articles
            
        except Exception as e:
            print(f"❌ {self.news_api_name} error: {e}")
            return []
    
    def _search_google_news_rss(self, brand_name: str) -> List[Dict]:
        """Search using Google News RSS"""
        try:
            import feedparser
            import urllib.parse
            
            # Google News RSS URL with proper encoding
            query = f'{brand_name} sustainability environmental social responsibility'
            encoded_query = urllib.parse.quote_plus(query)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
            
            feed = feedparser.parse(rss_url)
            articles = []
            
            print(f"📊 Found {len(feed.entries)} articles from Google News RSS")
            
            for entry in feed.entries[:25]:  # Limit to 25 articles
                article = {
                    'title': entry.get('title', ''),
                    'description': entry.get('summary', ''),
                    'content': entry.get('summary', ''),
                    'url': entry.get('link', ''),
                    'publishedAt': entry.get('published', ''),
                    'source': 'Google News',
                    'relevance_score': self._calculate_relevance_score({
                        'title': entry.get('title', ''),
                        'description': entry.get('summary', '')
                    })
                }
                articles.append(article)
            
            # Filter for sustainability relevance
            filtered_articles = [article for article in articles if self._is_sustainability_relevant(article)]
            
            print(f"✅ {len(filtered_articles)} relevant articles found")
            return filtered_articles[:5]  # Return top 5 most relevant articles
            
        except Exception as e:
            print(f"❌ Google News RSS error: {e}")
            return []
    
    def _is_sustainability_relevant(self, article: Dict) -> bool:
        """Check if an article is relevant to sustainability topics"""
        text = f"{article.get('title', '')} {article.get('description', '')}".lower()
        
        # Check for sustainability keywords
        keyword_matches = sum(1 for keyword in self.sustainability_keywords 
                             if keyword.lower() in text)
        
        return keyword_matches >= 1
    
    def _calculate_relevance_score(self, article: Dict) -> float:
        """Calculate relevance score for an article"""
        text = f"{article.get('title', '')} {article.get('description', '')}".lower()
        
        score = 0
        for keyword in self.sustainability_keywords:
            if keyword.lower() in text:
                score += 1
        
        return min(score / len(self.sustainability_keywords), 1.0)
    
    def analyze_news_with_gemini(self, articles: List[Dict], brand_name: str) -> Tuple[float, Dict]:
        """
        Analyze news articles using Gemini AI for sustainability sentiment.
        
        Args:
            articles: List of news articles
            brand_name: Name of the brand being analyzed
            
        Returns:
            Tuple of (sentiment_score, analysis_details)
        """
        if not self.gemini_api_key or not articles:
            return self.analyze_news_sentiment(articles)
        
        print(f"🤖 Using Gemini AI to analyze {len(articles)} articles for {brand_name}...")
        
        try:
            # Prepare articles text for analysis
            articles_text = []
            for article in articles[:5]:  # Limit to first 5 articles for API efficiency
                title = article.get('title', '')
                description = article.get('description', '')
                if title or description:
                    articles_text.append(f"Title: {title}\nDescription: {description}")
            
            if not articles_text:
                return self.analyze_news_sentiment(articles)
            
            # Create prompt for Gemini
            prompt = f"""
            Analyze the following news articles about {brand_name} for sustainability and social responsibility factors.
            
            Articles:
            {chr(10).join(articles_text)}
            
            Please provide:
            1. Overall sentiment (positive/negative/neutral)
            2. Key sustainability themes
            3. Any concerns or positive highlights
            4. A sentiment score from 1-10 (1=very negative, 10=very positive, 5=neutral)
            
            Respond in JSON format:
            {{
                "sentiment": "positive/negative/neutral",
                "score": 1-10,
                "themes": ["theme1", "theme2"],
                "highlights": ["positive point"],
                "concerns": ["negative point"]
            }}
            """
            
            # Call Gemini API
            headers = {
                'Content-Type': 'application/json',
            }
            
            data = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }]
            }
            
            response = requests.post(
                f"{self.gemini_api_url}?key={self.gemini_api_key}",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    ai_response = result['candidates'][0]['content']['parts'][0]['text']
                    
                    # Parse AI response
                    try:
                        # Extract JSON from response
                        import re
                        json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                        if json_match:
                            ai_analysis = json.loads(json_match.group())
                            
                            sentiment_score = float(ai_analysis.get('score', 5.0))
                            
                            analysis_details = {
                                "articles_analyzed": len(articles),
                                "positive_articles": 1 if ai_analysis.get('sentiment') == 'positive' else 0,
                                "negative_articles": 1 if ai_analysis.get('sentiment') == 'negative' else 0,
                                "neutral_articles": 1 if ai_analysis.get('sentiment') == 'neutral' else 0,
                                "positive_highlights": ai_analysis.get('highlights', []),
                                "negative_concerns": ai_analysis.get('concerns', []),
                                "key_themes": ai_analysis.get('themes', []),
                                "overall_sentiment": ai_analysis.get('sentiment', 'neutral'),
                                "ai_analysis": True
                            }
                            
                            print(f"🤖 Gemini AI Analysis: {analysis_details['overall_sentiment']} (Score: {sentiment_score:.1f}/10)")
                            return round(sentiment_score, 1), analysis_details
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        print(f"⚠️ Error parsing Gemini response: {e}")
                        return self.analyze_news_sentiment(articles)
                else:
                    print("⚠️ No valid response from Gemini API")
                    return self.analyze_news_sentiment(articles)
            else:
                print(f"⚠️ Gemini API error: {response.status_code}")
                return self.analyze_news_sentiment(articles)
                
        except Exception as e:
            print(f"⚠️ Gemini API error: {e}")
            return self.analyze_news_sentiment(articles)
    
    def analyze_news_sentiment(self, articles: List[Dict]) -> Tuple[float, Dict]:
        """
        Analyze news articles for sustainability sentiment.
        
        Args:
            articles: List of news articles
            
        Returns:
            Tuple of (sentiment_score, analysis_details)
        """
        if not articles:
            return 5.0, {"message": "No news articles found", "articles_analyzed": 0}
        
        print(f"📊 Analyzing {len(articles)} news articles...")
        
        # Simple sentiment analysis based on keywords
        positive_keywords = [
            'sustainable', 'ethical', 'fair', 'green', 'renewable', 'positive', 'improvement',
            'certified', 'organic', 'eco-friendly', 'carbon neutral', 'zero waste',
            'community', 'charity', 'donation', 'support', 'initiative'
        ]
        
        negative_keywords = [
            'violation', 'abuse', 'exploitation', 'unsafe', 'toxic', 'contamination',
            'lawsuit', 'fine', 'penalty', 'criticism', 'concern', 'problem', 'issue',
            'pollution', 'waste', 'harmful', 'damage', 'negative'
        ]
        
        positive_count = 0
        negative_count = 0
        total_articles = len(articles)
        
        analysis_details = {
            "articles_analyzed": total_articles,
            "positive_articles": 0,
            "negative_articles": 0,
            "neutral_articles": 0,
            "key_themes": [],
            "positive_highlights": [],
            "negative_concerns": []
        }
        
        for article in articles:
            text = f"{article.get('title', '')} {article.get('description', '')}".lower()
            
            article_positive = sum(1 for keyword in positive_keywords if keyword in text)
            article_negative = sum(1 for keyword in negative_keywords if keyword in text)
            
            positive_count += article_positive
            negative_count += article_negative
            
            if article_positive > article_negative:
                analysis_details["positive_articles"] += 1
                if article_positive > 0:
                    analysis_details["positive_highlights"].append(article.get('title', '')[:100])
            elif article_negative > article_positive:
                analysis_details["negative_articles"] += 1
                if article_negative > 0:
                    analysis_details["negative_concerns"].append(article.get('title', '')[:100])
            else:
                analysis_details["neutral_articles"] += 1
        
        # Calculate sentiment score
        if positive_count > negative_count:
            sentiment_score = min(10.0, 5.0 + (positive_count - negative_count) * 0.5)
            analysis_details["overall_sentiment"] = "positive"
        elif negative_count > positive_count:
            sentiment_score = max(1.0, 5.0 - (negative_count - positive_count) * 0.5)
            analysis_details["overall_sentiment"] = "negative"
        else:
            sentiment_score = 5.0
            analysis_details["overall_sentiment"] = "neutral"
        
        # Extract key themes
        all_text = ' '.join([f"{article.get('title', '')} {article.get('description', '')}" 
                           for article in articles]).lower()
        
        for keyword in self.sustainability_keywords:
            if keyword in all_text:
                analysis_details["key_themes"].append(keyword)
        
        print(f"📈 Sentiment Analysis: {analysis_details['overall_sentiment']} (Score: {sentiment_score:.1f}/10)")
        print(f"   Positive articles: {analysis_details['positive_articles']}")
        print(f"   Negative articles: {analysis_details['negative_articles']}")
        print(f"   Neutral articles: {analysis_details['neutral_articles']}")
        
        return round(sentiment_score, 1), analysis_details
    
    def calculate_carbon_score(self, product_name: str, nutrition_data: Dict) -> float:
        """
        Calculate carbon footprint score based on environmental factors.
        
        Args:
            product_name: Name of the product
            nutrition_data: Nutrition data from USDA
            
        Returns:
            Carbon score (0-10)
        """
        carbon_score = 5.0  # Start with neutral score
        
        # Factor 1: Product type and processing level
        if any(keyword in product_name.lower() for keyword in ['organic', 'local', 'fresh', 'natural']):
            carbon_score += 1.5  # Organic/local products have lower carbon footprint
        elif any(keyword in product_name.lower() for keyword in ['processed', 'canned', 'frozen', 'packaged']):
            carbon_score -= 1.0  # Processed foods have higher carbon footprint
        
        # Factor 2: Packaging indicators
        if any(keyword in product_name.lower() for keyword in ['bulk', 'unpackaged', 'loose']):
            carbon_score += 1.0  # Bulk items have less packaging waste
        elif any(keyword in product_name.lower() for keyword in ['single serve', 'individual', 'snack pack']):
            carbon_score -= 1.5  # Individual packaging increases waste
        
        # Factor 3: Transportation distance (estimated based on product type)
        if any(keyword in product_name.lower() for keyword in ['imported', 'tropical', 'exotic']):
            carbon_score -= 1.0  # Imported products have higher transportation emissions
        elif any(keyword in product_name.lower() for keyword in ['local', 'regional', 'domestic']):
            carbon_score += 0.5  # Local products have lower transportation emissions
        
        # Factor 4: Nutrition-based environmental impact
        if nutrition_data:
            # High sugar content often indicates more processing and energy use
            sugar_content = nutrition_data.get('sugar', 0)
            if sugar_content > 15:  # High sugar
                carbon_score -= 0.5
            elif sugar_content < 5:  # Low sugar
                carbon_score += 0.5
            
            # High protein content often indicates more resource-intensive production
            protein_content = nutrition_data.get('protein', 0)
            if protein_content > 20:  # Very high protein (likely meat/dairy)
                carbon_score -= 1.0
            elif protein_content > 10:  # High protein
                carbon_score -= 0.5
        
        # Factor 5: Brand sustainability (basic keyword analysis)
        if any(keyword in product_name.lower() for keyword in ['sustainable', 'eco', 'green', 'earth']):
            carbon_score += 1.0
        
        # Ensure score stays within 0-10 range
        return max(0, min(10, carbon_score))

    def calculate_social_ethics_score_with_gemini(self, brand_name: str, product_name: str) -> Tuple[float, Dict]:
        """
        Calculate social ethics score using Gemini AI to analyze brand ethics.
        
        Args:
            brand_name: Name of the brand
            product_name: Name of the product
            
        Returns:
            Tuple of (ethics_score, analysis_details)
        """
        if not self.gemini_api_key:
            return 5.0, {"message": "Gemini API key not available", "analysis": "fallback"}
        
        try:
            # Prepare prompt for Gemini AI
            prompt = f"""
            Analyze the social ethics and corporate responsibility of the brand "{brand_name}" for the product "{product_name}".
            
            Please research and evaluate the following aspects:
            1. Labor practices and worker rights
            2. Environmental responsibility and sustainability efforts
            3. Community involvement and social impact
            4. Supply chain ethics and fair trade practices
            5. Corporate governance and transparency
            6. Any controversies or ethical concerns
            
            Provide a score from 0-10 where:
            - 0-3: Poor ethics, major controversies, labor violations
            - 4-6: Average ethics, some concerns but generally acceptable
            - 7-10: Excellent ethics, strong social responsibility, positive impact
            
            Respond with a JSON object containing:
            {{
                "ethics_score": <number>,
                "reasoning": "<brief explanation>",
                "key_factors": ["<factor1>", "<factor2>", "<factor3>"],
                "controversies": ["<any issues>"],
                "positive_actions": ["<any positive actions>"]
            }}
            """
            
            # Call Gemini API
            headers = {
                'Content-Type': 'application/json',
                'x-goog-api-key': self.gemini_api_key
            }
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 1000
                }
            }
            
            response = requests.post(self.gemini_api_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    content = result['candidates'][0]['content']['parts'][0]['text']
                    
                    # Try to parse JSON response
                    try:
                        # Extract JSON from response
                        import re
                        json_match = re.search(r'\{.*\}', content, re.DOTALL)
                        if json_match:
                            analysis_data = json.loads(json_match.group())
                            ethics_score = analysis_data.get('ethics_score', 5.0)
                            return ethics_score, {
                                "ai_analysis": True,
                                "reasoning": analysis_data.get('reasoning', ''),
                                "key_factors": analysis_data.get('key_factors', []),
                                "controversies": analysis_data.get('controversies', []),
                                "positive_actions": analysis_data.get('positive_actions', [])
                            }
                    except json.JSONDecodeError:
                        pass
                    
                    # Fallback: extract score from text
                    score_match = re.search(r'ethics_score["\']?\s*:\s*(\d+(?:\.\d+)?)', content)
                    if score_match:
                        ethics_score = float(score_match.group(1))
                        return ethics_score, {
                            "ai_analysis": True,
                            "reasoning": "AI analysis completed",
                            "raw_response": content[:200] + "..."
                        }
            
            # Fallback to basic analysis
            return 5.0, {"message": "Gemini API analysis failed", "analysis": "fallback"}
            
        except Exception as e:
            return 5.0, {"message": f"Gemini API error: {str(e)}", "analysis": "fallback"}

    def calculate_sustainability_score(self, product_name: str, 
                                     carbon_footprint: Optional[float] = None,
                                     nutrition_metrics: Optional[Dict] = None,
                                     days_back: int = 30,
                                     use_usda_nutrition: bool = True) -> Dict:
        """
        Calculate sustainability score based on product name and news analysis.
        
        Args:
            product_name: Name of the product
            carbon_footprint: Optional carbon footprint data
            nutrition_metrics: Optional nutrition data
            days_back: Number of days to look back for news
            use_usda_nutrition: Whether to fetch real nutrition data from USDA API
            
        Returns:
            Dictionary with sustainability score and analysis
        """
        print(f"\n🌱 Calculating sustainability score for: {product_name}")
        print("=" * 60)
        
        # Step 1: Extract brand name
        brand_name = self.extract_brand_name(product_name)
        print(f"🏷️  Extracted brand: {brand_name}")
        
        # Step 2: Fetch USDA nutrition data (if enabled)
        usda_nutrition_data = None
        if use_usda_nutrition:
            try:
                usda_nutrition_data = self.nutrition_fetcher.fetch_nutrition_for_product(product_name)
                print(f"🥗 USDA Nutrition Score: {usda_nutrition_data.get('nutrition_score', 'N/A')}/10")
                print(f"   Processed Level: {usda_nutrition_data.get('processed_level', 'N/A')}")
            except Exception as e:
                print(f"⚠️  Could not fetch USDA nutrition data: {e}")
                usda_nutrition_data = None
        
        # Step 3: Search for news
        articles = self.search_news(brand_name, days_back)
        
        # Step 4: Calculate dynamic carbon score
        nutrition_data = usda_nutrition_data.get('nutrition_data', {}) if usda_nutrition_data else {}
        carbon_score = self.calculate_carbon_score(product_name, nutrition_data)
        print(f"🌍 Dynamic Carbon Score: {carbon_score}/10")
        
        # Step 5: Calculate dynamic social ethics score with Gemini AI
        ethics_score, ethics_analysis = self.calculate_social_ethics_score_with_gemini(brand_name, product_name)
        print(f"⚖️ Dynamic Social Ethics Score: {ethics_score}/10")
        
        # Step 6: Analyze news sentiment with Gemini AI
        news_score, news_analysis = self.analyze_news_with_gemini(articles, brand_name)
        
        # Step 7: Calculate base sustainability score
        # Use USDA nutrition data if available, otherwise use provided nutrition_metrics
        final_nutrition_metrics = nutrition_metrics
        if usda_nutrition_data and usda_nutrition_data.get('nutrition_data'):
            # Convert USDA nutrition data to format expected by sustainability scorer
            usda_data = usda_nutrition_data['nutrition_data']
            final_nutrition_metrics = {
                'sugar_g': usda_data.get('sugar', 0),
                'saturated_fat_g': usda_data.get('saturated_fat', 0),
                'processed_level': usda_nutrition_data.get('processed_level', 'medium')
            }
            print(f"🥗 Using USDA nutrition data: {final_nutrition_metrics}")
        
        base_score = self.sustainability_scorer.calculate_sustainability_score(
            product_name=product_name,
            carbon_footprint=carbon_footprint,
            nutrition_metrics=final_nutrition_metrics,
            recent_news=[article.get('title', '') for article in articles]
        )
        
        # Step 8: Combine scores with dynamic carbon and ethics scores
        # Weight: Nutrition (35%), Carbon (25%), Social Ethics (20%), News (20%)
        final_score = (
            base_score.breakdown["nutrition_score"] * 0.35 +
            carbon_score * 0.25 +
            ethics_score * 0.20 +
            news_score * 0.20
        )
        
        # Step 9: Generate enhanced justification
        justification = self._generate_enhanced_justification(
            product_name, base_score, news_score, news_analysis, len(articles)
        )
        
        result = {
            "product_name": product_name,
            "brand_name": brand_name,
            "sustainability_score": round(final_score, 1),
            "base_score": base_score.sustainability_score,
            "news_score": news_score,
            "breakdown": {
                "carbon_footprint_score": carbon_score,
                "nutrition_score": base_score.breakdown["nutrition_score"],
                "social_ethics_score": ethics_score
            },
            "carbon_analysis": {
                "score": carbon_score,
                "factors": ["Product type", "Packaging", "Transportation", "Nutrition impact", "Brand sustainability"]
            },
            "ethics_analysis": ethics_analysis,
            "news_analysis": news_analysis,
            "articles_found": len(articles),
            "justification": justification,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        # Add USDA nutrition data if available
        if usda_nutrition_data:
            result["usda_nutrition"] = {
                "nutrition_score": usda_nutrition_data.get('nutrition_score'),
                "processed_level": usda_nutrition_data.get('processed_level'),
                "nutrition_data": usda_nutrition_data.get('nutrition_data', {}),
                "score_breakdown": usda_nutrition_data.get('score_breakdown', {}),
                "source": "USDA FoodData Central"
            }
        
        print(f"\n🎯 Final Sustainability Score: {final_score:.1f}/10")
        print(f"   Base Score: {base_score.sustainability_score:.1f}/10")
        print(f"   News Score: {news_score:.1f}/10")
        print(f"   Articles Analyzed: {len(articles)}")
        
        return result
    
    def _generate_enhanced_justification(self, product_name: str, base_score, 
                                       news_score: float, news_analysis: Dict, 
                                       articles_count: int) -> str:
        """Generate enhanced justification including news insights"""
        justifications = []
        
        # Base score justification
        if base_score.sustainability_score >= 8:
            justifications.append("excellent base sustainability metrics")
        elif base_score.sustainability_score >= 6:
            justifications.append("good base sustainability metrics")
        elif base_score.sustainability_score >= 4:
            justifications.append("moderate base sustainability metrics")
        else:
            justifications.append("poor base sustainability metrics")
        
        # News analysis justification
        if articles_count > 0:
            sentiment = news_analysis.get('overall_sentiment', 'neutral')
            if sentiment == 'positive':
                justifications.append(f"positive recent news coverage ({articles_count} articles)")
            elif sentiment == 'negative':
                justifications.append(f"concerning recent news coverage ({articles_count} articles)")
            else:
                justifications.append(f"mixed recent news coverage ({articles_count} articles)")
        else:
            justifications.append("no recent sustainability news found")
        
        # Combine justifications
        if len(justifications) == 1:
            return f"{product_name} shows {justifications[0]}."
        else:
            return f"{product_name} shows {justifications[0]} and {justifications[1]}."


# Convenience function for easy use
def calculate_news_based_score(product_name: str, 
                             carbon_footprint: Optional[float] = None,
                             nutrition_metrics: Optional[Dict] = None,
                             news_api_key: Optional[str] = None,
                             usda_api_key: Optional[str] = None,
                             days_back: int = 30,
                             use_usda_nutrition: bool = True) -> Dict:
    """
    Convenience function to calculate news-based sustainability score.
    
    Args:
        product_name: Name of the product
        carbon_footprint: Optional carbon footprint data
        nutrition_metrics: Optional nutrition data
        news_api_key: Optional News API key
        usda_api_key: Optional USDA FoodData Central API key
        days_back: Number of days to look back for news
        use_usda_nutrition: Whether to fetch real nutrition data from USDA API
        
    Returns:
        Dictionary with sustainability score and analysis
    """
    scorer = SimpleNewsScorer(news_api_key, usda_api_key)
    return scorer.calculate_sustainability_score(
        product_name=product_name,
        carbon_footprint=carbon_footprint,
        nutrition_metrics=nutrition_metrics,
        days_back=days_back,
        use_usda_nutrition=use_usda_nutrition
    )


# Example usage and testing
if __name__ == "__main__":
    print("🌱 Simple News-Based Sustainability Scorer")
    print("=" * 50)
    
    # Test with a well-known brand
    test_products = [
        "Tesla Model 3",
        "Nestle KitKat", 
        "Patagonia Organic Cotton T-Shirt",
        "Coca-Cola Classic"
    ]
    
    for product in test_products:
        print(f"\n{'='*60}")
        try:
            score = calculate_news_based_score(product)
            print(f"\n✅ Analysis complete for {product}")
            print(f"   Final Score: {score['sustainability_score']}/10")
            print(f"   News Score: {score['news_score']}/10")
            print(f"   Articles Found: {score['articles_found']}")
            print(f"   Justification: {score['justification']}")
        except Exception as e:
            print(f"❌ Error analyzing {product}: {e}")
    
    print(f"\n{'='*60}")
    print("🎉 News-based sustainability analysis complete!")
