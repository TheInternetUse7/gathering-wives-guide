import requests
import json
from bs4 import BeautifulSoup
import os
import time
import redis

# --- Constants & Mappings ---
BASE_URL = "https://guide-server.aki-game.net"
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://wuwaguide.kurogames.com",
    "Referer": "https://wuwaguide.kurogames.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "x-language": "en",
    "x-token": "",
}
ATTRIBUTE_MAP = {
    "1": "Glacio",
    "2": "Fusion",
    "3": "Electro",
    "4": "Aero",
    "5": "Spectro",
    "6": "Havoc",
}

# --- Redis KV Store Connection ---
# Vercel automatically provides the KV_URL environment variable
KV_URL = os.getenv("KV_URL")
if KV_URL:
    try:
        kv = redis.from_url(KV_URL)
        print("Successfully connected to Vercel KV store.")
    except Exception as e:
        print(f"Failed to connect to Vercel KV: {e}")
        kv = None
else:
    print("KV_URL not found. KV store operations will be skipped (local mode).")
    kv = None


# --- Helper Functions ---
def fetch_with_retries(url, retries=3, delay=2):
    for i in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=20)
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 200:
                return data.get("data")
            return None
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            print(f"    - Attempt {i+1}/{retries} failed for {url}: {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                return None


def strip_html(html_content):
    if not html_content:
        return "N/A"
    return BeautifulSoup(html_content, "html.parser").get_text(
        separator="\n", strip=True
    )


# --- Main Fetching Logic ---
def process_character(char_data):
    char_id = char_data.get("roleGbId")
    char_name = char_data.get("texts", [{}])[0].get("name", "Unknown")
    print(f"  -> Processing {char_name} (ID: {char_id})...")
    guides = fetch_with_retries(f"{BASE_URL}/introduction/list?roleGbId={char_id}")
    if not guides:
        print(f"     [FAIL] Could not fetch guide list for {char_name}.")
        return None
    guides_sorted = sorted(guides, key=lambda g: g.get("likeCount", 0), reverse=True)
    if not guides_sorted:
        print(f"     [SKIP] No guides available for {char_name}.")
        return None
    top_guide = guides_sorted[0]
    guide_id = top_guide.get("id")
    detailed_guide = fetch_with_retries(
        f"{BASE_URL}/introduction/info?roleGbId={char_id}&id={guide_id}"
    )
    if not detailed_guide:
        print(f"     [FAIL] Could not fetch details for top guide of {char_name}.")
        return None
    en_base_texts = next(
        (
            item
            for item in detailed_guide.get("baseTexts", [])
            if item.get("language") == "en"
        ),
        {},
    )
    transformed_data = {
        "character_info": {
            "id": char_id,
            "name": detailed_guide.get("role", {}).get("texts", [{}])[0].get("name"),
            "rarity": detailed_guide.get("role", {}).get("star"),
            "attribute_id": str(
                detailed_guide.get("role", {}).get("element", {}).get("gbId")
            ),
            "attribute": ATTRIBUTE_MAP.get(
                str(detailed_guide.get("role", {}).get("element", {}).get("gbId"))
            ),
            "card_url": detailed_guide.get("role", {}).get("cardPictureUrl"),
            "illust_url": detailed_guide.get("role", {}).get("illustrationPictureUrl"),
        },
        "guide_meta": {
            "guide_name": en_base_texts.get("introductionName"),
            "source": en_base_texts.get("introductionSource"),
            "likes": top_guide.get("likeCount"),
            "guide_id": guide_id,
        },
        "overview": {
            "role_description": strip_html(en_base_texts.get("roleDescription")),
            "synopsis": strip_html(en_base_texts.get("introductionSynopsis")),
            "rotation": strip_html(en_base_texts.get("introductionDetail")),
        },
        "weapons": detailed_guide.get("weapon", {}),
        "echoes": detailed_guide.get("echo", {}),
        "teams": detailed_guide.get("teammate", {}),
        "skill_priority": detailed_guide.get("roleSkill", {}),
        "resonance_chains": detailed_guide.get("roleResonance", {}),
    }
    print(f"     [SUCCESS] Fetched and processed guide for {char_name}.")
    return transformed_data


def run_fetch_and_cache():
    print("Starting data fetch process...")
    if not kv:
        return {
            "status": "error",
            "message": "KV store is not configured. Cannot run fetcher.",
        }

    initial_chars = fetch_with_retries(f"{BASE_URL}/role/avatar/list")
    if not initial_chars:
        return {"status": "error", "message": "Could not fetch character list."}

    queue = sorted(
        [c for c in initial_chars if c.get("roleStatus") in [1, 3]],
        key=lambda x: x.get("sequence", 9999),
    )
    failed_queue = []
    manifest_chars = {}

    for char_data in queue:
        processed_guide = process_character(char_data)
        if processed_guide:
            char_id = processed_guide["character_info"]["id"]
            # Save individual character data to KV with a prefix
            kv.set(f"guide:{char_id}", json.dumps(processed_guide))
            manifest_chars[char_id] = processed_guide["character_info"]
        else:
            failed_queue.append(char_data)
        time.sleep(0.5) # Be respectful between characters

    if failed_queue:
        print(f"\nRetrying {len(failed_queue)} failed characters...")
        for char_data in failed_queue:
            processed_guide = process_character(char_data)
            if processed_guide:
                char_id = processed_guide["character_info"]["id"]
                kv.set(f"guide:{char_id}", json.dumps(processed_guide))
                manifest_chars[char_id] = processed_guide["character_info"]
            time.sleep(0.5)

    # Create and save the manifest to KV
    manifest = {
        "characters": manifest_chars,
        "last_updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    kv.set("manifest", json.dumps(manifest))

    print(f"\nData fetching complete. Saved to Vercel KV store.")
    return {"status": "success", "message": f"Cached {len(manifest_chars)} guides."}


# This is only for local testing, not for Vercel deployment.
if __name__ == "__main__":
    print("This script is intended to be run by the API endpoint on Vercel.")
    print(
        "It will not work locally unless you have a local Redis instance and set KV_URL."
    )
