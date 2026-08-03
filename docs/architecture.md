# Jarvis — architecture decisions (desktop + mobile, shared brain, open-source models)

> **BLUF:** You don't need to spin up instances, detect phone-off, or reset sessions.
> There is **one brain** (this repo) and **many thin clients** (desktop, phone, feature
> tabs, the career app). Clients hold no state. The brain is the single source of truth.
> Everything below is the phased path to that, with the hard calls made for you.

This doc answers the architecture brainstorm from 2026-08-01 (the FAANG-friend session):
Electron, `orc`/taskgraph, Qwen/Docker deployment, iPhone, and shared context. It's a
**decision record** — read it once, stop re-litigating it in your head.

---

## The one idea that dissolves the worry: one brain, many thin clients

Your whole tangle — *"do I spin up an instance per feature, per device? detect the phone
turning off and reset? does it live inside a chat like Claude?"* — comes from imagining
**stateful agents** you have to keep alive and synchronize.

You don't have those. Here's why:

- **LLM calls are stateless.** Every turn, you *send* the context and *get back* text.
  There is nothing to "keep running" between turns. The model doesn't remember — your
  brain files do.
- So there is no "instance" to spin up, keep warm, or reset. There is **one backend
  service** that, on each request, reads the brain, assembles context, makes one model
  call, and writes anything durable back. Close the phone mid-thought? Nothing to reset —
  the last thing worth keeping was already a file.
- **"Push upstream when new info is gained"** — you already named the mechanism. It's a
  **commit**. When any client learns a durable fact, it writes the fact file and commits.
  Other clients pull. That's the sync.

**Mental model:**

```
                 ┌─────────────────────────────┐
                 │   THE BRAIN  (this git repo) │
                 │  memory/ · skills/ · tools/  │  ← single source of truth
                 │  config/providers.yaml       │
                 └─────────────┬───────────────┘
                               │  read context / write facts
          ┌────────────────────┼────────────────────┐
          │                    │                     │
   desktop dashboard     phone (PWA)          career app / feature tab
   (thin client)         (thin client)        (thin client)
```

Every surface is a **window onto the same brain**, not its own agent. Get this and the
rest is just "how does each window reach the brain," which is the phased part.

---

## Decisions (what to do, with conviction)

### 1. Frontend: **PWA now, Electron only if a native need appears** — 85% confident

Your friend suggested Electron. I'd push back.

- Electron is **desktop-only** and ships a ~100MB Chromium wrapper around a web page **you
  already have** (the dashboard). It buys you native menus, a tray icon, global hotkeys.
- A **PWA** (installable web app) gets you a desktop "app" install **and** a phone
  home-screen app **from the one codebase you already wrote**. That is *literally* your
  "desktop, then mobile on the go" goal — in one move, near-zero cost.
- **Assumption I'm making:** you don't yet need OS-level integration (global hotkey, tray,
  file associations). The day you do, wrap the *same* web app in Electron/Tauri then —
  it's additive, not a rewrite. **Tauri over Electron** when that day comes (Rust, ~3MB
  vs ~100MB).

**Verdict:** Make the dashboard a PWA. Electron is a later, optional shell — not the path.

### 2. Orchestrator: **keep your own; `orc` and taskgraph are not dependencies** — 90% confident

I read both.

- **`orc` (sebastiengilbert73/orc)** — 2 stars, 38 commits, proof-of-concept. Its stack is
  **FastAPI + SQLite + React + Ollama** — *almost exactly what Jarvis already is.* That's
  the useful signal: it **validates your architecture**. It is far too immature to build
  on. **Steal ideas** (agent personas, human-in-the-loop approval, a live status view),
  not the code.
- **taskgraph (Mozilla Taskcluster)** — the engine that runs **Firefox's 30,000-task CI
  graph.** It is industrial CI infrastructure. For a personal assistant it is the wrong
  scale by three orders of magnitude. The *concept* — declaring multi-step work as a DAG
  with dependencies — is worth borrowing **later**, when you want autonomous multi-step
  runs. When that day comes, a ~50-line runner or a tiny lib like `daglib` is the right
  size, not Taskcluster.

**Verdict:** Your skill-based workflow model is the right size today. Don't adopt either.
Revisit a small DAG runner only when a real multi-step autonomous workflow needs it.

### 3. Models: **self-hosting Qwen is already a config flip** — verified, not vibes

