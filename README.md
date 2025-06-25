# Gathering Wives Guide API

An unofficial, cached, and streamlined API for [Wuthering Waves](https://wutheringwaves.kurogames.com/) character build guides.

## How It Works

1.  **Scheduled Fetching:** A cron job, managed by Vercel, runs a Python script once a day.
2.  **Caching:** This script calls the Kuro Games API and implements a retry/re-queue mechanism. If a request for a character fails, it's tried again at the end of the process.
3.  **Persistent Data Store:** The script stores all data in a Vercel KV (Serverless Redis) Store. A central `manifest` key holds character metadata, and each guide is stored under a `guide:{id}` key.
4.  **Fast API:** A FastAPI server reads directly from the Vercel KV store to serve cached data through simple, fast endpoints.

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

## Deployment to Vercel

This project is optimized for deployment on Vercel's free Hobby plan.

### Step 1: Create GitHub Repository

1.  Make sure all your project files (`api/`, `scripts/`, `data/`, `vercel.json`, `requirements.txt`, etc.) are ready.
2.  Push your entire project folder to a new repository on your GitHub account.

### Step 2: Create Vercel Project and Database

1.  Log in to [Vercel](https://vercel.com/) with your GitHub account.
2.  From your dashboard, click **"Add New..."** -> **"Project"**.
3.  Import the `gathering-wives-guide` repository you just created on GitHub.
4.  Before deploying, we need to set up the database. Go to the **"Storage"** tab in your new project's dashboard.
5.  From the list of "Marketplace Database Providers", select **Upstash**.
6.  You will be taken to the "Get started with Upstash" screen.
    *   Choose a **Primary Region** (e.g., "Washington, D.C., USA (East)").
    *   Ensure the **Free** plan is selected.
    *   Click **"Continue"**.
7.  On the confirmation screen, give your database a name (e.g., `gathering-wives-guide-kv`) and click **"Create"**.
8.  **Crucially**, after the database is created, you will be on a page showing your database credentials. Click the **"Connect Project"** button and link it to your `gathering-wives-guide` project. This automatically adds the `KV_URL` and other secrets as environment variables.

### Step 3: Deploy the Application

1.  After connecting the database, Vercel will prompt you to redeploy to apply the new environment variables.
2.  If it doesn't, go to the **"Deployments"** tab for your project, click the latest deployment, and choose **"Redeploy"** from the menu.
3.  Wait for the deployment to finish successfully.

### Step 4: Populate the Database (Important First Step)

Your API is now live, but the KV database is empty. You need to run the data fetcher once to populate it.

1.  In your Vercel project dashboard, navigate to the **Cron Jobs** tab in the project settings.
2.  You will see the `/api/cron/fetch-guides` job listed.
3.  To the right of the job, click the **Run** button to run it manually.
4.  You can monitor the progress by going to the **Logs** tab. You should see output from the `fetch_and_cache.py` script as it processes each character. This will take a few minutes to complete.

### Step 5: Verify the API is Working

Once the cron job has finished, your API is fully operational. You can test the following URLs in your browser (replace `gathering-wives-guide.vercel.app` with your actual Vercel URL):

-   **Character List:** [https://gathering-wives-guide.vercel.app/api/characters](https://gathering-wives-guide.vercel.app/api/characters)
-   **Example Guide:** [https://gathering-wives-guide.vercel.app/api/guide/encore](https://gathering-wives-guide.vercel.app/api/guide/encore)
-   **Interactive Docs:** [https://gathering-wives-guide.vercel.app/docs](https://gathering-wives-guide.vercel.app/docs)

Your API is now ready to serve! The cron job will automatically keep the data fresh every day.