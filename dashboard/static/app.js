/* ============================================================
   Jarvis dashboard — frontend logic
   No external dependencies (firewall-safe). Minimal MD renderer.
   ============================================================ */

// ---------- tiny markdown → HTML (safe-ish, self-contained) ----------
function esc(s) {
  // Escapes text AND attribute contexts (quotes included) — data-loop="..." injects
  // captured text into an attribute, so " and ' must be encoded too.
  return String(s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
function md(src) {
  if (!src) return "";
  let s = esc(src);
  // code fences
  s = s.replace(/```([\s\S]*?)```/g, (_, c) => `<pre><code>${c.trim()}</code></pre>`);
  // inline code
  s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
  // headers
  s = s.replace(/^###\s+(.*)$/gm, "<h3>$1</h3>");
  s = s.replace(/^##\s+(.*)$/gm, "<h2>$1</h2>");
  s = s.replace(/^#\s+(.*)$/gm, "<h1>$1</h1>");
  // bold / italic (underscore-italic only at word boundaries, so GEMINI_API_KEY is safe)
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
  s = s.replace(/(^|[\s(>])_([^_\n]+?)_(?=[\s).,!?:<]|$)/g, "$1<em>$2</em>");
  // blockquote
  s = s.replace(/^&gt;\s?(.*)$/gm, "<blockquote>$1</blockquote>");
  // hr
  s = s.replace(/^---$/gm, "<hr>");
  // bullets
  s = s.replace(/(?:^[-*]\s+.*(?:\n|$))+/gm, (block) => {
    const items = block.trim().split("\n").map(l => l.replace(/^[-*]\s+/, "")).map(l => `<li>${l}</li>`).join("");
    return `<ul>${items}</ul>`;
  });
  // paragraphs / line breaks
  s = s.split(/\n{2,}/).map(p => {
    if (/^\s*<(h\d|ul|pre|blockquote|hr)/.test(p)) return p;
    return `<p>${p.replace(/\n/g, "<br>")}</p>`;
  }).join("");
  return s;
}

// ---------- helpers ----------
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));
async function api(path, opts) {
  const res = await fetch(path, opts);
  return res.json();
}
async function post(path, body) {
  return api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}
let toastTimer;
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 2200);
}

// ---------- density (Focus / Full) — user-controlled declutter ----------
const DENSITY_KEY = "jarvis.density.v1";
function applyDensity(mode) {
  const focus = mode === "focus";
  document.body.classList.toggle("focus-mode", focus);
  const btn = $("#density-toggle");
  if (btn) btn.textContent = focus ? "◱ FOCUS" : "◱ FULL";
  try { localStorage.setItem(DENSITY_KEY, mode); } catch {}
}
$("#density-toggle")?.addEventListener("click", () => {
  applyDensity(document.body.classList.contains("focus-mode") ? "full" : "focus");
});

// ---------- clock ----------
function tickClock() {
  const now = new Date();
  const h = String(now.getHours()).padStart(2, "0");
  const m = String(now.getMinutes()).padStart(2, "0");
  const s = String(now.getSeconds()).padStart(2, "0");
  const el = $("#clock");
  if (el) el.textContent = `${h}:${m}:${s}`;
  const sync = $("#sb-sync");
  if (sync) sync.textContent = `${h}:${m}:${s}`;
  // hero clock (focus mode) — HH:MM big, seconds small
  const hc = $("#hero-clock");
  if (hc) hc.textContent = `${h}:${m}`;
  const hs = $("#hero-secs");
  if (hs) hs.textContent = s;
}
setInterval(tickClock, 1000);
tickClock();

// ---------- nav (hash-routed, deep-linkable) ----------
let KEY_SET = false;
function showView(view) {
  if (!["home", "chat", "journal", "memory"].includes(view)) view = "home";
  $$(".nav-item").forEach(b => b.classList.toggle("active", b.dataset.view === view));
  $$(".view").forEach(v => v.classList.remove("active"));
  $(`#view-${view}`).classList.add("active");
  if (view === "journal") loadJournal();
  if (view === "memory") loadMemory();
  if (view === "chat") { updateChatEmptyState(); setTimeout(() => $("#chat-input")?.focus(), 100); }
  if (location.hash !== `#${view}`) location.hash = view;
}
$$(".nav-item").forEach(btn => {
  btn.addEventListener("click", () => showView(btn.dataset.view));
});
window.addEventListener("hashchange", () => showView(location.hash.replace("#", "") || "home"));

// ---------- status chip ----------
async function loadStatus() {
  const s = await api("/api/status");
  KEY_SET = s.key_set;
  $("#topdate").textContent = s.date_short;
  const chip = $("#statuschip");
  if (s.key_set) {
    chip.textContent = `● ${s.model}`;
    chip.className = "chip chip-ok";
  } else {
    chip.textContent = "○ NO API KEY";
    chip.className = "chip chip-warn";
    chip.title = "Add GEMINI_API_KEY to .env to enable chat and AI briefs";
  }
  // HUD status bar
  const sbModel = $("#sb-model");
  if (sbModel) sbModel.textContent = (s.key_set ? s.model : "OFFLINE").toUpperCase();
}

// ---------- HOME ----------
async function loadHome() {
  const h = await api("/api/home");
  $("#greeting").innerHTML = `${h.greeting}, <em>${h.operator.name}</em>.`;
  $("#session-date").textContent = h.date;
  $("#op-name").textContent = h.operator.name;
  $("#op-role").textContent = h.operator.role;
  $("#op-focus").textContent = h.operator.focus;
  $("#op-streak").textContent = h.streak;

  // momentum ring — reward the daily loop; full ring = a small celebration
  if (h.momentum) {
    const m = h.momentum;
    const complete = m.done === m.total;
    const deg = Math.round(m.pct * 3.6);
    const ring = $("#momentum-ring");
    ring.style.background = `conic-gradient(var(--accent) ${deg}deg, var(--bg-2) ${deg}deg)`;
    ring.classList.toggle("complete", complete);
    $("#momentum-num").innerHTML = complete
      ? `<span class="mm-check">✓</span>`
      : `${m.done}<small>/${m.total}</small>`;
    const items = [
      ["Brief", m.briefed], ["Capture", m.captured], ["Debrief", m.debriefed],
    ];
    $("#momentum-legend").innerHTML =
      (complete ? `<div class="mlg-complete">Day complete</div>` : "") +
      items.map(([label, done]) =>
        `<div class="mlg ${done ? "done" : ""}"><span class="mlg-dot"></span>${label}</div>`
      ).join("");
  }

  // 7-day sparkline (real journal activity)
  if (h.activity7) {
    const max = Math.max(1, ...h.activity7.map(d => d.count));
    $("#spark").innerHTML = h.activity7.map(d => {
      const pct = Math.round((d.count / max) * 100);
      const active = d.count > 0;
      return `<div class="spark-col"><div class="spark-bar ${active ? "on" : ""}" style="height:${Math.max(pct, 6)}%"></div><div class="spark-day">${d.day}</div></div>`;
    }).join("");
  }

  // projects
  const pl = $("#projects-list");
  pl.innerHTML = h.projects.map(p =>
    `<div class="project"><div class="project-name">${esc(p.name)}</div>${p.desc ? `<div class="project-desc">${esc(p.desc)}</div>` : ""}</div>`
  ).join("") || `<div class="empty">No projects listed.</div>`;

  // today sections + open-loops checklist
  renderToday(h.today_sections, h.open_loops || []);

  // brief — auto-load if today has a Morning section (strip the leading _HH:MM_ stamp)
  const morning = h.today_sections.find(s => s.heading === "Morning");
  if (morning) {
    const body = morning.body.replace(/^_\d{1,2}:\d{2}_\s*/, "");
    $("#brief-body").innerHTML = md(body);
  }
}

function renderToday(sections, openLoops) {
  const tb = $("#today-body");
  // hidden from the free-text list: rendered specially or not useful here
  const HIDE = new Set(["Morning", "Open loops", "Closed"]);
  const other = sections.filter(s => !HIDE.has(s.heading));

  let html = "";

  // Open-loops checklist first — the satisfying check-off
  if (openLoops && openLoops.length) {
    html += `<div class="today-section"><div class="today-section-h">Open loops</div><div class="loops">`;
    html += openLoops.map(l =>
      `<label class="loop ${l.closed ? "done" : ""}">
        <input type="checkbox" ${l.closed ? "checked disabled" : ""} data-loop="${esc(l.text)}">
        <span class="loop-box"></span><span class="loop-text">${esc(l.text)}</span>
      </label>`
    ).join("");
    html += `</div></div>`;
  }

  // Any other captured sections as plain text
  html += other.map(s =>
    `<div class="today-section"><div class="today-section-h">${esc(s.heading)}</div><div class="today-section-b">${md(s.body)}</div></div>`
  ).join("");

  if (!html) {
    tb.innerHTML = `<div class="empty-state">
      <div class="empty-mark">✓</div>
      <div class="empty-title">A clean slate.</div>
      <div class="empty-note">Capture a thought above, or generate your brief to line up the day.</div>
    </div>`;
    return;
  }
  tb.innerHTML = html;

  // wire checkboxes
  tb.querySelectorAll('input[data-loop]:not([disabled])').forEach(cb => {
    cb.addEventListener("change", async () => {
      if (!cb.checked) return;
      const text = cb.dataset.loop;
      cb.disabled = true;
      cb.closest(".loop").classList.add("done");
      await post("/api/close-loop", { text });
      toast("Loop closed ✓");
    });
  });
}

// capture
$("#capture-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = $("#capture-input");
  const text = input.value.trim();
  if (!text) return;
  await post("/api/capture", { text, section: "Quick capture" });
  input.value = "";
  $("#capture-hint").textContent = "✓ captured to today's journal";
  setTimeout(() => $("#capture-hint").textContent = "", 2500);
  loadHome();
});

