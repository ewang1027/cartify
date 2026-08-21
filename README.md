# Cartify

**Shop smart. Spend wisely. Live sustainably.**

Built in 36 hours at HackHarvard 2025.

Cartify turns Ray-Ban Meta smart glasses into a real-time shopping assistant. As you walk through a store, the glasses' live video feed is analyzed to recognize the products you pick up and add them to a virtual cart — then Cartify compares prices against online listings, scores each item's sustainability, tracks your budget, and reads the results back to you through the glasses' speakers.

## How it works

1. **Stream** — the glasses livestream to an RTMP endpoint, and the vision service ingests the feed (a regular webcam or a recorded video works too).
2. **See** — frames are processed at ~1 FPS: a Roboflow SKU-detection workflow finds products, MediaPipe hand tracking plus Depth Anything V2 (Core ML) work out which item you're actually holding, OCR (docTR / Apple Vision) reads the packaging, and Gemini turns the crop and text into a clean product name and brand.
3. **Score** — the backend searches Google Shopping (via Oxylabs) for price comparison, pulls nutrition data from USDA FoodData Central, runs news sentiment analysis on the brand, and combines everything into a sustainability score covering nutrition, carbon footprint, and social ethics.
4. **Speak and show** — ElevenLabs text-to-speech announces price differences and eco-scores through the glasses, while the web dashboard displays the live annotated feed, your cart, budget status, and per-item scores.

## Repo layout

| Path | What it is |
|---|---|
| `vision_backends/` | Computer-vision pipeline: Roboflow SKU detection, YOLO variants, MediaPipe hands, Core ML depth, OCR, SAM, and the Gemini product-extraction step. `video_product_pipeline.py` runs the full pipeline over a video. |
| `backend/` | Sustainability scoring engine and APIs: Google Shopping scraping, USDA nutrition, news sentiment, Ray-Ban live-stream endpoints, and ElevenLabs TTS. |
| `frontend/` | React dashboard: landing page, live video feed, cart, budget tracking, and sustainability cards. |
| `models/` | Depth Anything V2 Small (Core ML) used for depth estimation. |

## Services

| Service | Port | Start with |
|---|---|---|
| Sustainability API (Flask) | 5008 | `python3 backend/start_api.py` |
| Shopping cart API (FastAPI) | 8000 | `python3 backend/shopping_cart_api.py` |
| Video stream server (Flask-SocketIO) | 5001 | `python3 backend/video_stream_server.py` |
| Frontend (Vite) | 8080 | `npm run dev` in `frontend/` |

## Running it

### Backend

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in `backend/` with your own keys:

```bash
OXYLABS_USERNAME=...      # Google Shopping scraping
OXYLABS_PASSWORD=...
GEMINI_API_KEY=...        # product extraction + analysis
NEWS_API_KEY=...          # news sentiment
USDA_API_KEY=...          # nutrition data
ELEVENLABS_API_KEY=...    # text-to-speech
ELEVENLABS_VOICE_ID=...
```

Then start the services:

```bash
python3 backend/start_api.py            # scoring API on :5008
python3 backend/shopping_cart_api.py    # cart API on :8000
python3 backend/video_stream_server.py  # annotated video feed on :5001
```

### Vision pipeline

Run the full detection pipeline over a recorded video:

```bash
python3 vision_backends/video_product_pipeline.py path/to/video.mp4
```

Or start the live vision app (RTMP/camera ingest):

```bash
python3 vision_backends/start_vision_app.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_BACKEND_URL` if the cart API isn't on `http://localhost:8000`.

## API highlights

- `POST /grocery/search` · `POST /grocery/analyze` · `POST /grocery/category` — product search and sustainability scoring (`:5008`)
- `POST /ray-ban/start-stream` · `POST /ray-ban/analyze-product` · `POST /ray-ban/quick-alert` — live-session endpoints that generate TTS announcements for the glasses (`:5008`)
- `GET /shopping-cart/with-urls` · `GET /all-items` · `GET /deal-analysis` — detected cart contents with captured product images (`:8000`)

See `backend/README.md` and `backend/RAY_BANS_SETUP_GUIDE.md` for details.

## Notes

This is a hackathon build — expect rough edges. Model weights are checked into the repo, the services assume localhost, and several vision backends in `vision_backends/` are alternative experiments rather than parts of the final pipeline.
