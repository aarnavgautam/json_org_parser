# UF Organizations Directory

Searchable directory of 1,000+ UF student organizations. Filter, select, export contacts, and track outreach.

## Deploy on Vercel (recommended)

1. Push this repo to GitHub
2. Import the project in [Vercel](https://vercel.com)
3. Deploy — Vercel runs `build_data.py` and serves the app
4. Share the live link with coworkers

### Team-wide tracking

**Option A: Google Sheets (recommended, no setup beyond Vercel)**

1. Create a Google Sheet with columns: **OrganizationId**, **GotResponse**, **OutreachCount**
   - **OrganizationId** = numeric ID from the app (e.g. 2470 for "180 Degrees Consulting at UF")
   - **GotResponse** = `Y` or `N` (or Yes/No, 1/0, ✓ for yes)
   - **OutreachCount** = number of times you reached out
   - Tip: Add an extra **OrganizationName** column for your reference; the app uses OrganizationId only for matching.
2. **File → Share → Publish to web** → choose **Comma-separated values (.csv)** → Publish
3. Copy the CSV URL (e.g. `https://docs.google.com/spreadsheets/d/SHEET_ID/export?format=csv&gid=0`)
4. In Vercel: **Settings → Environment Variables** → add:
   - `GOOGLE_SHEET_TRACKING_URL` = your published CSV URL
   - `GOOGLE_SHEET_EDIT_LINK` = (optional) banner link only—use when you want the banner to open a specific sheet URL. Does not affect data fetching (that uses `GOOGLE_SHEET_TRACKING_URL`). Example: `https://docs.google.com/spreadsheets/d/SHEET_ID/edit?usp=sharing`
5. Redeploy

The app reads from the sheet every 30 seconds. Edit the sheet manually; changes appear on the page automatically. Works in incognito and for all users.

**Option B: Vercel KV (Upstash Redis)**

1. In Vercel Dashboard → your project → **Storage**
2. Click **Create Database** → choose **KV** (Upstash)
3. Create the database (free tier: 256MB, 30K commands/month)
4. Click **Connect** to link it to your project
5. Redeploy the project

Vercel adds `KV_REST_API_URL` and `KV_REST_API_TOKEN` automatically. Tracking syncs when users change it in the app (not from a sheet).

## Local development

```bash
pip3 install -r requirements.txt
python3 build_data.py
python3 app/app.py
```

Then open **http://localhost:5555**

## Features

- **Search & filter** — Search, innovation fit, category, custom keywords
- **Position filter** — Include President, VP, Recruitment/Outreach, Other (select all / deselect all)
- **Select orgs** — Checkboxes, Select all visible, Deselect all
- **Export to CSV** — Selected orgs only, columns: OrganizationName, OfficerName, Position, Email
- **Outreach tracking** — Per org: "Got response" flag, "Reached out" counter. Team-wide when Vercel KV is connected; otherwise saved in browser

## Source files

- `final_organizations.json` — GatorConnect data
- `ignite_innovation_filtered_orgs.csv` — Innovation ratings
- `build_data.py` — Merges to `data/organizations.json` (and `app/data/`)
