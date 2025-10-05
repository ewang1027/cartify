# Meta Ray-Bans Live Streaming Integration Guide

## 🥽 Overview

This guide explains how to use the Meta Ray-Bans integration for live streaming with real-time price comparisons and sustainability announcements using ElevenLabs text-to-speech.

## 🔧 Setup Requirements

### 1. API Keys Required

You need the following API keys in your `.env` file:

```bash
# Existing keys (already configured)
OXYLABS_USERNAME=your_oxylabs_username
OXYLABS_PASSWORD=your_oxylabs_password
GEMINI_API_KEY=your_gemini_api_key_here
NEWS_API_KEY=your_news_api_key_here
USDA_API_KEY=your_usda_api_key_here

# NEW: ElevenLabs API key for text-to-speech
ELEVENLABS_API_KEY=your_actual_elevenlabs_api_key_here
ELEVENLABS_VOICE_ID=pNInz6obpgDQGcFmaJgB
```

### 2. Get ElevenLabs API Key

1. Go to [ElevenLabs.io](https://elevenlabs.io/)
2. Sign up for an account
3. Get your API key from the dashboard
4. Replace `your_actual_elevenlabs_api_key_here` in your `.env` file

## 🚀 How to Use

### 1. Start the API Server

```bash
cd /Users/ethanwang/hackharvard/google-gemini/backend
python3 start_api.py
```

The server will start on `http://localhost:5008` with these new endpoints:

- `POST /ray-ban/start-stream` - Start live streaming session
- `POST /ray-ban/stop-stream` - Stop live streaming session  
- `POST /ray-ban/analyze-product` - Analyze product in real-time
- `POST /ray-ban/quick-alert` - Generate quick TTS alert
- `GET /ray-ban/status` - Get streaming status

### 2. Live Streaming Workflow

#### Step 1: Start Streaming Session
```bash
curl -X POST http://localhost:5008/ray-ban/start-stream \
     -H "Content-Type: application/json" \
     -d '{"store_location": "Whole Foods Market"}'
```

#### Step 2: Analyze Products in Real-Time
```bash
curl -X POST http://localhost:5008/ray-ban/analyze-product \
     -H "Content-Type: application/json" \
     -d '{"product_name": "Organic Apples", "store_price": "$4.99"}'
```

This will:
- ✅ Search for online prices
- ✅ Calculate price differences
- ✅ Analyze sustainability score
- ✅ Generate TTS announcements
- ✅ Save audio files for Meta Ray-Bans

#### Step 3: Generate Quick Alerts
```bash
# Price alert
curl -X POST http://localhost:5008/ray-ban/quick-alert \
     -H "Content-Type: application/json" \
     -d '{"product_name": "Organic Apples", "alert_type": "price"}'

# Sustainability alert  
curl -X POST http://localhost:5008/ray-ban/quick-alert \
     -H "Content-Type: application/json" \
     -d '{"product_name": "Organic Apples", "alert_type": "sustainability"}'
```

#### Step 4: Stop Streaming Session
```bash
curl -X POST http://localhost:5008/ray-ban/stop-stream
```

## 🎤 Text-to-Speech Features

### Price Comparison Announcements
- Compares online vs store prices
- Calculates percentage differences
- Announces which is cheaper
- Includes sustainability score

### Sustainability Announcements
- Overall sustainability score
- Nutrition score breakdown
- Carbon footprint score
- Social ethics score

### Quick Alerts
- Instant price alerts
- Sustainability quick checks
- Perfect for live streaming

## 📱 Meta Ray-Bans Integration

### Audio Files Generated
- `welcome_announcement.mp3` - Session start
- `price_announcement_[timestamp].mp3` - Price comparisons
- `sustainability_announcement_[timestamp].mp3` - Sustainability analysis
- `quick_alert_[type]_[timestamp].mp3` - Quick alerts
- `closing_announcement.mp3` - Session end

### Live Streaming Workflow
1. **Start Session**: Begin live streaming at store location
2. **Scan Products**: Use Meta Ray-Bans to scan product barcodes/names
3. **Real-Time Analysis**: Get instant price and sustainability data
4. **TTS Announcements**: Hear results through Ray-Bans speakers
5. **Quick Alerts**: Generate instant alerts for price differences
6. **End Session**: Stop streaming and get summary

## 🧪 Testing

### Run the Demo
```bash
cd /Users/ethanwang/hackharvard/google-gemini/backend
python3 ray_ban_demo.py
```

### Test Individual Components
```bash
# Test TTS service
python3 tts_service.py

# Test Ray-Bans integration
python3 ray_ban_integration.py
```

## 🔧 Troubleshooting

### Common Issues

1. **401 Unauthorized from ElevenLabs**
   - Check your API key in `.env` file
   - Make sure you have credits in your ElevenLabs account

2. **TTS not working**
   - Verify `ELEVENLABS_API_KEY` is set correctly
   - Check internet connection
   - Ensure ElevenLabs service is available

3. **No audio files generated**
   - Check if TTS service is available
   - Verify API key permissions
   - Check file permissions in backend directory

4. **Product analysis fails**
   - Ensure Oxylabs credentials are working
   - Check USDA API key for nutrition data
   - Verify internet connection

### Debug Mode
```bash
# Check API server status
curl http://localhost:5008/health

# Check Ray-Bans status
curl http://localhost:5008/ray-ban/status
```

## 🎯 Use Cases

### Live Shopping Sessions
- **Grocery Shopping**: Compare prices while shopping
- **Sustainability Analysis**: Get real-time eco-scores
- **Price Alerts**: Instant notifications about deals
- **Product Research**: Learn about products on-the-go

### Content Creation
- **Live Streams**: Real-time product analysis
- **Reviews**: Instant sustainability insights
- **Comparisons**: Side-by-side product analysis
- **Educational Content**: Teach about sustainable shopping

## 📊 Example Response

```json
{
  "product_name": "Organic Apples",
  "store_price": "$4.99",
  "online_price": "$4.49",
  "price_difference": 0.50,
  "is_cheaper_online": true,
  "sustainability_score": 7.5,
  "audio_files": {
    "price_announcement": "price_announcement_1699123456.mp3",
    "sustainability_announcement": "sustainability_announcement_1699123456.mp3"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 🚀 Next Steps

1. **Set up your ElevenLabs API key** in the `.env` file
2. **Test the system** with the demo script
3. **Start live streaming** with Meta Ray-Bans
4. **Integrate with your app** using the API endpoints
5. **Customize TTS voices** and announcements as needed

Your Meta Ray-Bans live streaming integration is ready! 🥽✨
