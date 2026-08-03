"""
dashboard/start.py — one-step launcher for the Jarvis dashboard.

Removes daily-use friction: ensures deps are installed, starts the server, and
opens your browser to the dashboard. Cross-platform (Windows / macOS / Linux).

    python dashboard/start.py

On Windows you can also just double-click start-jarvis.bat in the repo root.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQS = Path(__file__).resolve().parent / "requirements.txt"
URL = "http://localhost:8000"
REQUIRED = ["fastapi", "uvicorn", "yaml"]  # import names (pyyaml imports as 'yaml')


def _missing() -> list[str]:
    return [m for m in REQUIRED if importlib.util.find_spec(m) is None]


def _ensure_deps() -> None:
    missing = _missing()
    if not missing:
        return
    print(f"Installing dashboard dependencies ({', '.join(missing)})...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(REQS)])
    except subprocess.CalledProcessError:
        print(
            "\nCouldn't auto-install. Run this once yourself, then re-launch:\n"
            f"    pip install -r {REQS}\n"
        )
        sys.exit(1)


def _open_browser_when_ready() -> None:
    """Poll the server, then open the browser once it responds."""
    import urllib.request

    for _ in range(40):  # ~20s max
        try:
            urllib.request.urlopen(URL + "/api/status", timeout=1)
            webbrowser.open(URL)
            return
        except Exception:
            time.sleep(0.5)


def main() -> None:
    _ensure_deps()
    print(f"\n  🧠 Jarvis dashboard starting at {URL}  (Ctrl+C to stop)\n")
    threading.Thread(target=_open_browser_when_ready, daemon=True).start()

    import uvicorn

    # Import the app after deps are guaranteed present.
    sys.path.insert(0, str(ROOT))
    from dashboard.server import app

    try:
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
    except KeyboardInterrupt:
        print("\n  Jarvis dashboard stopped.\n")


if __name__ == "__main__":
    main()
