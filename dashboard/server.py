"""
dashboard/server.py — Jarvis dashboard backend (FastAPI).

Serves a custom single-page dashboard (dashboard/static/) and exposes the brain
(memory, journal, brief, chat) as JSON APIs.

Run from the repo root:
    pip install -r dashboard/requirements.txt
    python dashboard/server.py           # → http://localhost:8000
    # or: uvicorn dashboard.server:app --reload --port 8000

Everything degrades gracefully with no API key — brief/journal/memory work offline;
only chat and the AI-written brief need GEMINI_API_KEY in .env.
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
STATIC_DIR = Path(__file__).resolve().parent / "static"

from tools.journal import list_journal_dates, read_journal, write_section, append_bullet
from tools.brief import generate_brief, build_brief_data
from tools.llm import active_model, _load_env, llm_chat

app = FastAPI(title="Jarvis Dashboard")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _strip_frontmatter(raw: str) -> str:
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        return parts[2].strip() if len(parts) >= 3 else raw
    return raw


def _key_set() -> tuple[str, bool]:
    try:
        _load_env()
        model, key_env = active_model()
        return model, (not key_env) or bool(os.getenv(key_env))
    except Exception:
        return "unknown", False


def _greeting() -> str:
    h = datetime.now().hour
    if h < 12:
        return "Good morning"
    if h < 18:
        return "Good afternoon"
    return "Good evening"


def _streak() -> int:
    """Consecutive days (ending today or yesterday) with a journal entry."""
    dates = set(list_journal_dates())
    if not dates:
        return 0
    from datetime import timedelta
    streak = 0
    cur = date.today()
    if cur not in dates:
        cur = cur - timedelta(days=1)
        if cur not in dates:
            return 0
    while cur in dates:
        streak += 1
        cur = cur - timedelta(days=1)
    return streak


def _parse_projects() -> list[dict]:
    profile = _read(ROOT / "memory" / "user-profile.md")
    projects = []
    in_section = False
    for line in profile.splitlines():
        if "## Active projects" in line:
            in_section = True
            continue
        if in_section:
            if line.startswith("##"):
                break
            s = line.strip()
            if s.startswith("-"):
                s = s.lstrip("- ").strip()
                # Split "**Name** — desc"
                if "—" in s:
                    name, desc = s.split("—", 1)
                else:
                    name, desc = s, ""
                projects.append({
                    "name": name.replace("*", "").strip(),
                    "desc": desc.strip(),
                })
    return projects


def _parse_journal_sections(content: str) -> list[dict]:
    """Split a journal file into {heading, body} sections."""
    if not content:
        return []
    sections = []
    lines = content.splitlines()
    cur_heading = None
    cur_body: list[str] = []
    for line in lines:
        if line.startswith("## "):
            if cur_heading is not None:
                sections.append({"heading": cur_heading, "body": "\n".join(cur_body).strip()})
            cur_heading = line[3:].strip()
            cur_body = []
        elif line.startswith("# "):
            continue  # skip the date title
        else:
            if cur_heading is not None:
                cur_body.append(line)
    if cur_heading is not None:
        sections.append({"heading": cur_heading, "body": "\n".join(cur_body).strip()})
    return sections


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/api/status")
def api_status():
    model, key_set = _key_set()
    return {
        "model": model,
        "key_set": key_set,
        "date": date.today().strftime("%A, %B %d, %Y"),
        "date_short": date.today().strftime("%b %d, %Y").upper(),
        "greeting": _greeting(),
        "streak": _streak(),
        "journal_count": len(list_journal_dates()),
        "memory_count": len([f for f in (ROOT / "memory").glob("*.md") if f.name != "MEMORY.md"]),
        "skill_count": len(list((ROOT / "skills").glob("*.md"))),
    }


def _momentum(today_content: str) -> dict:
    """Today's three core actions — the 'daily score' that builds the habit."""
    sections = _parse_journal_sections(today_content)
    headings = {s["heading"] for s in sections}
    briefed = "Morning" in headings
    debriefed = "Evening recap" in headings
    # any section that isn't the brief/recap counts as a capture/note
    captured = any(h not in ("Morning", "Evening recap") for h in headings)
    done = sum([briefed, captured, debriefed])
    return {
        "briefed": briefed,
        "captured": captured,
        "debriefed": debriefed,
        "done": done,
        "total": 3,
        "pct": round(done / 3 * 100),
    }


def _activity7() -> list[dict]:
    """Journal section-count per day for the last 7 days (real activity signal)."""
    from datetime import timedelta
    out = []
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        content = read_journal(d)
        count = len(_parse_journal_sections(content)) if content else 0
        out.append({"day": d.strftime("%a")[0], "count": count, "iso": d.isoformat()})
    return out


def _bullets_under(sections: list[dict], heading: str) -> list[str]:
    """Return the bullet texts (timestamp stripped) under a given section heading."""
    import re
    out = []
    for s in sections:
        if s["heading"] != heading:
            continue
        for line in s["body"].splitlines():
            line = line.strip()
            if line.startswith("- ") or line.startswith("* "):
                txt = line[2:].strip()
                txt = re.sub(r"^_\d{1,2}:\d{2}_\s*", "", txt)  # drop leading _HH:MM_
                out.append(txt.strip())
    return out


def _open_loops(sections: list[dict]) -> list[dict]:
    """Open loops not yet closed. Closed items live under the 'Closed' section as '✓ text'."""
    loops = _bullets_under(sections, "Open loops")
    closed = {c.removeprefix("✓").strip() for c in _bullets_under(sections, "Closed")}
    return [{"text": t, "closed": t in closed} for t in loops]


