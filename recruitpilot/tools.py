"""Tool integrations for the RecruitPilot agent.

Two real tools, both backed by local mock services (as permitted by the
Agent Maker-2026 brief):
  1. ATS tool  — SQLite "Applicant Tracking System" (create / search candidates)
  2. Email tool — drafts an outreach email; SEND is a guarded mock (writes to
     outbox.jsonl) and requires explicit human approval.

External-looking actions NEVER execute without approval (see guardrails.HITL
flow in agent.py / app.py).
"""
import json
import os
import sqlite3
import time
import uuid
from pathlib import Path

from . import guardrails

TOOL_SPECS = [
    {
        "name": "ats_create_candidate",
        "description": "Create a candidate record in the (mock) Applicant Tracking System with score, verdict and matched skills.",
        "requires_approval": True,
        "args_schema": {"name": "string", "email": "string", "role": "string",
                         "score": "integer (0-100)", "verdict": "Shortlist|Hold|Reject", "skills": "list[string]"},
    },
    {
        "name": "ats_search_candidates",
        "description": "Search the ATS for up to 5 candidates whose skills match a query string. Read-only.",
        "requires_approval": False,
        "args_schema": {"query": "string"},
    },
    {
        "name": "outreach_email_draft",
        "description": "Draft a personalised outreach email for a screened candidate. Produces a draft only; does NOT send.",
        "requires_approval": False,
        "args_schema": {"name": "string", "email": "string", "role": "string",
                         "verdict": "Shortlist|Hold|Reject", "missing_skills": "list[string]"},
    },
    {
        "name": "outreach_email_send",
        "description": "Send (mock) the drafted outreach email. Writes to outbox.jsonl. BLOCKED until a human approves.",
        "requires_approval": True,
        "args_schema": {"run_id": "string", "draft": "object{to,subject,body}"},
    },
]


def _db_path():
    return guardrails.data_dir() / "ats.db"


def _connect():
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS candidates ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "name TEXT NOT NULL, email TEXT, phone TEXT, role TEXT,"
        "score INTEGER, verdict TEXT, skills TEXT, created_at TEXT)"
    )
    return conn


def seed_if_empty():
    conn = _connect()
    try:
        n = conn.execute("SELECT COUNT(*) AS c FROM candidates").fetchone()["c"]
        if n:
            return
        seed_path = Path(__file__).parent / "data" / "seed_candidates.json"
        if seed_path.exists():
            rows = json.loads(seed_path.read_text(encoding="utf-8"))
            for r in rows:
                conn.execute(
                    "INSERT INTO candidates(name,email,phone,role,score,verdict,skills,created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (r["name"], r.get("email"), r.get("phone"), r.get("role"),
                     int(r.get("score", 0)), r.get("verdict", "Hold"),
                     ", ".join(r.get("skills", [])), time.strftime("%Y-%m-%dT%H:%M:%S")))
            conn.commit()
    finally:
        conn.close()


def tool_ats_create_candidate(name, email, role, score, verdict, skills, phone=None, approved=False):
    if not approved:
        raise guardrails.GuardrailBlocked("ATS write blocked: human approval required")
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO candidates(name,email,phone,role,score,verdict,skills,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (name or "Unnamed", email, phone, role or "Unspecified role",
             int(score), verdict, ", ".join(skills or []), time.strftime("%Y-%m-%dT%H:%M:%S")))
        conn.commit()
        cid = cur.lastrowid
    finally:
        conn.close()
    guardrails.audit("ats_candidate_created", details={"ats_id": cid, "verdict": verdict, "score": score})
    return {"ats_id": cid, "status": "created"}


def tool_ats_search_candidates(query, limit=5):
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, name, email, role, score, verdict, skills, created_at FROM candidates "
            "WHERE skills LIKE ? OR role LIKE ? ORDER BY score DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", int(limit))).fetchall()
    finally:
        conn.close()
    out = []
    for r in rows:
        out.append({
            "id": r["id"], "name": r["name"],
            "email": guardrails.redact_email(r["email"]) if r["email"] else None,
            "role": r["role"], "score": r["score"], "verdict": r["verdict"],
            "skills": r["skills"], "created_at": r["created_at"],
        })
    return out


def tool_outreach_email_draft(name, email, role, verdict, missing_skills):
    first = (name or "there").split()[0]
    role_txt = role or "the role"
    missing = missing_skills or []
    if verdict == "Shortlist":
        body = (f"Hi {first},\n\nCongratulations — after reviewing your profile for {role_txt}, "
                f"we would like to move you forward in the process. The next step is a technical interview. ")
        if missing:
            body += ("Before we meet, please brush up on: " + ", ".join(missing[:3]) + ". ")
        body += "\nPlease reply with your availability for the next interview slot.\n\nBest regards,\nTalent Team"
        subject = f"Next steps: {role_txt}"
    elif verdict == "Hold":
        body = (f"Hi {first},\n\nThank you for your interest in {role_txt}. Your profile is a partial match today; "
                f"we are keeping your application warm. Strengthening " + (", ".join(missing[:3]) or "your core skills") +
                " will improve your chances. We will reach out if a matching opening comes up.\n\nBest regards,\nTalent Team")
        subject = f"Update on your application: {role_txt}"
    else:
        body = (f"Hi {first},\n\nThank you for your interest in {role_txt}. After careful review we will not be moving "
                f"forward this time. We encourage you to apply again once you have strengthened " +
                (", ".join(missing[:3]) or "your relevant skills") + ".\n\nBest regards,\nTalent Team")
        subject = f"Application update: {role_txt}"
    return {"to": email, "subject": subject, "body": body, "verdict": verdict}


def tool_outreach_email_send(run_id, draft, approved=False):
    if not approved:
        raise guardrails.GuardrailBlocked("Outreach email blocked: human approval required")
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "run_id": run_id or str(uuid.uuid4()),
        "to": guardrails.redact_email((draft or {}).get("to")),
        "subject": (draft or {}).get("subject"),
        "body": (draft or {}).get("body"),
        "status": "mock-sent",
    }
    with open(guardrails.data_dir() / "outbox.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    guardrails.audit("outreach_email_mock_sent", run_id=run_id, details={"to": record["to"], "subject": record["subject"]})
    return {"status": "mock-sent", "to": record["to"]}


def read_outbox(limit=20):
    path = guardrails.data_dir() / "outbox.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(out))
