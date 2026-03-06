#!/usr/bin/env python3
"""
Build script: merges source data and derives categories.
Run this when source files change. Output: app/data/organizations.json
"""
import json
import csv
import re
import os

# Category keywords (match against org name + description)
CATEGORY_RULES = [
    ("Design", ["design", "graphic design", "ux", "ui", "product design", "creative", "art direction"]),
    ("Tech", ["tech", "coding", "programming", "software", "computer science", "ai ", "machine learning", "data science", "hackathon", "hack ", "cyber"]),
    ("Business", ["business", "consulting", "finance", "management", "entrepreneurship", "private equity", "investment"]),
    ("Engineering", ["engineering", "design team", "design/build", "aerospace", "robotics", "mechanical", "electrical", "civil"]),
    ("Cultural", ["student association", "cultural", "culture", "heritage", "international", "bhm", "latino", "asian", "african", "indian", "japanese", "chinese", "korean", "vietnamese", "caribbean", "hispanic", "middle east"]),
    ("Arts & Performance", ["a cappella", "dance", "ballet", "music", "theatre", "theater", "choir", "orchestra", "jazz"]),
    ("Pre-Professional", ["pre-med", "pre-law", "pharmacy", "pre-health", "pre-dental", "pre-vet"]),
    ("Greek", ["fraternity", "sorority", "alpha ", "beta ", "gamma ", "delta ", "sigma ", "phi ", "theta ", "kappa ", "chi ", "omega ", "psi ", "zeta "]),
    ("Sports & Recreation", ["sport", "athletic", "fitness", "club team", "intramural", "soccer", "basketball", "tennis", "swimming"]),
    ("Service & Community", ["service", "volunteer", "community", "outreach", "philanthropy"]),
]

def get_position_type(position):
    """Categorize officer position for filtering."""
    p = (position or "").lower()
    if "president" in p and "vice" not in p:
        return "President"
    if "vice president" in p or p.startswith("vp "):
        return "Vice President"
    if any(kw in p for kw in ["recruit", "outreach", "external", "liaison", "relations"]):
        return "Recruitment/Outreach"
    return "Other"

def derive_categories(name, description):
    """Derive category tags from org name and description."""
    text = f"{(name or '')} {(description or '')}".lower()
    tags = []
    for tag, keywords in CATEGORY_RULES:
        if any(kw in text for kw in keywords):
            tags.append(tag)
    return tags if tags else ["Other"]

def main():
    base = os.path.dirname(os.path.abspath(__file__))
    orgs_path = os.path.join(base, "final_organizations.json")
    ignite_path = os.path.join(base, "ignite_innovation_filtered_orgs.csv")
    # Load organizations
    with open(orgs_path, "r", encoding="utf-8") as f:
        orgs = json.load(f)

    # Load innovation metadata
    innovation_by_id = {}
    try:
        with open(ignite_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                oid = row.get("OrganizationId", "").strip()
                if oid:
                    innovation_by_id[oid] = {
                        "innovation_fit": row.get("innovation_fit", "").strip(),
                        "roundtable_recommended": row.get("roundtable_recommended", "").strip(),
                        "why_innovation_relevant": row.get("why_innovation_relevant", "").strip(),
                    }
    except FileNotFoundError:
        pass

    # Enrich each organization
    enriched = []
    for org in orgs:
        oid = str(org.get("OrganizationId", ""))
        name = org.get("OrganizationName", "")
        desc = org.get("OrganizationDescription", "")
        officers = org.get("Officers", [])

        innovation = innovation_by_id.get(oid, {})

        # Add position type to each officer
        officers_with_type = []
        for o in officers:
            o = dict(o)
            o["PositionType"] = get_position_type(o.get("Position", ""))
            officers_with_type.append(o)

        enriched.append({
            "OrganizationId": org.get("OrganizationId"),
            "OrganizationName": name,
            "OrganizationDescription": desc or "",
            "Categories": derive_categories(name, desc),
            "InnovationFit": innovation.get("innovation_fit", ""),
            "RoundtableRecommended": innovation.get("roundtable_recommended", ""),
            "WhyInnovationRelevant": innovation.get("why_innovation_relevant", ""),
            "Officers": officers_with_type,
        })

    for out_dir in [
        os.path.join(base, "app", "data"),
        os.path.join(base, "data"),
    ]:
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "organizations.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(enriched, f, ensure_ascii=False, indent=0)
        print(f"Built {out_path} with {len(enriched)} organizations.")

if __name__ == "__main__":
    main()
