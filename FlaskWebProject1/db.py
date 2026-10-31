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
    webhook_url TEXT,
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
    source_document TEXT,
    section TEXT,
    version TEXT DEFAULT '1.0',
    verified INTEGER NOT NULL DEFAULT 1,
    confidence TEXT NOT NULL DEFAULT 'high',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (profile_id) REFERENCES brand_profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS brand_colors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    hex_code TEXT NOT NULL,
    name TEXT,
    is_primary INTEGER NOT NULL DEFAULT 0,
    min_usage_percent REAL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (profile_id) REFERENCES brand_profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS brand_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    asset_type TEXT NOT NULL,
    filename TEXT NOT NULL,
    min_width INTEGER DEFAULT 0,
    min_height INTEGER DEFAULT 0,
    allowed_formats TEXT DEFAULT 'png,jpg,jpeg,svg',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (profile_id) REFERENCES brand_profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'author',
    display_name TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    user_id INTEGER,
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
    confidence TEXT NOT NULL DEFAULT 'medium',
    citation TEXT,
    status TEXT NOT NULL DEFAULT 'Needs Review',
    reviewer_decision TEXT,
    reviewer_notes TEXT,
    decided_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (review_id) REFERENCES reviews(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    message TEXT NOT NULL,
    link TEXT,
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_findings_review ON findings(review_id);
CREATE INDEX IF NOT EXISTS idx_rules_profile ON brand_rules(profile_id);
CREATE INDEX IF NOT EXISTS idx_facts_profile ON brand_facts(profile_id);
CREATE INDEX IF NOT EXISTS idx_colors_profile ON brand_colors(profile_id);
CREATE INDEX IF NOT EXISTS idx_assets_profile ON brand_assets(profile_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
"""


def get_connection():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


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


def _migrate(conn):
    migrations = [
        ("brand_profiles", "webhook_url", "TEXT"),
        ("reviews", "user_id", "INTEGER"),
        ("brand_facts", "source_document", "TEXT"),
        ("brand_facts", "section", "TEXT"),
        ("brand_facts", "version", "TEXT DEFAULT '1.0'"),
        ("brand_facts", "confidence", "TEXT NOT NULL DEFAULT 'high'"),
        ("findings", "confidence", "TEXT NOT NULL DEFAULT 'medium'"),
        ("findings", "citation", "TEXT"),
    ]
    for table, col, typedef in migrations:
        try:
            conn.execute("ALTER TABLE {} ADD COLUMN {} {}".format(table, col, typedef))
        except sqlite3.OperationalError:
            pass


def _seed_colors_assets(cur, profile_id):
    c = cur.execute("SELECT COUNT(*) FROM brand_colors WHERE profile_id = ?", (profile_id,)).fetchone()[0]
    if c and c > 0:
        return
    colors = [
        ("#4F46E5", "Indigo (primary)", 1, 15.0),
        ("#06B6D4", "Cyan (accent)", 0, 5.0),
        ("#10B981", "Emerald (success)", 0, 3.0),
        ("#1E293B", "Slate (text)", 0, 10.0),
    ]
    for hexc, name, primary, pct in colors:
        cur.execute(
            "INSERT INTO brand_colors (profile_id, hex_code, name, is_primary, min_usage_percent) VALUES (?,?,?,?,?)",
            (profile_id, hexc, name, primary, pct),
        )
    assets = [
        ("logo", "brandguard-logo.png", 200, 60, "png,svg"),
        ("banner", "social-banner.png", 1200, 630, "png,jpg,jpeg"),
    ]
    for atype, fname, mw, mh, fmts in assets:
        cur.execute(
            "INSERT INTO brand_assets (profile_id, asset_type, filename, min_width, min_height, allowed_formats) VALUES (?,?,?,?,?,?)",
            (profile_id, atype, fname, mw, mh, fmts),
        )


def init_db():
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    with db_cursor() as cur:
        cur.executescript(SCHEMA)
    conn = get_connection()
    try:
        _migrate(conn)
        conn.commit()
    finally:
        conn.close()
    seed_if_empty()


def row_to_dict(row):
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def seed_if_empty():
    with db_cursor() as cur:
        count = cur.execute("SELECT COUNT(*) FROM brand_profiles").fetchone()[0]
        if count and count > 0:
            for (pid,) in cur.execute("SELECT id FROM brand_profiles").fetchall():
                _seed_colors_assets(cur, pid)
            return

    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO brand_profiles (name, description, is_demo) VALUES (?,?,1)",
            ("Demo Brand (BrandGuard Sample)", "Sample brand profile for hackathon demo. All facts are fictional demo data."),
        )
        profile_id = cur.lastrowid

        rules = [
            ("prohibited_term", "cheap", "affordable", "high", "The word 'cheap' conflicts with the brand's premium positioning.", 0),
            ("prohibited_term", "stuff", "product", "medium", "Use 'product' instead of the informal word 'stuff'.", 0),
            ("prohibited_term", "guys", "team members", "low", "Use inclusive language: 'team members' instead of 'guys'.", 0),
            ("prohibited_term", "obviously", None, "medium", "Avoid 'obviously' because it can sound condescending to readers.", 0),
            ("preferred_term", "BrandGuard AI", None, "low", "Use the approved brand name 'BrandGuard AI' consistently.", 0),
            ("unsupported_claim", "guarantee", None, "high", "Claims of guarantees require legal review and supporting evidence.", 1),
            ("unsupported_claim", "100% effective", None, "critical", "Effectiveness percentages require verified test data and evidence.", 1),
            ("unsupported_claim", "cures", None, "critical", "Medical/health claims require regulatory approval and evidence.", 1),
            ("unsupported_claim", "best in the world", None, "high", "Superlative claims require independent verification and evidence.", 1),
            ("unsupported_claim", "risk-free", None, "high", "'Risk-free' claims require legal review and supporting evidence.", 1),
            ("tone", "!!", None, "medium", "Avoid excessive exclamation marks; they reduce professional tone.", 0),
            ("tone", "ALL_CAPS", None, "medium", "Avoid shouting in ALL CAPS; use sentence case for readability.", 0),
            ("accessibility", "click here", "use a descriptive link such as 'read the brand guidelines'", "medium", "'Click here' is not descriptive and is poor for screen-reader users.", 0),
            ("accessibility", "read more", "describe the destination, e.g. 'read the full brand guidelines'", "low", "Generic 'read more' links lack context for assistive technology.", 0),
        ]
        for rt, pat, repl, sev, expl, ev in rules:
            cur.execute(
                "INSERT INTO brand_rules (profile_id, rule_type, pattern, replacement, severity, explanation, requires_evidence) VALUES (?,?,?,?,?,?,?)",
                (profile_id, rt, pat, repl, sev, expl, ev),
            )

        facts = [
            ("founding_year", "2024", ["founded in (\\\\d{4})", "established in (\\\\d{4})", "since (\\\\d{4})", "founded (\\\\d{4})"], "Demo brand fact (fictional).", "Brand Guidelines v1.2", "Company Overview", "1.2", 1, "high"),
            ("headquarters", "Bengaluru, India", ["headquartered in ([A-Za-z ,]+)", "based in ([A-Za-z ,]+)", "headquarters in ([A-Za-z ,]+)"], "Demo brand fact (fictional).", "Brand Guidelines v1.2", "Company Overview", "1.2", 1, "high"),
            ("product_name", "BrandGuard AI", ["product is ([A-Za-z0-9 ]+)", "our product is ([A-Za-z0-9 ]+)"], "Demo brand fact (fictional).", "Brand Guidelines v1.2", "Product Naming", "1.2", 1, "high"),
        ]
        for key, val, pats, src, doc, section, version, ver, conf in facts:
            cur.execute(
                "INSERT INTO brand_facts (profile_id, fact_key, fact_value, patterns, source, source_document, section, version, verified, confidence) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (profile_id, key, val, json.dumps(pats), src, doc, section, version, ver, conf),
            )

        _seed_colors_assets(cur, profile_id)


def create_user(username, password, role="author", display_name=None):
    from werkzeug.security import generate_password_hash
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, password_hash, role, display_name) VALUES (?,?,?,?)",
            (username, generate_password_hash(password), role, display_name or username),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_user_by_username(username):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


def get_user(user_id):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


def verify_user(username, password):
    from werkzeug.security import check_password_hash
    user = get_user_by_username(username)
    if not user:
        return None
    if check_password_hash(user["password_hash"], password):
        return user
    return None


def list_users():
    conn = get_connection()
    try:
        rows = conn.execute("SELECT id, username, role, display_name, created_at FROM users ORDER BY id").fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        conn.close()


def add_notification(user_id, message, link=None):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO notifications (user_id, message, link) VALUES (?,?,?)", (user_id, message, link))
        conn.commit()
    finally:
        conn.close()


def list_notifications(user_id, unread_only=False):
    conn = get_connection()
    try:
        q = "SELECT * FROM notifications WHERE user_id = ?"
        if unread_only:
            q += " AND is_read = 0"
        q += " ORDER BY id DESC LIMIT 20"
        rows = conn.execute(q, (user_id,)).fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        conn.close()


def unread_notification_count(user_id):
    conn = get_connection()
    try:
        return conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0", (user_id,)).fetchone()[0]
    finally:
        conn.close()


def get_analytics():
    conn = get_connection()
    try:
        total_reviews = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
        total_findings = conn.execute("SELECT COUNT(*) FROM findings").fetchone()[0]
        approved = conn.execute("SELECT COUNT(*) FROM reviews WHERE final_decision = 'approved'").fetchone()[0]
        rejected = conn.execute("SELECT COUNT(*) FROM reviews WHERE final_decision = 'rejected'").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM reviews WHERE final_decision IS NULL").fetchone()[0]
        sev_rows = conn.execute("SELECT severity, COUNT(*) as c FROM findings GROUP BY severity").fetchall()
        sev = {r["severity"]: r["c"] for r in sev_rows}
        type_rows = conn.execute("SELECT issue_type, COUNT(*) as c FROM findings GROUP BY issue_type ORDER BY c DESC").fetchall()
        types = [(r["issue_type"], r["c"]) for r in type_rows]
        status_rows = conn.execute("SELECT status, COUNT(*) as c FROM findings GROUP BY status").fetchall()
        statuses = {r["status"]: r["c"] for r in status_rows}
        prof_rows = conn.execute("SELECT p.name, COUNT(r.id) as c FROM reviews r LEFT JOIN brand_profiles p ON p.id=r.profile_id GROUP BY p.name").fetchall()
        profiles = [(r["name"], r["c"]) for r in prof_rows]
        avg = (total_findings / total_reviews) if total_reviews else 0
        rw_rows = conn.execute("SELECT reviewer_decision, COUNT(*) as c FROM findings WHERE reviewer_decision IS NOT NULL GROUP BY reviewer_decision").fetchall()
        reviewer = {r["reviewer_decision"]: r["c"] for r in rw_rows}
        return {
            "total_reviews": total_reviews,
            "total_findings": total_findings,
            "approved": approved,
            "rejected": rejected,
            "pending": pending,
            "severity": sev,
            "types": types,
            "statuses": statuses,
            "profiles": profiles,
            "avg_findings": round(avg, 2),
            "reviewer": reviewer,
        }
    finally:
        conn.close()


def list_brand_colors(profile_id):
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM brand_colors WHERE profile_id = ? ORDER BY is_primary DESC, id", (profile_id,)).fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        conn.close()


def list_brand_assets(profile_id):
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM brand_assets WHERE profile_id = ? ORDER BY id", (profile_id,)).fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        conn.close()


def list_profiles():
    conn = get_connection()
    try:
        rows = conn.execute("SELECT id, name, description, is_demo, created_at, webhook_url FROM brand_profiles ORDER BY id").fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        conn.close()