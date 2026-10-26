"""
Routes and views for the Flask application.
"""

import os
import secrets
from datetime import datetime

from flask import (
    Flask, render_template, request, jsonify, session, abort,
)

from FlaskWebProject1 import app
from FlaskWebProject1.config import Config
from FlaskWebProject1.db import get_connection, row_to_dict, list_profiles
from FlaskWebProject1.engine import check_content, load_profile
from FlaskWebProject1.ai_service import enhance, is_enabled


# ---------- CSRF (lightweight) ----------
def _csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


@app.before_request
def _csrf_protect():
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    if request.path == "/health":
        return
    token = request.headers.get("X-CSRFToken") or request.form.get("csrf_token")
    if not token or token != session.get("csrf_token"):
        abort(400, description="Invalid or missing CSRF token.")


@app.context_processor
def _inject_globals():
    return {
        "csrf_token": _csrf_token(),
        "ai_enabled": is_enabled(),
        "year": datetime.now().year,
    }


def _json_error(message, status=400):
    return jsonify({"error": message}), status


# ---------- Pages ----------
@app.route("/")
@app.route("/home")
def home():
    profiles = list_profiles()
    return render_template("index.html", title="BrandGuard AI", profiles=profiles, year=datetime.now().year)


@app.route("/guidelines")
def guidelines():
    profiles = list_profiles()
    selected_id = request.args.get("profile_id", type=int)
    if selected_id is None and profiles:
        selected_id = profiles[0]["id"]
    data = load_profile(selected_id) if selected_id else None
    return render_template("guidelines.html", title="Brand Guidelines", profiles=profiles,
                          selected_id=selected_id, data=data, year=datetime.now().year)


@app.route("/history")
def history_page():
    return render_template("history.html", title="Review History", year=datetime.now().year)


@app.route("/about")
def about():
    return render_template("about.html", title="About", year=datetime.now().year,
                          message="BrandGuard AI helps organizations check content before publication.")


@app.route("/contact")
def contact():
    return render_template("contact.html", title="Contact", year=datetime.now().year,
                          message="Contact the project team.")


# ---------- API ----------
@app.route("/health")
def health():
    return jsonify({"status": "ok", "ai_enabled": is_enabled()})


@app.route("/api/profiles", methods=["GET"])
def api_profiles():
    return jsonify({"profiles": list_profiles()})


@app.route("/api/check", methods=["POST"])
def api_check():
    payload = request.get_json(silent=True) or {}
    content = (payload.get("content") or "").strip()
    profile_id = payload.get("profile_id")

    if not content:
        return _json_error("Content is required.")
    if len(content) > Config.CONTENT_MAX_CHARS:
        return _json_error(f"Content exceeds {Config.CONTENT_MAX_CHARS} characters.")
    try:
        profile_id = int(profile_id)
    except (TypeError, ValueError):
        return _json_error("A valid brand profile is required.")

    profile = load_profile(profile_id)
    if not profile:
        return _json_error("Brand profile not found.", 404)

    try:
        result = check_content(profile_id, content)
    except Exception as e:
        return _json_error(f"Review failed: {str(e)}", 500)

    ai_result = enhance(content, result["findings"])
    result["findings"] = ai_result["findings"]
    result["total_issues"] = len(result["findings"])
    if not result["findings"]:
        result["overall_status"] = "Passed"
    ai_used = bool(ai_result["ai_used"])

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO reviews (profile_id, content, overall_status, total_issues, ai_used)
               VALUES (?,?,?,?,?)""",
            (profile_id, content, result["overall_status"], result["total_issues"], 1 if ai_used else 0),
        )
        review_id = cur.lastrowid
        for f in result["findings"]:
            cur.execute(
                """INSERT INTO findings
                   (review_id, original_text, issue_type, severity, explanation,
                    rule_reference, suggested_correction, requires_evidence, status)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (review_id, f["original_text"], f["issue_type"], f["severity"],
                 f["explanation"], f.get("rule_reference"), f.get("suggested_correction"),
                 1 if f.get("requires_evidence") else 0, f.get("status", "Needs Review")),
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        return _json_error(f"Failed to save review: {str(e)}", 500)
    finally:
        conn.close()

    return jsonify({
        "review_id": review_id,
        "profile_id": profile_id,
        "profile_name": profile["profile"]["name"],
        "overall_status": result["overall_status"],
        "total_issues": result["total_issues"],
        "ai_used": ai_used,
        "findings": result["findings"],
        "created_at": datetime.now().isoformat(timespec="seconds"),
    })


