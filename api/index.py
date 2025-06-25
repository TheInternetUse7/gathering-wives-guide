from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import json
import os
import sys
import redis

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Gathering Wives Guide API",
    description="An unofficial, cached, and streamlined API for Wuthering Waves character build guides.",
    version="1.2.0",
)

# --- Redis KV Store Connection ---
KV_URL = os.getenv("KV_URL")
if not KV_URL:
    raise RuntimeError(
        "KV_URL environment variable not set. This app requires a Vercel KV store."
    )
try:
    kv = redis.from_url(KV_URL)
except Exception as e:
    raise RuntimeError(f"Could not connect to KV store: {e}")

# Add the parent directory to the path to import the fetcher script for the cron job
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scripts.fetch_and_cache import run_fetch_and_cache


# --- API Endpoints ---
@app.get("/", tags=["General"])
def read_root():
    """Root endpoint with API status and last cache update time."""
    manifest_str = kv.get("manifest")
    if not manifest_str:
        return {
            "status": "API is running, but no cache manifest found. Please trigger the cron job."
        }
    manifest = json.loads(manifest_str)
    return {
        "status": "Wuthering Waves Guide API is running.",
        "last_updated_utc": manifest.get("last_updated_utc", "N/A"),
        "cached_characters": len(manifest.get("characters", {})),
        "docs": "/docs",
    }


@app.get("/api/characters", tags=["Guides"])
def get_characters():
    """Returns a simplified list of all cached characters from the manifest."""
    manifest_str = kv.get("manifest")
    if not manifest_str:
        raise HTTPException(
            status_code=503, detail="Cache is not built yet. Please try again later."
        )

    manifest = json.loads(manifest_str)
    char_list = list(manifest.get("characters", {}).values())
    return sorted(char_list, key=lambda x: x.get("name", ""))


@app.get("/api/guide/{character_name}", tags=["Guides"])
def get_guide_by_name(character_name: str):
    """Fetches a pre-processed guide for a character by their name."""
    manifest_str = kv.get("manifest")
    if not manifest_str:
        raise HTTPException(
            status_code=503, detail="Cache is not built yet. Please try again later."
        )

    manifest = json.loads(manifest_str)
    target_char_id = None
    for char_id, char_info in manifest.get("characters", {}).items():
        if character_name.lower().replace(" ", "").replace(":", "") == char_info.get(
            "name", ""
        ).lower().replace(" ", "").replace(":", ""):
            target_char_id = char_id
            break

    if not target_char_id:
        raise HTTPException(
            status_code=404,
            detail=f"Guide for character '{character_name}' not found in manifest.",
        )

    guide_str = kv.get(f"guide:{target_char_id}")
    if not guide_str:
        raise HTTPException(
            status_code=404,
            detail=f"Cache for '{character_name}' is missing, despite being in the manifest. The cache might be rebuilding.",
        )

    return json.loads(guide_str)


@app.get("/api/cron/fetch-guides", tags=["Cron"], include_in_schema=False)
def trigger_fetch_guides(background_tasks: BackgroundTasks):
    """[CRON JOB ENDPOINT] Triggers the data fetching script in the background."""
    print("Cron job triggered: Fetching guides in the background.")
    background_tasks.add_task(run_fetch_and_cache)
    return JSONResponse(
        content={
            "status": "success",
            "message": "Guide fetching process started in the background.",
        }
    )
