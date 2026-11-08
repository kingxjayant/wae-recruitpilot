"""Optional Google Gemini integration (free tier) used ONLY for advisory text:
anatural-language rationale and tailored interview questions.

Scoring, parsing and guardrails are deterministic and never depend on the LLM.
If GEMINI_API_KEY is unset or the call fails/times out, we fall back to a
template — the agent always works offline. The key is read from the environment
and is never logged, printed or written to disk.
"""
import json
import os
import urllib.request

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + GEMINI_MODEL
    + ":generateContent"
)


def gemini_available():
    return bool(os.environ.get("GEMINI_API_KEY"))


def call_gemini(prompt, timeout=12):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 600},
    }).encode("utf-8")
    req = urllib.request.Request(
        GEMINI_URL, data=payload, method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return None


def generate_rationale(result, role):
    """2-3 sentence recruiter-style rationale. Advisory only."""
    prompt = (
        "You are a hiring assistant. In 2-3 sentences, summarise this screening result for a human "
        f"recruiter for the role: {role}. Be factual, do not invent facts, do not change the verdict.\n"
        f"Verdict: {result['verdict']} | Score: {result['total']}/100\n"
        f"Matched skills: {', '.join(result['overlap']['matched']) or 'none'}\n"
        f"Missing skills: {', '.join(result['overlap']['missing']) or 'none'}\n"
        f"Flags: {'; '.join(result['flags']) or 'none'}"
    )
    text = call_gemini(prompt)
    if text:
        return text
    matched = len(result["overlap"]["matched"])
    required = len(result["overlap"]["jd_skills"])
    gaps = ", ".join(result["overlap"]["missing"][:4]) or "none"
    return (f"Candidate matches {matched}/{required} required skills for {role}; "
            f"overall rubric score {result['total']}/100 → verdict: {result['verdict']}. "
            f"Key gaps: {gaps}. (Template rationale — set GEMINI_API_KEY for LLM-written summaries.)")


def generate_interview_questions(result):
    missing = result["overlap"]["missing"]
    qs = []
    for skill in missing[:4]:
        qs.append(f"Walk me through a project where you used {skill}. What would you do differently?")
    if not qs:
        qs = ["Describe the hardest bug you fixed and how you diagnosed it.",
              "Tell me about a time you learned a new technology under pressure."]
    qs.append("Tell me about a time you received critical feedback — how did you respond?")
    return qs
