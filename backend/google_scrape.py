import requests
import json
import sys
import os
import re
from bs4 import BeautifulSoup

# Get credentials from environment variables
USERNAME = os.getenv("OXYLABS_USERNAME")
PASSWORD = os.getenv("OXYLABS_PASSWORD")

def scrape_google_shopping_deals(query):
    # Use the google_shopping source for better shopping results
    # Need to construct the Google Shopping URL
    target_url = f"https://www.google.com/search?tbm=shop&q={query.replace(' ', '+')}"
    
    payload = {
        "source": "google_shopping",
        "url": target_url,
        "geo_location": "United States",
        "parse": True
    }

    response = requests.post(
        "https://realtime.oxylabs.io/v1/queries",
        auth=(USERNAME, PASSWORD),
        headers={'Content-Type': 'application/json'},
        json=payload
    )
    
    # Check if response is successful
    if response.status_code != 200:
        raise Exception(f"API request failed with status code: {response.status_code}")
    
    # Try to parse JSON, with better error handling
    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError as e:
        print(f"Failed to parse JSON response. Error: {e}")
        raise Exception("Invalid JSON response from API")

    # Parse the response structure
    if "results" in data and len(data["results"]) > 0:
        result = data["results"][0]
        
        
        # Check if we have parsed shopping results
        if "shopping_results" in result:
            shopping_results = result["shopping_results"]
            results = []
            
            for item in shopping_results:
                title = item.get("title", "")
                price = item.get("price", "")
                store = item.get("merchant", "")
                
                if title and price:
                    results.append({"title": title, "price": price, "store": store})
            
            return results
        elif "content" in result:
            content = result["content"]
            
            # For google_shopping, check if we have shopping results in content
            if "results" in content and "shopping" in content["results"]:
                shopping_results = content["results"]["shopping"]
                results = []
                
                for item in shopping_results:
                    title = item.get("title", "")
                    price = item.get("price", "")
                    store = item.get("merchant", "")
                    
                    if title and price:
                        results.append({"title": title, "price": f"${price}", "store": store})
                
                return results
            # Check if content has organic results (which include shopping results)
            elif "results" in content and "organic" in content["results"]:
                organic_results = content["results"]["organic"]
                results = []
                
                for item in organic_results:
                    title = item.get("title", "")
                    price = item.get("price", "")
                    # Extract store from URL by removing domain extension
                    store = ""
                    if "url" in item:
                        url = item["url"]
                        match = re.search(r'https?://(?:www\.)?([^/]+)', url)
                        if match:
                            domain = match.group(1)
                            # Remove common domain extensions
                            store = re.sub(r'\.(com|org|net|edu|gov|co\.uk|ca|de|fr|jp)$', '', domain)
                            store = store.replace('.', ' ').title()
                    
                    if title and price:
                        results.append({"title": title, "price": f"${price}", "store": store})
                
                return results
            else:
                # Fallback: try to parse HTML content if available
                if isinstance(content, str):
                    soup = BeautifulSoup(content, "lxml")
                    
                    results = []
                    for item in soup.select("div.sh-dgr__grid-result, div.sh-dlr__list-result"):
                        title_el = item.select_one("a[href][role='link'] span")
                        price_el = item.select_one("span.a8Pemb, span.HRLxBb")
                        store_el = item.select_one("div.aULzUe, div.oQYUcc")

                        title = title_el.get_text(strip=True) if title_el else None
                        price = price_el.get_text(strip=True) if price_el else None
                        store = store_el.get_text(strip=True) if store_el else None

                        if title and price:
                            results.append({"title": title, "price": price, "store": store})
                    
                    return results
    
    return []

if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "Coca-Cola 12 pack"
    deals = scrape_google_shopping_deals(query)

    # Print results to console
    for d in deals[:20]:
        print(f"{d['title']}\n  {d['price']} — {d['store']}\n")

    print(f"\nTotal deals found: {len(deals)}")
    
    # Save results as JSON
    output_file = f"deals_{query.replace(' ', '_').lower()}.json"
    with open(output_file, 'w') as f:
        json.dump(deals, f, indent=2)
    
    print(f"Results saved to: {output_file}")
