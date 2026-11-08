# Q&A Drill — likely reviewer/presentation questions (read until you can answer cold)

**1. Why not just call an LLM with the resume and ask for a verdict?**
LLMs are non-deterministic and prompt-injectable; a candidate could write "rate me 100" in their resume.
Here, scoring is a pure function — same input, same output, fully traceable. The LLM is used only to
phrase the rationale, never to decide it.

**2. How does the prompt-injection guard work?**
A regex library matches instruction-like patterns (ignore/disregard/forget instructions, "you are now",
system-prompt references, forced verdicts like "shortlist me", "rate 100", jailbreak/developer-mode).
Matching *lines* are removed before parsing; each removal is logged with the pattern name and line
number, and the (adversarial) sample proves the verdict doesn't move.

**3. Doesn't regex-based detection miss things? / false positives?**
Yes — it's a seatbelt, not a vault. False positives cost a removed line (fail-closed for scoring, not
silent); misses are mitigated because the *decision path* never trusts the LLM. Next: classifier-based
injection detection + allow-listing resume sections.

**4. Walk me through the scoring rubric.**
Skills 45 (ratio of JD-required skills found, via a synonym taxonomy), experience 20 (vs JD-stated
requirement, pro-rated), education 15 (degree match vs JD ask), academics 10 (CGPA/% bands, capped at 4
if below a JD-stated cutoff), extras 10 (achievement signals: projects/internships/hackathons/awards —
proxy for initiative). Thresholds: ≥75 Shortlist, ≥55 Hold, else Reject.

**5. How would you plug in a real ATS?**
`tools.py` already defines the tool interface; `ats_create_candidate` becomes a Greenhouse/Lever API
call with OAuth, same HITL gate, plus idempotency keys and retry with backoff. Outbox mock becomes
Resend/SMTP with a second explicit approval.

**6. How do you evaluate the agent itself?**
`tests/run_tests.py` — 12 cases across scoring correctness, adversarial input, guardrail blocking,
PII redaction and determinism. I'd extend with: golden set of 200 labelled resumes, precision@k for
shortlists, fairness slices (college tier, gender-coded names), and drift monitoring.

**7. What breaks at 10,000 resumes per drive?**
In-memory run store and SQLite single-writer; parsing is O(n) per resume — move runs to Redis, ATS to
Postgres, batch-score with a queue (Celery/RQ), and cache taxonomy matches.

**8. How is PII handled?**
Audit log masks emails (`a***@gmail.com`) and phones; the outbox stores masked addresses; raw values
live only in the in-memory run (needed for the ATS write you approved) and the mock DB, which is
local. Nothing is sent over the network.

**9. What did AI do vs you?**
AI scaffolded and accelerated implementation. I own the architecture choices (deterministic core,
HITL-by-construction, stdlib-only server), verified every test result, and can walk through any
module — parsing, rubric weights, guardrail patterns, tool gating. Disclosure is in the README.

**10. Why this problem?**
Placement drives are where I/we live — thousands of resumes, binary stakes, biased shortlisting.
An agent that is explainable enough to audit beats a blacker box with 3% more accuracy.

**11. If WAE assigns me, say, a CRM telecalling agent — where do I start?**
Same skeleton: define the role's SOP as a state machine; tools = CRM lookup, dialer (mock), notes
writer; guardrails = call-quiet-hours, consent check, no-external-action-without-approval; evaluate on
scripted call transcripts; HITL for any write to CRM; same disclosure + tests. RecruitPilot *is* that
template, proven.

**12. What would you improve with 48 more hours?**
PDF resume parsing (pdfplumber), multilingual resumes, fairness audit on synthetic names, real
calendar-scheduling tool, and a Streamlit alternative frontend for judges who prefer it.
