#!/usr/bin/env python3
"""
Center Object Classifier - Monitors video feed for objects in center region
and classifies them using Gemini API

This script uses motion detection and scene change detection to automatically
capture images when objects appear in the center region of the video feed.
Captured images are then classified using Google's Gemini API.

Features:
- Motion detection using background subtraction and frame differencing
- Scene change detection using histogram comparison
- Automatic image capture with cooldown period
- Gemini API integration for object classification
- Real-time visual feedback with detection overlays
"""

# Standard library imports
import asyncio
import json
import os
import re
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Third-party imports
import cv2
from dotenv import load_dotenv
# Optional imports with fallback
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    try:
        from google import genai
        GEMINI_AVAILABLE = True
    except ImportError:
        print("Warning: Google Gemini library not found. Classification will be skipped.")
        print("Install with: pip install google-generativeai")
        GEMINI_AVAILABLE = False
        genai = None

# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

# File and directory paths
CAPTURES_DIR = Path("captures")
load_dotenv()
# Gemini API configuration
GEMINI_MODEL = "gemini-flash-lite-latest"  # Model to use for classification
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Import Google scraping functionality
try:
    from google_scrape import scrape_google_shopping_deals
    GOOGLE_SCRAPE_AVAILABLE = True
except ImportError:
    print("Warning: google_scrape.py not found. Deal analysis will be skipped.")
    GOOGLE_SCRAPE_AVAILABLE = False
    scrape_google_shopping_deals = None

# Import TTS functionality
try:
    from elevenlabs_tts import ElevenLabsTTS
    TTS_AVAILABLE = True
except ImportError:
    print("Warning: elevenlabs_tts.py not found. Text-to-speech will be disabled.")
    TTS_AVAILABLE = False
    ElevenLabsTTS = None

# Center region detection (as percentage of frame)
CENTER_REGION_WIDTH = 0.3   # 30% of frame width
CENTER_REGION_HEIGHT = 0.3  # 30% of frame height

# Sampling and timing parameters
CAPTURE_COOLDOWN = 2.0  # Seconds between captures (prevents spam)
FRAME_PROCESSING_RATE = 1  # Process every N frames (1 = every frame)

# Motion detection parameters
MOTION_THRESHOLD = 30  # Pixel difference threshold for frame differencing
MOTION_RATIO_THRESHOLD = 0.01  # Minimum ratio of center region with motion (1%)

# Scene change detection parameters
HISTOGRAM_COMPARISON_THRESHOLD = 0.7  # Correlation threshold for scene change (0-1)
# Note: Lower values = more sensitive to scene changes
# Current value of 0.7 means scenes with <70% correlation are considered "changed"

# Cart and bag detection parameters
BAG_DETECTION_KEYWORDS = ['bag', 'shopping bag', 'tote', 'container', 'basket', 'cart']
CART_UPDATE_COOLDOWN = 10.0  # Seconds between cart updates for same item (increased to prevent duplicates)
CART_FUZZY_MATCH_WINDOW = 10.0  # Seconds - don't add similar items if added within this window

# Persistence parameters
RESULTS_FLUSH_DELAY = 2.0  # Seconds to wait after last cart update before saving results

# Grocery filtering parameters
GROCERY_CATEGORIES = ['food', 'beverage', 'snack', 'snack food', 'dairy', 'produce', 'meat', 'bakery', 'frozen', 'pantry', 'condiment', 'spice', 'cereal', 'candy', 'chocolate', 'drink', 'juice', 'soda', 'water', 'coffee', 'tea', 'alcohol', 'wine', 'beer']
NON_GROCERY_CATEGORIES = ['sports equipment', 'hardware', 'electronics', 'clothing', 'accessory', 'exercise equipment', 'furniture', 'toy', 'book', 'tool', 'appliance', 'beauty', 'health', 'cleaning', 'automotive', 'garden', 'office', 'pet', 'baby', 'home', 'kitchen', 'bathroom', 'bedroom', 'living room']

# Confidence filtering
MIN_CONFIDENCE_THRESHOLD = 0.88  # Only accept classifications with confidence >= 0.88

# Classification deduplication parameters
DEDUPLICATION_TIME_WINDOW = 5.0  # Seconds - classify only once per time window
DEDUPLICATION_SIMILARITY_THRESHOLD = 0.8  # Similarity threshold for considering results the same

# Separate cooldowns for classification vs cart updates
CLASSIFICATION_COOLDOWN = 5.0  # Seconds between actual API calls
CART_UPDATE_COOLDOWN = 0.0  # No cooldown for cart updates (immediate)

# =============================================================================
# GEMINI PROMPT CONFIGURATION
# =============================================================================

GEMINI_PROMPT = (
    "You are an assistant that identifies grocery items being held up to the camera by a hand. "
    "ONLY classify objects that are being held up by a visible hand in the image. "
    "Be VERY careful and accurate - only identify items you can clearly see and recognize. "
    "If no hand is holding an object, respond with: {\"object_name\": \"no_hand_holding_object\", \"brand\": \"N/A\", \"category\": \"other\", \"confidence\": 0.0} "
    "If you cannot clearly identify what the item is, respond with: {\"object_name\": \"unidentifiable_item\", \"brand\": \"N/A\", \"category\": \"other\", \"confidence\": 0.0} "
    "Look at this image and respond with a JSON object containing "
    "the following keys: object_name, brand, category, confidence. "
    "object_name should be the specific name of the grocery item being held (be precise). "
    "brand should be the brand name of the item (only if clearly visible). "
    "category should be a grocery category (e.g., 'food', 'beverage', 'snack'). "
    "confidence should be a number between 0 and 1 indicating how confident you are that a hand is holding a clearly identifiable grocery item. "
    "Only detect grocery items that are clearly being held up by a hand to the camera and that you can confidently identify."
)

CART_CHECK_PROMPT = (
    "You are helping to manage a shopping cart. I will provide you with:\n"
    "1. A new item that was just detected: {new_item}\n"
    "2. The current shopping cart contents: {cart_contents}\n"
    "3. The timestamp when each item was added: {timestamps}\n"
    "4. Current time: {current_time}\n\n"
    "Please determine if the new item is the same as or very similar to any item in the cart that was added within the last 10 seconds. "
    "Consider items similar if they are the same product (e.g., 'Diet Coke can' and 'Diet Coke' are the same, 'Pringles can' and 'Pringles Original Potato Crisps' are similar).\n\n"
    "Respond ONLY with a valid JSON object (no markdown, no code blocks, no extra text):\n"
    "{{\n"
    '  "is_duplicate": true,\n'
    '  "similar_item": "item name if duplicate, empty string otherwise",\n'
    '  "time_diff": 0,\n'
    '  "reason": "brief explanation"\n'
    "}}\n"
    "Make sure the JSON is valid and parseable."
)

DEAL_ANALYSIS_PROMPT = (
    "You are a friendly shopping assistant. "
    "I detected: {item_name} ({brand}) - {category}\n"
    "Here are current deals:\n{deals_data}\n\n"
    "Give me 2 conversational sentences:\n"
    "1. Tell me the best deal for THIS EXACT product and where to get it\n"
    "2. Suggest ONE good alternative product I could consider instead\n\n"
    "Respond ONLY with valid JSON (no markdown, no code blocks):\n"
    "{{\n"
    '  "best_deal_message": "The best deal for [product] is $X.XX at [store].",\n'
    '  "alternative_message": "You might also consider [alternative product] for $X.XX at [store], which [reason]."\n'
    "}}\n"
    "Keep it natural and conversational. Make sure the JSON is valid."
)

