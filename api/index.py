from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import json
import os
import sys

# Add the parent directory to the path so we can import from 'scripts'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.fetch_and_cache import run_fetch_and_cache

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Gathering Wives Guide API",
    description="An unofficial, cached, and streamlined API for Wuthering Waves character build guides.",
    version="1.1.0"
)

# --- File Path and Cache Loading ---
IS_VERCEL = os.getenv('VERCEL') == '1'
BASE_DATA_PATH = '/tmp' if IS_VERCEL else os.path.join(os.path.dirname(__file__), '..', 'data')
CHAR_DATA_PATH = os.path.join(BASE_DATA_PATH, 'characters')
MANIFEST_PATH = os.path.join(BASE_DATA_PATH, 'manifest.json')

def load_manifest():
    """Loads the manifest file."""
    if not os.path.exists(MANIFEST_PATH):
        if not IS_VERCEL:
            print("Manifest not found. Running fetcher to create it...")
            run_fetch_and_cache()
        else:
            return {"error": "Cache manifest not found. The cron job may not have run yet."}
    
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return {"error": f"Could not load or parse manifest file: {e}"}

manifest = load_manifest()

# --- API Endpoints ---
@app.get("/", tags=["General"])
def read_root():
    """Root endpoint with API status and last cache update time."""
    return {
        "status": "Wuthering Waves Guide API is running.",
        "last_updated_utc": manifest.get("last_updated_utc", "N/A"),
        "cached_characters": len(manifest.get("characters", {})),
        "docs": "/docs"
    }

@app.get("/api/characters", tags=["Guides"])
def get_characters():
    """Returns a simplified list of all cached characters from the manifest."""
    if "error" in manifest:
        raise HTTPException(status_code=500, detail=manifest["error"])
    
    char_list = list(manifest.get("characters", {}).values())
    return sorted(char_list, key=lambda x: x.get('name', ''))

@app.get("/api/guide/{character_name}", tags=["Guides"])
def get_guide_by_name(character_name: str):
    """Fetches a guide for a character by name from their individual JSON file."""
    if "error" in manifest:
        raise HTTPException(status_code=500, detail=manifest["error"])

    # Find the character ID from the manifest
    target_char_id = None
    for char_id, char_info in manifest.get("characters", {}).items():
        if character_name.lower().replace(" ", "").replace(":", "") == char_info.get("name", "").lower().replace(" ", "").replace(":", ""):
            target_char_id = char_id
            break

    if not target_char_id:
        raise HTTPException(status_code=404, detail=f"Guide for character '{character_name}' not found in manifest.")
    
    # Load the specific character's JSON file
    char_file_path = os.path.join(CHAR_DATA_PATH, f"{target_char_id}.json")
    try:
        with open(char_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Cache file for '{character_name}' not found on server.")


@app.get("/api/cron/fetch-guides", tags=["Cron"], include_in_schema=False)
def trigger_fetch_guides(background_tasks: BackgroundTasks):
    """[CRON JOB ENDPOINT] Triggers the data fetching script in the background."""
    print("Cron job triggered: Fetching guides in the background.")
    background_tasks.add_task(run_fetch_and_cache)
    return JSONResponse(content={"status": "success", "message": "Guide fetching process started in the background."})