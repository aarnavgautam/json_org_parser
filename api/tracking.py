"""
Team-wide outreach tracking via Vercel KV (Upstash Redis).
Requires: Create KV database in Vercel Dashboard → Storage → Connect to project.
"""
import json
import os
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from http.server import BaseHTTPRequestHandler

KEY = "uf-orgs-tracking"


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


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        data = get_tracking()
        if data is None:
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(
                json.dumps({"error": "KV not configured"}).encode("utf-8")
            )
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_PATCH(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(
                json.dumps({"error": "Bad request"}).encode("utf-8")
            )
            return
        try:
            body = self.rfile.read(content_length).decode("utf-8")
            updates = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(
                json.dumps({"error": "Invalid JSON"}).encode("utf-8")
            )
            return

        current = get_tracking()
        if current is None:
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(
                json.dumps({"error": "KV not configured"}).encode("utf-8")
            )
            return

        for org_id, v in updates.items():
            org_id = str(org_id)
            if org_id and isinstance(v, dict):
                existing = current.get(org_id, {})
                current[org_id] = {
                    "gotResponse": v.get("gotResponse", existing.get("gotResponse", False)),
                    "outreachCount": v.get("outreachCount", existing.get("outreachCount", 0)),
                }

        if not set_tracking(current):
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(
                json.dumps({"error": "Failed to save"}).encode("utf-8")
            )
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(current).encode("utf-8"))
