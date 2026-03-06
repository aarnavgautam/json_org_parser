import json
import os
from urllib.parse import urlparse
from http.server import BaseHTTPRequestHandler

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "organizations.json")


def load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
            data = load_data()
            categories = set()
            innovation_fits = set()
            for org in data:
                categories.update(org.get("Categories", []))
                if org.get("InnovationFit"):
                    innovation_fits.add(org["InnovationFit"])

            body = json.dumps({
                "categories": sorted(categories),
                "innovation_fits": sorted(innovation_fits),
            })
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