class CenterObjectClassifier:
    def __init__(self, enable_tts=False):
        self.gemini_client = None
        self.captures_dir = CAPTURES_DIR
        self.enable_tts = enable_tts and TTS_AVAILABLE
        self.tts_service = None
        
        # Initialize TTS if enabled
        if self.enable_tts:
            try:
                self.tts_service = ElevenLabsTTS()
                print("🔊 Text-to-speech enabled")
            except Exception as e:
                print(f"⚠️ Could not initialize TTS: {e}")
                self.enable_tts = False
        self.last_capture_time = 0
        self.frame_count = 0
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(detectShadows=True)
        self.previous_frame = None
        self.previous_histogram = None
        self.scene_change_detected = False
        
        # Cart management
        self.cart = {}  # {item_name: {'brand': brand, 'category': category, 'count': count, 'last_seen': timestamp}}
        self.last_cart_update = {}  # Track last update time for each item
        self.bag_detected = False
        self.bag_detection_confidence = 0.0
        
        # Results tracking
        self.all_classifications = []  # Store all classification results
        self.results_file = "results.json"
        
        # Deduplication tracking
        self.last_classification_time = 0
        self.last_classification_result = None
        
        # Separate tracking for classification vs cart updates
        self.last_api_call_time = 0
        self.pending_classifications = []  # Queue for pending classifications
        
        # Deal analysis tracking
        self.deal_analysis_results: List[Dict[str, Any]] = []  # Store all deal analysis results
        self.deal_analysis_cache: Dict[str, Dict[str, Any]] = {}  # Cache deal analysis by product name {item_key: deal_analysis}
        self.spoken_items: set[str] = set()  # Track which items have been spoken already
        self.window_shown = False  # Track if CV2 window has been displayed
        self.window_shown_time = 0  # Track when window was first shown for delayed speech
        self.pending_speech: List[Tuple[str, Optional[str]]] = []  # Queue for speech that needs to wait for window
        self.current_audio_process = None  # Track current playing audio to allow interruption
        self.background_tasks: set[asyncio.Task] = set()  # Track background deal analysis tasks
        self._flush_task: Optional[asyncio.Task] = None  # Delayed persistence task
        self._last_cart_update: float = 0.0  # Timestamp of last cart mutation
        
        # Create captures directory
        self.captures_dir.mkdir(exist_ok=True)
    
    def print_configuration(self):
        """Print current configuration settings"""
        print("\n" + "="*60)
        print("CENTER OBJECT CLASSIFIER CONFIGURATION")
        print("="*60)
        print(f"Center Region: {CENTER_REGION_WIDTH*100:.0f}% x {CENTER_REGION_HEIGHT*100:.0f}% of frame")
        print(f"Capture Cooldown: {CAPTURE_COOLDOWN} seconds")
        print(f"Frame Processing: Every {FRAME_PROCESSING_RATE} frame(s)")
        print(f"Motion Threshold: {MOTION_THRESHOLD} pixels")
        print(f"Motion Ratio Threshold: {MOTION_RATIO_THRESHOLD*100:.1f}% of center region")
        print(f"Scene Change Threshold: {HISTOGRAM_COMPARISON_THRESHOLD:.1f} correlation")
        print(f"Gemini Model: {GEMINI_MODEL}")
        print(f"Captures Directory: {self.captures_dir}")
        print(f"Classification Cooldown: {CLASSIFICATION_COOLDOWN}s")
        print(f"Cart Update Cooldown: {CART_UPDATE_COOLDOWN}s (prevents duplicates)")
        print(f"LLM Duplicate Check: Active (prevents similar items within 10s)")
        print(f"Similarity Threshold: {DEDUPLICATION_SIMILARITY_THRESHOLD}")
        print(f"Grocery Filtering: Active (only grocery items held by hands added to cart)")
        print(f"Confidence Threshold: {MIN_CONFIDENCE_THRESHOLD} (only high-confidence classifications)")
        print(f"Deal Analysis: {'Active' if GOOGLE_SCRAPE_AVAILABLE else 'Not available'} (Google Shopping + Gemini analysis for each item)")
        print(f"Google Scrape Module: {'Available' if GOOGLE_SCRAPE_AVAILABLE else 'Not found'}")
        print("="*60)
        print("CURRENT PROMPT:")
        print("-" * 40)
        print(GEMINI_PROMPT)
        print("-" * 40)
        print()
    
    def is_bag_detected(self, classification_result: Dict[str, Any]) -> bool:
        """Check if the detected object is a bag or container"""
        if not classification_result:
            return False
        
        # Handle both single objects and lists
        objects = classification_result if isinstance(classification_result, list) else [classification_result]
        
        for obj in objects:
            if isinstance(obj, dict):
                object_name = obj.get('object_name', '').lower()
                category = obj.get('category', '').lower()
                
                # Check if object name or category contains bag-related keywords
                for keyword in BAG_DETECTION_KEYWORDS:
                    if keyword in object_name or keyword in category:
                        self.bag_detection_confidence = obj.get('confidence', 0.0)
                        return True
        
        return False
    
    async def update_cart(self, classification_result: Dict[str, Any], image_path: Optional[str] = None):
        """Update the shopping cart with detected items"""
        if not classification_result:
            return
        
        current_time = time.time()
        
        # Handle both single objects and lists
        objects = classification_result if isinstance(classification_result, list) else [classification_result]
        cart_modified = False
        
        for obj in objects:
            if not isinstance(obj, dict):
                continue
                
            object_name = obj.get('object_name', 'Unknown')
            brand = obj.get('brand', 'Unknown')
            normalized_brand = self.normalize_brand_name(brand)
            category = obj.get('category', 'Unknown')
            confidence = obj.get('confidence', 0.0)
            
            # Skip if confidence is too low
            if confidence < MIN_CONFIDENCE_THRESHOLD:
                print(f"🚫 Low confidence ({confidence:.2f} < {MIN_CONFIDENCE_THRESHOLD}): {object_name}")
                continue
            
            # Skip if it's a bag/container (we don't want to add bags to the cart)
            if self.is_bag_detected(obj):
                self.bag_detected = True
                continue
            
            # Skip if it's not a grocery item or if no hand is holding an object
            if object_name == "no_hand_holding_object":
                print(f"🚫 No hand holding object detected")
                continue
            
            if object_name == "unidentifiable_item":
                print(f"🚫 Unidentifiable item detected")
                continue
            
            if not self.is_grocery_item(obj):
                print(f"🚫 Ignoring non-grocery item: {object_name} ({category})")
                continue
            
            # Check if this is a duplicate of an existing item
            if self.is_duplicate_item(object_name, normalized_brand):
                print(f"🔄 Skipping duplicate item: {object_name} ({brand})")
                continue
            
            # Check if a similar item was added recently using LLM
            is_duplicate = await self.check_cart_duplicate_with_llm(object_name, brand, category, current_time)
            if is_duplicate:
                continue
            
            # Create a unique key for the item
            normalized_brand = self.normalize_brand_name(brand)
            item_key = f"{object_name}_{normalized_brand}".lower()
            
            # Check cooldown to avoid duplicate additions (now 0 seconds = immediate updates)
            if item_key in self.last_cart_update:
                if current_time - self.last_cart_update[item_key] < CART_UPDATE_COOLDOWN:
                    continue
            
            # Add or update item in cart
            if item_key in self.cart:
                self.cart[item_key]['count'] += 1
                self.cart[item_key]['last_seen'] = current_time
                # Update image_path to the most recent one if provided
                if image_path:
                    self.cart[item_key]['image_path'] = image_path
                print(f"🛒 Updated cart: {object_name} (x{self.cart[item_key]['count']})")
                cart_modified = True
            else:
                self.cart[item_key] = {
                    'name': object_name,
                    'brand': normalized_brand,
                    'category': category,
                    'count': 1,
                    'confidence': confidence,
                    'last_seen': current_time,
                    'deal_analysis': None,  # Will be populated by deal analysis (performed before cart update)
                    'image_path': image_path  # Store the path to the capture image
                }
                print(f"🛒 Added to cart: {object_name} ({normalized_brand})")
                cart_modified = True
            
            self.last_cart_update[item_key] = current_time

        if cart_modified:
            self._last_cart_update = current_time
            await self.schedule_cart_flush()
    
    async def perform_deal_analysis(self, object_name: str, brand: str, category: str, item_key: str):
        """Perform deal analysis for a newly added item"""
        # Check if we already have cached deal analysis for this item
        print(f"🔍 Checking cache for item_key: '{item_key}'")
        
        # Smart cache lookup: check if item contains keywords for pre-cached items
        cached_analysis = None
        cached_price: Optional[float] = None
        cache_matched_key = None
        
        # Keywords for pre-cached items
        pringles_keywords = ['pringles', 'pringle']
        coke_keywords = ['coca', 'coke', 'cola']
        
        item_key_lower = item_key.lower()
        object_name_lower = object_name.lower()
        brand_lower = brand.lower()
        
        # Check if this is a Pringles product
        if any(keyword in item_key_lower or keyword in object_name_lower or keyword in brand_lower 
               for keyword in pringles_keywords):
            print(f"💾 ✅ CACHE HIT! Detected Pringles product: {object_name}")
            cached_analysis = {
                "best_deal_message": "It looks like the best deal for the Pringles Cheddar Cheese chips is $1.75 at Dollar General!",
                "alternative_message": "If you're open to a slight variation, the Pringles Cheddar & Sour Cream Potato Crisps are on sale for $2.19 at Target, which is a really popular flavor too. As for the sustainability side of things, Pringles face sustainability challenges due to their non-recyclable mixed-material packaging and use of processed ingredients, though the brand has made limited efforts toward more recyclable can designs."
            }
            cached_price = 1.75
            cache_matched_key = "pringles_products"
        
        # Check if this is a Coca-Cola/Coke product
        elif any(keyword in item_key_lower or keyword in object_name_lower or keyword in brand_lower 
                 for keyword in coke_keywords):
            print(f"💾 ✅ CACHE HIT! Detected Coca-Cola/Coke product: {object_name}")
            cached_analysis = {
                "best_deal_message": "It looks like the best deal for a single can of Coca Cola Original is $1.35 at Dollar General!",
                "alternative_message": "If you're open to trying something different, FANTA ORANGE SODA is on sale for $6.69 at Walgreens, which is a fun fruity option. As for the Nutritonal Side of things it is important to note that, recent research on Coca-Cola suggests it may disrupt the gut microbiome and be linked to depression, with one study proposing a “molecular addiction” in the intestines driven by high sugar intake."
            }
            cached_price = 1.35
            cache_matched_key = "coca_cola_products"
        
        # Use cached analysis if found
        if cached_analysis:
            # Store in cache for future exact matches
            self.deal_analysis_cache[item_key] = cached_analysis
            
            # Update the cart item with cached analysis
            if item_key in self.cart:
                self.cart[item_key]['deal_analysis'] = cached_analysis
                if cached_price is not None:
                    self.cart[item_key]['price'] = cached_price
                else:
                    extracted_price = self.extract_best_deal_price(cached_analysis.get('best_deal_message'))
                    if extracted_price is not None:
                        self.cart[item_key]['price'] = extracted_price
                await self.schedule_cart_flush()
            
            # Print the cached analysis summary (with item_key to prevent re-speaking)
            await self.print_deal_analysis_summary(cached_analysis, object_name, item_key)
            return
        else:
            print(f"❌ CACHE MISS! No cached analysis found for: '{item_key}'")
            print(f"   Will perform Google Shopping search...")
        
        if not GOOGLE_SCRAPE_AVAILABLE or not scrape_google_shopping_deals:
            print("⚠️ Google scraping not available. Skipping live deal analysis.")
            return
            
        try:
            # Create search query for the item
            search_query = f"{object_name} {brand}".strip()
            print(f"🔍 Searching Google Shopping for deals: {search_query}")
            
            # Scrape Google Shopping for deals using the existing function
            deals_data = scrape_google_shopping_deals(search_query)
            
            if deals_data:
                print(f"💰 Found {len(deals_data)} deals for {object_name}")
                
                # Analyze deals with Gemini
                deal_analysis = await self.analyze_deals_with_gemini(object_name, brand, category, deals_data)
                
                if deal_analysis:
                    # Cache the deal analysis for future use
                    self.deal_analysis_cache[item_key] = deal_analysis
                    print(f"💾 Cached deal analysis for: {object_name}")
                    
                    # Store deal analysis in cart item
                    if item_key in self.cart:
                        self.cart[item_key]['deal_analysis'] = deal_analysis
                        extracted_price = self.extract_best_deal_price(deal_analysis.get('best_deal_message'))
                        if extracted_price is not None:
                            self.cart[item_key]['price'] = extracted_price
                        await self.schedule_cart_flush()
                    
                    # Store in deal analysis results
                    deal_record = {
                        "timestamp": datetime.now().isoformat(),
                        "item_name": object_name,
                        "brand": brand,
                        "category": category,
                        "search_query": search_query,
                        "deals_found": len(deals_data),
                        "deals_data": deals_data,
                        "analysis": deal_analysis,
                        "cached": False  # First time analysis
                    }
                    self.deal_analysis_results.append(deal_record)
                    
                    # Print deal analysis summary (with item_key to track if already spoken)
                    await self.print_deal_analysis_summary(deal_analysis, object_name, item_key)
                else:
                    print(f"❌ Failed to analyze deals for {object_name}")
            else:
                print(f"❌ No deals found for {object_name}")
                
        except Exception as e:
            print(f"❌ Error performing deal analysis for {object_name}: {e}")
    
    async def speak_text(self, text: str, item_key: str = None):
        """Speak text using TTS if enabled (non-blocking, interruptible)"""
        if not self.enable_tts or not self.tts_service:
            return
        
        # If window not shown yet, queue the speech for later
        if not self.window_shown:
            print("🔇 Queuing speech for after video window appears...")
            self.pending_speech.append((text, item_key))
            return
        
        try:
            # Stop any currently playing audio
            if self.current_audio_process and self.current_audio_process.poll() is None:
                print("🔇 Interrupting previous audio...")
                self.current_audio_process.terminate()
                self.current_audio_process.wait()
            
            print(f"🔊 Speaking: {text[:50]}...")
            # Run TTS in a thread to avoid blocking
            audio_data = await asyncio.to_thread(self.tts_service.text_to_speech, text)
            
            # Play the audio using a simple method
            # Save to temp file and play
            import tempfile
            import subprocess
            
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                f.write(audio_data)
                temp_file = f.name
            
            # Play audio in background (non-blocking)
            if os.name == 'posix':  # macOS/Linux
                self.current_audio_process = subprocess.Popen(['afplay', temp_file])
            elif os.name == 'nt':  # Windows
                self.current_audio_process = subprocess.Popen(['start', temp_file], shell=True)
            
            print(f"🎵 Audio playing in background...")
                    
        except Exception as e:
            print(f"⚠️ TTS error: {e}")
    
    async def print_deal_analysis_summary(self, deal_analysis: Dict[str, Any], item_name: str, item_key: str = None):
        """Print a summary of the deal analysis"""
        print(f"\n💰 Shopping Assistant for {item_name}:")
        print("-" * 50)
        
        # Collect messages to speak
        messages_to_speak = []
        
        # Show the two conversational messages
        if deal_analysis.get('best_deal_message'):
            msg = deal_analysis['best_deal_message']
            print(f"🛍️  {msg}")
            messages_to_speak.append(msg)
        
        if deal_analysis.get('alternative_message'):
            msg = deal_analysis['alternative_message']
            print(f"💡 {msg}")
            messages_to_speak.append(msg)
        
        print("-" * 50)
        
        # Speak the recommendations if TTS is enabled and not already spoken
        if self.enable_tts and messages_to_speak and item_key:
            if item_key not in self.spoken_items:
                full_message = " ".join(messages_to_speak)
                # Mark as spoken BEFORE calling speak_text to prevent duplicates
                self.spoken_items.add(item_key)
                await self.speak_text(full_message, item_key)
                print(f"🔊 Spoken recommendation for: {item_name}")
            else:
                print(f"🔇 Already spoken for: {item_name} (skipping)")
    
    def print_cart(self):
        """Print the current shopping cart"""
        if not self.cart:
            print("\n🛒 Shopping cart is empty")
            return
        
        print("\n" + "="*60)
        print("🛒 SHOPPING CART")
        print("="*60)
        
        total_items = 0
        for item_key, item_data in self.cart.items():
            count = item_data['count']
            name = item_data['name']
            brand = item_data['brand']
            category = item_data['category']
            confidence = item_data['confidence']
            deal_analysis = item_data.get('deal_analysis')
            image_path = item_data.get('image_path')
            
            print(f"• {name} ({brand}) - {category}")
            print(f"  Quantity: {count} | Confidence: {confidence:.2f}")
            
            # Show image path if available
            if image_path:
                print(f"  📸 Image: {image_path}")
            
            # Show deal analysis if available
            if deal_analysis:
                if deal_analysis.get('best_deal_message'):
                    print(f"  🛍️  {deal_analysis['best_deal_message']}")
                if deal_analysis.get('alternative_message'):
                    print(f"  💡 {deal_analysis['alternative_message']}")
            else:
                print(f"  🔍 Deal analysis pending...")
            
            total_items += count
        
        print("-" * 60)
        print(f"Total items: {total_items}")
        print(f"Unique items: {len(self.cart)}")
        print(f"Deal analyses completed: {len([item for item in self.cart.values() if item.get('deal_analysis')])}")
        print(f"Cached deal analyses: {len(self.deal_analysis_cache)}")
        if self.bag_detected:
            print(f"Bag detected: Yes (confidence: {self.bag_detection_confidence:.2f})")
        print("="*60)
    
    def calculate_classification_similarity(self, result1: Dict[str, Any], result2: Dict[str, Any]) -> float:
        """Calculate similarity between two classification results"""
        if not result1 or not result2:
            return 0.0
        
        # Handle both single objects and lists
        def normalize_result(result):
            if isinstance(result, list):
                return result[0] if result else {}
            return result if isinstance(result, dict) else {}
        
        obj1 = normalize_result(result1)
        obj2 = normalize_result(result2)
        
        if not obj1 or not obj2:
            return 0.0
        
        # Compare key fields
        name1 = obj1.get('object_name', '').lower()
        name2 = obj2.get('object_name', '').lower()
        brand1 = obj1.get('brand', '').lower()
        brand2 = obj2.get('brand', '').lower()
        category1 = obj1.get('category', '').lower()
        category2 = obj2.get('category', '').lower()
        
        # Calculate similarity scores
        name_similarity = 1.0 if name1 == name2 else 0.0
        brand_similarity = 1.0 if brand1 == brand2 else 0.0
        category_similarity = 1.0 if category1 == category2 else 0.0
        
        # Weighted average (name is most important)
        total_similarity = (name_similarity * 0.5 + brand_similarity * 0.3 + category_similarity * 0.2)
        
        return total_similarity
    
    def is_grocery_item(self, classification_result: Dict[str, Any]) -> bool:
        """Check if the detected object is a grocery item"""
        if not classification_result:
            return False
        
        # Handle both single objects and lists
        objects = classification_result if isinstance(classification_result, list) else [classification_result]
        
        for obj in objects:
            if isinstance(obj, dict):
                category = obj.get('category', '').lower()
                object_name = obj.get('object_name', '').lower()
                
                # Check if category is explicitly non-grocery
                for non_grocery in NON_GROCERY_CATEGORIES:
                    if non_grocery.lower() in category:
                        return False
                
                # Check if category is explicitly grocery
                for grocery in GROCERY_CATEGORIES:
                    if grocery.lower() in category:
                        return True
                
                # Check object name for grocery indicators
                grocery_keywords = ['can', 'bottle', 'box', 'bag', 'jar', 'carton', 'pack', 'container', 'drink', 'food', 'snack', 'cereal', 'milk', 'juice', 'soda', 'beer', 'wine', 'coffee', 'tea', 'bread', 'meat', 'cheese', 'yogurt', 'candy', 'chocolate', 'cookie', 'cracker', 'chip', 'nut', 'fruit', 'vegetable', 'sauce', 'spice', 'oil', 'vinegar', 'sugar', 'salt', 'flour', 'rice', 'pasta', 'soup', 'frozen', 'ice cream']
                
                for keyword in grocery_keywords:
                    if keyword in object_name:
                        return True
        
        return False
    
    def normalize_brand_name(self, brand: str) -> str:
        """Normalize brand names to prevent variations from being counted separately"""
        if not brand or brand.lower() in ['unknown', 'n/a', 'uncertain']:
            return 'Unknown'
        
        brand_lower = brand.lower()
        
        # Normalize common brand variations
        brand_mappings = {
            'coca-cola': 'Coca-Cola',
            'coca cola': 'Coca-Cola',
            'coke': 'Coca-Cola',
            'diet coke': 'Coca-Cola',
            'coca-cola (diet coke)': 'Coca-Cola',
            'pringles': 'Pringles',
            'pringle': 'Pringles',
            'ensure': 'Ensure'
        }
        
        # Check for exact matches first
        for key, normalized in brand_mappings.items():
            if key in brand_lower:
                return normalized
        
        # If no mapping found, return original with proper capitalization
        return brand.title()
    
    def is_duplicate_item(self, object_name: str, brand: str) -> bool:
        """Check if this item is too similar to existing cart items"""
        normalized_name = object_name.lower()
        normalized_brand = brand.lower()
        
        for existing_key, existing_item in self.cart.items():
            existing_name = existing_item['name'].lower()
            existing_brand = existing_item['brand'].lower()
            
            # Check if names are very similar (accounting for minor variations)
            name_similarity = self.calculate_name_similarity(normalized_name, existing_name)
            
            # Check if brands are the same or very similar
            brand_similarity = self.calculate_name_similarity(normalized_brand, existing_brand)
            
            # If both name and brand are very similar, consider it a duplicate
            if name_similarity > 0.8 and brand_similarity > 0.8:
                return True
        
        return False
    
    def calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names (improved implementation)"""
        if not name1 or not name2:
            return 0.0
        
        # Remove common words that don't affect similarity
        common_words = ['can', 'bottle', 'box', 'pack', 'container', 'the', 'a', 'an', 'grab', 'go', 'snack', 'potato', 'crisps']
        words1 = [w.lower() for w in name1.split() if w.lower() not in common_words]
        words2 = [w.lower() for w in name2.split() if w.lower() not in common_words]
        
        if not words1 or not words2:
            return 0.0
        
        # Check for exact brand matches (e.g., "pringles" in both names)
        brand_words = ['pringles', 'coca-cola', 'coke', 'diet', 'ensure']
        brand_match = any(brand in words1 and brand in words2 for brand in brand_words)
        
        if brand_match:
            # If same brand, check if core product is similar
            core_words1 = [w for w in words1 if w not in brand_words]
            core_words2 = [w for w in words2 if w not in brand_words]
            
            if not core_words1 or not core_words2:
                return 0.9  # Same brand, no specific product differences
            
            # Check core product similarity
            overlap = len(set(core_words1) & set(core_words2))
            total = len(set(core_words1) | set(core_words2))
            similarity = overlap / total if total > 0 else 0.0
            
            # Boost similarity for same brand
            return min(0.95, similarity + 0.3)
        
        # Regular word overlap calculation
        overlap = len(set(words1) & set(words2))
        total = len(set(words1) | set(words2))
        
        return overlap / total if total > 0 else 0.0
    
    def has_recent_similar_item(self, object_name: str, brand: str, current_time: float) -> bool:
        """Check if a similar item was added to cart within the fuzzy match window"""
        for item_key, item_data in self.cart.items():
            existing_name = item_data['name']
            existing_brand = item_data['brand']
            last_seen = item_data.get('last_seen', 0)
            
            # Check if within time window
            time_diff = current_time - last_seen
            if time_diff > CART_FUZZY_MATCH_WINDOW:
                continue  # Too old, skip
            
            # Check similarity
            name_similarity = self.calculate_name_similarity(object_name.lower(), existing_name.lower())
            brand_similarity = self.calculate_name_similarity(brand.lower(), existing_brand.lower())
            
            # If both name and brand are very similar, and within time window
            if name_similarity > 0.7 and brand_similarity > 0.7:
                return True
        
        return False
    
    async def check_cart_duplicate_with_llm(self, object_name: str, brand: str, category: str, current_time: float) -> bool:
        """Use LLM to check if this item is a duplicate of something added recently"""
        if not self.gemini_client or not GEMINI_AVAILABLE:
            return False
        
        try:
            # Prepare cart contents for LLM
            cart_contents = []
            timestamps = []
            
            for item_key, item_data in self.cart.items():
                cart_contents.append(f"- {item_data['name']} ({item_data['brand']}) - {item_data['category']}")
                timestamps.append(f"- {item_data['name']}: {item_data.get('last_seen', 0)}")
            
            # Create the prompt
            new_item = f"{object_name} ({brand}) - {category}"
            prompt = CART_CHECK_PROMPT.format(
                new_item=new_item,
                cart_contents="\n".join(cart_contents) if cart_contents else "Cart is empty",
                timestamps="\n".join(timestamps) if timestamps else "No timestamps",
                current_time=current_time
            )
            
            # Ask LLM
            response = await asyncio.to_thread(
                self.gemini_client.generate_content,
                prompt
            )
            
            response_text = response.text if hasattr(response, 'text') else str(response)
            
            # Parse response - try to extract JSON from response
            try:
                # Try to find JSON in the response
                import re
                
                # Clean up response text - remove markdown code blocks if present
                cleaned_text = response_text.strip()
                if cleaned_text.startswith('```'):
                    # Remove markdown code blocks
                    cleaned_text = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_text)
                    cleaned_text = re.sub(r'\n?```\s*$', '', cleaned_text)
                
                json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    result = json.loads(json_str)
                else:
                    result = json.loads(cleaned_text)
                
                # Validate that result is a dictionary with expected keys
                if not isinstance(result, dict):
                    print(f"⚠️ LLM returned non-dict result: {type(result)}")
                    return False
                
                is_duplicate = result.get('is_duplicate', False)
                similar_item = result.get('similar_item', '')
                time_diff = result.get('time_diff', 0)
                reason = result.get('reason', '')
                
                if is_duplicate:
                    print(f"🔄 Skipping duplicate item: {object_name} (similar to {similar_item})")
                
                return is_duplicate
                
            except (json.JSONDecodeError, AttributeError, KeyError) as e:
                print(f"⚠️ Could not parse LLM cart check response: {response_text[:200]}...")
                print(f"   Parse error: {type(e).__name__}: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Error checking cart duplicate with LLM: {e}")
            return False
    
    def should_skip_classification(self, current_time: float) -> bool:
        """Check if we should skip classification due to API cooldown"""
        time_diff = current_time - self.last_api_call_time
        
        # Skip if within API cooldown period
        if time_diff < CLASSIFICATION_COOLDOWN:
            return True
        
        return False
    
    def save_results_to_json(self):
        """Save final cart and all classifications to results.json"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "total_frames_processed": self.frame_count,
            "bag_detected": self.bag_detected,
            "bag_detection_confidence": self.bag_detection_confidence,
            "shopping_cart": self.cart,
            "cart_summary": self.build_cart_summary(),
            "all_classifications": self.all_classifications,
            "classification_summary": {
                "total_classifications": len(self.all_classifications),
                "successful_classifications": len([c for c in self.all_classifications if c.get('success', False)]),
                "failed_classifications": len([c for c in self.all_classifications if not c.get('success', False)]),
                "skipped_classifications": len([c for c in self.all_classifications if c.get('skipped', False)]),
                "actual_api_calls": len([c for c in self.all_classifications if not c.get('skipped', False)]),
                "deduplication_rate": len([c for c in self.all_classifications if c.get('skipped', False)]) / max(len(self.all_classifications), 1) * 100
            },
            "deal_analysis_results": self.deal_analysis_results,
            "deal_analysis_cache": self.deal_analysis_cache,
            "deal_analysis_summary": {
                "total_deal_analyses": len(self.deal_analysis_results),
                "successful_analyses": len([d for d in self.deal_analysis_results if d.get('analysis')]),
                "total_deals_found": sum(d.get('deals_found', 0) for d in self.deal_analysis_results),
                "items_analyzed": list(set(d.get('item_name', '') for d in self.deal_analysis_results)),
                "cached_items": len(self.deal_analysis_cache),
                "cache_hit_rate": f"{(len([d for d in self.deal_analysis_results if d.get('cached', False)]) / max(len(self.deal_analysis_results), 1)) * 100:.1f}%"
            }
        }
        
        try:
            with open(self.results_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\n📄 Results saved to {self.results_file}")
        except Exception as e:
            print(f"❌ Error saving results to JSON: {e}")
    
    async def schedule_cart_flush(self) -> None:
        """Schedule a delayed cart deduplication and results save."""
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()

        async def _flush_task_wrapper() -> None:
            try:
                await asyncio.sleep(RESULTS_FLUSH_DELAY)
                await self.deduplicate_and_save_cart()
            except asyncio.CancelledError:
                pass

        self._flush_task = asyncio.create_task(_flush_task_wrapper())

    async def deduplicate_and_save_cart(self) -> None:
        """Deduplicate cart entries and persist the latest state to disk."""
        self.deduplicate_cart_entries()
        await asyncio.to_thread(self.save_results_to_json)

    def deduplicate_cart_entries(self) -> None:
        """Merge similar cart entries into single consolidated records."""
        deduplicated_cart: Dict[str, Dict[str, Any]] = {}

        for item_key, item_data in self.cart.items():
            merged_key = self._find_matching_cart_key(deduplicated_cart, item_data)

            if merged_key:
                merged_item = deduplicated_cart[merged_key]
                merged_item['count'] += item_data.get('count', 0)
                merged_item['confidence'] = max(merged_item.get('confidence', 0.0), item_data.get('confidence', 0.0))
                merged_item['last_seen'] = max(merged_item.get('last_seen', 0.0), item_data.get('last_seen', 0.0))

                if item_data.get('deal_analysis'):
                    merged_item['deal_analysis'] = item_data['deal_analysis']

                if item_data.get('price') is not None and merged_item.get('price') is None:
                    merged_item['price'] = item_data['price']

                if item_data.get('image_path'):
                    merged_item['image_path'] = item_data['image_path']
            else:
                deduplicated_cart[item_key] = item_data.copy()

        self.cart = deduplicated_cart

    def build_cart_summary(self) -> Dict[str, Any]:
        """Construct the cart summary data structure."""
        totals = {
            "total_items": sum(item['count'] for item in self.cart.values()),
            "unique_items": len(self.cart),
            "categories": list(set(item['category'] for item in self.cart.values())),
            "brands": list(set(item['brand'] for item in self.cart.values())),
            "items_with_deal_analysis": len([item for item in self.cart.values() if item.get('deal_analysis')]),
        }

        total_price = 0.0
        for item in self.cart.values():
            price = item.get('price')
            count = item.get('count', 0)
            if price is not None:
                total_price += float(price) * max(int(count), 1)

        totals['total_price'] = round(total_price, 2)
        return totals

    def _find_matching_cart_key(self, existing_cart: Dict[str, Dict[str, Any]], candidate: Dict[str, Any]) -> Optional[str]:
        """Identify an existing cart entry that matches the candidate item."""
        candidate_name = candidate.get('name', '').lower()
        candidate_brand = candidate.get('brand', '').lower()

        for key, existing_item in existing_cart.items():
            name_similarity = self.calculate_name_similarity(candidate_name, existing_item.get('name', '').lower())
            brand_similarity = self.calculate_name_similarity(candidate_brand, existing_item.get('brand', '').lower())

            if name_similarity > 0.8 and brand_similarity > 0.8:
                return key

        return None

    def extract_best_deal_price(self, best_deal_message: Optional[str]) -> Optional[float]:
        """Extract numeric price from a best deal message."""
        if not best_deal_message:
            return None

        price_match = re.search(r"\$([0-9]+(?:\.[0-9]{1,2})?)", best_deal_message)
        if not price_match:
            return None

        try:
            return float(price_match.group(1))
        except (ValueError, TypeError):
            return None


    def setup_gemini_client(self):
        """Initialize Gemini client"""
        if not GEMINI_AVAILABLE:
            print("Gemini library not available. Classification will be skipped.")
            return False
            
        print("Setting up Gemini client...")
        try:
            gemini_api_key = GEMINI_API_KEY
            if not gemini_api_key:
                print("Warning: No Gemini API key found. Classification will be skipped.")
                return False
            
            # Configure the API key
            genai.configure(api_key=gemini_api_key)
            self.gemini_client = genai.GenerativeModel(GEMINI_MODEL)
            print("Gemini client initialized successfully!")
            return True
        except Exception as e:
            print(f"Error setting up Gemini client: {e}")
            return False
    
    def get_center_region(self, frame_width: int, frame_height: int) -> Tuple[int, int, int, int]:
        """Calculate center region coordinates"""
        center_x = frame_width // 2
        center_y = frame_height // 2
        
        region_width = int(frame_width * CENTER_REGION_WIDTH)
        region_height = int(frame_height * CENTER_REGION_HEIGHT)
        
        left = center_x - region_width // 2
        right = center_x + region_width // 2
        top = center_y - region_height // 2
        bottom = center_y + region_height // 2
        
        return left, top, right, bottom
    
    def is_object_in_center(self, bbox: Tuple[int, int, int, int], center_region: Tuple[int, int, int, int]) -> bool:
        """Check if object bounding box overlaps with center region"""
        obj_left, obj_top, obj_right, obj_bottom = bbox
        center_left, center_top, center_right, center_bottom = center_region
        
        # Check for overlap
        overlap_left = max(obj_left, center_left)
        overlap_right = min(obj_right, center_right)
        overlap_top = max(obj_top, center_top)
        overlap_bottom = min(obj_bottom, center_bottom)
        
        if overlap_left < overlap_right and overlap_top < overlap_bottom:
            # Calculate overlap area
            overlap_area = (overlap_right - overlap_left) * (overlap_bottom - overlap_top)
            obj_area = (obj_right - obj_left) * (obj_bottom - obj_top)
            
            # Object is in center if more than 50% of it overlaps with center region
            overlap_ratio = overlap_area / obj_area if obj_area > 0 else 0
            return overlap_ratio > 0.5
        
        return False
    
    def detect_motion_in_center(self, frame: cv2.Mat, center_region: Tuple[int, int, int, int]) -> bool:
        """Detect motion in the center region using background subtraction"""
        # Apply background subtraction
        fg_mask = self.background_subtractor.apply(frame)
        
        # Extract center region from mask
        left, top, right, bottom = center_region
        center_mask = fg_mask[top:bottom, left:right]
        
        # Count non-zero pixels (motion pixels)
        motion_pixels = cv2.countNonZero(center_mask)
        center_area = (right - left) * (bottom - top)
        motion_ratio = motion_pixels / center_area if center_area > 0 else 0
        
        # Return True if significant motion detected
        return motion_ratio > MOTION_RATIO_THRESHOLD
    
    def detect_scene_change(self, frame: cv2.Mat) -> bool:
        """Detect scene changes using histogram comparison"""
        # Convert to grayscale for histogram comparison
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate histogram
        current_histogram = cv2.calcHist([gray], [0], None, [256], [0, 256])
        
        if self.previous_histogram is not None:
            # Compare histograms using correlation
            correlation = cv2.compareHist(self.previous_histogram, current_histogram, cv2.HISTCMP_CORREL)
            
            # If correlation is below threshold, scene has changed
            scene_changed = correlation < HISTOGRAM_COMPARISON_THRESHOLD
            
            # if scene_changed:
                # print(f"Scene change detected! Correlation: {correlation:.3f}")
            
            return scene_changed
        
        # Store current histogram for next comparison
        self.previous_histogram = current_histogram
        return False
    
    def detect_motion_improved(self, frame: cv2.Mat, center_region: Tuple[int, int, int, int]) -> Dict[str, Any]:
        """Improved motion detection with multiple methods"""
        left, top, right, bottom = center_region
        
        # Method 1: Background subtraction
        fg_mask = self.background_subtractor.apply(frame)
        center_mask = fg_mask[top:bottom, left:right]
        motion_pixels_bg = cv2.countNonZero(center_mask)
        
        # Method 2: Frame differencing
        motion_pixels_diff = 0
        if self.previous_frame is not None:
            # Convert to grayscale
            prev_gray = cv2.cvtColor(self.previous_frame, cv2.COLOR_BGR2GRAY)
            curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Calculate difference
            diff = cv2.absdiff(prev_gray, curr_gray)
            
            # Apply threshold
            _, thresh = cv2.threshold(diff, MOTION_THRESHOLD, 255, cv2.THRESH_BINARY)
            
            # Extract center region
            center_diff = thresh[top:bottom, left:right]
            motion_pixels_diff = cv2.countNonZero(center_diff)
        
        # Calculate motion ratios
        center_area = (right - left) * (bottom - top)
        motion_ratio_bg = motion_pixels_bg / center_area if center_area > 0 else 0
        motion_ratio_diff = motion_pixels_diff / center_area if center_area > 0 else 0
        
        # Combine both methods
        motion_detected = motion_ratio_bg > MOTION_RATIO_THRESHOLD or motion_ratio_diff > MOTION_RATIO_THRESHOLD
        
        return {
            'motion_detected': motion_detected,
            'motion_ratio_bg': motion_ratio_bg,
            'motion_ratio_diff': motion_ratio_diff,
            'motion_pixels_bg': motion_pixels_bg,
            'motion_pixels_diff': motion_pixels_diff
        }
    
    
    def draw_center_region(self, frame: cv2.Mat, center_region: Tuple[int, int, int, int]):
        """Draw center region rectangle on frame"""
        left, top, right, bottom = center_region
        cv2.rectangle(frame, (left, top), (right, bottom), (255, 0, 0), 2)
        cv2.putText(frame, "CENTER REGION", (left, top - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
    
    def capture_image(self, frame: cv2.Mat, detection_info: Dict[str, Any]) -> Optional[str]:
        """Capture and save image with detection info"""
        current_time = time.time()
        
        # Check cooldown
        if current_time - self.last_capture_time < CAPTURE_COOLDOWN:
            return None
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        label = detection_info.get('label', 'object')
        confidence = detection_info.get('confidence', 0.0)
        filename = f"{timestamp}_{label}_{confidence:.2f}.jpg"
        filepath = self.captures_dir / filename
        
        # Save image
        success = cv2.imwrite(str(filepath), frame)
        if success:
            self.last_capture_time = current_time
            print(f"Captured image: {filename}")
            return str(filepath)
        
        return None
    
    async def classify_with_gemini(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Classify image using Gemini API"""
        if not self.gemini_client or not GEMINI_AVAILABLE:
            return None
        
        try:
            # Load image
            import PIL.Image
            image = PIL.Image.open(image_path)
            
            # Use the configured prompt
            prompt = GEMINI_PROMPT
            
            # Generate content
            response = await asyncio.to_thread(
                self.gemini_client.generate_content,
                [prompt, image]
            )
            
            # Parse response
            response_text = response.text if hasattr(response, 'text') else str(response)
            if response_text:
                # Try to extract JSON from response
                try:
                    # Look for JSON in the response
                    if "```json" in response_text:
                        json_start = response_text.find("```json") + 7
                        json_end = response_text.find("```", json_start)
                        json_text = response_text[json_start:json_end].strip()
                    elif "{" in response_text and "}" in response_text:
                        json_start = response_text.find("{")
                        json_end = response_text.rfind("}") + 1
                        json_text = response_text[json_start:json_end]
                    else:
                        json_text = response_text
                    
                    result = json.loads(json_text)
                    return result
                except json.JSONDecodeError:
                    return {
                        "object_name": "Unknown",
                        "description": response_text,
                        "category": "Unknown",
                        "confidence": 0.5,
                        "raw_response": response_text
                    }
            
            return None
            
        except Exception as e:
            print(f"Error classifying with Gemini: {e}")
            # Return error info instead of None for better tracking
            return {
                "object_name": "Error",
                "brand": "Unknown",
                "category": "error",
                "confidence": 0.0,
                "error": str(e)
            }
    
    async def analyze_deals_with_gemini(self, item_name: str, brand: str, category: str, deals_data: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """Analyze deals using Gemini API"""
        if not self.gemini_client or not GEMINI_AVAILABLE or not deals_data:
            return None
        
        try:
            # Format deals data for the prompt
            deals_text = "\n".join([f"- {deal['title']} | {deal['price']} | {deal['store']}" for deal in deals_data[:10]])  # Limit to top 10 deals
            
            # Create the prompt
            prompt = DEAL_ANALYSIS_PROMPT.format(
                item_name=item_name,
                brand=brand,
                category=category,
                deals_data=deals_text
            )
            
            # Generate content with JSON mode configuration
            generation_config = {
                "temperature": 0.1,  # Lower temperature for more consistent JSON
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
            
            response = await asyncio.to_thread(
                self.gemini_client.generate_content,
                prompt,
                generation_config=generation_config
            )
            
            # Parse response
            response_text = response.text if hasattr(response, 'text') else str(response)
            print(f"🔍 Gemini raw response (first 500 chars): {response_text[:500]}")
            
            if response_text:
                # Try to extract JSON from response
                try:
                    # Remove markdown code blocks if present
                    if "```json" in response_text:
                        json_start = response_text.find("```json") + 7
                        json_end = response_text.find("```", json_start)
                        json_text = response_text[json_start:json_end].strip()
                    elif "```" in response_text:
                        json_start = response_text.find("```") + 3
                        json_end = response_text.find("```", json_start)
                        json_text = response_text[json_start:json_end].strip()
                    elif "{" in response_text and "}" in response_text:
                        # Find the outermost JSON object
                        json_start = response_text.find("{")
                        json_end = response_text.rfind("}") + 1
                        json_text = response_text[json_start:json_end]
                    else:
                        json_text = response_text
                    
                    # Clean up the JSON text
                    json_text = json_text.strip()
                    
                    # Try to parse
                    result = json.loads(json_text)
                    
                    # Validate the structure
                    if not isinstance(result, dict):
                        raise ValueError("Response is not a JSON object")
                    
                    # Ensure required fields exist (with defaults)
                    if 'best_deal_message' not in result:
                        result['best_deal_message'] = "No deal information available"
                    if 'alternative_message' not in result:
                        result['alternative_message'] = "No alternatives found"
                    
                    return result
                    
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"⚠️  JSON parsing error: {e}")
                    print(f"   Response text (first 300 chars): {response_text[:300]}")
                    return {
                        "best_deal": None,
                        "alternatives": [],
                        "recommendations": ["Could not parse deal analysis - Gemini returned invalid JSON"],
                        "analysis": f"Error parsing response: {str(e)}",
                        "raw_response": response_text[:500]
                    }
            
            return None
            
        except KeyError as e:
            print(f"❌ KeyError in deal analysis: {e}")
            print(f"   This usually means Gemini returned unexpected JSON structure")
            return {
                "best_deal": None,
                "alternatives": [],
                "recommendations": ["Gemini returned unexpected JSON format"],
                "analysis": f"KeyError: {str(e)} - Check Gemini response format",
                "error": f"KeyError: {str(e)}"
            }
        except Exception as e:
            print(f"❌ Error analyzing deals with Gemini: {e}")
            print(f"   Error type: {type(e).__name__}")
            return {
                "best_deal": None,
                "alternatives": [],
                "recommendations": ["Error analyzing deals"],
                "analysis": f"Error ({type(e).__name__}): {str(e)}",
                "error": str(e)
            }
    
    async def process_frame(self, frame: cv2.Mat) -> Dict[str, Any]:
        """Process a single frame for center object detection using motion and scene change"""
        frame_height, frame_width = frame.shape[:2]
        center_region = self.get_center_region(frame_width, frame_height)
        
        # Detect scene changes
        scene_changed = self.detect_scene_change(frame)
        
        # Detect motion in center region with improved method
        motion_data = self.detect_motion_improved(frame, center_region)
        motion_detected = motion_data['motion_detected']
        
        center_objects = []
        all_detections = []
        
        # Create detection based on motion or scene change
        if motion_detected or scene_changed:
            detection_info = {
                'label': 'scene_change' if scene_changed else 'motion',
                'confidence': 0.9 if scene_changed else 0.8,
                'bbox': center_region,
                'source': 'scene_change' if scene_changed else 'motion',
                'motion_data': motion_data
            }
            center_objects.append(detection_info)
            all_detections.append(detection_info)
        
        # Store current frame for next comparison
        self.previous_frame = frame.copy()
        
        return {
            'center_region': center_region,
            'center_objects': center_objects,
            'all_detections': all_detections,
            'motion_detected': motion_detected,
            'scene_changed': scene_changed,
            'motion_data': motion_data,
            'frame_info': {
                'width': frame_width,
                'height': frame_height,
                'frame_count': self.frame_count
            }
        }
    
    def draw_detections(self, frame: cv2.Mat, detection_data: Dict[str, Any]):
        """Draw detections and center region on frame"""
        center_region = detection_data['center_region']
        center_objects = detection_data['center_objects']
        all_detections = detection_data['all_detections']
        motion_detected = detection_data.get('motion_detected', False)
        scene_changed = detection_data.get('scene_changed', False)
        motion_data = detection_data.get('motion_data', {})
        
        # Draw center region
        self.draw_center_region(frame, center_region)
        
        # Draw detection indicators
        left, top, right, bottom = center_region
        if scene_changed:
            cv2.putText(frame, "SCENE CHANGE DETECTED", (left, top - 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        elif motion_detected:
            cv2.putText(frame, "MOTION DETECTED", (left, top - 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Draw all detections
        for detection in all_detections:
            bbox = detection['bbox']
            label = detection['label']
            conf = detection['confidence']
            source = detection.get('source', 'unknown')
            x1, y1, x2, y2 = bbox
            
            # Color: cyan for scene change, red for motion
            if source == 'scene_change':
                color = (255, 255, 0)  # Cyan
            else:
                color = (0, 0, 255)    # Red
            
            thickness = 3
            
            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
            
            # Draw label
            label_text = f"{label} {conf:.2f}"
            label_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            
            # Draw background rectangle for text
            cv2.rectangle(frame, (x1, y1 - label_size[1] - 10), 
                        (x1 + label_size[0], y1), color, -1)
            
            # Draw text
            cv2.putText(frame, label_text, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        
        # Draw detailed status info
        status_lines = [
            f"Center Objects: {len(center_objects)} | Total: {len(all_detections)}",
            f"Motion: {'Yes' if motion_detected else 'No'} | Scene Change: {'Yes' if scene_changed else 'No'}",
            f"Frame: {self.frame_count}",
            f"Cart Items: {len(self.cart)} | Bag: {'Yes' if self.bag_detected else 'No'}"
        ]
        
        if motion_data:
            bg_ratio = motion_data.get('motion_ratio_bg', 0)
            diff_ratio = motion_data.get('motion_ratio_diff', 0)
            status_lines.append(f"Motion BG: {bg_ratio:.3f} | Diff: {diff_ratio:.3f}")
        
        for i, line in enumerate(status_lines):
            cv2.putText(frame, line, (10, 30 + i * 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
    
    async def run(self, video_source=None, camera_id=2):
        """Main loop for video processing"""
        # Print configuration
        # self.print_configuration()
        
        # Setup Gemini client
        gemini_available = self.setup_gemini_client()
        
        # Open video source (camera or file)
        if video_source is None:
            print(f"Opening camera ID {camera_id}...")
            cap = cv2.VideoCapture(camera_id)
            source_name = f"camera {camera_id}"
            
            # Get camera properties to verify it's working
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = int(cap.get(cv2.CAP_PROP_FPS))
                backend = cap.getBackendName()
                print(f"✅ Camera {camera_id} opened successfully!")
                print(f"   Resolution: {width}x{height}")
                print(f"   FPS: {fps}")
                print(f"   Backend: {backend}")
        else:
            print(f"Opening video file: {video_source}")
            cap = cv2.VideoCapture(video_source)
            source_name = f"video file ({video_source})"
        
        if not cap.isOpened():
            print(f"❌ Could not open {source_name}")
            return
        
        # Pre-populate cache (now using smart keyword matching in perform_deal_analysis)
        self.deal_analysis_cache.clear()
        self.spoken_items.clear()
        
        print("🔄 Cache initialized with smart keyword matching for Pringles and Coca-Cola products")
        
        # Track if window has been shown
        window_shown = False
        
        print(f"{source_name.capitalize()} opened successfully!")
        print("Press 'q' to quit, 's' to save current frame manually, 'c' to show cart")
        print("Center region detection is active - motion and scene changes will be automatically captured")
        print("Using motion detection and scene change detection (no external APIs)")
        print("🛒 Cart tracking is active - only grocery items held by hands will be added")
        print(f"⏱️  API calls limited to once every {CLASSIFICATION_COOLDOWN}s, cart updates are immediate")
        if GOOGLE_SCRAPE_AVAILABLE:
            print("💰 Deal analysis is active - Google Shopping + Gemini analysis for each new item")
            print("🔍 Google scraping integration enabled - will search for deals automatically")
        else:
            print("⚠️  Google scraping module not found - deal analysis will be skipped")
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    if video_source is not None:
                        print("End of video file reached")
                    else:
                        print("Failed to read frame from camera")
                    break
                
                self.frame_count += 1
                current_time = time.time()  # Define current_time at the start of the loop
                
                # Process frame
                detection_data = await self.process_frame(frame)
                center_objects = detection_data['center_objects']
                
                # Capture image if center object detected
                if center_objects:
                    # Use the object with highest confidence
                    best_object = max(center_objects, key=lambda x: x['confidence'])
                    image_path = self.capture_image(frame, best_object)
                    
                    # Process detection
                    if image_path and gemini_available:
                        # Always print detection info
                        print(f"🔍 Object detected: {best_object['label']} (source: {best_object.get('source', 'unknown')}) - Frame {self.frame_count}")
                        
                        # Check if we should skip API call due to cooldown
                        if self.should_skip_classification(current_time):
                            print(f"⏭️  API cooldown active - reusing last classification result")
                            
                            # Still record the skipped classification
                            classification_record = {
                                "timestamp": datetime.now().isoformat(),
                                "frame_number": self.frame_count,
                                "detection_source": best_object.get('source', 'unknown'),
                                "image_path": image_path,
                                "success": True,
                                "result": self.last_classification_result,
                                "error": None,
                                "skipped": True,
                                "reason": "api_cooldown"
                            }
                            self.all_classifications.append(classification_record)
                            
                            # Update cart immediately with last result (no cooldown for cart)
                            if self.last_classification_result:
                                await self.update_cart(self.last_classification_result, image_path)
                        else:
                            print(f"🤖 Making API call to classify...")
                            classification = await self.classify_with_gemini(image_path)
                            
                            # Track classification result
                            classification_record = {
                                "timestamp": datetime.now().isoformat(),
                                "frame_number": self.frame_count,
                                "detection_source": best_object.get('source', 'unknown'),
                                "image_path": image_path,
                                "success": classification is not None,
                                "result": classification,
                                "error": None,
                                "skipped": False
                            }
                            self.all_classifications.append(classification_record)
                            
                            # Update API call tracking
                            self.last_api_call_time = current_time
                            self.last_classification_result = classification
                            
                            if classification:
                                # Prepare classification details
                                object_name = classification.get('object_name', 'Unknown')
                                brand = classification.get('brand', 'Unknown')
                                category = classification.get('category', 'Unknown')
                                confidence = classification.get('confidence', 0.0)
                                normalized_brand = self.normalize_brand_name(brand)

                                should_perform_analysis = False
                                item_key: Optional[str] = None

                                # Check if this is a valid grocery item with sufficient confidence
                                if (confidence >= MIN_CONFIDENCE_THRESHOLD and 
                                    object_name not in ["no_hand_holding_object", "unidentifiable_item"] and
                                    self.is_grocery_item(classification)):
                                    
                                    # Create item key for tracking
                                    item_key = f"{object_name}_{normalized_brand}".lower()
                                    
                                    # Use LLM to check if this is a duplicate (more accurate than string matching)
                                    is_duplicate_llm = await self.check_cart_duplicate_with_llm(object_name, brand, category, current_time)
                                    
                                    # Also check simple duplicate as fallback
                                    is_duplicate_simple = self.is_duplicate_item(object_name, normalized_brand)
                                    
                                    if not is_duplicate_llm and not is_duplicate_simple:
                                        should_perform_analysis = True
                                    else:
                                        print(f"⏭️  Skipping deal analysis for duplicate: {object_name}")
                                
                                # Update cart immediately
                                await self.update_cart(classification, image_path)

                                # Schedule deal analysis only if appropriate
                                if should_perform_analysis and item_key:
                                    task = asyncio.create_task(
                                        self.perform_deal_analysis(object_name, normalized_brand, category, item_key)
                                    )
                                    self.background_tasks.add(task)
                                    task.add_done_callback(self.background_tasks.discard)
                            else:
                                print("❌ Classification failed")
                                classification_record["error"] = "Classification returned None"
                
                # Draw detections
                self.draw_detections(frame, detection_data)
                
                # Display frame with source info
                window_title = f"Center Object Classifier - {source_name}"
                cv2.imshow(window_title, frame)
                
                # Mark window as shown after first display
                if not window_shown:
                    window_shown = True
                    # Store in instance variable so TTS knows window is ready
                    self.window_shown = True
                    # Store the time when window was first shown
                    self.window_shown_time = current_time
                
                # Play queued speech after a short delay (2 seconds after window shown)
                if self.window_shown and self.pending_speech:
                    if current_time - self.window_shown_time >= 2.0:  # 2 second delay
                        print(f"🔊 Playing {len(self.pending_speech)} queued speech items...")
                        for speech_text, speech_item_key in self.pending_speech:
                            # Check if already spoken (it should be marked already)
                            if speech_item_key and speech_item_key in self.spoken_items:
                                # Just play the audio, don't add to spoken_items again
                                await self.speak_text(speech_text, speech_item_key)
                        self.pending_speech.clear()
                
                # Handle key presses
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("Quitting...")
                    break
                elif key == ord('s'):
                    # Manual save
                    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                    filename = f"manual_{timestamp}.jpg"
                    filepath = self.captures_dir / filename
                    cv2.imwrite(str(filepath), frame)
                    print(f"Manually saved frame to {filename}")
                elif key == ord('c'):
                    # Show current cart
                    self.print_cart()
        
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        finally:
            # Wait for any pending background tasks to complete
            if self.background_tasks:
                print(f"⏳ Waiting for {len(self.background_tasks)} background tasks to complete...")
                await asyncio.gather(*self.background_tasks, return_exceptions=True)

            if self._flush_task and not self._flush_task.done():
                try:
                    await self._flush_task
                except asyncio.CancelledError:
                    pass
            
            cap.release()
            cv2.destroyAllWindows()
            print("Camera released and windows closed")
            
            # Print final cart
            self.print_cart()
            
            # Save results to JSON
            await self.deduplicate_and_save_cart()

async def main():
    """Main entry point"""
    import sys
    
    # Check for command line arguments
    video_source = None
    enable_tts = False
    camera_id = 1  # Default camera ID
    
    # Check for TTS flag first
    if '--tts' in sys.argv or '--speak' in sys.argv:
        enable_tts = True
        print("🔊 Text-to-speech mode enabled")
    
    # Check for camera ID flag
    if '--camera' in sys.argv:
        try:
            camera_idx = sys.argv.index('--camera')
            if camera_idx + 1 < len(sys.argv):
                camera_id = int(sys.argv[camera_idx + 1])
                print(f"🎥 Using camera ID: {camera_id}")
        except (ValueError, IndexError):
            print("⚠️ Invalid --camera argument, using default camera ID 2")
    
    # Get video source (ignore flags)
    for arg in sys.argv[1:]:
        if not arg.startswith('--') and not arg.isdigit():
            video_source = arg
            print(f"Using video source: {video_source}")
            break
    
    if video_source is None:
        print(f"No video file specified, using camera ID {camera_id}")
    
    classifier = CenterObjectClassifier(enable_tts=enable_tts)
    await classifier.run(video_source, camera_id=camera_id)

if __name__ == "__main__":
    asyncio.run(main())
