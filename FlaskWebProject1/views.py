"""
Routes and views for the Flask application.
"""

import os
import secrets
from datetime import datetime

from flask import (
    Flask, render_template, request, jsonify, session, abort, redirect, url_for,
)

from FlaskWebProject1 import app
from FlaskWebProject1.config import Config
from FlaskWebProject1.db import (get_connection, row_to_dict, list_profiles,
    create_user, get_user, verify_user, get_user_by_username, list_users,
    add_notification, list_notifications, unread_notification_count, get_analytics,
    list_brand_colors, list_brand_assets)
from FlaskWebProject1.engine import check_content, load_profile
from FlaskWebProject1.ai_service import enhance, is_enabled
from FlaskWebProject1.visual_service import check_image


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


def _current_user():
    uid = session.get("user_id")
    if uid:
        return get_user(uid)
    return None


@app.context_processor
def _inject_globals():
    uid = session.get("user_id")
    unread = unread_notification_count(uid) if uid else 0
    return {
        "csrf_token": _csrf_token(),
        "ai_enabled": is_enabled(),
        "year": datetime.now().year,
        "current_user": _current_user(),
        "unread_count": unread,
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


# ---------- Auth (Improvement 3) ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html", title="Register", year=datetime.now().year)
    data = request.get_json(silent=True) or request.form
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    role = (data.get("role") or "author").strip()
    if not username or not password:
        return _json_error("Username and password are required.")
    if len(password) < 6:
        return _json_error("Password must be at least 6 characters.")
    if role not in ("author", "reviewer", "approver"):
        role = "author"
    uid = create_user(username, password, role)
    if not uid:
        return _json_error("Username already taken.")
    session["user_id"] = uid
    if request.is_json:
        return jsonify({"ok": True, "user_id": uid, "username": username, "role": role})
    return redirect(url_for("home"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", title="Login", year=datetime.now().year)
    data = request.get_json(silent=True) or request.form
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    user = verify_user(username, password)
    if not user:
        return _json_error("Invalid username or password.", 401)
    session["user_id"] = user["id"]
    if request.is_json:
        return jsonify({"ok": True, "user_id": user["id"], "username": user["username"], "role": user["role"]})
    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("home"))


# ---------- Analytics (Improvement 3) ----------
@app.route("/analytics")
def analytics_page():
    data = get_analytics()
    return render_template("analytics.html", title="Analytics", data=data, year=datetime.now().year)


@app.route("/notifications")
def notifications_page():
    uid = session.get("user_id")
    notifs = list_notifications(uid) if uid else []
    if uid:
        # mark all read
        conn = get_connection()
        try:
            conn.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (uid,))
            conn.commit()
        finally:
            conn.close()
    return render_template("notifications.html", title="Notifications", notifications=notifs, year=datetime.now().year)


@app.route("/api/notifications")
def api_notifications():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"notifications": [], "unread": 0})
    return jsonify({
        "notifications": list_notifications(uid),
        "unread": unread_notification_count(uid),
    })


@app.route("/api/notifications/<int:nid>/read", methods=["POST"])
def api_notification_read(nid):
    conn = get_connection()
    try:
        conn.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (nid,))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


