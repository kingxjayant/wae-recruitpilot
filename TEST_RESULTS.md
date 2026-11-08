# RecruitPilot — Test Results

**12/12 cases passed** — deterministic rubric, injection guardrail, HITL approvals, PII redaction.

| # | Test case | Result | Details |
|---|-----------|--------|---------|
| 1 | Strong fit vs Graduate SDE JD → Shortlist | ✅ PASS | `total=78 verdict=Shortlist breakdown={'skills': 32, 'experience': 12, 'education': 15, 'cgpa': 9, 'extras': 10} injection_hits=0` |
| 2 | Weak fit vs Graduate SDE JD → Reject | ✅ PASS | `total=37 verdict=Reject breakdown={'skills': 0, 'experience': 12, 'education': 15, 'cgpa': 4, 'extras': 6} injection_hits=0` |
| 3 | Partial fit (Java backend) vs SDE JD → Hold | ✅ PASS | `total=58 verdict=Hold breakdown={'skills': 13, 'experience': 12, 'education': 15, 'cgpa': 8, 'extras': 10} injection_hits=0` |
| 4 | Backend/SWE candidate vs ML-intern JD → Hold (gaps surfaced, not rubber-stamped) | ✅ PASS | `total=59 verdict=Hold breakdown={'skills': 15, 'experience': 10, 'education': 15, 'cgpa': 9, 'extras': 10} injection_hits=0` |
| 5 | Prompt-injection resume neutralised → verdict unchanged vs Reject baseline | ✅ PASS | `total=51 verdict=Reject breakdown={'skills': 10, 'experience': 12, 'education': 15, 'cgpa': 4, 'extras': 10} injection_hits=2` |
| 6 | Empty resume → score 0, verdict Reject, no crash | ✅ PASS | `total=0 verdict=Reject breakdown={'skills': 0, 'experience': 0, 'education': 0, 'cgpa': 0, 'extras': 0} injection_hits=0` |
| 7 | Empty JD → ValueError raised (mapped to HTTP 400 by app) | ✅ PASS | `ValueError raised as expected: Job description is empty` |
| 8 | Full skills match but CGPA below JD cutoff → rubric caps academics + flags it | ✅ PASS | `total=83 verdict=Shortlist breakdown={'skills': 42, 'experience': 12, 'education': 15, 'cgpa': 4, 'extras': 10} injection_hits=0` |
| 9 | Outreach email send without approval → blocked | ✅ PASS | `GuardrailBlocked: Outreach email blocked: human approval required` |
| 10 | ATS write without approval → blocked, then approved actions execute | ✅ PASS | `blocked w/o approval; approved → ats_id=1, outbox=1 mock-sent` |
| 11 | PII redaction (email/phone masked in audit log & outbox) | ✅ PASS | `redact_email→a***@gmail.com, redact_phone→+9198********10, raw_pii_in_audit=False` |
| 12 | Determinism + breakdown sums to total (0-100) | ✅ PASS | `run1=78 run2=78 sum(breakdown)=78` |

Run: `python3 tests/run_tests.py` — no third-party dependencies.

Cases 1–8 exercise the deterministic scoring rubric (including adversarial input).
Cases 9–12 exercise the guardrails: HITL approval gate, PII redaction, determinism.
