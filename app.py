"""RecruitPilot — explainable AI recruitment-screening agent (WAE Agent Maker-2026).

Zero third-party dependencies. Run:  python app.py   (PORT env, default 8000)
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from recruitpilot import agent, guardrails, tools  # noqa: E402

tools.seed_if_empty()

MAX_BODY = 256 * 1024
WEB_DIR = ROOT / "web"


class Handler(BaseHTTPRequestHandler):
    server_version = "RecruitPilot/1.0"

    # ---- helpers ----------------------------------------------------------
    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, path: Path):
        if not path.exists():
            self._send_json({"error": "not found"}, 404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            raise ValueError("Empty request body")
        if length > MAX_BODY:
            raise ValueError("Payload too large")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def log_message(self, fmt, *args):
        sys.stderr.write("[recruitpilot] %s - %s\n" % (self.address_string(), fmt % args))

    # ---- routing ----------------------------------------------------------
    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/":
            return self._send_html(WEB_DIR / "index.html")
        if path == "/api/health":
            return self._send_json({"ok": True, "tools": [t["name"] for t in tools.TOOL_SPECS]})
        if path == "/api/samples":
            samples = {}
            sample_dir = ROOT / "sample_data"
            for p in sample_dir.glob("*.json"):
                samples[p.stem] = json.loads(p.read_text(encoding="utf-8"))
            return self._send_json(samples)
        if path == "/api/audit":
            return self._send_json(guardrails.read_audit(50))
        if path == "/api/outbox":
            return self._send_json(tools.read_outbox(20))
        if path == "/api/candidates":
            return self._send_json(_list_candidates())
        if path == "/api/tools":
            return self._send_json(tools.TOOL_SPECS)
        return self._send_json({"error": f"Unknown route: {path}"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        try:
            body = self._read_json()
        except Exception as e:
            return self._send_json({"error": f"Bad request: {e}"}, 400)

        if path == "/api/screen":
            try:
                out = agent.run_agent(
                    resume_text=body.get("resume", ""),
                    jd_text=body.get("jd", ""),
                    name=body.get("name"),
                    email=body.get("email"),
                    phone=body.get("phone"),
                    role=body.get("role"),
                )
                return self._send_json(out)
            except ValueError as e:
                return self._send_json({"error": str(e)}, 400)
        if path == "/api/approve":
            run_id = body.get("run_id")
            action = body.get("action")
            approved = bool(body.get("approved", True))
            out = agent.approve_action(run_id, action, approved=approved)
            status = 200 if out.get("status") in ("executed", "rejected", "already_done") else 400
            return self._send_json(out, status)
        return self._send_json({"error": f"Unknown route: {path}"}, 404)


def _list_candidates():
    import sqlite3
    conn = sqlite3.connect(str(guardrails.data_dir() / "ats.db"))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id,name,email,role,score,verdict,skills,created_at FROM candidates ORDER BY id DESC LIMIT 25"
        ).fetchall()
    finally:
        conn.close()
    return [{
        "id": r["id"], "name": r["name"],
        "email": guardrails.redact_email(r["email"]) if r["email"] else None,
        "role": r["role"], "score": r["score"], "verdict": r["verdict"],
        "skills": r["skills"], "created_at": r["created_at"],
    } for r in rows]


def main():
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"RecruitPilot running → http://0.0.0.0:{port}")
    print("Deterministic rubric + injection guardrail + HITL approvals. Zero dependencies.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
