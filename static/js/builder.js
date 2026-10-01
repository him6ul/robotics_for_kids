// Arena builder: design your own arenas (walls, tape, zones, gems, blocks, lights) and test them.
import { api, celebrate, esc, setContext, state, toast, uiEvent } from "./core.js";
import { ArenaView, colorOf } from "./arena.js";
import { showBadge } from "./workspace.js";
import { badgeProgress, refreshState } from "./kid.js";

const TOOLS = [
  ["start", "🤖", "Robot start", "Click to place, then click again to aim"],
  ["wall", "▬", "Wall", "Click-drag a straight wall"],
  ["box", "■", "Box", "Click-drag a solid box"],
  ["line", "〰", "Tape line", "Click points; double-click to finish (Shift-click closes a loop)"],
  ["zone", "▦", "Colour zone", "Click-drag a coloured floor zone"],
  ["gem", "◆", "Gem", "Click to drop a gem"],
  ["block", "▪", "Block", "Click to drop a block (for grippers)"],
  ["light", "☀", "Light", "Click to place a light bulb"],
  ["erase", "⌫", "Eraser", "Click near anything to remove it"],
];
const COLORS = ["red", "green", "blue", "yellow", "orange", "purple"];
const blank = () => ({ name: "My arena", size: [300, 200], start: [40, 40, 0], time_limit: 60, walls: [], boxes: [], lines: [], zones: [], gems: [], blocks: [], lights: [],
  noise: 0, gps: false, gripper: false });

let view = null;
export function disposeBuilder() { if (view) { view.dispose(); view = null; } }

