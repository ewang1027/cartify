"""
ElevenLabs Text-to-Speech Service for Meta Ray-Bans Live Streaming

This module provides text-to-speech functionality for real-time price comparisons
and sustainability announcements during live streaming with Meta Ray-Bans.
"""

import os
import requests
import json
import io
import base64
from typing import Optional, Dict, Any
from datetime import datetime


class ElevenLabsTTS:
    """
    ElevenLabs Text-to-Speech service for Meta Ray-Bans integration
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize ElevenLabs TTS service
        
        Args:
            api_key: ElevenLabs API key (optional, uses environment variable)
        """
        self.api_key = api_key or os.getenv('ELEVENLABS_API_KEY')
        self.base_url = "https://api.elevenlabs.io/v1"
        self.voice_id = os.getenv('ELEVENLABS_VOICE_ID', 'pNInz6obpgDQGcFmaJgB')  # Default voice
        
        if not self.api_key:
            raise ValueError("ElevenLabs API key is required. Set ELEVENLABS_API_KEY environment variable.")
    
    def get_voices(self) -> Dict[str, Any]:
        """
        Get available voices from ElevenLabs
        
        Returns:
            Dictionary containing available voices
        """
        try:
            response = requests.get(
                f"{self.base_url}/voices",
                headers={"xi-api-key": self.api_key}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error fetching voices: {e}")
            return {}
    
    def text_to_speech(self, text: str, voice_id: Optional[str] = None, 
                      model_id: str = "eleven_monolingual_v1") -> Optional[bytes]:
        """
        Convert text to speech using ElevenLabs API
        
        Args:
            text: Text to convert to speech
            voice_id: Voice ID to use (optional, uses default)
            model_id: Model to use for generation
            
        Returns:
            Audio data as bytes, or None if failed
        """
        try:
            voice_id = voice_id or self.voice_id
            
            payload = {
                "text": text,
                "model_id": model_id,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            
            response = requests.post(
                f"{self.base_url}/text-to-speech/{voice_id}",
                headers={
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": self.api_key
                },
                json=payload
            )
            
            response.raise_for_status()
            return response.content
            
        except Exception as e:
            print(f"❌ TTS Error: {e}")
            return None
    
    def save_audio(self, audio_data: bytes, filename: str) -> bool:
        """
        Save audio data to file
        
        Args:
            audio_data: Audio data as bytes
            filename: Filename to save to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filename, 'wb') as f:
                f.write(audio_data)
            return True
        except Exception as e:
            print(f"❌ Error saving audio: {e}")
            return False
    
    def get_audio_base64(self, audio_data: bytes) -> str:
        """
        Convert audio data to base64 for web streaming
        
        Args:
            audio_data: Audio data as bytes
            
        Returns:
            Base64 encoded audio string
        """
        return base64.b64encode(audio_data).decode('utf-8')


class PriceComparisonTTS:
    """
    Specialized TTS service for price comparisons and sustainability announcements
    """
    
    def __init__(self, elevenlabs_api_key: Optional[str] = None):
        """
        Initialize price comparison TTS service
        
        Args:
            elevenlabs_api_key: ElevenLabs API key
        """
        self.tts = ElevenLabsTTS(elevenlabs_api_key)
    
    def generate_price_comparison_announcement(self, product_name: str, 
                                             online_price: str, 
                                             store_price: str,
                                             sustainability_score: float) -> Optional[bytes]:
        """
        Generate TTS announcement for price comparison
        
        Args:
            product_name: Name of the product
            online_price: Online price (e.g., "$4.99")
            store_price: In-store price (e.g., "$5.49")
            sustainability_score: Sustainability score (0-10)
            
        Returns:
            Audio data as bytes
        """
        # Calculate price difference
        try:
            online_val = float(online_price.replace('$', '').replace(',', ''))
            store_val = float(store_price.replace('$', '').replace(',', ''))
            difference = store_val - online_val
            percent_diff = (difference / online_val) * 100
            
            if difference > 0:
                price_message = f"Online price is {percent_diff:.1f} percent cheaper"
            elif difference < 0:
                price_message = f"Store price is {abs(percent_diff):.1f} percent cheaper"
            else:
                price_message = "Prices are the same"
        except:
            price_message = "Price comparison available"
        
        # Generate sustainability message
        if sustainability_score >= 8:
            sustainability_message = "This product has excellent sustainability credentials"
        elif sustainability_score >= 6:
            sustainability_message = "This product has good sustainability ratings"
        elif sustainability_score >= 4:
            sustainability_message = "This product has moderate sustainability impact"
        else:
            sustainability_message = "This product has poor sustainability ratings"
        
        # Create announcement text
        announcement = f"""
        {product_name} detected. 
        Online price: {online_price}. 
        Store price: {store_price}. 
        {price_message}. 
        Sustainability score: {sustainability_score:.1f} out of 10. 
        {sustainability_message}.
        """
        
        return self.tts.text_to_speech(announcement.strip())
    
    def generate_sustainability_announcement(self, product_name: str, 
                                           sustainability_data: Dict[str, Any]) -> Optional[bytes]:
        """
        Generate TTS announcement for sustainability analysis
        
        Args:
            product_name: Name of the product
            sustainability_data: Dictionary containing sustainability analysis
            
        Returns:
            Audio data as bytes
        """
        score = sustainability_data.get('sustainability_score', 0)
        nutrition_score = sustainability_data.get('breakdown', {}).get('nutrition_score', 0)
        carbon_score = sustainability_data.get('breakdown', {}).get('carbon_footprint_score', 0)
        ethics_score = sustainability_data.get('breakdown', {}).get('social_ethics_score', 0)
        
        # Create detailed announcement
        announcement = f"""
        Sustainability analysis for {product_name}:
        Overall score: {score:.1f} out of 10.
        Nutrition score: {nutrition_score:.1f} out of 10.
        Carbon footprint score: {carbon_score:.1f} out of 10.
        Social ethics score: {ethics_score:.1f} out of 10.
        """
        
        return self.tts.text_to_speech(announcement.strip())
    
    def generate_quick_price_alert(self, product_name: str, 
                                  price_difference: float, 
                                  is_cheaper_online: bool) -> Optional[bytes]:
        """
        Generate quick price alert for live streaming
        
        Args:
            product_name: Name of the product
            price_difference: Price difference amount
            is_cheaper_online: Whether online is cheaper
            
        Returns:
            Audio data as bytes
        """
        if is_cheaper_online:
            message = f"{product_name} is {price_difference:.2f} dollars cheaper online"
        else:
            message = f"{product_name} is {price_difference:.2f} dollars cheaper in store"
        
        return self.tts.text_to_speech(message)
    
    def generate_sustainability_quick_alert(self, product_name: str, 
                                           score: float) -> Optional[bytes]:
        """
        Generate quick sustainability alert
        
        Args:
            product_name: Name of the product
            score: Sustainability score
            
        Returns:
            Audio data as bytes
        """
        if score >= 7:
            message = f"{product_name} has excellent sustainability rating"
        elif score >= 5:
            message = f"{product_name} has moderate sustainability rating"
        else:
            message = f"{product_name} has poor sustainability rating"
        
        return self.tts.text_to_speech(message)


def test_tts_service():
    """
    Test the TTS service functionality
    """
    print("🎤 Testing ElevenLabs TTS Service...")
    
    try:
        # Initialize TTS service
        tts = ElevenLabsTTS()
        
        # Test basic TTS
        test_text = "Hello, this is a test of the ElevenLabs text-to-speech service."
        audio_data = tts.text_to_speech(test_text)
        
        if audio_data:
            print("✅ Basic TTS working")
            
            # Save test audio
            tts.save_audio(audio_data, "test_tts.mp3")
            print("✅ Audio saved to test_tts.mp3")
        else:
            print("❌ TTS failed")
        
        # Test price comparison TTS
        price_tts = PriceComparisonTTS()
        price_audio = price_tts.generate_price_comparison_announcement(
            "Organic Apples",
            "$4.99",
            "$5.49",
            7.5
        )
        
        if price_audio:
            print("✅ Price comparison TTS working")
            price_tts.tts.save_audio(price_audio, "price_comparison.mp3")
            print("✅ Price comparison audio saved")
        else:
            print("❌ Price comparison TTS failed")
            
    except Exception as e:
        print(f"❌ TTS Test Error: {e}")


if __name__ == "__main__":
    test_tts_service()
