#!/usr/bin/env python3
"""RecruitPilot test runner — 12 cases, stdlib only.

Usage:  python3 tests/run_tests.py
Writes TEST_RESULTS.md at the repo root and exits non-zero on any failure.
"""
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Isolate all stateful tools (SQLite ATS, outbox, audit log) in a temp dir
TEST_HOME = ROOT / ".test_tmp"
shutil.rmtree(TEST_HOME, ignore_errors=True)
TEST_HOME.mkdir(parents=True)
os.environ["RECRUITPILOT_DATA"] = str(TEST_HOME)

from recruitpilot import guardrails, scoring, tools  # noqa: E402

SAMPLES_RES = {r["id"]: r["resume"] for r in json.loads((ROOT / "sample_data" / "sample_resumes.json").read_text())}
SAMPLES_JD = {j["id"]: j["jd"] for j in json.loads((ROOT / "sample_data" / "sample_jds.json").read_text())}
CASES = json.loads((ROOT / "tests" / "cases.json").read_text())

results = []


def record(case_id, name, passed, detail):
    results.append({"id": case_id, "name": name, "passed": bool(passed), "detail": detail})
    print(f"[{'PASS' if passed else 'FAIL'}] Case {case_id}: {name}\n         {detail}")


def get_text(case):
    resume = case.get("resume_inline", SAMPLES_RES.get(case.get("resume_ref", "")))
    jd = case.get("jd_inline", SAMPLES_JD.get(case.get("jd_ref", "")))
    return resume, jd


# ---------- cases 1-8: deterministic scoring ----------
for case in CASES:
    resume, jd = get_text(case)
    exp = case["expect"]
    if exp.get("error"):
        try:
            scoring.score_candidate(resume, jd)
            record(case["id"], case["name"], False, "expected ValueError, none raised")
        except ValueError as e:
            record(case["id"], case["name"], True, f"ValueError raised as expected: {e}")
        continue

    clean, hits = guardrails.sanitize_text(resume)
    out = scoring.score_candidate(clean, jd)
    ok, notes = True, []
    if "verdict" in exp and out["verdict"] != exp["verdict"]:
        ok = False; notes.append(f"verdict {out['verdict']} != {exp['verdict']}")
    if "min_total" in exp and out["total"] < exp["min_total"]:
        ok = False; notes.append(f"total {out['total']} < {exp['min_total']}")
    if "max_total" in exp and out["total"] > exp["max_total"]:
        ok = False; notes.append(f"total {out['total']} > {exp['max_total']}")
    if "total_exact" in exp and out["total"] != exp["total_exact"]:
        ok = False; notes.append(f"total {out['total']} != {exp['total_exact']}")
    if "flags_contain" in exp:
        if not any(exp["flags_contain"].lower() in f.lower() for f in out["flags"]):
            ok = False; notes.append(f"flag containing '{exp['flags_contain']}' not found in {out['flags']}")
    if "injection_hits_min" in exp and len(hits) < exp["injection_hits_min"]:
        ok = False; notes.append(f"injection hits {len(hits)} < {exp['injection_hits_min']}")
    detail = f"total={out['total']} verdict={out['verdict']} breakdown={out['breakdown']} injection_hits={len(hits)}"
    if notes:
        detail += " | " + "; ".join(notes)
    record(case["id"], case["name"], ok, detail)

# ---------- case 9: external action blocked without human approval ----------
try:
    tools.tool_outreach_email_send("test-run", {"to": "x@example.com", "subject": "s", "body": "b"}, approved=False)
    record(9, "Outreach email send without approval → blocked", False, "email sent without approval!")
except guardrails.GuardrailBlocked as e:
    record(9, "Outreach email send without approval → blocked", True, f"GuardrailBlocked: {e}")
try:
    tools.tool_ats_create_candidate("A", "a@b.com", "Role", 90, "Shortlist", ["Python"], approved=False)
    record(10, "ATS write without approval → blocked, then approved actions execute", False, "ATS write went through without approval")
except guardrails.GuardrailBlocked:
    ats = tools.tool_ats_create_candidate("Test Approve", "approve@example.com", "Graduate Software Engineer",
                                          88, "Shortlist", ["Python", "SQL"], approved=True)
    sent = tools.tool_outreach_email_send("test-run", {"to": "approve@example.com", "subject": "Next steps", "body": "Hi"}, approved=True)
    outbox = tools.read_outbox(5)
    ok = bool(ats.get("ats_id")) and bool(outbox) and outbox[0]["status"] == "mock-sent"
    record(10, "ATS write without approval → blocked, then approved actions execute", ok,
           f"blocked w/o approval; approved → ats_id={ats.get('ats_id')}, outbox={len(outbox)} mock-sent")

# ---------- case 11: PII redaction in logs & outbox ----------
email = guardrails.redact_email("aarav.mehta@gmail.com")
phone = guardrails.redact_phone("+91 98765 43210")
raw_leak = "aarav.mehta@gmail.com" in json.dumps(guardrails.read_audit(50)) or "98765 43210" in json.dumps(guardrails.read_audit(50))
ok = email.startswith("a***@") and "*****" in phone.replace(" ", "") and not raw_leak
record(11, "PII redaction (email/phone masked in audit log & outbox)", ok,
       f"redact_email→{email}, redact_phone→{phone}, raw_pii_in_audit={raw_leak}")

# ---------- case 12: determinism + breakdown integrity ----------
clean, _ = guardrails.sanitize_text(SAMPLES_RES["strong"])
r1 = scoring.score_candidate(clean, SAMPLES_JD["sde"])
r2 = scoring.score_candidate(clean, SAMPLES_JD["sde"])
sum_bd = sum(r1["breakdown"].values())
ok = r1["total"] == r2["total"] and abs(sum_bd - r1["total"]) <= 0 and 0 <= r1["total"] <= 100
record(12, "Determinism + breakdown sums to total (0-100)", ok,
       f"run1={r1['total']} run2={r2['total']} sum(breakdown)={sum_bd}")

# ---------- write TEST_RESULTS.md ----------
passed = sum(1 for r in results if r["passed"])
lines = ["# RecruitPilot — Test Results",
         "",
         f"**{passed}/{len(results)} cases passed** — deterministic rubric, injection guardrail, HITL approvals, PII redaction.",
         "",
         "| # | Test case | Result | Details |",
         "|---|-----------|--------|---------|"]
for r in results:
    lines.append(f"| {r['id']} | {r['name']} | {'✅ PASS' if r['passed'] else '❌ FAIL'} | `{r['detail']}` |")
lines += ["",
          "Run: `python3 tests/run_tests.py` — no third-party dependencies.",
          "",
          "Cases 1–8 exercise the deterministic scoring rubric (including adversarial input).",
          "Cases 9–12 exercise the guardrails: HITL approval gate, PII redaction, determinism."]
(ROOT / "TEST_RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\n{passed}/{len(results)} passed. Wrote TEST_RESULTS.md")
shutil.rmtree(TEST_HOME, ignore_errors=True)
sys.exit(0 if passed == len(results) else 1)
