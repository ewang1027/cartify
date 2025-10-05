import os
import requests
import base64
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

class ElevenLabsTTS:
    def __init__(self):
        self.api_key = os.getenv('ELEVENLABS_API_KEY')
        self.base_url = "https://api.elevenlabs.io/v1"
        self.voice_id = os.getenv('ELEVENLABS_VOICE_ID', 'pNInz6obpgDQGcFmaJgB')  # Default voice if not specified
        
    def generate_sustainability_comment(self, preference: str) -> str:
        """Generate positive comments based on sustainability preference"""
        comments = {
            'low': [
                "Smart choice focusing on budget! Every dollar saved is a step toward financial freedom.",
                "Great to see you're being mindful of your spending. That's responsible shopping!",
                "Budget-focused shopping shows real wisdom. You're making every penny count!",
                "Excellent financial thinking! Being budget-conscious is always a sustainable choice."
            ],
            'medium': [
                "Perfect balance! You're showing that you can care for both your wallet and the planet.",
                "Love your balanced approach! You're proving that sustainability doesn't have to break the bank.",
                "Smart thinking! Finding that sweet spot between cost and environmental impact is the way to go.",
                "What a thoughtful approach! You're making conscious choices that work for everyone."
            ],
            'high': [
                "Amazing environmental consciousness! You're making a real difference for our planet!",
                "Love your commitment to sustainability! Every eco-friendly choice makes the world better.",
                "You're a true environmental champion! Your choices are helping create a greener future.",
                "Incredible dedication to the planet! You're setting a wonderful example for others to follow."
            ]
        }
        
        import random
        return random.choice(comments.get(preference, comments['medium']))
    
    def text_to_speech(self, text: str) -> bytes:
        """Convert text to speech using ElevenLabs API"""
        if not self.api_key:
            raise ValueError("ElevenLabs API key not found in environment variables")
        
        url = f"{self.base_url}/text-to-speech/{self.voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            return response.content
        else:
            raise Exception(f"ElevenLabs API error: {response.status_code} - {response.text}")
    
    def generate_sustainability_audio(self, preference: str) -> str:
        """Generate audio comment for sustainability preference and return as base64"""
        try:
            comment = self.generate_sustainability_comment(preference)
            audio_data = self.text_to_speech(comment)
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            return {
                "success": True,
                "audio": audio_base64,
                "comment": comment
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "comment": self.generate_sustainability_comment(preference)
            }
    

# Initialize the TTS service
tts_service = ElevenLabsTTS()

def create_tts_endpoints(app):
    """Add TTS endpoints to Flask app"""
    
    @app.route('/api/sustainability-comment', methods=['POST'])
    def get_sustainability_comment():
        try:
            data = request.get_json()
            preference = data.get('preference', 'medium')
            
            if preference not in ['low', 'medium', 'high']:
                return jsonify({"error": "Invalid preference. Must be 'low', 'medium', or 'high'"}), 400
            
            result = tts_service.generate_sustainability_audio(preference)
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/tts', methods=['POST'])
    def text_to_speech_endpoint():
        try:
            data = request.get_json()
            text = data.get('text', '')
            
            if not text:
                return jsonify({"error": "No text provided"}), 400
            
            audio_data = tts_service.text_to_speech(text)
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            return jsonify({
                "success": True,
                "audio": audio_base64
            })
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
