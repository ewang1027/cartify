from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import base64
from pathlib import Path
from typing import Dict, Any

app = FastAPI(title="Shopping Cart API", description="API to retrieve shopping cart data and images")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base paths
BASE_DIR = Path(__file__).parent
RESULTS_FILE = BASE_DIR / "results.json"
CAPTURES_DIR = BASE_DIR / "captures"


def load_results() -> Dict[str, Any]:
    """Load and parse the results.json file."""
    if not RESULTS_FILE.exists():
        raise HTTPException(status_code=404, detail="results.json not found")
    
    try:
        with open(RESULTS_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON in results.json")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Shopping Cart API",
        "endpoints": {
            "/shopping-cart": "Get shopping cart data with image paths",
            "/shopping-cart/with-urls": "Get shopping cart data with full image URLs",
            "/image/{image_name}": "Get a specific image by name",
            "/cart-summary": "Get cart summary information",
            "/all-items": "Get all items with image URLs",
            "/all-items-with-images": "Get all items with embedded base64 images (for frontend)"
        }
    }


@app.get("/shopping-cart")
async def get_shopping_cart():
    """
    Get the shopping cart data from results.json.
    Returns the shopping_cart object with image paths.
    """
    data = load_results()
    return {
        "shopping_cart": data.get("shopping_cart", {}),
        "cart_summary": data.get("cart_summary", {}),
        "timestamp": data.get("timestamp", "")
    }


@app.get("/shopping-cart/with-urls")
async def get_shopping_cart_with_urls():
    """
    Get the shopping cart data with full image URLs.
    Constructs image URLs that can be accessed via the /image endpoint.
    """
    data = load_results()
    shopping_cart = data.get("shopping_cart", {})
    
    # Add full image URLs to each item
    cart_with_urls = {}
    for item_key, item_data in shopping_cart.items():
        item_copy = item_data.copy()
        if "image_path" in item_data:
            # Extract just the filename from the path
            image_path = item_data["image_path"]
            if image_path:
                # Get the filename (e.g., "20251005-032746_motion_0.80.jpg")
                filename = Path(image_path).name
                item_copy["image_url"] = f"/image/{filename}"
        cart_with_urls[item_key] = item_copy
    
    return {
        "shopping_cart": cart_with_urls,
        "cart_summary": data.get("cart_summary", {}),
        "timestamp": data.get("timestamp", "")
    }


@app.get("/image/{image_name}")
async def get_image(image_name: str):
    """
    Serve an image from the captures directory.
    
    Args:
        image_name: Name of the image file (e.g., "20251005-032746_motion_0.80.jpg")
    
    Returns:
        The image file
    """
    # Security: Prevent path traversal attacks
    if ".." in image_name or "/" in image_name or "\\" in image_name:
        raise HTTPException(status_code=400, detail="Invalid image name")
    
    image_path = CAPTURES_DIR / image_name
    
    if not image_path.exists():
        raise HTTPException(status_code=404, detail=f"Image {image_name} not found")
    
    if not image_path.is_file():
        raise HTTPException(status_code=400, detail="Invalid image path")
    
    return FileResponse(
        image_path,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=3600"}
    )


@app.get("/cart-summary")
async def get_cart_summary():
    """Get just the cart summary information."""
    data = load_results()
    return {
        "cart_summary": data.get("cart_summary", {}),
        "timestamp": data.get("timestamp", ""),
        "total_frames_processed": data.get("total_frames_processed", 0),
        "bag_detected": data.get("bag_detected", False)
    }


@app.get("/deal-analysis")
async def get_deal_analysis():
    """Get deal analysis information from the shopping cart."""
    data = load_results()
    return {
        "deal_analysis_cache": data.get("deal_analysis_cache", {}),
        "deal_analysis_summary": data.get("deal_analysis_summary", {})
    }


@app.get("/all-items")
async def get_all_items_with_images():
    """
    Get all shopping cart items with their complete information and image URLs.
    This is a comprehensive endpoint that includes everything you might need.
    """
    data = load_results()
    shopping_cart = data.get("shopping_cart", {})
    
    items = []
    for item_key, item_data in shopping_cart.items():
        # Create a comprehensive item object
        item = {
            "id": item_key,
            "name": item_data.get("name", ""),
            "brand": item_data.get("brand", ""),
            "category": item_data.get("category", ""),
            "count": item_data.get("count", 0),
            "confidence": item_data.get("confidence", 0),
            "last_seen": item_data.get("last_seen", 0),
            "deal_analysis": item_data.get("deal_analysis"),
        }
        
        # Add image information
        if "image_path" in item_data and item_data["image_path"]:
            filename = Path(item_data["image_path"]).name
            item["image_url"] = f"/image/{filename}"
            item["image_path"] = item_data["image_path"]
        
        items.append(item)
    
    return {
        "items": items,
        "summary": data.get("cart_summary", {}),
        "timestamp": data.get("timestamp", "")
    }


@app.get("/all-items-with-images")
async def get_all_items_with_embedded_images():
    """
    Get all shopping cart items with images embedded as base64 data.
    This endpoint includes the actual image data in the JSON response,
    allowing the frontend to display images without additional requests.
    
    Note: This response can be large. For better performance, use /all-items
    with the /image/{name} endpoint instead.
    """
    data = load_results()
    shopping_cart = data.get("shopping_cart", {})
    
    items = []
    for item_key, item_data in shopping_cart.items():
        # Create a comprehensive item object
        item = {
            "id": item_key,
            "name": item_data.get("name", ""),
            "brand": item_data.get("brand", ""),
            "category": item_data.get("category", ""),
            "count": item_data.get("count", 0),
            "confidence": item_data.get("confidence", 0),
            "last_seen": item_data.get("last_seen", 0),
            "deal_analysis": item_data.get("deal_analysis"),
        }
        
        # Add image information and embed the image as base64
        if "image_path" in item_data and item_data["image_path"]:
            image_path = BASE_DIR / item_data["image_path"]
            if image_path.exists():
                try:
                    with open(image_path, "rb") as img_file:
                        image_data = base64.b64encode(img_file.read()).decode('utf-8')
                        item["image_base64"] = f"data:image/jpeg;base64,{image_data}"
                        item["image_path"] = item_data["image_path"]
                except Exception as e:
                    item["image_error"] = str(e)
        
        items.append(item)
    
    return {
        "items": items,
        "summary": data.get("cart_summary", {}),
        "timestamp": data.get("timestamp", "")
    }


if __name__ == "__main__":
    import uvicorn
    
    print("=" * 70)
    print("Starting Shopping Cart API Server")
    print("=" * 70)
    print("\nAvailable endpoints:")
    print("  - http://localhost:8000/                         - API documentation")
    print("  - http://localhost:8000/shopping-cart            - Get shopping cart data")
    print("  - http://localhost:8000/shopping-cart/with-urls  - Cart with image URLs")
    print("  - http://localhost:8000/image/{name}             - Get specific image")
    print("  - http://localhost:8000/cart-summary             - Get cart summary")
    print("  - http://localhost:8000/deal-analysis            - Get deal analysis")
    print("  - http://localhost:8000/all-items                - Get all items with URLs")
    print("  - http://localhost:8000/all-items-with-images    - Get items with embedded images ⭐")
    print("  - http://localhost:8000/docs                     - Interactive API docs")
    print("=" * 70)
    print()
    
    uvicorn.run(
        "shopping_cart_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
