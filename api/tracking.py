"""
Team-wide outreach tracking via Vercel KV (Upstash Redis) or Google Sheets.
- KV: Create KV database in Vercel Dashboard → Storage → Connect to project.
- Google Sheets: Set GOOGLE_SHEET_TRACKING_URL to a published CSV URL. Edit the
  sheet manually; the app reads from it and refreshes periodically.
"""
import csv
import json
import os
from io import StringIO
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from http.server import BaseHTTPRequestHandler

KEY = "uf-orgs-tracking"


def get_tracking_from_sheet():
    """Fetch tracking data from a published Google Sheet CSV. Returns None if not configured or on error."""
    url = os.environ.get("GOOGLE_SHEET_TRACKING_URL")
    if not url or not url.strip():
        return None
    try:
        req = Request(url.strip(), headers={"User-Agent": "UF-Orgs-Tracker/1.0"})
        with urlopen(req, timeout=15) as r:
            raw = r.read().decode("utf-8", errors="replace")
    except (URLError, HTTPError, OSError):
        return None
    try:
        reader = csv.DictReader(StringIO(raw))
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
        if not rows or not fieldnames:
            return {}
        # Find columns (flexible naming)
        col_org = None
        col_response = None
        col_count = None
        for fn in fieldnames:
            h = (fn or "").strip().lower().replace(" ", "").replace("_", "")
            if h in ("organizationid", "orgid", "id"):
                col_org = fn
            elif "response" in h or h == "gotresponse":
                col_response = fn
            elif h in ("outreachcount", "reachedout", "reachedoutcount", "contacted") or "outreach" in h or "reached" in h:
                col_count = fn
        if col_org is None:
            col_org = fieldnames[0]
        if col_response is None:
            for fn in fieldnames:
                if "response" in (fn or "").lower():
                    col_response = fn
                    break
        if col_count is None:
            for fn in fieldnames:
                if "out" in (fn or "").lower() or "reach" in (fn or "").lower() or "contact" in (fn or "").lower():
                    col_count = fn
                    break
        out = {}
        for row in rows:
            org_id = str((row.get(col_org) or "").strip())
            if not org_id:
                continue
            got_response = False
            rv = (row.get(col_response) or "").strip().lower()
            if rv in ("y", "yes", "1", "true", "x", "✓", "✔"):
                got_response = True
            count = 0
            if col_count:
                try:
                    count = max(0, int(float((row.get(col_count) or "0").strip())))
                except (ValueError, TypeError):
                    pass
            out[org_id] = {"gotResponse": got_response, "outreachCount": count}
        return out
    except (csv.Error, ValueError, KeyError):
        return None


def kv_command(cmd):
    """Send command to Upstash Redis REST API. Supports both Vercel KV and Upstash env var names."""
    url = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    if not url or not token:
        return None
    try:
        body = json.dumps(cmd).encode("utf-8")
        req = Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
            return data.get("result")
    except (URLError, HTTPError, ValueError, OSError):
        return None


def get_tracking():
    raw = kv_command(["GET", KEY])
    if raw is None:
        return None
    try:
        return json.loads(raw) if raw else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def set_tracking(data):
    return kv_command(["SET", KEY, json.dumps(data)]) is not None


def _get_tracking():
    """Get tracking data from Google Sheet only."""
    sheet = get_tracking_from_sheet()
    if sheet is not None:
        return sheet, "sheet"
    return {}, "none"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        data, source = _get_tracking()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        out = dict(data)
        out["_source"] = "google-sheet"
        url = os.environ.get("GOOGLE_SHEET_TRACKING_URL", "").strip()
        if url:
            base = url.split("?")[0].rstrip("/")
            if "/pub" in base:
                base = base.split("/pub")[0]
            elif "/export" in base:
                base = base.split("/export")[0]
            out["_sheetLink"] = base + "/edit"
        self.wfile.write(json.dumps(out).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_PATCH(self):
        self.send_response(501)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(
            json.dumps({"error": "Tracking is read-only from Google Sheet. Update the sheet directly."}).encode("utf-8")
        )
        return

