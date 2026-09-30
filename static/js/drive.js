// Drive mode: steer the robot with the keyboard (or on-screen buttons) and watch every sensor live.
import { api, badgeProgress, celebrate, esc, modal, setContext, sfx, state, store } from "./core.js";
import { ArenaView } from "./arena.js";
import { refreshState } from "./kid.js";
import { showBadge } from "./workspace.js";

let session = null;
export function disposeDrive() {
  if (session) { session.stop(); session = null; }
}

const SENSORS = [
  ["distance_front", "Distance front", 200, "cm"], ["distance_left", "Distance left", 200, "cm"], ["distance_right", "Distance right", 200, "cm"],
  ["floor_left", "Floor left", 100, ""], ["floor_center", "Floor centre", 100, ""], ["floor_right", "Floor right", 100, ""],
  ["light_left", "Light left", 100, ""], ["light_right", "Light right", 100, ""], ["heading", "Heading", 180, "°"],
  ["encoder_left", "Encoder left", 0, "cm"], ["encoder_right", "Encoder right", 0, "cm"], ["bumper", "Bumper", 1, ""],
];

export async function viewDrive(app) {
  setContext("_drive", "-");
  const st = await refreshState();
  const list = await api(`/api/learners/${state.learner.id}/arenas`);
  const drivable = [...list.mine.map((a) => ({ ...a, group: "My arenas", kind: "drive" })), ...list.built_in].filter((a) => a.kind !== "arm");
  const selected = store.get("rq_drive_arena", "sandbox:sensor_park");
  app.innerHTML = `<div class="drive-layout">
    <div class="arena-box"><div data-arena></div>
      <div class="row small faint">Keys: <kbd>W</kbd><kbd>A</kbd><kbd>S</kbd><kbd>D</kbd> or arrows to drive · <kbd>Shift</kbd> slow · <kbd>G</kbd> grab/release · <kbd>P</kbd> pen · <kbd>B</kbd> beep · <kbd>R</kbd> back to start</div></div>
    <aside class="stack" style="overflow-y:auto">
      <div class="card"><h3>Drive mode</h3><p class="muted small" style="margin-top:0">Feel how a two-wheeled robot moves, and watch what each sensor reads as you go. Engineers call this <b>teleoperation</b>.</p>
        <select data-pick style="width:100%">${drivable.map((a) => `<option value="${a.ref}" ${a.ref === selected ? "selected" : ""}>${esc(a.group)} — ${esc(a.name)}</option>`).join("")}</select>
        <div class="keys" style="margin-top:12px"><div></div><div data-k="up">W</div><div></div><div data-k="left">A</div><div data-k="down">S</div><div data-k="right">D</div></div>
        <div class="row" style="margin-top:10px;justify-content:center">
          <label class="small">Power <input type="range" min="20" max="100" value="60" data-power style="width:120px;vertical-align:middle;padding:0;border:0"></label></div>
        <div class="row" style="margin-top:6px;justify-content:center"><div class="kv small" data-motors></div></div></div>
      <div class="card"><h3>Live sensors</h3><div class="sensor-grid" data-sensors></div>
        <p class="small muted" style="margin-bottom:0" data-extra></p></div>
      <div class="card"><h3>This drive</h3><div class="kv" data-summary></div>
        <p style="margin:10px 0 0"><button class="btn" data-end>🏁 End drive</button></p></div>
      <div class="card"><h3>Badges</h3>${badgeProgress(st.badges)}
        <p class="faint small" style="margin:0">${st.badges.find((b) => b.id === "driver")?.earned_at
          ? "🎮 Test Driver earned — nice driving!" : "Drive for 5 minutes in total to earn 🎮 Test Driver."}</p></div>
    </aside></div>`;
  const view = new ArenaView(app.querySelector("[data-arena]"));
  const keys = new Set();
  let ws = null, timer = null, closed = false;
  const power = () => +app.querySelector("[data-power]").value;

  function connect(ref) {
    if (ws) ws.close();
    store.set("rq_drive_arena", ref);
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/ws/drive`);
    ws.onopen = () => ws.send(JSON.stringify({ learner: state.learner.id, arena: ref }));
    ws.onmessage = (ev) => {
      const m = JSON.parse(ev.data);
      if (m.t === "arena") view.startLive(m.arena);
      else if (m.t === "state") { view.pushLive(m); panel(m); }
      else if (m.t === "error") app.querySelector("[data-extra]").textContent = m.msg;
      else if (m.t === "summary") showSummary(m);
    };
  }
  function cmd() {
    const up = keys.has("up"), down = keys.has("down"), left = keys.has("left"), right = keys.has("right");
    let p = power() * (keys.has("slow") ? 0.4 : 1), l = 0, r = 0;
    if (up || down) {
      const dir = up ? 1 : -1;
      l = r = p * dir;
      if (left) { l *= 0.35; } if (right) { r *= 0.35; }
    } else if (left) { l = -p * 0.6; r = p * 0.6; } else if (right) { l = p * 0.6; r = -p * 0.6; }
    app.querySelectorAll("[data-k]").forEach((k) => k.classList.toggle("on", keys.has(k.dataset.k)));
    if (ws?.readyState === 1) ws.send(JSON.stringify({ type: "cmd", l, r }));
  }
  function action(a) { if (ws?.readyState === 1) ws.send(JSON.stringify({ type: "action", a, color: "blue" })); }

  function panel(m) {
    const s = m.sensors || {};
    app.querySelector("[data-sensors]").innerHTML = SENSORS.filter(([k]) => k in s).map(([k, label, max, unit]) => {
      const v = s[k];
      const pct = max ? Math.max(0, Math.min(100, (k === "heading" ? (v + 180) / 360 : v / max) * 100)) : 0;
      return `<div class="sensor"><div class="l">${label}</div><div class="v">${k === "bumper" ? (v ? "pressed" : "—") : v}${unit && k !== "bumper" ? ` <span class="faint small">${unit}</span>` : ""}</div>
        ${max ? `<div class="bar"><i style="width:${pct}%"></i></div>` : ""}</div>`;
    }).join("");
    const cam = (m.camera || []).map((c) => `${c.color} ${c.kind} at ${c.angle}°, ${c.distance} cm`).join(" · ");
    app.querySelector("[data-extra]").innerHTML = `Floor colour: <b>${esc(m.color)}</b>${cam ? ` · Camera: ${esc(cam)}` : ""}${m.held !== null && m.held !== undefined ? " · Holding a block" : ""}`;
    app.querySelector("[data-motors]").innerHTML = `<dt>Left motor</dt><dd>${Math.round(m.pl)}</dd><dt>Right motor</dt><dd>${Math.round(m.pr)}</dd>`;
    const su = m.summary;
    app.querySelector("[data-summary]").innerHTML = `<dt>Time</dt><dd>${m.time.toFixed(0)} s</dd><dt>Distance</dt><dd>${Math.round(su.distance)} cm</dd>
      <dt>Crashes</dt><dd>${su.crashes}</dd>${su.gems_total ? `<dt>Gems</dt><dd>${su.gems}/${su.gems_total}</dd>` : ""}${su.laps ? `<dt>Laps</dt><dd>${su.laps}</dd>` : ""}`;
  }

  const map = { ArrowUp: "up", KeyW: "up", ArrowDown: "down", KeyS: "down", ArrowLeft: "left", KeyA: "left", ArrowRight: "right", KeyD: "right", ShiftLeft: "slow", ShiftRight: "slow" };
  const down = (e) => {
    if (/INPUT|SELECT|TEXTAREA/.test(e.target.tagName) && e.target.type !== "range") return;
    if (map[e.code]) { e.preventDefault(); keys.add(map[e.code]); cmd(); }
    else if (e.code === "KeyG") action("grab");
    else if (e.code === "KeyP") action("pen");
    else if (e.code === "KeyB") action("beep");
    else if (e.code === "KeyR") action("reset");
  };
  const up = (e) => { if (map[e.code]) { keys.delete(map[e.code]); cmd(); } };
  window.addEventListener("keydown", down);
  window.addEventListener("keyup", up);
  window.addEventListener("blur", () => { keys.clear(); cmd(); });
  app.querySelectorAll("[data-k]").forEach((k) => {
    const on = (e) => { e.preventDefault(); keys.add(k.dataset.k); cmd(); }, off = () => { keys.delete(k.dataset.k); cmd(); };
    k.addEventListener("pointerdown", on); k.addEventListener("pointerup", off); k.addEventListener("pointerleave", off);
  });
  app.querySelector("[data-pick]").onchange = (e) => connect(e.target.value);
  app.querySelector("[data-end]").onclick = () => {
    keys.clear(); cmd();
    if (ws?.readyState === 1) ws.send(JSON.stringify({ type: "end" }));
  };
  function showSummary(m) {
    ws = null;
    sfx(m.new_badges.length ? "badge" : "ok");
    if (m.new_badges.length) celebrate(0.8);
    m.new_badges.forEach((b, i) => setTimeout(() => showBadge(b), 400 + i * 600));
    const d = modal(`<div class="big">🏁</div><h2>Drive complete</h2>
      <dl class="kv" style="max-width:280px;margin:12px auto;text-align:left">
        <dt>Time</dt><dd>${Math.round(m.seconds)} s</dd><dt>Distance</dt><dd>${Math.round(m.distance)} cm</dd>
        <dt>Crashes</dt><dd>${m.crashes}</dd>${m.gems_total ? `<dt>Gems</dt><dd>${m.gems}/${m.gems_total}</dd>` : ""}${m.laps ? `<dt>Laps</dt><dd>${m.laps}</dd>` : ""}
        ${m.xp ? `<dt>XP</dt><dd>+${m.xp}</dd>` : ""}</dl>
      <div style="text-align:left;margin:14px 0">${badgeProgress(Array.from({ length: m.badges_total }, (_, i) => ({ earned_at: i < m.badges_earned ? 1 : null })))}
        <p class="faint small" style="margin:0">${m.new_badges.length ? `New: ${m.new_badges.map((b) => `${b.emoji} ${esc(b.name)}`).join(", ")}`
          : m.drive_minutes_total >= 5 ? "🎮 Test Driver earned — nice driving!" : `${m.drive_minutes_total} of 5 minutes towards 🎮 Test Driver.`}</p></div>
      <div class="row" style="justify-content:center"><button class="btn primary" data-again>Drive again</button><a class="btn" href="#/home" data-close>Home</a></div>`);
    d.node.querySelector("[data-again]").onclick = () => { d.close(); connect(app.querySelector("[data-pick]").value); };
    refreshState();
  }
  timer = setInterval(cmd, 250);   // keep-alive / resend current command
  connect(selected);
  session = {
    stop: () => {
      if (closed) return;
      closed = true;
      clearInterval(timer);
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
      ws?.close();
      view.dispose();
    },
  };
}
