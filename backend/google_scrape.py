import requests
import json
import sys
import os
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get credentials from environment variables
USERNAME = os.getenv("OXYLABS_USERNAME")
PASSWORD = os.getenv("OXYLABS_PASSWORD")


def clean_store_name(raw_name: str) -> str:
    if not raw_name:
        return ""
    name = raw_name.strip()
    if not name:
        return ""

    # Parse a URL if provided
    if name.startswith("http"):
        parsed = urlparse(name)
        name = parsed.netloc or parsed.path

    # Remove URL extras like query/path
    if '/' in name:
        name = name.split('/', 1)[0]

    # Remove leading www.
    name = re.sub(r'^www\.', '', name, flags=re.IGNORECASE)

    # Remove common domain extensions
    name = re.sub(r'\.(com|org|net|edu|gov|co\.uk|ca|de|fr|jp)$', '', name, flags=re.IGNORECASE)

    # Replace separators with spaces and title-case
    name = name.replace('-', ' ').replace('.', ' ').strip()
    return name.title() if name else ""


def extract_store_name(item: dict) -> str:
    preferred_keys = ["store", "seller", "seller_name", "merchant"]

    for key in preferred_keys:
        value = item.get(key)
        if isinstance(value, dict):
            value = value.get("name") or value.get("title")
        if isinstance(value, list):
            for entry in value:
                candidate = entry.get("name") if isinstance(entry, dict) else entry
                clean = clean_store_name(candidate or "")
                if clean and clean.lower() != "google":
                    return clean
            continue
        clean = clean_store_name(value or "")
        if clean and clean.lower() != "google":
            return clean

    # Check nested offers / sub results for individual merchants
    nested_keys = ["offers", "sub_results", "seller_details", "shops"]
    for nested_key in nested_keys:
        nested = item.get(nested_key)
        if isinstance(nested, list):
            for entry in nested:
                if not isinstance(entry, dict):
                    continue
                for key in preferred_keys + ["name", "title"]:
                    candidate = entry.get(key)
                    clean = clean_store_name(candidate or "")
                    if clean and clean.lower() != "google":
                        return clean

    # Fall back to product links to infer domain
    for link_key in ("product_link", "link", "url"):
        link = item.get(link_key)
        if link:
            clean = clean_store_name(link)
            if clean and clean.lower() != "google":
                return clean

    # Final fallback: return merchant even if it's Google
    return clean_store_name(item.get("merchant", "")) or "Google"

def _perform_oxylabs_request(query: str):
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

    if response.status_code == 204:
        print(f"⚠️ Oxylabs returned 204 (no content) for query '{query}'")
        return None
    if response.status_code != 200:
        print(f"⚠️ Oxylabs request failed with status {response.status_code} for query '{query}'")
        return None

    try:
        return response.json()
    except ValueError as e:
        print(f"⚠️ Failed to parse JSON response for query '{query}': {e}")
        return None


def _extract_results(data: dict):
    if not data or "results" not in data or not data["results"]:
        return []

    result = data["results"][0]

    def build_entries(items, price_formatter=lambda p: p):
        entries = []
        for item in items:
            title = item.get("title", "")
            price = item.get("price", "")
            store = extract_store_name(item)
            if title and price:
                entries.append({
                    "title": title,
                    "price": price_formatter(price),
                    "store": store
                })
        return entries

    if "shopping_results" in result:
        return build_entries(result["shopping_results"])

    content = result.get("content")
    if isinstance(content, dict):
        shopping = content.get("results", {}).get("shopping")
        if shopping:
            return build_entries(shopping, price_formatter=lambda p: f"${p}")

        organic = content.get("results", {}).get("organic")
        if organic:
            return build_entries(organic, price_formatter=lambda p: f"${p}")

    if isinstance(content, str):
        soup = BeautifulSoup(content, "lxml")
        entries = []
        for item in soup.select("div.sh-dgr__grid-result, div.sh-dlr__list-result"):
            title_el = item.select_one("a[href][role='link'] span")
            price_el = item.select_one("span.a8Pemb, span.HRLxBb")
            store_el = item.select_one("div.aULzUe, div.oQYUcc")

            title = title_el.get_text(strip=True) if title_el else None
            price = price_el.get_text(strip=True) if price_el else None
            store = clean_store_name(store_el.get_text(strip=True) if store_el else "")

            if title and price:
                entries.append({"title": title, "price": price, "store": store})
        return entries

    return []


def scrape_google_shopping_deals(query):
    queries = []
    seen = set()

    def add_query(q):
        q = q.strip()
        if q and q.lower() not in seen:
            seen.add(q.lower())
            queries.append(q)

    add_query(query)
    tokens = query.split()
    if len(tokens) > 2:
        add_query(" ".join(tokens[:2]))
    if tokens:
        add_query(tokens[0])

    for attempt in queries:
        data = _perform_oxylabs_request(attempt)
        if not data:
            continue
        results = _extract_results(data)
        if results:
            if attempt != query:
                print(f"ℹ️ Falling back to simplified query '{attempt}'")
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
