import requests
import json
import sys
import os
import re

def scrape_google_shopping_serpapi(query):
    """Scrape Google Shopping using SerpAPI"""    
    # Get API key from environment variable
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        raise Exception("Please set SERPAPI_KEY environment variable")
    
    # SerpAPI Google Shopping endpoint
    url = "https://serpapi.com/search"
    
    params = {
        "engine": "google_shopping_light",
        "q": query,
        "api_key": api_key,
        "google_domain": "google.com",
        "hl": "en",  # Language
        "gl": "us",  # Country
        "device": "desktop",
        "sort_by": "1",  # Sort by relevance
        "on_sale": "true"  # Only show items on sale
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        results = []
        
        # Extract shopping results
        if "shopping_results" in data:
            for item in data["shopping_results"]:
                # Get all available fields from the item
                all_fields = {}
                for key, value in item.items():
                    all_fields[key] = value
                
                # Also extract the main fields we care about
                title = item.get("title", "")
                price = item.get("price", "")
                store = item.get("source", "")
                
                # Clean up price formatting
                if price:
                    # Remove currency symbols and clean up
                    price_clean = re.sub(r'[^\d.,]', '', price)
                    if price_clean:
                        price = f"${price_clean}"
                
                # Clean up store name
                if store:
                    # Remove domain extensions and clean up
                    store = re.sub(r'\.(com|org|net|edu|gov|co\.uk|ca|de|fr|jp)$', '', store)
                    store = store.replace('.', ' ').title()
                
                if title and price:
                    # Add cleaned fields to the full data
                    all_fields["cleaned_price"] = price
                    all_fields["cleaned_store"] = store
                    results.append(all_fields)
        
        return results
        
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return []
    except Exception as e:
        print(f"Error processing results: {e}")
        return []

if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "Coca-Cola 12 pack"
    
    print(f"Searching for: {query}")
    print("Using SerpAPI Google Shopping...")
    
    deals = scrape_google_shopping_serpapi(query)
    
    # Show all available fields from the first result
    if deals:
        print("=== ALL AVAILABLE FIELDS FROM FIRST RESULT ===")
        first_result = deals[0]
        for key, value in first_result.items():
            print(f"{key}: {value}")
        print("=" * 50)
        print()
    
    # Print results to console
    for d in deals[:20]:  # Show first 20 results
        print(f"{d['title']}\n  {d['price']} — {d['source']}\n")
    
    print(f"\nTotal deals found: {len(deals)}")
    
    # Save results as JSON
    output_file = f"serpapi_deals_{query.replace(' ', '_').lower()}.json"
    with open(output_file, 'w') as f:
        json.dump(deals, f, indent=2)
    
    print(f"Results saved to: {output_file}")