@app.get("/api/home")
def api_home():
    model, key_set = _key_set()
    today = read_journal()
    sections = _parse_journal_sections(today)
    return {
        "greeting": _greeting(),
        "date": date.today().strftime("%A, %B %d, %Y"),
        "streak": _streak(),
        "projects": _parse_projects(),
        "today_sections": sections,
        "open_loops": _open_loops(sections),
        "has_brief": "## Morning" in today,
        "key_set": key_set,
        "momentum": _momentum(today),
        "activity7": _activity7(),
        "operator": {
            "name": "Fakhri",
            "role": "Software Engineer",
            "focus": "Building Jarvis",
        },
    }


async def _safe_json(request: Request) -> dict:
    """Parse a JSON body, returning {} on empty/malformed input (clean, no 500)."""
    try:
        data = await request.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


@app.post("/api/brief")
async def api_brief(request: Request):
    body = await _safe_json(request)
    use_llm = bool(body.get("use_llm", True))
    save = bool(body.get("save", True))
    try:
        text = generate_brief(use_llm=use_llm)
        if save:
            write_section("Morning", text)
        return {"ok": True, "brief": text}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/journal")
def api_journal(d: str | None = None):
    dates = list_journal_dates()
    date_list = [
        {"iso": dt.isoformat(), "label": dt.strftime("%A, %b %d %Y")}
        for dt in dates
    ]
    target = None
    if d:
        try:
            target = date.fromisoformat(d)
        except ValueError:
            target = None
    if target is None and dates:
        target = dates[0]

    content = read_journal(target) if target else ""
    return {
        "dates": date_list,
        "selected": target.isoformat() if target else None,
        "sections": _parse_journal_sections(content),
    }


@app.post("/api/capture")
async def api_capture(request: Request):
    body = await _safe_json(request)
    text = (body.get("text") or "").strip()
    section = (body.get("section") or "Quick capture").strip()
    if not text:
        return JSONResponse({"ok": False, "error": "empty"}, status_code=400)
    append_bullet(section, text)  # append (not idempotent) so repeated captures persist
    return {"ok": True}


@app.post("/api/close-loop")
async def api_close_loop(request: Request):
    """Mark an open loop done — appends a closure note (journals are append-only)."""
    body = await _safe_json(request)
    text = (body.get("text") or "").strip()
    if not text:
        return JSONResponse({"ok": False, "error": "empty"}, status_code=400)
    append_bullet("Closed", f"✓ {text}")
    return {"ok": True}


@app.post("/api/debrief")
async def api_debrief(request: Request):
    body = await _safe_json(request)
    text = (body.get("text") or "").strip()
    use_llm = bool(body.get("use_llm", True))
    if not text:
        return JSONResponse({"ok": False, "error": "empty"}, status_code=400)
    from tools.debrief import generate_debrief
    recap = generate_debrief(text, use_llm=use_llm)
    write_section("Evening recap", recap)
    return {"ok": True, "recap": recap}


@app.get("/api/memory")
def api_memory():
    memory_dir = ROOT / "memory"
    files = []
    for mf in sorted(memory_dir.glob("*.md")):
        if mf.name == "MEMORY.md":
            continue
        files.append({
            "name": mf.stem,
            "body": _strip_frontmatter(mf.read_text(encoding="utf-8")),
        })
    skills = []
    for sf in sorted((ROOT / "skills").glob("*.md")):
        content = sf.read_text(encoding="utf-8")
        desc = ""
        if content.startswith("---"):
            for line in content.split("\n"):
                if line.startswith("description:"):
                    desc = line.replace("description:", "").strip()
                    break
        skills.append({"name": sf.stem, "desc": desc})
    return {"files": files, "skills": skills}


def _build_system_prompt() -> str:
    agents = _read(ROOT / "AGENTS.md")
    profile = _read(ROOT / "memory" / "user-profile.md")
    recent = "\n\n---\n\n".join(
        read_journal(d) for d in list_journal_dates()[:2] if read_journal(d)
    )
    today_str = date.today().strftime("%A, %B %d, %Y")
    return (
        f"You are Jarvis, Fakhri's personal assistant.\n\n{agents}\n\n---\n\n"
        f"User profile:\n{profile}\n\n---\n\n"
        f"Recent journal:\n{recent or '(none yet)'}\n\n---\n\n"
        f"Today is {today_str}. Follow the communication rules in AGENTS.md exactly."
    )


@app.post("/api/chat")
async def api_chat(request: Request):
    body = await _safe_json(request)
    history = body.get("messages", [])
    _, key_set = _key_set()
    if not key_set:
        return JSONResponse(
            {"ok": False, "error": "No API key set. Add GEMINI_API_KEY to .env."},
            status_code=400,
        )
    messages = [{"role": "system", "content": _build_system_prompt()}] + history
    try:
        reply = llm_chat(messages)
        return {"ok": True, "reply": reply}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


# PWA: the service worker and manifest must live at the ROOT so the worker's default
# scope covers the whole app (a worker served from /static/ can only control /static/).
@app.get("/sw.js")
def service_worker():
    return FileResponse(
        STATIC_DIR / "sw.js",
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
    )


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(STATIC_DIR / "manifest.webmanifest", media_type="application/manifest+json")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn
    print("\n  🧠 Jarvis dashboard → http://localhost:8000\n")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
