import re
import requests

BASE = "https://akshita97.pythonanywhere.com"
s = requests.Session()

print("== 0. Health check ==")
r = s.get(f"{BASE}/health")
print(r.status_code, r.json())

print("\n== 1. Home page ==")
html = s.get(f"{BASE}/").text
m = re.search(r'name="csrf-token" content="([^"]+)"', html)
assert m, "CSRF token not found"
csrf = m.group(1)
print("CSRF token OK")
assert "BrandGuard AI" in html

print("\n== 2. Profiles ==")
profs = s.get(f"{BASE}/api/profiles").json()["profiles"]
assert profs, "no profiles"
pid = profs[0]["id"]
print("Profile:", profs[0]["name"], "id=", pid)

def check(content, label):
    r = s.post(f"{BASE}/api/check", json={"content": content, "profile_id": pid},
               headers={"X-CSRFToken": csrf})
    print(f"\n-- {label} -- status={r.status_code}")
    if r.status_code != 200:
        print("ERROR:", r.text[:300])
        return None
    d = r.json()
    print("overall:", d["overall_status"], "| issues:", d["total_issues"], "| ai:", d["ai_used"])
    for f in d["findings"]:
        print(f"   [{f['severity']}] {f['issue_type']}: {f['original_text'][:60]}")
        print(f"       rule: {f.get('rule_reference')}")
        print(f"       suggestion: {f.get('suggested_correction')}")
    return d

# Test 1: prohibited terminology
d1 = check("This product is cheap and made of stuff.", "Test1 prohibited terms")
assert d1 and any(f["issue_type"] == "prohibited_term" for f in d1["findings"]), "prohibited_term not detected"

# Test 2: incorrect fact
d2 = check("We were founded in 2020 and are based in New York.", "Test2 factual conflict")
assert d2 and any(f["issue_type"] == "factual_conflict" for f in d2["findings"]), "factual_conflict not detected"

# Test 3: unsupported claim
d3 = check("Our product guarantees 500% growth for every customer.", "Test3 unsupported claim")
assert d3 and any(f["issue_type"] == "unsupported_claim" for f in d3["findings"]), "unsupported_claim not detected"
uc = [f for f in d3["findings"] if f["issue_type"] == "unsupported_claim"][0]
assert uc["status"] == "Needs Review", "not marked Needs Review"
assert "factual_conflict" not in [f["issue_type"] for f in d3["findings"]], "wrongly marked false"

# Test 4: suggested correction present
assert all(f.get("suggested_correction") for f in d1["findings"]), "missing suggestion"

# Test 5: human decision persistence
rid = d1["review_id"]
review = s.get(f"{BASE}/api/review/{rid}").json()
fid = review["findings"][0]["id"]
rd = s.post(f"{BASE}/api/finding/{fid}/decision",
            json={"decision": "accepted", "notes": "live test"}, headers={"X-CSRFToken": csrf})
print("\n-- Test5 decision --", rd.status_code, rd.json())
assert rd.status_code == 200 and rd.json()["decision"] == "accepted"

fr = s.post(f"{BASE}/api/review/{rid}/finalize",
            json={"decision": "approved", "notes": "live test done"}, headers={"X-CSRFToken": csrf})
print("-- Test5 finalize --", fr.status_code, fr.json())
assert fr.status_code == 200 and fr.json()["final_decision"] == "approved"

# Verify persistence after refresh (new session)
s2 = requests.Session()
s2.get(f"{BASE}/")
review2 = s2.get(f"{BASE}/api/review/{rid}").json()
print("\n-- Persistence check --")
print("final_decision:", review2["review"]["final_decision"])
print("finding decision:", review2["findings"][0]["reviewer_decision"])
assert review2["review"]["final_decision"] == "approved"
assert review2["findings"][0]["reviewer_decision"] == "accepted"
print("PERSISTENCE OK")

# Error handling tests
print("\n== Error handling ==")
e1 = s.post(f"{BASE}/api/check", json={"content": "", "profile_id": pid}, headers={"X-CSRFToken": csrf})
print("empty content:", e1.status_code, e1.json())
assert e1.status_code == 400

e2 = s.post(f"{BASE}/api/check", json={"content": "hi", "profile_id": 99999}, headers={"X-CSRFToken": csrf})
print("bad profile:", e2.status_code)
assert e2.status_code == 404

e3 = s.post(f"{BASE}/api/check", json={"content": "hi", "profile_id": pid})  # no CSRF
print("missing CSRF:", e3.status_code)
assert e3.status_code == 400

print("\n== Guidelines page ==")
g = s.get(f"{BASE}/guidelines")
print(g.status_code)
assert g.status_code == 200 and "Approved facts" in g.text

print("\n== History page ==")
h = s.get(f"{BASE}/history")
print(h.status_code)
assert h.status_code == 200

print("\nALL LIVE TESTS PASSED")
