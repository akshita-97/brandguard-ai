"""Deterministic brand-content review engine for BrandGuard AI."""

import json
import re
from typing import List, Dict, Any

from .db import get_connection, row_to_dict


SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def _context(text: str, start: int, end: int, window: int = 45) -> str:
    left = max(0, start - window)
    right = min(len(text), end + window)
    snippet = text[left:right].replace("\n", " ").strip()
    snippet = re.sub(r"\s+", " ", snippet)
    if left > 0:
        snippet = "..." + snippet
    if right < len(text):
        snippet = snippet + "..."
    return snippet


def load_profile(profile_id: int) -> Dict[str, Any]:
    conn = get_connection()
    try:
        profile = conn.execute(
            "SELECT * FROM brand_profiles WHERE id = ?", (profile_id,)
        ).fetchone()
        if not profile:
            return None
        rules = conn.execute(
            "SELECT * FROM brand_rules WHERE profile_id = ? AND active = 1",
            (profile_id,),
        ).fetchall()
        facts = conn.execute(
            "SELECT * FROM brand_facts WHERE profile_id = ?", (profile_id,)
        ).fetchall()
        return {
            "profile": row_to_dict(profile),
            "rules": [row_to_dict(r) for r in rules],
            "facts": [row_to_dict(f) for f in facts],
        }
    finally:
        conn.close()


def _finding(original_text, issue_type, severity, explanation, rule_reference=None,
             suggested_correction=None, status="Needs Review", requires_evidence=False,
             confidence="high", citation=None):
    return {
        "original_text": original_text,
        "issue_type": issue_type,
        "severity": severity,
        "explanation": explanation,
        "rule_reference": rule_reference,
        "suggested_correction": suggested_correction,
        "status": status,
        "requires_evidence": requires_evidence,
        "confidence": confidence,
        "citation": citation,
    }