@app.route("/api/review/<int:review_id>", methods=["GET"])
def api_get_review(review_id):
    conn = get_connection()
    try:
        review = conn.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
        if not review:
            return _json_error("Review not found.", 404)
        findings = conn.execute(
            "SELECT * FROM findings WHERE review_id = ? ORDER BY id", (review_id,)
        ).fetchall()
        profile = conn.execute(
            "SELECT name FROM brand_profiles WHERE id = ?", (review["profile_id"],)
        ).fetchone()
        return jsonify({
            "review": row_to_dict(review),
            "profile_name": profile["name"] if profile else "",
            "findings": [row_to_dict(f) for f in findings],
        })
    finally:
        conn.close()


@app.route("/api/finding/<int:finding_id>/decision", methods=["POST"])
def api_finding_decision(finding_id):
    payload = request.get_json(silent=True) or {}
    decision = (payload.get("decision") or "").strip().lower()
    notes = (payload.get("notes") or "").strip()
    allowed = {"accepted", "rejected", "resolved", "needs_review"}
    if decision not in allowed:
        return _json_error(f"Decision must be one of: {', '.join(sorted(allowed))}.")
    if len(notes) > 1000:
        return _json_error("Notes too long.")

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM findings WHERE id = ?", (finding_id,))
        if not cur.fetchone():
            return _json_error("Finding not found.", 404)
        status_map = {
            "accepted": "Accepted",
            "rejected": "Rejected",
            "resolved": "Resolved",
            "needs_review": "Needs Review",
        }
        cur.execute(
            """UPDATE findings SET reviewer_decision = ?, reviewer_notes = ?,
               status = ?, decided_at = datetime('now') WHERE id = ?""",
            (decision, notes, status_map[decision], finding_id),
        )
        conn.commit()
        return jsonify({"ok": True, "finding_id": finding_id, "decision": decision, "status": status_map[decision]})
    except Exception as e:
        conn.rollback()
        return _json_error(f"Failed: {str(e)}", 500)
    finally:
        conn.close()


@app.route("/api/review/<int:review_id>/finalize", methods=["POST"])
def api_finalize(review_id):
    payload = request.get_json(silent=True) or {}
    decision = (payload.get("decision") or "").strip().lower()
    notes = (payload.get("notes") or "").strip()
    if decision not in {"approved", "rejected"}:
        return _json_error("Final decision must be 'approved' or 'rejected'.")
    if len(notes) > 2000:
        return _json_error("Notes too long.")

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM reviews WHERE id = ?", (review_id,))
        if not cur.fetchone():
            return _json_error("Review not found.", 404)
        cur.execute(
            """UPDATE reviews SET final_decision = ?, final_notes = ?, decided_at = datetime('now')
               WHERE id = ?""",
            (decision, notes, review_id),
        )
        conn.commit()
        return jsonify({"ok": True, "review_id": review_id, "final_decision": decision})
    except Exception as e:
        conn.rollback()
        return _json_error(f"Failed: {str(e)}", 500)
    finally:
        conn.close()


@app.route("/api/history", methods=["GET"])
def api_history():
    limit = request.args.get("limit", default=25, type=int)
    limit = max(1, min(limit, 100))
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT r.id, r.profile_id, r.overall_status, r.total_issues, r.ai_used,
                      r.final_decision, r.created_at, r.decided_at, p.name AS profile_name
               FROM reviews r LEFT JOIN brand_profiles p ON p.id = r.profile_id
               ORDER BY r.id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return jsonify({"reviews": [row_to_dict(r) for r in rows]})
    finally:
        conn.close()


# ---------- Error handlers ----------
@app.errorhandler(400)
def _bad_request(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": getattr(e, "description", "Bad request")}), 400
    return render_template("error.html", title="Error", message=getattr(e, "description", "Bad request"),
                          year=datetime.now().year), 400


@app.errorhandler(404)
def _not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found"}), 404
    return render_template("error.html", title="Error", message="Page not found.", year=datetime.now().year), 404


@app.errorhandler(413)
def _too_large(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Request too large."}), 413
    return render_template("error.html", title="Error", message="Request too large.", year=datetime.now().year), 413