# ---------- Webhook settings (Improvement 3) ----------
@app.route("/api/profile/<int:profile_id>/webhook", methods=["POST"])
def api_set_webhook(profile_id):
    payload = request.get_json(silent=True) or {}
    url = (payload.get("webhook_url") or "").strip()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM brand_profiles WHERE id = ?", (profile_id,))
        if not cur.fetchone():
            return _json_error("Profile not found.", 404)
        cur.execute("UPDATE brand_profiles SET webhook_url = ? WHERE id = ?", (url or None, profile_id))
        conn.commit()
        return jsonify({"ok": True, "webhook_url": url or None})
    except Exception as e:
        conn.rollback()
        return _json_error(f"Failed: {str(e)}", 500)
    finally:
        conn.close()


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
        uid = session.get("user_id")
        cur.execute(
            """INSERT INTO reviews (profile_id, user_id, content, overall_status, total_issues, ai_used)
               VALUES (?,?,?,?,?,?)""",
            (profile_id, uid, content, result["overall_status"], result["total_issues"], 1 if ai_used else 0),
        )
        review_id = cur.lastrowid
        for f in result["findings"]:
            cur.execute(
                """INSERT INTO findings
                   (review_id, original_text, issue_type, severity, explanation,
                    rule_reference, suggested_correction, requires_evidence, status,
                    confidence, citation)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (review_id, f["original_text"], f["issue_type"], f["severity"],
                 f["explanation"], f.get("rule_reference"), f.get("suggested_correction"),
                 1 if f.get("requires_evidence") else 0, f.get("status", "Needs Review"),
                 f.get("confidence", "medium"), f.get("citation")),
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        return _json_error(f"Failed to save review: {str(e)}", 500)
    finally:
        conn.close()

    uid = session.get("user_id")
    if uid:
        try:
            add_notification(uid, "Review #{} submitted: {} ({} issues).".format(review_id, result["overall_status"], result["total_issues"]),
                             "/history?review={}".format(review_id))
        except Exception:
            pass

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
    webhook_url = None
    content = ""
    profile_name = ""
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

        row = conn.execute(
            "SELECT r.content, p.webhook_url, p.name FROM reviews r LEFT JOIN brand_profiles p ON p.id=r.profile_id WHERE r.id = ?",
            (review_id,),
        ).fetchone()
        if row:
            content = row["content"] or ""
            webhook_url = row["webhook_url"]
            profile_name = row["name"] or ""
    except Exception as e:
        conn.rollback()
        return _json_error(f"Failed: {str(e)}", 500)
    finally:
        conn.close()

    uid = session.get("user_id")
    if uid:
        try:
            add_notification(uid, "Review #{} {}: {}".format(review_id, decision, profile_name),
                             "/history?review={}".format(review_id))
        except Exception:
            pass

    if decision == "approved" and webhook_url:
        try:
            import requests as _r
            _r.post(webhook_url, json={"review_id": review_id, "content": content,
                                       "profile": profile_name, "decision": decision}, timeout=5)
        except Exception:
            pass

    return jsonify({"ok": True, "review_id": review_id, "final_decision": decision})


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


# ---------- Visual brand check (Improvement 2) ----------
@app.route("/api/visual/check", methods=["POST"])
def api_visual_check():
    profile_id = request.form.get("profile_id") or request.args.get("profile_id")
    try:
        profile_id = int(profile_id)
    except (TypeError, ValueError):
        return _json_error("A valid brand profile is required.")

    profile = load_profile(profile_id)
    if not profile:
        return _json_error("Brand profile not found.", 404)

    if "file" not in request.files:
        return _json_error("No image uploaded.")
    f = request.files["file"]
    if not f or not f.filename:
        return _json_error("No file selected.")

    image_bytes = f.read()
    if not image_bytes:
        return _json_error("Empty file.")
    if len(image_bytes) > 5 * 1024 * 1024:
        return _json_error("Image too large (max 5 MB).")

    colors = list_brand_colors(profile_id)
    assets = list_brand_assets(profile_id)
    findings = check_image(image_bytes, f.filename, profile_id, colors, assets)

    # Persist as a review (visual-only)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO reviews (profile_id, content, overall_status, total_issues, ai_used)
               VALUES (?,?,?,?,?)""",
            (profile_id, f"[Visual check: {f.filename}]", "Needs Review", len(findings), 0),
        )
        review_id = cur.lastrowid
        for fd in findings:
            cur.execute(
                """INSERT INTO findings
                   (review_id, original_text, issue_type, severity, explanation,
                    rule_reference, suggested_correction, requires_evidence, status,
                    confidence, citation)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (review_id, fd["original_text"], fd["issue_type"], fd["severity"],
                 fd["explanation"], fd.get("rule_reference"), fd.get("suggested_correction"),
                 1 if fd.get("requires_evidence") else 0, fd.get("status", "Needs Review"),
                 fd.get("confidence", "medium"), fd.get("citation")),
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        return _json_error(f"Failed to save: {str(e)}", 500)
    finally:
        conn.close()

    return jsonify({
        "review_id": review_id,
        "profile_id": profile_id,
        "profile_name": profile["profile"]["name"],
        "overall_status": "Needs Review",
        "total_issues": len(findings),
        "ai_used": False,
        "findings": findings,
    })


# ---------- Document extraction (Improvement 1) ----------
@app.route("/api/facts/extract", methods=["POST"])
def api_extract_facts():
    if "file" not in request.files:
        return _json_error("No file uploaded.")
    f = request.files["file"]
    if not f or not f.filename:
        return _json_error("No file selected.")
    filename = f.filename.lower()
    text = ""
    try:
        if filename.endswith(".txt"):
            text = f.read().decode("utf-8", errors="ignore")
        elif filename.endswith(".pdf"):
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(f.read()))
            for page in reader.pages:
                text += (page.extract_text() or "") + "\n"
        else:
            return _json_error("Only .txt and .pdf files are supported.")
    except Exception as e:
        return _json_error(f"Failed to read file: {str(e)}", 500)

    lines = [ln.strip() for ln in text.splitlines() if len(ln.strip()) > 10]
    # dedupe while preserving order
    seen = set()
    unique = []
    for ln in lines:
        if ln.lower() in seen:
            continue
        seen.add(ln.lower())
        unique.append(ln)
    unique = unique[:50]  # cap
    return jsonify({
        "filename": f.filename,
        "line_count": len(unique),
        "candidates": unique,
    })


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
