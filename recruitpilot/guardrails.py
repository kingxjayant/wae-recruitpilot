"""Guardrails: prompt-injection detection, PII redaction, human-in-the-loop (HITL)
approvals, and audit logging.

Design principle: the resume/JD are DATA, never instructions. Lines that look
like instructions to the evaluator are neutralised before parsing, and any
external action (outreach email, ATS write) is blocked until a human approves
it in the UI.
"""
import json
import os
import re
import time
from pathlib import Path

INJECTION_PATTERNS = [
    ("ignore_instructions", re.compile(r"ignore\s+(all|any|the|previous|above|prior)\s+(instructions?|prompts?|rules?|messages?)", re.I)),
    ("disregard_instructions", re.compile(r"disregard\s+(all|any|the|previous|above|prior)\s+(instructions?|prompts?|rules?)", re.I)),
    ("forget_instructions", re.compile(r"forget\s+(all|any|the|previous|above|prior)\s+(instructions?|prompts?|rules?)", re.I)),
    ("you_are_now", re.compile(r"you\s+are\s+now\b|from\s+now\s+on\s+you", re.I)),
    ("system_prompt", re.compile(r"system\s+prompt|developer\s+message|hidden\s+(rules|instructions)", re.I)),
    ("rate_100", re.compile(r"(rate|score|give)\s+(me|this|the\s+candidate|him|her)?[^\n.]{0,30}\b(100|full\s*marks?|10/10|perfect)", re.I)),
    ("force_shortlist", re.compile(r"(shortlist|select|choose|pick)\s+(me|this\s+candidate|him|her)\b", re.I)),
    ("force_verdict", re.compile(r"(mark|declare|classify)\s+(me|this\s+candidate|him|her|them)[^\n.]{0,30}\b(selected|shortlisted|hired|qualified)", re.I)),
    ("act_as", re.compile(r"\bact\s+as\b.{0,40}(recruiter|evaluator|grader|hiring\s+manager|llm|ai)", re.I)),
    ("jailbreak", re.compile(r"jailbreak|developer\s+mode|dan\s+mode|do\s+anything\s+now", re.I)),
    ("override_scoring", re.compile(r"(override|bypass|change)\s+(the\s+)?(scoring|rubric|evaluation|grading)", re.I)),
    ("new_instructions", re.compile(r"new\s+(instructions?|task)\s*[:\-]", re.I)),
]

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+91[-\s]?[6-9]\d{9}|\b[6-9]\d{4}[-\s]?\d{5}\b|\b[6-9]\d{9}\b)")


class GuardrailBlocked(Exception):
    """Raised when an action is attempted without human approval (or input is unsafe)."""


def scan_injection(text):
    """Return list of {pattern, line, excerpt} for instruction-like lines."""
    hits = []
    for i, line in enumerate((text or "").splitlines(), start=1):
        for name, rx in INJECTION_PATTERNS:
            if rx.search(line):
                hits.append({"pattern": name, "line": i, "excerpt": line.strip()[:120]})
                break  # one hit per line is enough
    return hits


def sanitize_text(text):
    """Remove instruction-like lines from untrusted input. Returns (clean, hits)."""
    hits = scan_injection(text)
    bad_lines = {h["line"] for h in hits}
    kept = [f"[line removed by injection guardrail]" if (i + 1) in bad_lines else line
            for i, line in enumerate((text or "").splitlines())]
    return "\n".join(kept), hits


def redact_email(email):
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    keep = local[:1] if local else "*"
    return f"{keep}***@{domain}"


def redact_phone(phone):
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) < 4:
        return "****"
    prefix = "+" + digits[:2] if (phone or "").strip().startswith("+") else ""
    return f"{prefix}{digits[2:4] if prefix else digits[:2]}{'*' * (len(digits) - 4)}{digits[-2:]}"


def redact_pii_text(text):
    if not text:
        return text
    out = EMAIL_RE.sub(lambda m: redact_email(m.group(0)), text)
    out = PHONE_RE.sub(lambda m: redact_phone(m.group(0)), out)
    return out


def data_dir():
    d = os.environ.get("RECRUITPILOT_DATA")
    if not d:
        d = str(Path(__file__).resolve().parent.parent / "data" / "runtime")
    p = Path(d)
    p.mkdir(parents=True, exist_ok=True)
    return p


def audit(event, run_id=None, details=None):
    """Append a redacted audit event. Audit entries NEVER contain raw PII."""
    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "event": event,
        "run_id": run_id,
        "details": redact_pii_text(json.dumps(details or {}, ensure_ascii=False))[:2000],
    }
    try:
        with open(data_dir() / "audit.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass  # auditing must never crash the request path
    return rec


def read_audit(limit=50):
    path = data_dir() / "audit.jsonl"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines[-limit:]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(out))
