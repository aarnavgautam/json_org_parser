"""
UF Organizations Directory - Backend
Run: python app.py (or flask run from app directory)
"""
import json
import os
from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path

app = Flask(__name__, static_folder="static", static_url_path="")
DATA_PATH = Path(__file__).parent / "data" / "organizations.json"


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
    """position_filter: Presidents only, Vice Presidents, Recruitment/Outreach, All, or comma-separated"""
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
    """Custom free-text filter - user can add their own search terms"""
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
    """Return only officers matching the position filter."""
    if not position_filter or position_filter.lower() == "all":
        return org.get("Officers", [])

    wanted = [p.strip().lower() for p in position_filter.split(",")]
    result = []
    for officer in org.get("Officers", []):
        pt = (officer.get("PositionType") or "").lower()
        if pt in wanted:
            result.append(officer)
    return result


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/organizations")
def api_organizations():
    data = load_data()

    search = request.args.get("search", "").strip()
    position = request.args.get("position", "").strip()
    innovation_fit = request.args.get("innovation_fit", "").strip()
    category = request.args.get("category", "").strip()
    custom_filter = request.args.get("custom_filter", "").strip()

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

    return jsonify({"organizations": results, "total": len(results)})


@app.route("/api/filters")
def api_filters():
    data = load_data()
    categories = set()
    innovation_fits = set()
    for org in data:
        categories.update(org.get("Categories", []))
        if org.get("InnovationFit"):
            innovation_fits.add(org["InnovationFit"])
    return jsonify({
        "categories": sorted(categories),
        "innovation_fits": sorted(innovation_fits),
    })


def filter_officers_for_export(org, positions_set):
    if not positions_set or "all" in positions_set:
        return [o for o in org.get("Officers", []) if o.get("Email")]
    return [
        o for o in org.get("Officers", [])
        if (o.get("PositionType") or "other").lower() in positions_set and o.get("Email")
    ]


@app.route("/api/export", methods=["GET", "POST"])
def api_export():
    import csv
    import io

    if request.method == "POST":
        data = request.get_json() or {}
    else:
        data = {k: (v[0] if isinstance(v, list) else v) for k, v in request.args.to_dict(flat=False).items()}
        if data.get("orgIds") and isinstance(data["orgIds"], str):
            data["orgIds"] = data["orgIds"].split(",")
        if data.get("positions") and isinstance(data["positions"], str):
            data["positions"] = [p.strip() for p in data["positions"].split(",") if p.strip()]

    org_ids = set(str(x) for x in data.get("orgIds", []))
    positions = data.get("positions", [])
    positions_set = set(p.strip().lower() for p in positions) if positions else {"all"}

    orgs_data = load_data()
    org_by_id = {str(o["OrganizationId"]): o for o in orgs_data}

    rows = []
    for oid in org_ids:
        org = org_by_id.get(oid)
        if not org:
            continue
        for o in filter_officers_for_export(org, positions_set):
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

    from flask import Response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": 'attachment; filename="org_contacts_export.csv"'},
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5555, debug=True)
