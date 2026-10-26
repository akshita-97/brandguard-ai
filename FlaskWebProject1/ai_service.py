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
            })
            count += 1
            ai_used = True

    return {"findings": result_findings, "ai_used": ai_used}