// quick actions
$$(".qa").forEach(btn => btn.addEventListener("click", () => {
  const action = btn.dataset.action;
  if (action === "brief") { showView("home"); $("#gen-brief").click(); }
  else if (action === "chat") { showView("chat"); }
  else if (action === "debrief") { showView("home"); $("#debrief-input")?.focus(); $("#debrief-input")?.scrollIntoView({behavior:"smooth"}); }
}));

// generate brief
$("#gen-brief").addEventListener("click", async () => {
  const bb = $("#brief-body");
  bb.innerHTML = `<div class="empty">Generating${KEY_SET ? " with AI" : ""}…</div>`;
  const r = await post("/api/brief", { use_llm: KEY_SET, save: true });
  if (r.ok) {
    bb.innerHTML = md(r.brief);
    toast("Brief generated");
    loadHome();
  } else {
    bb.innerHTML = `<div class="empty">Error: ${esc(r.error || "unknown")}</div>`;
  }
});

// debrief
$("#save-debrief").addEventListener("click", async () => {
  const inp = $("#debrief-input");
  const text = inp.value.trim();
  if (!text) { toast("Nothing to save"); return; }
  $("#save-debrief").textContent = "SAVING…";
  const r = await post("/api/debrief", { text, use_llm: KEY_SET });
  $("#save-debrief").textContent = "SAVE RECAP ▸";
  if (r.ok) {
    inp.value = "";
    toast("Evening recap saved");
    loadHome();
  } else {
    toast("Error saving");
  }
});

