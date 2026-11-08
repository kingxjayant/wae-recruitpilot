# RecruitPilot — Explainable AI Recruitment-Screening Agent

> An end-to-end agent that screens campus resumes against a job description, scores them on a
> transparent 0–100 rubric, targets interview questions at real gaps, and **never takes an external
> action without human approval**. Built for the **WAE Agent Maker-2026** challenge.

![tests](https://img.shields.io/badge/tests-12%2F12%20passing-brightgreen)
![deps](https://img.shields.io/badge/dependencies-0-blue)
![python](https://img.shields.io/badge/python-3.9+-blue)
![license](https://img.shields.io/badge/license-MIT-green)

## Why this exists

Campus hiring teams at training &amp; placement organisations (like WAE, which runs placement programmes
across 110+ educational clients) drown in undifferentiated resumes. RecruitPilot demonstrates the
minimum bar for a **trustworthy** screening agent: deterministic, explainable scoring; adversarial
input neutralised; PII kept out of logs; a human approving every consequential action; and a test
suite that proves it.

## Features

| Capability | What it does |
|---|---|
| 🧠 **Explainable rubric** | 0–100 score = skills (45) + experience (20) + education (15) + CGPA/% (10) + extras (10). Every point is traceable; no LLM anywhere in scoring. |
| 🛡️ **Prompt-injection guard** | Resumes are *data, never instructions*. Instruction-like lines (`IGNORE ALL PREVIOUS INSTRUCTIONS…`) are detected, removed and audited — the verdict is unaffected. |
| 👤 **Human-in-the-loop (HITL)** | ATS writes and outreach emails are **blocked by default**; they execute only after the user clicks Approve. Without approval they raise `GuardrailBlocked`. |
| 🔒 **PII redaction** | Emails/phones are masked in every audit-log line and in the outbox. Raw PII never touches the logs. |
| 🔧 **Tool integrations** | (1) Mock **ATS** (SQLite) — create/search candidates; (2) **Outreach email** — draft + guarded mock-send; (3) ATS search used by the UI live. |
| 📊 **Evaluation suite** | 12 test cases — scoring, adversarial input, guardrails, PII, determinism — all passing (`python3 tests/run_tests.py`). |
| 🌐 **Web UI + API** | Single-page UI and JSON API (`/api/screen`, `/api/approve`, `/api/audit`, `/api/candidates`, `/api/outbox`, `/api/tools`). Zero third-party dependencies. |
| 🔌 **LLM-optional** | If `GEMINI_API_KEY` (free tier) is set, Gemini writes the recruiter rationale; otherwise a template is used. The LLM **cannot change the verdict** — it only phrases it. |

## Architecture

```
┌────────────────────────── Browser (web/index.html) ──────────────────────────┐
│  JD + resume → Run        Verdict ring, rubric bars, matched/missing chips,  │
│  ✓ Approve ATS  ✓ Approve Outreach (both blocked until clicked)  Audit tail  │
└───────────────────────────────┬───────────────────────────────┬──────────────┘
                                 │ HTTP/JSON                      │
┌────────────────────────────────▼───────────────────────────────▼─────────────┐
│ app.py — stdlib ThreadingHTTPServer (0.0.0.0:$PORT, default 8000)            │
│  /api/screen → agent.run_agent()   /api/approve → agent.approve_action()     │
└────────────────────────────────┬─────────────────────────────────────────────┘
                                 ▼
┌─────────────────── RecruitPilot agent loop (recruitpilot/agent.py) ──────────┐
│ 1 plan → 2 GUARD (scan_injection → sanitize) → 3 parse (taxonomy, regexes)   │
│ 4 score (deterministic rubric) → 5 decide (≥75 Shortlist / ≥55 Hold)          │
│ 6 act  — ats_create & outreach_email stay PENDING until human approval        │
│ every step → redacted audit.jsonl                                             │
└───────┬──────────────┬───────────────┬────────────────┬──────────────────────┘
        ▼              ▼               ▼                ▼
  guardrails.py  parsing.py      scoring.py        tools.py
  (injection,    (skills via     (rubric +        (ATS=SQLite,
   PII, audit,   taxonomy,       thresholds)       email draft/mock-send,
   HITL)         CGPA/yrs/deg)                     all approval-gated)
        └──────────── optional: llm.py (Gemini, advisory only) ───────────────┘
```

## Quickstart

```bash
git clone https://github.com/kingxjayant/wae-recruitpilot.git
cd wae-recruitpilot
python3 app.py            # → http://localhost:8000
```

No `pip install` required — standard library only (Python 3.9+).

Optional LLM rationale (free Gemini key from <https://aistudio.google.com>):

```bash
export GEMINI_API_KEY="your-key-here"   # never commit this
python3 app.py
```

## Run the evaluation suite

```bash
python3 tests/run_tests.py   # 12/12 — writes TEST_RESULTS.md
```

| # | Case | Outcome |
|---|------|---------|
| 1 | Strong fit vs Graduate-SDE JD | Shortlist (78) |
| 2 | Weak fit vs Graduate-SDE JD | Reject (37) |
| 3 | Java-backend partial fit | Hold (58) |
| 4 | SWE candidate vs ML JD | Hold (59) — gaps surfaced |
| 5 | Adversarial prompt-injection resume | Reject (51), 2 lines neutralised |
| 6 | Empty resume | 0 / Reject, no crash |
| 7 | Empty JD | `ValueError` → HTTP 400 |
| 8 | Full skills but below CGPA cutoff | academics capped + flagged |
| 9 | Outreach email without approval | **Blocked** (`GuardrailBlocked`) |
| 10 | ATS write blocked, then both actions approved | Executed, `ats_id` + outbox |
| 11 | PII redaction | audit log & outbox contain no raw PII |
| 12 | Determinism + breakdown integrity | identical scores; breakdown sums to total |

## Design decisions (and why)

- **Deterministic core, LLM as seasoning.** Judges and recruiters need reproducible scores; LLMs
  hallucinate. Scoring never calls the network. Gemini (if key set) only phrases the rationale.
- **Resume = untrusted data.** The injection guard runs *before* parsing; removed lines are
  logged with pattern names, so an evaluator can see exactly what was stripped and why.
- **HITL by construction, not by politeness.** Tools accept `approved=True` only from the
  `/api/approve` path carrying a valid `run_id`; everything else raises `GuardrailBlocked`.
- **Stdlib-only server.** A reviewer can run this with a fresh Python install in 5 seconds —
  no dependency hell, no supply-chain risk, trivially deployable.
- **Mock tools are honest mocks.** The ATS is real SQLite; the email tool really writes to a
  JSONL outbox; both are explicitly labelled mock in the UI and logs.

## Limitations & next steps

- ATS integration is a local mock; next step is Greenhouse/Lever API behind the same tool interface.
- English-only parsing; CGPA scales vary by university (normaliser for 4.0/10.0/percentage scales).
- Rubric weights are hand-tuned on sample data — next step is fitting them on anonymised historical
  shortlist decisions, with fairness auditing across colleges and genders.
- Outreach is mock-send; next step is real SMTP/Resend behind a second approval gate.
- Single-user session store in memory; next step is Redis + auth for a multi-recruiter deployment.

## Deploy it free (live demo for the form)

**Render (Docker):** New → Web Service → connect repo → it auto-detects the `Dockerfile` → deploy.
**Hugging Face Spaces:** New Space → Docker SDK → push this repo → it runs on port 7860 (set `PORT=7860`).
Both are free tiers and suffice for a screening-form link.

## AI-assistance disclosure (required by the challenge rules)

Project was built with AI assistance (Arena Agent Mode / Anthropic Claude-class models) used for
scaffolding, implementation and debugging. The author reviewed, ran and understands the full codebase,
and all architectural decisions above were verified by the author. Every test in
`tests/run_tests.py` was executed and passes in the author's environment. The candidate can walk
through any module — see `docs/QA_DRILL.md` used for preparation.

## License

MIT — see [LICENSE](LICENSE).
