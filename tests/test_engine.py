import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from FlaskWebProject1.engine import check_content
from FlaskWebProject1.db import list_profiles


def _demo_profile_id():
    profiles = list_profiles()
    assert profiles, "no profiles seeded"
    return profiles[0]["id"]


def test_prohibited_term_detected():
    pid = _demo_profile_id()
    result = check_content(pid, "This product is cheap and made of stuff.")
    types = [f["issue_type"] for f in result["findings"]]
    assert "prohibited_term" in types
    assert result["total_issues"] >= 2


def test_factual_conflict_detected():
    pid = _demo_profile_id()
    result = check_content(pid, "We were founded in 2020 and are based in New York.")
    types = [f["issue_type"] for f in result["findings"]]
    assert "factual_conflict" in types


def test_unsupported_claim_detected():
    pid = _demo_profile_id()
    result = check_content(pid, "Our product is 100% effective and risk-free.")
    types = [f["issue_type"] for f in result["findings"]]
    assert "unsupported_claim" in types
    uc = [f for f in result["findings"] if f["issue_type"] == "unsupported_claim"][0]
    assert uc["requires_evidence"] is True
    assert uc["status"] == "Needs Review"


def test_accessibility_check():
    pid = _demo_profile_id()
    result = check_content(pid, "Click here to read more about our services.")
    types = [f["issue_type"] for f in result["findings"]]
    assert "accessibility" in types


def test_clean_content_no_major_issues():
    pid = _demo_profile_id()
    result = check_content(pid, "BrandGuard AI helps teams review content. Founded in 2024.")
    bad = [f for f in result["findings"] if f["issue_type"] in ("prohibited_term", "factual_conflict", "unsupported_claim")]
    assert bad == [], f"unexpected findings: {bad}"


def test_unknown_claim_not_marked_false():
    pid = _demo_profile_id()
    result = check_content(pid, "Our tool saves 3 hours per review.")
    types = [f["issue_type"] for f in result["findings"]]
    assert "factual_conflict" not in types


def test_invalid_profile_raises():
    try:
        check_content(99999, "hello")
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_finding_fields():
    pid = _demo_profile_id()
    result = check_content(pid, "This is cheap stuff.")
    assert result["findings"]
    f = result["findings"][0]
    for key in ("original_text", "issue_type", "severity", "explanation", "status"):
        assert key in f
    assert f["severity"] in ("low", "medium", "high", "critical")