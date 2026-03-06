import json
import os
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "organizations.json")


def load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def matches_search(org, query):
    if not query or not query.strip():
        return True
    q = query.lower().strip()
    name = (org.get("OrganizationName") or "").lower()
    desc = (org.get("OrganizationDescription") or "").lower()
    if q in name or q in desc:
        return True
    for officer in org.get("Officers", []):
        officer_name = (officer.get("Name") or "").lower()
        officer_email = (officer.get("Email") or "").lower()
        if q in officer_name or q in officer_email:
            return True
    return False


def matches_position_filter(org, position_filter):
    if not position_filter or position_filter.lower() == "all":
        return True
    wanted = [p.strip().lower() for p in position_filter.split(",")]
    for officer in org.get("Officers", []):
        pt = (officer.get("PositionType") or "").lower()
        if pt in wanted:
            return True
    return False


def _parse_multi_values(raw):
    if not raw:
        return []
    values = []
    for v in raw.split(","):
        t = v.strip().lower()
        if t and t != "any":
            values.append(t)
    return values


def matches_innovation_filter(org, innovation_filter):
    wanted = _parse_multi_values(innovation_filter)
    if not wanted:
        return True
    fit = (org.get("InnovationFit") or "").lower()
    return fit in wanted


def matches_category_filter(org, category_filter):
    wanted = set(_parse_multi_values(category_filter))
    if not wanted:
        return True
    cats = {(c or "").lower() for c in org.get("Categories", [])}
    return bool(cats.intersection(wanted))


def matches_custom_filter(org, custom_query):
    if not custom_query or not custom_query.strip():
        return True
    q = custom_query.lower().strip()
    name = (org.get("OrganizationName") or "").lower()
    desc = (org.get("OrganizationDescription") or "").lower()
    cats = " ".join(org.get("Categories", [])).lower()
    for officer in org.get("Officers", []):
        pos = (officer.get("Position") or "").lower()
        officer_name = (officer.get("Name") or "").lower()
        officer_email = (officer.get("Email") or "").lower()
        if q in name or q in desc or q in cats or q in pos or q in officer_name or q in officer_email:
            return True
    return False


def filter_officers(org, position_filter):
    if not position_filter or position_filter.lower() == "all":
        return org.get("Officers", [])
    wanted = [p.strip().lower() for p in position_filter.split(",")]
    return [o for o in org.get("Officers", []) if (o.get("PositionType") or "").lower() in wanted]


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        search = (params.get("search", [""])[0] or "").strip()
        position = (params.get("position", [""])[0] or "").strip()
        innovation_fit = (params.get("innovation_fit", [""])[0] or "").strip()
        category = (params.get("category", [""])[0] or "").strip()
        custom_filter = (params.get("custom_filter", [""])[0] or "").strip()

        data = load_data()
        results = []
        for org in data:
            if not matches_search(org, search):
                continue
            if not matches_position_filter(org, position):
                continue
            if not matches_innovation_filter(org, innovation_fit):
                continue
            if not matches_category_filter(org, category):
                continue
            if not matches_custom_filter(org, custom_filter):
                continue

            officers = filter_officers(org, position)
            if position and position.lower() != "all" and not officers:
                continue

            results.append({
                **{k: v for k, v in org.items() if k != "Officers"},
                "Officers": officers if officers else org.get("Officers", []),
            })

        body = json.dumps({"organizations": results, "total": len(results)})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))
