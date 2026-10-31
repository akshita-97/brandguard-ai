"""Helper script to add a new brand profile to BrandGuard AI.

Edit the values below, then run:
    python add_brand_profile.py

The new profile appears in the app immediately (refresh the page).
"""

import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from FlaskWebProject1.db import get_connection

# ---------- EDIT THESE VALUES ----------
PROFILE_NAME = "Acme Corp (Sample)"
PROFILE_DESCRIPTION = "Custom brand profile added by you. Edit this script to change rules."

# Each rule: (rule_type, pattern, replacement or None, severity, explanation, requires_evidence 0/1)
RULES = [
    ("prohibited_term", "cheap", "cost-effective", "high",
     "Acme avoids 'cheap'; use 'cost-effective'.", 0),
    ("prohibited_term", "stuff", "product", "medium",
     "Use 'product' instead of 'stuff'.", 0),
    ("unsupported_claim", "guaranteed", None, "high",
     "Guarantee claims need legal review.", 1),
    ("accessibility", "click here", "use a descriptive link", "medium",
     "'Click here' is not accessible.", 0),
    ("tone", "!!", None, "medium", "Avoid excessive exclamation marks.", 0),
]

# Each fact: (fact_key, fact_value, [regex patterns], source, verified 0/1)
FACTS = [
    ("founding_year", "2019",
     ["founded in (\\d{4})", "established in (\\d{4})", "since (\\d{4})"],
     "Your approved source.", 1),
    ("headquarters", "Mumbai, India",
     ["headquartered in ([A-Za-z ,]+)", "based in ([A-Za-z ,]+)"],
     "Your approved source.", 1),
]
# --------------------------------------

conn = get_connection()
cur = conn.cursor()
cur.execute("INSERT INTO brand_profiles (name, description, is_demo) VALUES (?,?,0)",
            (PROFILE_NAME, PROFILE_DESCRIPTION))
profile_id = cur.lastrowid

for rt, pat, repl, sev, expl, ev in RULES:
    cur.execute(
        """INSERT INTO brand_rules
           (profile_id, rule_type, pattern, replacement, severity, explanation, requires_evidence)
           VALUES (?,?,?,?,?,?,?)""",
        (profile_id, rt, pat, repl, sev, expl, ev),
    )

for key, val, pats, src, ver in FACTS:
    cur.execute(
        """INSERT INTO brand_facts
           (profile_id, fact_key, fact_value, patterns, source, verified)
           VALUES (?,?,?,?,?,?)""",
        (profile_id, key, val, json.dumps(pats), src, ver),
    )

# Default brand colours and assets
for hexc, name, primary, pct in [("#4F46E5","Primary",1,15.0),("#06B6D4","Accent",0,5.0)]:
    cur.execute("INSERT INTO brand_colors (profile_id, hex_code, name, is_primary, min_usage_percent) VALUES (?,?,?,?,?)",
                (profile_id, hexc, name, primary, pct))
for atype, fname, mw, mh, fmts in [("logo","logo.png",200,60,"png,svg")]:
    cur.execute("INSERT INTO brand_assets (profile_id, asset_type, filename, min_width, min_height, allowed_formats) VALUES (?,?,?,?,?,?)",
                (profile_id, atype, fname, mw, mh, fmts))

conn.commit()
conn.close()
print(f"Added profile '{PROFILE_NAME}' with id {profile_id}.")
print("Refresh the app page to see it in the dropdown.")