// ---------- CHAT ----------
const CHAT_KEY = "jarvis.chat.v1";
function loadChatHistory() {
  try { return JSON.parse(localStorage.getItem(CHAT_KEY)) || []; }
  catch { return []; }
}
function saveChatHistory() {
  try { localStorage.setItem(CHAT_KEY, JSON.stringify(chatHistory.slice(-40))); } catch {}
}
let chatHistory = loadChatHistory();

// Re-render any persisted conversation on load
function restoreChat() {
  if (!chatHistory.length) return;
  $("#chat-empty")?.remove();
  const log = $("#chat-log");
  log.innerHTML = "";
  chatHistory.forEach(m => appendMsg(m.role, m.content));
}
$("#chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = $("#chat-input");
  const text = input.value.trim();
  if (!text) return;

  if (!KEY_SET) {
    appendMsg("assistant", "**No API key set.** Add `GEMINI_API_KEY=your_key` to `.env` in the repo root, then restart the dashboard. Everything else works offline.");
    return;
  }

  $("#chat-empty")?.remove();
  appendMsg("user", text);
  chatHistory.push({ role: "user", content: text });
  saveChatHistory();
  input.value = "";

  const typing = appendTyping();
  const btn = $(".chat-send");
  btn.disabled = true;

  const r = await post("/api/chat", { messages: chatHistory });
  typing.remove();
  btn.disabled = false;

  if (r.ok) {
    appendMsg("assistant", r.reply);
    chatHistory.push({ role: "assistant", content: r.reply });
    saveChatHistory();
  } else {
    appendMsg("assistant", `**Error:** ${r.error}`);
  }
  input.focus();
});

