// Shared helpers: API calls, app state, theme, modals, toasts, sounds, active-time tracker, charts.

export const state = {
  learner: null,     // current learner row
  curriculum: null,  // /api/curriculum
  kidState: null,    // /api/learners/:id/state
  context: { project: "_home", step: "-" },  // what the learner is doing (for time tracking)
};

export async function api(path, opts = {}) {
  const init = { method: opts.method || "GET", headers: {}, credentials: "same-origin" };
  if (opts.body !== undefined) {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(opts.body);
  }
  const r = await fetch(path, init);
  if (!r.ok) {
    let msg = r.statusText;
    try { msg = (await r.json()).detail || msg; } catch (e) { /* not json */ }
    const err = new Error(msg);
    err.status = r.status;
    throw err;
  }
  return r.headers.get("content-type")?.includes("json") ? r.json() : r.text();
}

export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

export function el(html) {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}

export function fmtMin(sec) {
  const m = Math.round((sec || 0) / 60);
  if (m < 60) return `${m} min`;
  return `${Math.floor(m / 60)}h ${m % 60}m`;
}

export function fmtTime(ts) {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

// ---------- theme ----------
const store = {
  get: (k, d) => { try { return localStorage.getItem(k) ?? d; } catch (e) { return d; } },
  set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* storage blocked */ } },
};
export { store };

export function applyTheme(theme, accent) {
  if (theme) store.set("rq_theme", theme);
  if (accent) store.set("rq_accent", accent);
  const t = store.get("rq_theme", "system"), a = store.get("rq_accent", "blue");
  const dark = t === "dark" || (t === "system" && matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  document.documentElement.dataset.accent = a;
  document.dispatchEvent(new CustomEvent("theme-changed"));
}
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => applyTheme());

export function cssVar(name, root = document.documentElement) {
  return getComputedStyle(root).getPropertyValue(name).trim();
}

// ---------- toasts & modals ----------
export function toast(html, ms = 3200) {
  const t = el(`<div class="toast">${html}</div>`);
  document.getElementById("toasts").appendChild(t);
  setTimeout(() => t.remove(), ms);
}

export function modal(html, { wide = false, onClose } = {}) {
  const root = document.getElementById("modal-root");
  const bg = el(`<div class="modal-bg"><div class="modal ${wide ? "wide" : ""}">${html}</div></div>`);
  const close = () => { bg.remove(); document.removeEventListener("keydown", onKey); onClose && onClose(); };
  const onKey = (e) => { if (e.key === "Escape") close(); };
  document.addEventListener("keydown", onKey);
  bg.addEventListener("click", (e) => { if (e.target === bg) close(); });
  bg.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", close));
  root.appendChild(bg);
  return { node: bg.querySelector(".modal"), close };
}

// Calm celebration: a small, soft burst in the theme's muted colours.
export function celebrate(power = 1) {
  if (!window.confetti || store.get("rq_celebrate", "on") === "off") return;
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const colors = [1, 3, 4, 5].map((i) => cssVar(`--series-${i}`));
  confetti({ particleCount: Math.round(40 * power), spread: 55, startVelocity: 28, gravity: 1.1, scalar: .8, ticks: 120, origin: { y: .75 }, colors });
}

// ---------- sound effects (tiny, soft WebAudio tones) ----------
let actx = null;
function ctx() {
  actx = actx || new (window.AudioContext || window.webkitAudioContext)();
  return actx;
}
export function tone(freq, dur = 0.12, vol = 0.06, type = "sine") {
  if (!state.learner || !state.learner.sound) return;
  try {
    const a = ctx(), o = a.createOscillator(), g = a.createGain();
    o.type = type; o.frequency.value = freq;
    g.gain.setValueAtTime(vol, a.currentTime);
    g.gain.exponentialRampToValueAtTime(0.0001, a.currentTime + dur);
    o.connect(g).connect(a.destination);
    o.start(); o.stop(a.currentTime + dur + 0.02);
  } catch (e) { /* audio not available */ }
}
export function sfx(kind) {
  const seq = { run: [[520, .05]], ok: [[660, .07], [880, .1]], fail: [[330, .12]], pass: [[523, .08], [659, .08], [784, .14]],
    level: [[523, .09], [659, .09], [784, .09], [1046, .22]], badge: [[784, .07], [1046, .16]], click: [[700, .025]], error: [[220, .16]] }[kind] || [[440, .08]];
  let t = 0;
  for (const [f, d] of seq) { setTimeout(() => tone(f, d), t * 1000); t += d * 0.9; }
}

// ---------- active-time tracker ----------
// Counts a second only when the tab is visible and the learner did something in the last 90s.
let lastActivity = Date.now(), pending = 0;
["keydown", "mousemove", "mousedown", "wheel", "touchstart"].forEach((ev) =>
  window.addEventListener(ev, () => { lastActivity = Date.now(); }, { passive: true }));
setInterval(() => {
  if (!state.learner || document.visibilityState !== "visible") return;
  if (Date.now() - lastActivity < 90_000) pending += 1;
}, 1000);

function flushTime(beacon = false) {
  if (!state.learner || pending <= 0) return;
  const body = JSON.stringify({ seconds: Math.min(pending, 30), project: state.context.project, step: state.context.step });
  pending = 0;
  const url = `/api/learners/${state.learner.id}/heartbeat`;
  if (beacon && navigator.sendBeacon) navigator.sendBeacon(url, new Blob([body], { type: "application/json" }));
  else fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body }).catch(() => {});
}
setInterval(() => flushTime(), 15_000);
document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") flushTime(true); });
window.addEventListener("pagehide", () => flushTime(true));

export function setContext(project, step) {
  if (state.context.project !== project || state.context.step !== step) flushTime();
  state.context = { project, step };
}

// Small UI signals (throttled) — how he investigates: scrubbing replays, opening telemetry, the manual.
const lastEvent = {};
export function uiEvent(type, where = "", details = null) {
  if (!state.learner) return;
  const k = type + where;
  if (lastEvent[k] && Date.now() - lastEvent[k] < 20_000) return;
  lastEvent[k] = Date.now();
  api(`/api/learners/${state.learner.id}/event`, { method: "POST", body: { type, where, details } }).catch(() => {});
}

// ---------- chart helpers (Chart.js) ----------
export function seriesColors() {
  return [1, 2, 3, 4, 5, 6, 7, 8].map((i) => cssVar(`--series-${i}`));
}
export function chartDefaults() {
  const text = cssVar("--text-2") || "#666", grid = cssVar("--line") || "#ddd";
  Chart.defaults.font.family = "Inter, system-ui, sans-serif";
  Chart.defaults.font.size = 12;
  Chart.defaults.color = text;
  Chart.defaults.borderColor = grid;
  return { text, grid };
}
const charts = new Map();
export function makeChart(canvas, config) {
  if (charts.has(canvas.id)) charts.get(canvas.id).destroy();
  const c = new Chart(canvas, config);
  charts.set(canvas.id, c);
  return c;
}
export function destroyCharts() { charts.forEach((c) => c.destroy()); charts.clear(); }

// ---------- badge progress bar (shared by many pages) ----------
export function badgeProgress(badges) {
  const got = badges.filter((b) => b.earned_at).length, total = badges.length;
  return `<div style="margin-bottom:12px"><div class="row"><span class="muted small">Badges collected</span><span class="spacer"></span>
    <b class="small">${got}/${total}</b></div>
    <div class="progress" style="margin-top:5px" title="${Math.round(got / total * 100)}% of all badges"><i style="width:${total ? got / total * 100 : 0}%"></i></div></div>`;
}