export async function viewBuilder(app, id) {
  setContext("_builder", id || "new");
  await refreshState();
  let spec = blank(), arenaId = null;
  if (id) {
    const row = await api(`/api/learners/${state.learner.id}/arenas/${id}`);
    spec = { ...blank(), ...row.spec };
    arenaId = row.id;
  }
  const mine = (await api(`/api/learners/${state.learner.id}/arenas`)).mine;
  app.innerHTML = `<div class="builder-layout">
    <aside class="stack" style="overflow-y:auto">
      <div class="card"><h3>Tools</h3><div class="tools">${TOOLS.map(([k, ic, n]) => `<button data-tool="${k}" title="${esc(TOOLS.find((t) => t[0] === k)[3])}"><span class="ic">${ic}</span>${n}</button>`).join("")}</div>
        <p class="faint small" data-help style="margin-bottom:0"></p>
        <div class="choice-grid" data-colors style="margin-top:8px">${COLORS.map((c, i) => `<button class="swatch ${i ? "" : "sel"}" data-c="${c}" style="background:${colorOf(c)}" title="${c}"></button>`).join("")}</div></div>
      <div class="card"><h3>My arenas</h3><div class="list-sm">${mine.map((a) => `<div class="it"><a href="#/builder/${a.id}" style="flex:1">${esc(a.name)}</a><span class="faint small">${a.complexity}</span></div>`).join("") || `<span class="faint">None yet</span>`}</div>
        <p style="margin-bottom:0"><a class="btn small" href="#/builder">+ New arena</a></p></div>
      <div class="card"><h3>Badges</h3><div data-badges></div></div>
    </aside>
    <div class="arena-box"><div data-arena></div><div class="row small faint"><span data-coords>—</span><span class="spacer"></span>
      <button class="btn small ghost" data-undo>Undo</button><button class="btn small ghost" data-clear>Clear all</button></div></div>
    <aside class="stack" style="overflow-y:auto">
      <div class="card"><h3>Settings</h3><div class="stack">
        <label>Name <input data-f="name" value="${esc(spec.name)}" maxlength="40" style="width:100%"></label>
        <div class="row"><label>Width <input type="number" data-f="w" value="${spec.size[0]}" min="80" max="600" style="width:80px"></label>
          <label>Height <input type="number" data-f="h" value="${spec.size[1]}" min="80" max="400" style="width:80px"></label></div>
        <label>Time limit (s) <input type="number" data-f="time_limit" value="${spec.time_limit}" min="5" max="180" style="width:80px"></label>
        <label>Noise (0 = perfect, 1 = wobbly) <input type="range" data-f="noise" min="0" max="1" step="0.1" value="${spec.noise}" style="width:100%;padding:0;border:0"></label>
        <label><input type="checkbox" data-f="gps" ${spec.gps ? "checked" : ""}> GPS (robot.position() works)</label>
        <label><input type="checkbox" data-f="gripper" ${spec.gripper ? "checked" : ""}> Gripper fitted</label>
      </div></div>
      <div class="card"><h3>Save & test</h3><p class="muted small" style="margin-top:0">Design score: <b data-score>—</b>/100 — variety and detail make it higher.</p>
        <div class="row"><button class="btn primary" data-save>Save</button><button class="btn" data-play disabled>Try in Playground</button><button class="btn" data-drive disabled>Drive it</button></div>
        ${arenaId ? `<p style="margin-bottom:0"><button class="btn small ghost" data-del>Delete arena</button></p>` : ""}</div>
      <div class="card"><h3>Challenge idea</h3><p class="muted small" style="margin:0">Build a maze and see if your wall-follower escapes. Or hide gems behind boxes and race a friend in Drive mode.</p></div>
    </aside></div>`;
  const renderBadges = (badges) => {
    const b = badges.find((x) => x.id === "builder");
    app.querySelector("[data-badges]").innerHTML = badgeProgress(badges) + `<p class="faint small" style="margin:0">${b?.earned_at
      ? "🏗️ Arena Architect earned — great designs!" : `Design 3 arenas to earn 🏗️ Arena Architect (${Math.min(mine.length, 3)}/3).`}</p>`;
  };
  renderBadges(state.kidState.badges);
  disposeBuilder();
  view = new ArenaView(app.querySelector("[data-arena]"), { noHud: true });
  const $ = (s) => app.querySelector(s);
  let tool = "wall", color = "red", drag = null, linePts = null, undoStack = [];
  const refresh = () => {
    view.setArena({ ...spec, type: "drive", border: true });
    const kinds = ["walls", "boxes", "lines", "zones", "gems", "blocks", "lights"];
    const variety = kinds.filter((k) => spec[k].length).length;
    const amount = kinds.reduce((a, k) => a + Math.min(spec[k].length, 12), 0);
    const pts = spec.lines.reduce((a, l) => a + l.pts.length, 0);
    const extras = (spec.noise ? 1 : 0) + (spec.gripper ? 1 : 0);
    $("[data-score]").textContent = Math.min(100, Math.round(variety / 7 * 40 + Math.min(amount, 40) / 40 * 35 + Math.min(pts, 40) / 40 * 15 + extras / 3 * 10));
  };
  const snap = (v) => Math.round(v / 5) * 5;
  const push = () => { undoStack.push(JSON.stringify(spec)); if (undoStack.length > 50) undoStack.shift(); };
  const setTool = (t) => {
    tool = t;
    app.querySelectorAll("[data-tool]").forEach((b) => b.classList.toggle("on", b.dataset.tool === t));
    $("[data-help]").textContent = TOOLS.find((x) => x[0] === t)[3];
    linePts = null;
  };
  setTool("wall");
  app.querySelectorAll("[data-tool]").forEach((b) => b.onclick = () => setTool(b.dataset.tool));
  app.querySelectorAll("[data-c]").forEach((b) => b.onclick = () => { color = b.dataset.c; app.querySelectorAll("[data-c]").forEach((x) => x.classList.toggle("sel", x === b)); });

  view.overlay = (g, v) => {
    g.strokeStyle = v.c.accent; g.fillStyle = v.c.accent; g.lineWidth = 2; g.setLineDash([5, 4]);
    if (drag) {
      const [x0, y0] = drag.a, [x1, y1] = drag.b;
      if (tool === "wall") { g.beginPath(); g.moveTo(v.X(x0), v.Y(y0)); g.lineTo(v.X(x1), v.Y(y1)); g.stroke(); }
      else g.strokeRect(v.X(Math.min(x0, x1)), v.Y(Math.max(y0, y1)), Math.abs(x1 - x0) * v.s, Math.abs(y1 - y0) * v.s);
    }
    if (linePts?.length) {
      g.beginPath(); g.moveTo(v.X(linePts[0][0]), v.Y(linePts[0][1]));
      linePts.slice(1).forEach((p) => g.lineTo(v.X(p[0]), v.Y(p[1])));
      if (hover) g.lineTo(v.X(hover[0]), v.Y(hover[1]));
      g.stroke();
    }
    g.setLineDash([]);
  };
  let hover = null;
  const cv = view.canvas;
  const W = (e) => {
    const [x, y] = view.toWorld(e.clientX, e.clientY);
    if (!Number.isFinite(x) || !Number.isFinite(y)) return null;          // canvas not laid out yet
    return [Math.max(0, Math.min(spec.size[0], snap(x))), Math.max(0, Math.min(spec.size[1], snap(y)))];
  };
  cv.addEventListener("pointerdown", (e) => {
    const p = W(e);
    if (!p) return;
    if (["wall", "box", "zone"].includes(tool)) { drag = { a: p, b: p }; cv.setPointerCapture(e.pointerId); }
  });
  cv.addEventListener("pointermove", (e) => {
    const p = W(e);
    if (!p) return;
    hover = p;
    $("[data-coords]").textContent = `x ${p[0]}  y ${p[1]}`;
    if (drag) { drag.b = p; view.draw(); } else if (linePts) view.draw();
  });
  cv.addEventListener("pointerup", (e) => {
    if (!drag) return;
    const [x0, y0] = drag.a, [x1, y1] = drag.b;
    if (!W(e)) { drag = null; return; }
    drag = null;
    if (Math.hypot(x1 - x0, y1 - y0) < 5) { view.draw(); return; }
    push();
    if (tool === "wall") spec.walls.push([x0, y0, x1, y1]);
    else {
      const r = [Math.min(x0, x1), Math.min(y0, y1), Math.abs(x1 - x0), Math.abs(y1 - y0)];
      if (tool === "box") spec.boxes.push(r);
      else spec.zones.push({ name: `${color}${spec.zones.length + 1}`, rect: r, color, label: "" });
    }
    refresh();
  });
  cv.addEventListener("click", (e) => {
    const p = W(e);
    if (!p) return;
    if (tool === "start") {
      push();
      const [sx, sy] = spec.start;
      if (Math.hypot(p[0] - sx, p[1] - sy) < 10 || spec._aim) { spec.start = [sx, sy, Math.round(Math.atan2(p[1] - sy, p[0] - sx) * 180 / Math.PI / 15) * 15]; delete spec._aim; }
      else { spec.start = [p[0], p[1], spec.start[2]]; spec._aim = true; toast("Now click where the robot should face"); }
    } else if (tool === "gem") { push(); spec.gems.push(p); }
    else if (tool === "block") { push(); spec.blocks.push({ pos: p, color }); }
    else if (tool === "light") { push(); spec.lights.push(p); }
    else if (tool === "line") {
      if (!linePts) linePts = [];
      linePts.push(p);
      if (e.shiftKey && linePts.length > 2) { push(); spec.lines.push({ pts: linePts, closed: true, width: 2.5 }); linePts = null; }
    } else if (tool === "erase") erase(p);
    refresh();
  });
  cv.addEventListener("dblclick", () => {
    if (tool === "line" && linePts && linePts.length >= 2) {
      push();
      const pts = linePts.filter((p, i) => i === 0 || p[0] !== linePts[i - 1][0] || p[1] !== linePts[i - 1][1]);
      spec.lines.push({ pts, closed: false, width: 2.5 });
      linePts = null; refresh();
    }
  });
  function erase([x, y]) {
    const near = (px, py) => Math.hypot(px - x, py - y) < 8;
    const segNear = (x1, y1, x2, y2) => {
      const dx = x2 - x1, dy = y2 - y1, L = dx * dx + dy * dy || 1, t = Math.max(0, Math.min(1, ((x - x1) * dx + (y - y1) * dy) / L));
      return Math.hypot(x1 + t * dx - x, y1 + t * dy - y) < 6;
    };
    const inRect = ([rx, ry, rw, rh]) => x >= rx && x <= rx + rw && y >= ry && y <= ry + rh;
    push();
    for (const [k, test] of [["gems", (g) => near(g[0], g[1])], ["lights", (l) => near(l[0], l[1])], ["blocks", (b) => near(b.pos[0], b.pos[1])],
      ["walls", (w) => segNear(...w)], ["lines", (l) => l.pts.some((p, i) => i && segNear(l.pts[i - 1][0], l.pts[i - 1][1], p[0], p[1]))],
      ["boxes", inRect], ["zones", (z) => inRect(z.rect)]]) {
      const i = spec[k].findIndex(test);
      if (i >= 0) { spec[k].splice(i, 1); return; }
    }
    undoStack.pop();
  }
  app.querySelectorAll("[data-f]").forEach((inp) => inp.addEventListener("change", () => {
    const f = inp.dataset.f;
    if (f === "w") spec.size[0] = +inp.value;
    else if (f === "h") spec.size[1] = +inp.value;
    else if (inp.type === "checkbox") spec[f] = inp.checked;
    else if (inp.type === "number" || inp.type === "range") spec[f] = +inp.value;
    else spec[f] = inp.value;
    refresh();
  }));
  $("[data-undo]").onclick = () => { if (undoStack.length) { spec = JSON.parse(undoStack.pop()); refresh(); } };
  $("[data-clear]").onclick = () => { if (confirm("Clear everything?")) { push(); spec = { ...blank(), name: spec.name, size: spec.size }; refresh(); } };
  const enable = (ref) => {
    $("[data-play]").disabled = false; $("[data-drive]").disabled = false;
    $("[data-play]").onclick = () => { location.hash = `#/playground/${encodeURIComponent(ref)}`; };
    $("[data-drive]").onclick = () => { try { localStorage.setItem("rq_drive_arena", ref); } catch (e) { /* */ } location.hash = "#/drive"; };
  };
  if (arenaId) enable(`custom:${arenaId}`);
  $("[data-save]").onclick = async () => {
    const clean = { ...spec }; delete clean._aim;
    const r = await api(`/api/learners/${state.learner.id}/arenas`, { method: "POST", body: { id: arenaId, spec: clean } });
    const first = !arenaId;
    arenaId = r.id;
    toast(`Saved “${esc(r.spec.name)}” · design score ${r.complexity}${r.xp ? ` · +${r.xp} XP` : ""}`);
    if (first) celebrate(0.6);
    r.badges.forEach((b) => showBadge(b, r.badge_count));
    if (first) mine.push({ id: r.id });
    refreshState().then((st) => renderBadges(st.badges));
    uiEvent("builder.test", `arena/${r.id}`);
    enable(r.ref);
    if (first) window.history.replaceState(null, "", `#/builder/${r.id}`);
  };
  $("[data-del]")?.addEventListener("click", async () => {
    if (!confirm("Delete this arena?")) return;
    await api(`/api/learners/${state.learner.id}/arenas/${arenaId}`, { method: "DELETE" });
    location.hash = "#/builder";
  });
  refresh();
}