// When Chat is opened with no key (and no history), show inviting onboarding
// instead of a dead orb — so the path to turning Jarvis "online" is obvious.
function updateChatEmptyState() {
  const empty = $("#chat-empty");
  if (!empty || chatHistory.length) return;
  if (KEY_SET) return;
  empty.innerHTML = `
    <div class="chat-empty-orb dim"></div>
    <div class="chat-empty-title">Bring Jarvis online</div>
    <div class="chat-empty-sub">Chat &amp; AI briefs need one free key. Two steps:</div>
    <ol class="onboard">
      <li>Get a free key at <span class="ob-code">aistudio.google.com/apikey</span></li>
      <li>Create <span class="ob-code">.env</span> in the repo root with:<br><span class="ob-code">GEMINI_API_KEY=your_key</span></li>
    </ol>
    <div class="chat-empty-sub">Then restart the dashboard. Everything else works offline right now.</div>`;
}

// Clear conversation (memory + storage)
$("#chat-clear")?.addEventListener("click", () => {
  chatHistory = [];
  saveChatHistory();
  const log = $("#chat-log");
  log.innerHTML = `<div class="chat-empty" id="chat-empty">
    <div class="chat-empty-orb"></div>
    <div class="chat-empty-title">Talk to Jarvis</div>
    <div class="chat-empty-sub">It already knows who you are.</div></div>`;
  toast("Conversation cleared");
});

function appendMsg(role, content) {
  const log = $("#chat-log");
  const div = document.createElement("div");
  div.className = `msg msg-${role}`;
  const avatar = role === "assistant" ? "🧠" : "F";
  div.innerHTML = `<div class="msg-avatar">${avatar}</div><div class="msg-bubble">${md(content)}</div>`;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
  return div;
}
function appendTyping() {
  const log = $("#chat-log");
  const div = document.createElement("div");
  div.className = "msg msg-assistant";
  div.innerHTML = `<div class="msg-avatar">🧠</div><div class="msg-bubble"><span class="typing"><span></span><span></span><span></span></span></div>`;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
  return div;
}

// ---------- JOURNAL ----------
async function loadJournal(iso) {
  const data = await api("/api/journal" + (iso ? `?d=${iso}` : ""));
  const dl = $("#journal-dates");
  dl.innerHTML = data.dates.map(d =>
    `<div class="jdate ${d.iso === data.selected ? "active" : ""}" data-iso="${d.iso}">${d.label}</div>`
  ).join("") || `<div class="empty">No entries yet.</div>`;
  dl.querySelectorAll(".jdate").forEach(el =>
    el.addEventListener("click", () => loadJournal(el.dataset.iso))
  );

  const jc = $("#journal-content");
  if (!data.sections.length) {
    jc.innerHTML = `<div class="empty">No entry for this day.</div>`;
    return;
  }
  jc.innerHTML = data.sections.map(s =>
    `<div class="jsection"><div class="jsection-h">${esc(s.heading)}</div><div class="jsection-b">${md(s.body)}</div></div>`
  ).join("");
}

// ---------- MEMORY ----------
async function loadMemory() {
  const data = await api("/api/memory");
  $("#memory-files").innerHTML = data.files.map(f =>
    `<div class="mem-card"><div class="mem-name">${esc(f.name)}</div><div class="mem-body">${md(f.body)}</div></div>`
  ).join("") || `<div class="empty">No memory files.</div>`;
  $("#memory-skills").innerHTML = data.skills.map(s =>
    `<div class="skill-card"><div class="skill-name">⚡ ${esc(s.name)}</div><div class="skill-desc">${esc(s.desc || "")}</div></div>`
  ).join("") || `<div class="empty">No skills.</div>`;
}

// ---------- keyboard shortcuts (power-user, invisible until used) ----------
document.addEventListener("keydown", (e) => {
  const typing = /^(INPUT|TEXTAREA)$/.test(document.activeElement?.tagName || "");
  if (e.key === "Escape" && typing) { document.activeElement.blur(); return; }
  if (typing) return;
  if (e.key === "/") { e.preventDefault(); showView("home"); $("#capture-input")?.focus(); }
  else if (e.key === "c") { showView("chat"); }
  else if (e.key === "h") { showView("home"); }
  else if (e.key === "j") { showView("journal"); }
  else if (e.key === "m") { showView("memory"); }
});

// ---------- init ----------
(async function init() {
  // Default to FOCUS (calm) — Fakhri's dominant feedback was "too cluttered", so the
  // first impression should be the decluttered view. Toggle to FULL is one click.
  applyDensity(localStorage.getItem(DENSITY_KEY) || "focus");
  await loadStatus();
  await loadHome();
  restoreChat();
  const initial = location.hash.replace("#", "");
  if (initial && initial !== "home") showView(initial);
})();

// ---------- PWA: register the service worker (installable + offline shell) ----------
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {/* non-fatal — app still works */});
  });
}
