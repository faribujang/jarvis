# Jarvis Dashboard

A custom "operator OS" dashboard for your portable brain — dark, terminal-inspired,
built to actually enjoy opening every day.

## Run it

**Easiest (one step):** double-click **`start-jarvis.bat`** in the repo root (Windows),
or run:

```bash
python dashboard/start.py
```

This installs dependencies if needed, starts the server, and opens your browser.

**Manual:**
```bash
pip install -r dashboard/requirements.txt
python dashboard/server.py
```

Then open **http://localhost:8000**

### Install it as an app (desktop + phone)

The dashboard is a **PWA** — installable, no store, one codebase.

- **Desktop (Chrome/Edge):** open the URL → click the **install icon** in the address bar
  (or ⋮ menu → *Install Jarvis*). It opens in its own window with the Jarvis icon.
- **iPhone/Android:** open the URL in the browser → **Share → Add to Home Screen**. It
  gets a home-screen icon and launches full-screen like a native app.

Offline behavior is deliberately conservative: the app **shell** works offline, but data
(`/api/*`) is **never cached** — you never see stale brain content.

## What's on each screen

| View | Purpose |
|------|---------|
| **HOME** | Bento grid — operator card, greeting + capture bar, morning brief, active projects, today's journal, evening debrief. Your command center. |
| **CHAT** | Talk to Jarvis. It loads your AGENTS.md + profile + recent journal, so it already knows you. |
| **JOURNAL** | Browse every day's entry by date. |
| **MEMORY** | Your durable facts and skills. |

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| `/` | Jump to Home and focus the capture bar |
| `c` | Chat · `h` Home · `j` Journal · `m` Memory |
| `Esc` | Blur the current input |

Chat history persists across reloads (stored locally in your browser). Use **CLEAR ✕** to reset it.

## Modes

- **Offline (no key):** brief, journal, capture, memory, debrief all work. Brief is a clean structured card.
- **AI mode (with key):** add `GEMINI_API_KEY=your_key` to `.env` in the repo root → chat turns on and briefs/debriefs get AI-written.

## Architecture

- `server.py` — FastAPI backend. Exposes the brain as JSON APIs (`/api/home`, `/api/chat`, `/api/brief`, `/api/journal`, `/api/memory`, `/api/capture`, `/api/debrief`).
- `static/` — hand-built frontend (`index.html`, `style.css`, `app.js`). Zero external dependencies — no CDN, firewall-safe.
- Reads/writes the same `memory/` and `tools/` as everything else. The dashboard is just another engine on top of the brain.

## CLI (no dashboard needed)

```bash
python tools/brief.py --write      # morning brief → today's journal
python tools/debrief.py --text "…" # evening recap
```
