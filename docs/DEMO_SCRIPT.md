# Demo Video Script (≤ 5 minutes) — for the 48h challenge submission / portfolio

> Goal: a reviewer who never clones the repo still understands and trusts it after 5 minutes.
> Record screen + voice (your own). Honest, calm pace. Total ≈ 4:30.

| Time | Beat | What to show / say |
|---|---|---|
| 0:00–0:25 | Hook | "RecruitPilot screens campus resumes like a sharp recruiter — explainable, adversarially robust, and it never acts without a human." Show the landing UI (header, badges). |
| 0:25–1:10 | The problem | "Placement cells review thousands of resumes per drive. Keyword filters get gamed; raw LLM scoring is a black box. I wanted a third way." Show the input panel. |
| 1:10–2:00 | The happy path | Paste sample SDE JD + strong resume → Run. Walk the verdict ring, rubric bars, matched vs missing chips, CGPA cutoff flag. Say: "Every point traces to a weight — 45 skills, 20 experience, 15 education, 10 academics, 10 extras." |
| 2:00–2:45 | The adversarial case | Load the **Adversarial** sample (Neha Kapoor). Run. Point at the 🛡 banner: "Two instruction-like lines removed — the resume is data, not instructions. Verdict: Reject, 51 — unchanged." |
| 2:45–3:30 | Guardrails + tools | Click **Approve & save to ATS** → runs to `ats_id`; refresh ATS table — new row. Click **Approve & send outreach** → outbox counter increments; open audit log — every entry redacted (show masked email). Say: "Without those clicks, both actions raise GuardrailBlocked — tested in case 9." |
| 3:30–4:15 | Code tour (30s) | Open repo tree: `recruitpilot/parsing.py → scoring.py → guardrails.py → tools.py → agent.py`. "No dependencies; rubric is pure functions — `python3 tests/run_tests.py` → 12/12." Show TEST_RESULTS.md. |
| 4:15–4:45 | Disclosure + close | "Built with AI assistance, disclosed per the rules; I designed the architecture and can explain any line. Next: Greenhouse/Lever API behind the same tool interface. Thanks for your time." |

## Recording checklist
- 1080p, browser zoom 110%, hide bookmarks bar, close notifications (Focus mode).
- Rehearse twice; keep under 5:00 — shorter beats polish.
- Upload unlisted/public to YouTube or Drive ("anyone with the link") and paste into README/form.
