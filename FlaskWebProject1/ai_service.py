"""Optional AI assistance for BrandGuard AI."""

import json
import os
import re

import requests

from .config import Config

ALLOWED_ISSUE_TYPES = {"tone", "unsupported_claim", "style", "uncertain_claim"}
ALLOWED_SEVERITIES = {"low", "medium", "high", "critical"}


def is_enabled() -> bool:
    return bool(Config.AI_API_KEY)


def _headers():
    return {
        "Authorization": f"Bearer {Config.AI_API_KEY}",
        "Content-Type": "application/json",
    }


def _sanitize_text(value, max_len=400):
    if not isinstance(value, str):
        return None
    value = value.strip()
    value = re.sub(r"<[^>]+>", "", value)
    if not value or len(value) > max_len:
        return None
    return value


def _call_chat(messages):
    if not is_enabled():
        return None
    url = f"{Config.AI_API_BASE}/chat/completions"
    payload = {
        "model": Config.AI_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 900,
        "response_format": {"type": "json_object"},
    }
    try:
        resp = requests.post(url, headers=_headers(), json=payload, timeout=Config.AI_TIMEOUT)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    try:
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError, TypeError):
        return None
    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
        return None


def explain_finding(content: str, finding: dict, profile_name: str = "") -> dict:
    """Return {'explanation': str, 'rewrite': str, 'ai_used': bool}.

    AI explains a single finding in plain language and proposes a full rewrite
    of the problematic sentence. Falls back gracefully on failure.
    """
    if not is_enabled():
        return {"explanation": None, "rewrite": None, "ai_used": False}

    system = (
        "You are a brand-governance assistant. Explain findings in plain language "
        "and propose a corrected version of the sentence. Never invent facts. "
        "Return only valid JSON with keys: explanation, rewrite."
    )
    user = (
        "Brand profile: {}\n".format(profile_name or "Demo Brand") +
        "Original content:\n---\n{}\n---\n".format(content[:3000]) +
        "Finding to explain:\n"
        "Issue type: {}\n".format(finding.get("issue_type")) +
        "Severity: {}\n".format(finding.get("severity")) +
        "Original text: {}\n".format(finding.get("original_text")) +
        "Rule reference: {}\n".format(finding.get("rule_reference")) +
        "Current suggestion: {}\n".format(finding.get("suggested_correction")) +
        "\nReturn JSON: {\"explanation\": \"plain-language explanation of why this matters\", "
        "\"rewrite\": \"a full rewritten version of the original sentence that fixes the issue\"}. "
        "Keep explanation under 60 words. Keep rewrite under 80 words."
    )

    parsed = _call_chat([{"role": "system", "content": system},
                        {"role": "user", "content": user}])
    if not isinstance(parsed, dict):
        return {"explanation": None, "rewrite": None, "ai_used": False}

    expl = _sanitize_text(parsed.get("explanation"), 300)
    rewrite = _sanitize_text(parsed.get("rewrite"), 400)
    ai_used = bool(expl or rewrite)
    return {"explanation": expl, "rewrite": rewrite, "ai_used": ai_used}


def chat(question: str, content: str = "", profile_name: str = "", rules_context: str = "") -> dict:
    """Return {'answer': str, 'ai_used': bool} for a user question about brand guidelines."""
    if not is_enabled():
        return {"answer": None, "ai_used": False}

    system = (
        "You are BrandGuard AI's helpful assistant. Answer questions about brand guidelines, "
        "content review, and how to use THIS application. Be concise and practical. "
        "ONLY use the information provided below. Do NOT make up features, pages, or details "
        "that are not listed. If you don't know, say so honestly. "
        "The application has these pages: Review (home), Guidelines, History, Analytics, About, Notifications. "
        "Features: content submission, brand profile selection, rule-based checking, findings with explanations, "
        "human approval/rejection, review history, optional AI, visual brand check, document upload, analytics. "
        "Return only valid JSON with key: answer."
    )
    user = "Question: {}\n".format(question[:500])
    if rules_context:
        user += "Brand rules and approved facts for the selected profile:\n{}\n".format(rules_context[:2000])
    if content:
        user += "Current content being reviewed:\n---\n{}\n---\n".format(content[:2000])
    if profile_name:
        user += "Brand profile: {}\n".format(profile_name)
    user += "\nReturn JSON: {\"answer\": \"your helpful answer (under 120 words)\"}."

    parsed = _call_chat([{"role": "system", "content": system},
                        {"role": "user", "content": user}])
    if not isinstance(parsed, dict):
        return {"answer": None, "ai_used": False}
    ans = _sanitize_text(parsed.get("answer"), 600)
    return {"answer": ans, "ai_used": bool(ans)}


