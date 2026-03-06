import json
import os
import csv
import io
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "organizations.json")


def load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def filter_officers(org, positions_set):
    if not positions_set or "all" in positions_set:
        return org.get("Officers", [])
    return [
        o for o in org.get("Officers", [])
        if (o.get("PositionType") or "other").lower() in positions_set and o.get("Email")
    ]


def build_csv(org_ids, positions_set, org_by_id):
    rows = []
    for oid in org_ids:
        org = org_by_id.get(oid)
        if not org:
            continue
        officers = filter_officers(org, positions_set)
        for o in officers:
            if o.get("Email"):
                rows.append({
                    "OrganizationName": org.get("OrganizationName", ""),
                    "OfficerName": o.get("Name", ""),
                    "Position": o.get("Position", ""),
                    "Email": o.get("Email", ""),
                })
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["OrganizationName", "OfficerName", "Position", "Email"])
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {}

        org_ids = set(str(x) for x in data.get("orgIds", []))
        positions = data.get("positions", [])
        if isinstance(positions, str):
            positions = [p.strip().lower() for p in positions.split(",") if p.strip()]
        else:
            positions = [str(p).strip().lower() for p in positions if p]
        positions_set = set(positions) if positions else {"all"}

        orgs_data = load_data()
        org_by_id = {str(o["OrganizationId"]): o for o in orgs_data}
        csv_content = build_csv(org_ids, positions_set, org_by_id)

        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="org_contacts_export.csv"')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(csv_content.encode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        org_ids = params.get("orgIds", [])
        if org_ids:
            org_ids = org_ids[0].split(",")
        positions = params.get("positions", [])
        if positions:
            positions = [p.strip().lower() for p in positions[0].split(",") if p.strip()]
        else:
            positions = ["all"]

        orgs_data = load_data()
        org_by_id = {str(o["OrganizationId"]): o for o in orgs_data}
        positions_set = set(positions)
        csv_content = build_csv([i.strip() for i in org_ids], positions_set, org_by_id)

        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="org_contacts_export.csv"')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(csv_content.encode("utf-8"))
