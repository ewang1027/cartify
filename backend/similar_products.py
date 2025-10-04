# -*- coding: utf-8 -*-
import os, re, json, requests
from typing import List, Dict, Any
from rapidfuzz import fuzz

SERP_BASE = "https://serpapi.com/search.json"

def _parse_price(price_str: str):
    if not price_str: return None, None
    m = re.match(r"([£€$])\s?([\d\.,]+)", price_str.strip())
    if not m: return None, None
    sym, num = m.groups()
    currency = {"$":"USD","£":"GBP","€":"EUR"}.get(sym, None)
    try: value = float(num.replace(",", ""))
    except: value = None
    return value, currency

def fetch_google_shopping_results(query: str, gl: str = "us", hl: str = "en", num: int = 30) -> List[Dict[str, Any]]:
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        raise RuntimeError("Set SERPAPI_KEY env var.")

    params = {
        "engine": "google_shopping",
        "q": query,
        "api_key": api_key,
        "gl": gl,
        "hl": hl,
    }
    r = requests.get(SERP_BASE, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    out = []
    for it in (data.get("shopping_results") or [])[:num]:
        price, currency = _parse_price(it.get("price"))
        out.append({
            "source": "google_shopping",
            "title": it.get("title", ""),
            "price": price,
            "currency": currency,
            "url": it.get("link", ""),
            "image": it.get("thumbnail"),
            "seller": it.get("source"),
            "extra": {
                "delivery": it.get("delivery"),
                "extracted_price": it.get("extracted_price"),
            }
        })
    return out

# --- SIMPLE "SIMILARITY" RANKER (text-only, no exact-match enforcement) ---

def rank_similar(query: str, listings: List[Dict[str, Any]], top_k: int = 12):
    ranked = []
    for li in listings:
        title = li.get("title", "")
        # Token-set fuzzy match gives a nice robust score on short product titles
        base = fuzz.token_set_ratio(query, title) / 100.0  # 0..1
        # Light bonuses for brand/variant words found in query
        bonus = 0.0
        for kw in ("zero", "diet", "classic", "vanilla", "cherry"):
            if kw in query.lower() and kw in title.lower():
                bonus += 0.05

        score = base * 0.9 + bonus  # cap influence of bonuses
        li["_score"] = round(score, 4)
        ranked.append(li)

    ranked.sort(key=lambda x: x["_score"], reverse=True)
    return ranked[:top_k]

def find_similar_products_google(query: str, gl: str = "us", hl: str = "en", top_k: int = 12):
    results = fetch_google_shopping_results(query, gl=gl, hl=hl, num=60)
    ranked = rank_similar(query, results, top_k=top_k)
    return [{
        "title": r["title"],
        "price": r["price"],
        "currency": r["currency"],
        "seller": r["seller"],
        "url": r["url"],
        "image": r["image"],
        "score": r["_score"]
    } for r in ranked]

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help='e.g. "Coca-Cola Zero Sugar 12 fl oz 12-pack"')
    ap.add_argument("--gl", default="us", help="Country code for localization (e.g., us, sg, gb)")
    ap.add_argument("--hl", default="en", help="UI language code (e.g., en, fr)")
    ap.add_argument("--top_k", type=int, default=12)
    args = ap.parse_args()

    items = find_similar_products_google(args.query, gl=args.gl, hl=args.hl, top_k=args.top_k)
    print(json.dumps(items, indent=2, ensure_ascii=False))