This is the payoff of the Layer-B design (`tools/llm.py` + `config/providers.yaml`).
I added ready-to-use `qwen`, `kimi`, and `ollama-qwen` provider profiles and **proved the
swap**: flipping `active: gemini` → `active: ollama-qwen` changed the engine from
`gemini/gemini-2.5-flash` to `ollama/qwen2.5 (no API key required)` with **zero code
changed**. Try it:

```bash
python tools/llm.py            # active model: gemini/gemini-2.5-flash (key ...)
# edit config/providers.yaml → active: ollama-qwen
python tools/llm.py            # active model: ollama/qwen2.5 (no API key required)
```

**Deployment (Docker + Qwen on a hosted box)** is real and cheap with your credits, but
it's **Phase 3, not now.** You only need it when you want always-on inference the phone
can reach without your desktop being up. When you do: run Ollama (or vLLM) in a Docker
container on **Cloud Run / a small always-on VM** (GCP $300/3mo or AWS $200/6mo), and
point `ollama-qwen`'s `api_base` at it. Same config entry, new URL.

### 4. iPhone: **thin client to the brain, not local inference** — 80% confident

Running a mini-model on the phone via Apple Metal is a cool trick, but it's the wrong
first move.

- For a personal assistant, the **quality bottleneck is context/memory, not where
  inference runs.** A phone-sized model gives materially worse answers than your phone
  hitting a real backend with your full brain loaded.
- **Path:** phone = the **PWA** (Decision 1), talking to the hosted brain (Decision 3).
  One codebase, real answers, your whole memory available.
- **Local-on-phone inference** is a nice **offline fallback** for later — not the primary
  path, and possibly never worth the effort. Don't build it now.

### 5. Shared context: **don't redesign memory — make the one you have reachable**

Your two-tier memory (episodic append-only journal + small deduped durable overlay) is
**already the efficient model.** The gap isn't the design; it's that the files are
local-only. Two phases, and you're already standing in Phase 1:

| Phase | Sync mechanism | Real-time? | Cost | When |
|-------|----------------|-----------|------|------|
| **1 (now)** | **Git.** Private repo = versioned shared brain. Clients clone; writes commit+push; others pull. | No (pull to refresh) | Free | Today — the plan already says this |
| **2 (later)** | **Hosted brain API.** Backend on one always-on host; clients hit it over HTTPS; capture-on-phone shows on desktop live. | Yes | ~$0 on free credits | When you actually feel the pull-to-refresh friction |

**The rule that makes "push upstream on new info" concrete:** a durable fact learned on
*any* client = write the fact file + commit + push. That's it. That IS the upstream push
you described — no new system needed.

---

## Phased roadmap (so "everything" becomes an ordered list, not a cloud)

- **Phase 1 — one brain, reachable (now).**
  - [x] Layer-B provider swap proven (Qwen/Ollama profiles live).
  - [ ] Make the dashboard a **PWA** (installable desktop + phone, one codebase).
  - [ ] Private GitHub repo as the sync layer; document the clone/pull/commit loop.
- **Phase 2 — hosted brain (when pull-to-refresh annoys you).**
  - [ ] Put the FastAPI backend on one always-on host (free credits).
  - [ ] Clients (desktop PWA, phone PWA) point at it; capture syncs live.
- **Phase 3 — self-hosted open model (when you want cheap always-on inference).**
  - [ ] Qwen in Docker (Ollama/vLLM) on the same host; flip `api_base`.
- **Phase 4 — autonomous multi-step (only if a real workflow needs it).**
  - [ ] Tiny DAG runner (~50 lines / `daglib`) for chained tasks. Not Taskcluster.
  - [ ] Optional native shell (**Tauri**, not Electron) if you need global hotkeys/tray.

**Cost reality check:** Phases 1–3 fit inside the free credits with one small always-on
host. You are not paying per-instance-per-feature — there is one backend and one model
endpoint, shared. The "spin up an instance for every tab" fear was the thing to avoid, and
this architecture avoids it by design.

---

## What I changed in this pass

- `config/providers.yaml` — added real `qwen`, `kimi`, `ollama-qwen` profiles; verified the
  swap changes the resolved model with no code edit.
- `docs/architecture.md` — this decision record.

**Open question for you (one thing):** do you want me to do the **PWA conversion next**
(installable on desktop + phone, ~15 min, the single highest-value step toward your
whole vision)? It's additive and reversible.