def check_content(profile_id: int, content: str) -> Dict[str, Any]:
    data = load_profile(profile_id)
    if not data:
        raise ValueError("Brand profile not found.")
    profile = data["profile"]
    rules = data["rules"]
    facts = data["facts"]

    findings: List[Dict[str, Any]] = []
    text = content
    lower = text.lower()

    prohibited = [r for r in rules if r["rule_type"] == "prohibited_term"]
    for r in prohibited:
        pat = r["pattern"]
        if " " in pat:
            regex = re.compile(re.escape(pat), re.IGNORECASE)
        else:
            regex = re.compile(r"\b" + re.escape(pat) + r"\b", re.IGNORECASE)
        matches = list(regex.finditer(text))
        if not matches:
            continue
        m0 = matches[0]
        snippet = _context(text, m0.start(), m0.end())
        count = len(matches)
        expl = r["explanation"]
        if count > 1:
            expl = expl + f" (found {count} times)"
        findings.append(_finding(
            snippet, "prohibited_term", r["severity"], expl,
            rule_reference=f"Brand rule (prohibited term): '{pat}'",
            suggested_correction=(r["replacement"] if r["replacement"] else "Remove or replace this term."),
        ))

    claims = [r for r in rules if r["rule_type"] == "unsupported_claim"]
    for r in claims:
        pat = r["pattern"]
        # substring match (case-insensitive) so stems like "guarantee" catch
        # "guarantees", "guaranteed", etc.
        regex = re.compile(re.escape(pat), re.IGNORECASE)
        matches = list(regex.finditer(text))
        if not matches:
            continue
        m0 = matches[0]
        snippet = _context(text, m0.start(), m0.end())
        count = len(matches)
        expl = r["explanation"]
        if count > 1:
            expl = expl + f" (found {count} times)"
        findings.append(_finding(
            snippet, "unsupported_claim", r["severity"], expl,
            rule_reference=f"Brand rule (claim requiring evidence): '{pat}'",
            suggested_correction="Remove this claim or support it with verified evidence and legal review.",
            status="Needs Review", requires_evidence=True,
        ))

    acc = [r for r in rules if r["rule_type"] == "accessibility"]
    for r in acc:
        pat = r["pattern"]
        regex = re.compile(re.escape(pat), re.IGNORECASE)
        matches = list(regex.finditer(text))
        if not matches:
            continue
        m0 = matches[0]
        snippet = _context(text, m0.start(), m0.end())
        findings.append(_finding(
            snippet, "accessibility", r["severity"], r["explanation"],
            rule_reference=f"Accessibility rule: '{pat}'",
            suggested_correction=(r["replacement"] if r["replacement"] else "Use more descriptive text."),
        ))

    excl_count = text.count("!")
    if excl_count > 2:
        idx = text.find("!")
        findings.append(_finding(
            _context(text, max(0, idx - 10), idx + 1), "tone", "medium",
            f"Found {excl_count} exclamation marks. Excessive exclamation reduces professional tone.",
            rule_reference="Brand tone rule: avoid excessive '!'",
            suggested_correction="Use at most one exclamation mark, or none.",
        ))
    caps_matches = re.findall(r"\b[A-Z]{4,}\b", text)
    if caps_matches:
        unique = sorted(set(caps_matches))
        findings.append(_finding(
            ", ".join(unique[:8]), "tone", "medium",
            "ALL-CAPS words can read as shouting and reduce readability.",
            rule_reference="Brand tone rule: avoid ALL CAPS",
            suggested_correction="Use sentence case instead.",
        ))
    sentences = re.split(r"[.!?]+", text)
    long_ones = [s for s in sentences if len(s.split()) > 40]
    if long_ones:
        findings.append(_finding(
            _context(text, text.find(long_ones[0].strip()[:20]), text.find(long_ones[0].strip()[:20]) + 40),
            "tone", "low",
            f"Found {len(long_ones)} very long sentence(s) (>40 words). Consider splitting for readability.",
            rule_reference="Brand style: prefer concise sentences",
            suggested_correction="Split long sentences into shorter ones.",
        ))
    slang = ["lol", "omg", "kinda", "gonna", "wanna"]
    found_slang = [w for w in slang if re.search(r"\b" + w + r"\b", lower)]
    if found_slang:
        findings.append(_finding(
            ", ".join(found_slang), "tone", "low",
            "Informal slang detected; consider more professional wording.",
            rule_reference="Brand tone rule: professional language",
            suggested_correction="Replace slang with professional equivalents.",
        ))

    for f in facts:
        patterns = []
        try:
            patterns = json.loads(f["patterns"]) if f["patterns"] else []
        except (json.JSONDecodeError, TypeError):
            patterns = []
        approved = (f["fact_value"] or "").strip().lower()
        for pat in patterns:
            try:
                rx = re.compile(pat, re.IGNORECASE)
            except re.error:
                continue
            for m in rx.finditer(text):
                try:
                    extracted = m.group(1)
                except IndexError:
                    extracted = m.group(0)
                extracted_norm = (extracted or "").strip().lower().rstrip(".,!?")
                if extracted_norm and extracted_norm != approved:
                    snippet = _context(text, m.start(), m.end())
                    doc = f.get("source_document") or "Demo brand guidelines"
                    section = f.get("section") or "General"
                    version = f.get("version") or "1.0"
                    citation = f"{doc} — {section} (v{version})"
                    findings.append(_finding(
                        snippet, "factual_conflict", "high",
                        f"Content states '{extracted.strip()}' but the approved fact is '{f['fact_value']}'.",
                        rule_reference=f"Approved fact ({f['fact_key']}): {f['fact_value']} (source: {f.get('source') or 'demo'})",
                        suggested_correction=f"Correct to the approved fact: {f['fact_value']}.",
                        confidence="high",
                        citation=citation,
                    ))
                    break

    preferred = [r for r in rules if r["rule_type"] == "preferred_term"]
    for r in preferred:
        if r["pattern"].lower() not in lower and len(text.strip()) > 60:
            findings.append(_finding(
                text[:80].replace("\n", " ").strip() + ("..." if len(text) > 80 else ""),
                "style", "low",
                f"Content does not mention the approved brand name '{r['pattern']}'.",
                rule_reference=f"Brand style: use '{r['pattern']}'",
                suggested_correction=f"Include the approved brand name '{r['pattern']}' where appropriate.",
            ))

    approved_numbers = set()
    for f in facts:
        for tok in re.findall(r"\d+", f["fact_value"] or ""):
            approved_numbers.add(tok)
    for m in re.finditer(r"\b\d+(?:\.\d+)?\s*%", text):
        val = m.group(0)
        if val.split("%")[0].strip() not in approved_numbers:
            findings.append(_finding(
                _context(text, m.start(), m.end()), "uncertain_claim", "medium",
                f"Numeric percentage '{val}' is not in the approved facts and requires verification.",
                rule_reference="Approved facts (none match this number)",
                suggested_correction="Verify this statistic and cite a source, or remove it.",
                status="Needs Review", requires_evidence=True,
                confidence="low",
                citation="No approved source found",
            ))
    for m in re.finditer(r"\b(?:over|more than|up to)\s+(\d[\d,]*)\s+(?:customers|users|clients|companies)\b", lower):
        num = m.group(1).replace(",", "")
        if num not in approved_numbers:
            findings.append(_finding(
                _context(text, m.start(), m.end()), "uncertain_claim", "medium",
                "Customer/user count claim is not in the approved facts and requires evidence.",
                rule_reference="Approved facts (none match this count)",
                suggested_correction="Verify the count against approved data or remove the claim.",
                status="Needs Review", requires_evidence=True,
                confidence="low",
                citation="No approved source found",
            ))

    seen = set()
    deduped = []
    for f in findings:
        key = (f["issue_type"], f["original_text"].lower().strip())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(f)
    findings = deduped

    if not findings:
        overall = "Passed"
    else:
        max_sev = max(SEVERITY_ORDER.get(f["severity"], 1) for f in findings)
        if max_sev >= 3:
            overall = "Needs Review (High Priority)"
        else:
            overall = "Needs Review"

    return {
        "overall_status": overall,
        "total_issues": len(findings),
        "findings": findings,
    }
