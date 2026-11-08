"""RecruitPilot agent loop.

plan -> guard(scan+sanitise) -> parse -> score -> decide -> act (guarded) -> audit

Every run is stored in-memory (RUNS) with its own id. External-looking actions
(ATS write, outreach email send) are PENDING until approved by a human via
approve_action(); until then they are blocked by construction.
"""
import threading
import uuid

from . import guardrails, llm, parsing, scoring, tools

RUNS = {}
_LOCK = threading.Lock()

ALLOWED_ACTIONS = {"ats_create", "outreach_email"}


def run_agent(resume_text, jd_text, name=None, email=None, phone=None, role=None):
    if jd_text is None or not str(jd_text).strip():
        raise ValueError("Job description is empty")
    name = (name or "Candidate").strip()
    role = (role or str(jd_text).strip().splitlines()[0][:80] or "the role").strip()

    run_id = str(uuid.uuid4())[:8]
    events = []

    # 1) Guardrail: the JD is ours (trusted-ish) but resume is untrusted DATA.
    clean_resume, hits = guardrails.sanitize_text(resume_text or "")
    for h in hits:
        guardrails.audit("injection_line_removed", run_id=run_id,
                         details={"pattern": h["pattern"], "line": h["line"]})
        events.append(f"Guardrail: removed instruction-like line {h['line']} ({h['pattern']})")

    # 2) Parse + score (deterministic, explainable)
    result = scoring.score_candidate(clean_resume, jd_text)

    # 3) Decide (thresholds live in scoring.py)
    verdict = result["verdict"]
    contacts = parsing.extract_contacts(resume_text or "")
    email = email or (contacts["emails"][0] if contacts["emails"] else None)
    phone = phone or (contacts["phones"][0] if contacts["phones"] else None)

    # 4) Advisory LLM layer (never overrides score)
    rationale = llm.generate_rationale(result, role)
    questions = llm.generate_interview_questions(result)

    draft = tools.tool_outreach_email_draft(name, email, role, verdict, result["overlap"]["missing"])

    # 5) Guarded actions — both require explicit human approval
    pending = ["ats_create", "outreach_email"]
    run = {
        "run_id": run_id, "name": name, "email": email, "phone": phone, "role": role,
        "result": result, "rationale": rationale, "questions": questions,
        "email_draft": draft, "pending_actions": pending, "completed_actions": [],
        "injection_hits": hits, "events": events,
    }
    with _LOCK:
        RUNS[run_id] = run
    guardrails.audit("screening_completed", run_id=run_id,
                     details={"verdict": verdict, "score": result["total"], "injection_hits": len(hits)})
    return _public(run, include_private=True)


def approve_action(run_id, action, approved=True):
    with _LOCK:
        run = RUNS.get(run_id)
    if run is None:
        return {"status": "error", "detail": "Unknown run_id — run the agent first"}
    if action not in ALLOWED_ACTIONS:
        return {"status": "error", "detail": f"Unknown action '{action}'"}
    if action in run["completed_actions"]:
        return {"status": "already_done", "detail": f"{action} already executed for run {run_id}"}
    if not approved:
        guardrails.audit("action_rejected_by_human", run_id=run_id, details={"action": action})
        return {"status": "rejected", "detail": "Human rejected the action — nothing executed"}

    try:
        if action == "ats_create":
            out = tools.tool_ats_create_candidate(
                run["name"], run["email"], run["role"],
                run["result"]["total"], run["result"]["verdict"],
                run["result"]["overlap"]["matched"], phone=run["phone"], approved=True)
        else:  # outreach_email
            out = tools.tool_outreach_email_send(run_id, run["email_draft"], approved=True)
    except guardrails.GuardrailBlocked as e:
        guardrails.audit("action_blocked", run_id=run_id, details={"action": action, "reason": str(e)})
        return {"status": "blocked", "detail": str(e)}

    with _LOCK:
        run["completed_actions"].append(action)
        if action in run["pending_actions"]:
            run["pending_actions"].remove(action)
    return {"status": "executed", "action": action, "output": out}


def _public(run, include_private=False):
    r = run["result"]
    out = {
        "run_id": run["run_id"],
        "name": run["name"],
        "role": run["role"],
        "email": guardrails.redact_email(run["email"]) if run.get("email") else None,
        "overall": r["total"],
        "verdict": r["verdict"],
        "breakdown": r["breakdown"],
        "weights": scoring.WEIGHTS,
        "skills": {
            "matched": r["overlap"]["matched"],
            "missing": r["overlap"]["missing"],
            "extra": r["overlap"]["extra"],
            "jd_required": r["overlap"]["jd_skills"],
        },
        "flags": r["flags"],
        "years_experience": r["years_experience"],
        "required_experience": r["required_experience"],
        "cgpa": r["cgpa"],
        "degrees": r["degrees"],
        "achievement_signals": r["achievement_signals"],
        "rationale": run["rationale"],
        "questions": run["questions"],
        "injection_hits": run["injection_hits"],
        "events": run["events"],
        "pending_actions": run["pending_actions"],
        "completed_actions": run["completed_actions"],
        "llm_enabled": llm.gemini_available(),
    }
    if include_private:
        # only the draft goes back to the caller's browser (it is their own input);
        # raw PII stays server-side for the ATS write.
        out["email_draft"] = run["email_draft"]
    return out
