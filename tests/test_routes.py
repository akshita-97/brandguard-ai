import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from FlaskWebProject1 import app
import pytest


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        c.get("/")
        yield c


def _csrf(client):
    with client.session_transaction() as sess:
        return sess.get("csrf_token")


def test_health():
    c = app.test_client()
    r = c.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_index_loads():
    c = app.test_client()
    r = c.get("/")
    assert r.status_code == 200
    assert b"BrandGuard AI" in r.data


def test_check_requires_content(client):
    token = _csrf(client)
    r = client.post("/api/check", json={"content": "", "profile_id": 1},
                    headers={"X-CSRFToken": token})
    assert r.status_code == 400


def test_check_rejects_bad_profile(client):
    token = _csrf(client)
    r = client.post("/api/check", json={"content": "hello world", "profile_id": 99999},
                    headers={"X-CSRFToken": token})
    assert r.status_code == 404


def test_full_check_and_review_flow(client):
    token = _csrf(client)
    profs = client.get("/api/profiles").get_json()["profiles"]
    assert profs
    pid = profs[0]["id"]

    r = client.post("/api/check", json={
        "content": "Our stuff is cheap. Founded in 2020. Click here.",
        "profile_id": pid,
    }, headers={"X-CSRFToken": token})
    assert r.status_code == 200
    data = r.get_json()
    assert "review_id" in data
    assert data["total_issues"] >= 1
    rid = data["review_id"]

    r2 = client.get(f"/api/review/{rid}")
    assert r2.status_code == 200
    rd = r2.get_json()
    assert len(rd["findings"]) == data["total_issues"]

    fid = rd["findings"][0]["id"]
    r3 = client.post(f"/api/finding/{fid}/decision", json={"decision": "accepted", "notes": "ok"},
                     headers={"X-CSRFToken": token})
    assert r3.status_code == 200
    assert r3.get_json()["decision"] == "accepted"

    r4 = client.post(f"/api/review/{rid}/finalize", json={"decision": "approved", "notes": "done"},
                     headers={"X-CSRFToken": token})
    assert r4.status_code == 200
    assert r4.get_json()["final_decision"] == "approved"


def test_history_endpoint(client):
    token = _csrf(client)
    r = client.get("/api/history")
    assert r.status_code == 200
    assert "reviews" in r.get_json()


def test_csrf_blocks_missing_token(client):
    r = client.post("/api/check", json={"content": "hi", "profile_id": 1})
    assert r.status_code == 400


def test_guidelines_page():
    c = app.test_client()
    r = c.get("/guidelines")
    assert r.status_code == 200


def test_history_page():
    c = app.test_client()
    r = c.get("/history")
    assert r.status_code == 200