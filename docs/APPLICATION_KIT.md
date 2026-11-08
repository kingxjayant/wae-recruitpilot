# Agent Maker-2026 — Application Kit
**Read this before touching the Google Form.** Draft answers below are starting points — personalize
them in your own voice, keep the character limits, and *never write anything untrue.*

## ⏰ First: the deadline discrepancy — act today
- The **form itself** says "complete this form by **2 Nov 2026**" (already past).
- The **official brief PDF** (v. *Latest*, linked from the form) says screening is **open up to 11 Nov 2026**, shortlisting 12–13 Nov, challenge 14 Nov 10:00 IST.
Today is **8 Nov 2026**. Two possibilities: an outdated header on the form, or late entries closed.
**Do both today:** (1) open the form — if it shows "This form is no longer accepting responses", it's closed;
(2) regardless, email **info@waecs.in** and call **8290450219** asking to confirm late submission is
accepted (the brief is the newer document). Screenshot the form and any reply as proof.

## ✅ Submission checklist (in order)
1. **Eligibility, truthfully:** passing out in **2027 or 2028** only. If you pass out earlier/later, don't tick the box.
2. **Resume PDF** uploaded to Google Drive → right-click → Share → "Anyone with the link → Viewer". Paste the link in the form. Test it in an **incognito window**.
3. **GitHub repo public:** push RecruitPilot (see commands below) → repo Settings → ensure it says **Public**. Open the repo URL in incognito to verify it loads without login.
4. **Live demo (optional but strong):** deploy free on Render (Docker auto-detect) or Hugging Face Spaces; verify the incognito link works. If deploy isn't ready, the repo link alone is acceptable ("Link to best existing work" can be a repository).
5. Paste the two draft answers below, edited. **Project ≤ 500 chars, why-agents ≤ 300 chars** — Google Forms enforces this.
6. "Type of your best work" → **AI or agent project**. "Can reviewers open this link without logging in?" → **Yes** (after your incognito check). "Can you work full-time 24 Nov – 4 Jan?" → answer honestly.
7. Eligibility + consent confirmations → tick only if true.
8. Submit. **Screenshot the confirmation page** and save the email WAE sends.
9. If the form errors out or is closed, email info@waecs.in with subject *"Agent Maker-2026 — screening form issue (late entry?)"* and call 8290450219.

## 📝 Draft: "Tell us about one project you built" (489 / 500 chars)
```
RecruitPilot — explainable AI recruitment-screening agent for campus hiring. Scores resume vs JD 0-100 on a transparent rubric (skills 45/exp 20/edu 15/CGPA 10/extras 10), flags gaps, drafts gap-targeted questions. Human approval required before ATS writes or outreach emails (mock). Prompt-injection guard (resumes are data, not instructions), PII-redacted audit logs, 12/12 tests, web UI. Pure Python, zero deps. Built with AI assistance (disclosed). github.com/kingxjayant/wae-recruitpilot
```
Replace `kingxjayant` with your GitHub username. Trim elsewhere if needed — keep ≤500.

## 📝 Draft: "Why do you want to build AI agents?" (273 / 300 chars)
```
Agents don't just answer, they act. I want to build agents that do real, auditable work — guardrails before external actions, human checkpoints, measurable quality. WAE's library-of-business-agents mission is where I'll grow fastest: real roles, real users, real standards.
```
Rewrite one clause in your own words so it genuinely sounds like you.

## 🔗 Pushing the repo public (token route you chose)
```bash
cd wae-recruitpilot
git init && git add -A && git commit -m "RecruitPilot: explainable AI recruitment-screening agent (WAE Agent Maker-2026)"
git branch -M main
git remote add origin https://github.com/kingxjayant/wae-recruitpilot.git
git push -u origin main        # username = your GitHub handle, password = your token
```
**Token hygiene:** create a token with only `repo` scope (or fine-grained: this repo, Contents read/write);
never commit it (`.gitignore` already covers `.env` — don't paste tokens in files); revoke it after pushing;
never share it in the form — forms get shared, repos get indexed. Once pushed, `git remote -v` is enough proof.

## 🏆 What shortlisting actually rewards (from the official brief)
1. **Form answers, resume, existing public work** → this kit + RecruitPilot + a tight README + tests.
2. **Challenge (50%):** working agent, guardrails, code quality, ≥10 tests, README, ≤5-min demo — RecruitPilot is exactly this shape; rehearse with `docs/DEMO_SCRIPT.md`.
3. **Presentation & Q&A (30%):** `docs/QA_DRILL.md` — read until every answer is cold.
4. **Ownership & communication (20%):** reply to WAE emails within the hour; on challenge day, keep scope, ship, be honest about what's mock.

## ⚠️ Honesty guardrails (protect yourself)
- RecruitPilot must be *yours* to present: run it, read `recruitpilot/*.py`, break it, fix it. The presentation includes Q&A on your own code — "the AI wrote it, no idea" loses the internship.
- Disclose AI assistance in the challenge submission and README (already done) — the rules allow it, penalise hiding it.
- Don't invent CGPA, links, eligibility, or experience anywhere in the form. The confirmation box is under your name.
- Don't paste your GitHub token or passwords into any form. The form explicitly says never submit passwords.
- A live demo with fake "sent email" screenshots = honest (it *is* a mock, labelled as such). A demo pretending to be a real production ATS = not okay. Keep the labels.