def enhance(content: str, findings: list) -> dict:
    result_findings = [dict(f) for f in findings]
    ai_used = False
    if not is_enabled():
        return {"findings": result_findings, "ai_used": False}

    summary = []
    for i, f in enumerate(findings):
        summary.append({
            "index": i,
            "issue_type": f.get("issue_type"),
            "severity": f.get("severity"),
            "original_text": (f.get("original_text") or "")[:200],
        })

    system = (
        "You are a brand-governance assistant. You must NOT contradict approved facts. "
        "Return only valid JSON with keys: additional_findings (array) and improved_suggestions (object). "
        "additional_findings items: {issue_type, severity, original_text, explanation, suggested_correction}. "
        "issue_type must be one of: tone, unsupported_claim, style, uncertain_claim. "
        "severity must be one of: low, medium, high, critical. "
        "Keep explanations concise and non-alarmist. Do not invent facts."
    )
    user = (
        f"Brand content to review:\n---\n{content[:4000]}\n---\n"
        f"Existing deterministic findings (JSON):\n{json.dumps(summary)}\n\n"
        "Identify up to 3 additional tone or claim issues not already covered, "
        "and optionally provide improved suggested corrections for existing findings "
        "(keyed by their index as strings). Return JSON only."
    )

    parsed = _call_chat([{"role": "system", "content": system},
                        {"role": "user", "content": user}])
    if not isinstance(parsed, dict):
        return {"findings": result_findings, "ai_used": False}

    improved = parsed.get("improved_suggestions")
    if isinstance(improved, dict):
        for k, v in improved.items():
            try:
                idx = int(k)
            except (ValueError, TypeError):
                continue
            if 0 <= idx < len(result_findings):
                s = _sanitize_text(v, 400)
                if s:
                    result_findings[idx]["suggested_correction"] = s
                    ai_used = True

    additional = parsed.get("additional_findings")
    if isinstance(additional, list):
        existing_keys = {(f["issue_type"], (f.get("original_text") or "").lower().strip())
                         for f in result_findings}
        count = 0
        for item in additional:
            if count >= 3:
                break
            if not isinstance(item, dict):
                continue
            itype = item.get("issue_type")
            if itype not in ALLOWED_ISSUE_TYPES:
                continue
            sev = item.get("severity")
            if sev not in ALLOWED_SEVERITIES:
                sev = "medium"
            orig = _sanitize_text(item.get("original_text"), 200)
            expl = _sanitize_text(item.get("explanation"), 400)
            sugg = _sanitize_text(item.get("suggested_correction"), 400)
            if not orig or not expl:
                continue
            key = (itype, orig.lower().strip())
            if key in existing_keys:
                continue
            existing_keys.add(key)
            result_findings.append({
                "original_text": orig,
                "issue_type": itype,
                "severity": sev,
                "explanation": expl + " (AI-assisted observation)",
                "rule_reference": f"AI model: {Config.AI_MODEL} (advisory)",
                "suggested_correction": sugg or "Review and adjust wording.",
                "status": "Needs Review",
                "requires_evidence": (itype in {"unsupported_claim", "uncertain_claim"}),
                "confidence": "medium",
                "citation": f"AI model: {Config.AI_MODEL} (advisory, not an approved source)",
            })
            count += 1
            ai_used = True

    return {"findings": result_findings, "ai_used": ai_used}
