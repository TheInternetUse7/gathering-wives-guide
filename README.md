# Gathering Wives Guide API

An unofficial, cached, and streamlined API for [Wuthering Waves](https://wutheringwaves.kurogames.com/) character build guides.

## How It Works

1.  **Scheduled Fetching:** A cron job, managed by Vercel, runs a Python script every 12 hours.
2.  **Caching:** This script calls the Kuro Games API and implements a retry/re-queue mechanism. If a request for a character fails, it's tried again at the end of the process.
3.  **Granular Data Storage:** Each character's guide is saved as a separate `[id].json` file. A central `manifest.json` file keeps track of all available characters.
4.  **Fast API:** A FastAPI server serves the cached data through simple, fast endpoints.

## API Endpoints

Once deployed, the following endpoints will be available:

### `GET /docs`

FastAPI provides automatic interactive documentation. Go to this endpoint in your browser to see all available routes and test them live.

### `GET /api/characters`

Returns a list of all available characters with basic information. Useful for populating selection menus.

-   **Example Response:**
    ```json
    [
      {
        "id": "1205",
        "name": "Changli",
        "rarity": 5,
        "attribute": "Fusion"
      },
      ...
    ]
    ```

### `GET /api/guide/{character_name}`

Returns the full, cleaned-up guide for a specific character. The `character_name` is case-insensitive and ignores spaces and colons.

-   **Example Usage:**
    -   `/api/guide/jiyan`
    -   `/api/guide/changli`
    -   `/api/guide/rover-aero`

---

## Local Development & Testing

Follow these steps to run the API on your own machine.

### 1. Prerequisites

-   Python 3.8+
-   Git

### 2. Setup

Clone the repository and set up a virtual environment.

```bash
git clone https://github.com/TheInternetUse7/gathering-wives-guide.git
cd gathering-wives-guide

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Generate the Initial Cache

Before you can run the API, you need to fetch the data from the source at least once. This will create the `data/manifest.json` file and the `data/characters/` directory with individual JSON files.

```bash
python scripts/fetch_and_cache.py
```

### 4. Run the Local API Server

Use `uvicorn` to run the FastAPI application.

```bash
uvicorn api.index:app --reload
```

The server will now be running at `http://127.0.0.1:8000`.

### 5. Test the Endpoints

You can now use your browser or a tool like `curl` to test the endpoints:

-   **Root:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
-   **Character List:** [http://127.0.0.1:8000/api/characters](http://127.0.0.1:8000/api/characters)
-   **Jiyan's Guide:** [http://127.0.0.1:8000/api/guide/jiyan](http://127.0.0.1:8000/api/guide/jiyan)
-   **Interactive Docs:** Go to [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to see and test all your endpoints live.