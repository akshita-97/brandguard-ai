"""SQLite database helpers and schema management for BrandGuard AI."""

import json
import os
import sqlite3
from contextlib import contextmanager

from .config import Config

SCHEMA = """
CREATE TABLE IF NOT EXISTS brand_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_demo INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS brand_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    rule_type TEXT NOT NULL,
    pattern TEXT NOT NULL,
    replacement TEXT,
    severity TEXT NOT NULL DEFAULT 'medium',
    explanation TEXT NOT NULL,
    requires_evidence INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (profile_id) REFERENCES brand_profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS brand_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    fact_key TEXT NOT NULL,
    fact_value TEXT NOT NULL,
    patterns TEXT NOT NULL DEFAULT '[]',
    source TEXT,
    verified INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (profile_id) REFERENCES brand_profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    overall_status TEXT NOT NULL,
    total_issues INTEGER NOT NULL DEFAULT 0,
    ai_used INTEGER NOT NULL DEFAULT 0,
    final_decision TEXT,
    final_notes TEXT,
    decided_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (profile_id) REFERENCES brand_profiles(id)
);

CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id INTEGER NOT NULL,
    original_text TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    explanation TEXT NOT NULL,
    rule_reference TEXT,
    suggested_correction TEXT,
    requires_evidence INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'Needs Review',
    reviewer_decision TEXT,
    reviewer_notes TEXT,
    decided_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (review_id) REFERENCES reviews(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_findings_review ON findings(review_id);
CREATE INDEX IF NOT EXISTS idx_rules_profile ON brand_rules(profile_id);
CREATE INDEX IF NOT EXISTS idx_facts_profile ON brand_facts(profile_id);
"""


def get_connection():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


class _CursorCtx:
    pass


from contextlib import contextmanager


@contextmanager
def db_cursor():
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    with db_cursor() as cur:
        cur.executescript(SCHEMA)
    seed_if_empty()


def row_to_dict(row):
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def seed_if_empty():
    with db_cursor() as cur:
        count = cur.execute("SELECT COUNT(*) FROM brand_profiles").fetchone()[0]
        if count and count > 0:
            return
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO brand_profiles (name, description, is_demo) VALUES (?,?,1)",
            ("Demo Brand (BrandGuard Sample)", "Sample brand profile for hackathon demo. All facts are fictional demo data."),
        )
        profile_id = cur.lastrowid

        rules = [
            ("prohibited_term", "cheap", "affordable", "high",
             "The word 'cheap' conflicts with the brand's premium positioning.", 0),
            ("prohibited_term", "stuff", "product", "medium",
             "Use 'product' instead of the informal word 'stuff'.", 0),
            ("prohibited_term", "guys", "team members", "low",
             "Use inclusive language: 'team members' instead of 'guys'.", 0),
            ("prohibited_term", "obviously", None, "medium",
             "Avoid 'obviously' because it can sound condescending to readers.", 0),
            ("preferred_term", "BrandGuard AI", None, "low",
             "Use the approved brand name 'BrandGuard AI' consistently.", 0),
            ("unsupported_claim", "guaranteed", None, "high",
             "Claims of guarantees require legal review and supporting evidence.", 1),
            ("unsupported_claim", "100% effective", None, "critical",
             "Effectiveness percentages require verified test data and evidence.", 1),
            ("unsupported_claim", "cures", None, "critical",
             "Medical/health claims require regulatory approval and evidence.", 1),
            ("unsupported_claim", "best in the world", None, "high",
             "Superlative claims require independent verification and evidence.", 1),
            ("unsupported_claim", "risk-free", None, "high",
             "'Risk-free' claims require legal review and supporting evidence.", 1),
            ("tone", "!!", None, "medium",
             "Avoid excessive exclamation marks; they reduce professional tone.", 0),
            ("tone", "ALL_CAPS", None, "medium",
             "Avoid shouting in ALL CAPS; use sentence case for readability.", 0),
            ("accessibility", "click here", "use a descriptive link such as 'read the brand guidelines'", "medium",
             "'Click here' is not descriptive and is poor for screen-reader users.", 0),
            ("accessibility", "read more", "describe the destination, e.g. 'read the full brand guidelines'", "low",
             "Generic 'read more' links lack context for assistive technology.", 0),
        ]
        for rt, pat, repl, sev, expl, ev in rules:
            cur.execute(
                """INSERT INTO brand_rules
                   (profile_id, rule_type, pattern, replacement, severity, explanation, requires_evidence)
                   VALUES (?,?,?,?,?,?,?)""",
                (profile_id, rt, pat, repl, sev, expl, ev),
            )

        facts = [
            ("founding_year", "2024",
             ["founded in (\\d{4})", "established in (\\d{4})", "since (\\d{4})", "founded (\\d{4})"],
             "Demo brand fact (fictional).", 1),
            ("headquarters", "Bengaluru, India",
             ["headquartered in ([A-Za-z ,]+)", "based in ([A-Za-z ,]+)", "headquarters in ([A-Za-z ,]+)"],
             "Demo brand fact (fictional).", 1),
            ("product_name", "BrandGuard AI",
             ["product is ([A-Za-z0-9 ]+)", "our product ([A-Za-z0-9 ]+)"],
             "Demo brand fact (fictional).", 1),
        ]
        for key, val, pats, src, ver in facts:
            cur.execute(
                """INSERT INTO brand_facts
                   (profile_id, fact_key, fact_value, patterns, source, verified)
                   VALUES (?,?,?,?,?,?)""",
                (profile_id, key, val, json.dumps(pats), src, ver),
            )


def list_profiles():
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, name, description, is_demo, created_at FROM brand_profiles ORDER BY id"
        ).fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        conn.close()
