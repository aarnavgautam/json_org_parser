# UF Organizations Directory

Searchable directory of 1,000+ UF student organizations. Filter, select, export contacts, and track outreach.

## Deploy on Vercel (recommended)

1. Push this repo to GitHub
2. Import the project in [Vercel](https://vercel.com)
3. Deploy — Vercel runs `build_data.py` and serves the app
4. Share the live link with coworkers

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
- **Outreach tracking** — Per org: "Got response" flag, "Reached out" counter (saved in browser)

## Source files

- `final_organizations.json` — GatorConnect data
- `ignite_innovation_filtered_orgs.csv` — Innovation ratings
- `build_data.py` — Merges to `data/organizations.json` (and `app/data/`)
