// The robot workspace: code editor + arena replay + console / telemetry / results.
// Used by missions, side quests, the playground and the remix lab.
import { api, badgeProgress, celebrate, el, esc, modal, sfx, state, toast, uiEvent } from "./core.js";
import { ArenaView } from "./arena.js";
import { Telemetry } from "./telemetry.js";
import { createTutor } from "./tutor.js";
import { robotHint, toggleManual } from "./manual.js";

export function createWorkspace(host, { project, step, mode = "step", checkable = true, onPassed, extraButtons = "", arenaRef = null,
  arenaChoices = null, onArenaChange = null }) {
  host.innerHTML = `
    <div class="coding">
      <div class="toolbar">
        <button class="btn primary" data-act="run" title="Run (Ctrl+Enter)">▶ Run</button>
        ${checkable ? `<button class="btn" data-act="check">✓ Test my robot</button>` : ""}
        ${extraButtons}
        ${arenaChoices ? `<select data-arena-pick title="Arena">${arenaChoices}</select>` : ""}
        <span class="spacer"></span>
        <button class="btn ghost small" data-act="manual" title="Every robot command">📘 Manual</button>
        ${state.tutor?.available ? `<button class="btn soft small" data-act="tutor" title="Ask Sprocket, your AI tutor">🔧 Ask Sprocket</button>
          <button class="btn ghost small" data-act="review" title="Get feedback on your code">Review</button>` : ""}
        <span class="saved-ind" data-saved></span>
        <button class="btn ghost small" data-act="font" title="Bigger / smaller text">A±</button>
        <button class="btn ghost small" data-act="reset" title="Start this mission's code over">↺</button>
      </div>
      <div class="split">
        <div class="editor-wrap"></div>
        <div class="arena-box">
          <div data-arena></div>
          <div class="replay">
            <button class="btn small" data-act="restart" title="Restart replay">⏮</button>
            <button class="btn small" data-act="play" title="Play / pause (space)">▶</button>
            <div class="seg" data-speed>${[0.5, 1, 2, 4].map((s) => `<button data-s="${s}" class="${s === 1 ? "on" : ""}">${s}×</button>`).join("")}</div>
            <input type="range" min="0" max="1000" value="0" data-scrub aria-label="Replay position">
            <span class="tlabel" data-tlabel>0.0 / 0.0 s</span>
            <button class="btn ghost small" data-act="rays" title="Show / hide sensor beams">👁</button>
          </div>
        </div>
      </div>
      <div class="bottom">
        <div class="tabs"><button data-tab="console" class="on">Console</button><button data-tab="telemetry">Telemetry</button><button data-tab="result">Result</button></div>
        <div class="panel" data-panel="console"><div class="console" aria-live="polite"><span class="sys">Press ▶ Run and watch your robot. What it prints shows up here, time-stamped.</span></div></div>
        <div class="panel hidden" data-panel="telemetry"></div>
        <div class="panel hidden" data-panel="result"><p class="faint small" style="padding:10px 12px">Run your robot, then press <b>Test my robot</b> to check the mission goals.</p></div>
      </div>
    </div>`;
  const $ = (s) => host.querySelector(s);
  const cm = CodeMirror($(".editor-wrap"), {
    mode: "python", lineNumbers: true, indentUnit: 4, tabSize: 4, indentWithTabs: false, matchBrackets: true,
    autoCloseBrackets: true, styleActiveLine: true, lineWrapping: false, value: "",
    extraKeys: {
      Tab: (c) => (c.somethingSelected() ? c.indentSelection("add") : c.replaceSelection("    ", "end")),
      "Shift-Tab": (c) => c.indentSelection("subtract"),
      "Ctrl-Enter": () => run(), "Cmd-Enter": () => run(),
      "Ctrl-Space": (c) => c.showHint({ hint: robotHint, completeSingle: false }),
    },
  });
  cm.on("inputRead", (c, ch) => { if (ch.text[0] === ".") c.showHint({ hint: robotHint, completeSingle: false }); });
  const view = new ArenaView($("[data-arena]"));
  const tele = new Telemetry($("[data-panel=telemetry]"), view);
  const consoleEl = $(".console");
  let errorMark = null, fontSize = 14, saveTimer = null, loaded = false, running = false, lines = [];
  let currentRef = arenaRef;
  let lastRun = null;
  const tutor = state.tutor?.available ? createTutor({ project, step, cm, getCode: () => cm.getValue(), getRun: () => lastRun }) : null;

  // ---------- arena ----------
  function defaultRef() {
    if (currentRef) return currentRef;
    if (project === "_practice") return `practice:${step}`;
    if (project === "_playground") return "sandbox:open_lab";
    if (step === "remix") return `remix:${project}`;
    return `step:${project}/${step}`;
  }
  async function loadArena() {
    const a = await api(`/api/learners/${state.learner.id}/arena?ref=${encodeURIComponent(defaultRef())}`);
    view.setArena(a);
    updateTime();
  }
  $("[data-arena-pick]")?.addEventListener("change", (e) => {
    currentRef = e.target.value;
    loadArena();
    onArenaChange && onArenaChange(currentRef);
  });

  // ---------- load & autosave ----------
  async function load() {
    const r = await api(`/api/learners/${state.learner.id}/code?project=${encodeURIComponent(project)}&step=${encodeURIComponent(step)}`);
    cm.setValue(r.code || "");
    cm.clearHistory();
    loaded = true;
    setTimeout(() => cm.refresh(), 30);
    if (r.source === "carried") toast("Your code from the last mission came along.");
  }
  cm.on("change", () => {
    if (!loaded) return;
    clearError();
    $("[data-saved]").textContent = "…";
    clearTimeout(saveTimer);
    saveTimer = setTimeout(save, 1200);
  });
  async function save() {
    clearTimeout(saveTimer);
    await api(`/api/learners/${state.learner.id}/code`, { method: "PUT", body: { project, step, code: cm.getValue() } });
    $("[data-saved]").textContent = "✓ saved";
  }

  // ---------- tabs ----------
  function tab(name) {
    host.querySelectorAll("[data-tab]").forEach((b) => b.classList.toggle("on", b.dataset.tab === name));
    host.querySelectorAll("[data-panel]").forEach((p) => p.classList.toggle("hidden", p.dataset.panel !== name));
    if (name === "telemetry") { uiEvent("telemetry.open", `${project}/${step}`); requestAnimationFrame(() => tele.rows.forEach((r) => tele.plot(r)) || tele.cursor()); }
  }
  host.querySelectorAll("[data-tab]").forEach((b) => b.onclick = () => tab(b.dataset.tab));

  // ---------- console ----------
  function clearError() {
    if (errorMark !== null) { cm.removeLineClass(errorMark, "background", "cm-error-line"); errorMark = null; }
  }
  function renderConsole(res, label) {
    consoleEl.innerHTML = label ? `<div class="sys">${esc(label)}</div>` : "";
    lines = [];
    let buf = "";
    for (const [t, s] of res.prints || []) {
      buf += s;
      const parts = buf.split("\n");
      buf = parts.pop();
      for (const p of parts) lines.push([t, p]);
    }
    if (buf) lines.push([res.prints[res.prints.length - 1][0], buf]);
    for (const [t, text] of lines) {
      const d = el(`<div class="ln"><span class="ts">${t.toFixed(2)}s</span><span></span></div>`);
      d.lastChild.textContent = text;
      d._t = t;
      consoleEl.appendChild(d);
    }
    for (const e of (res.events || []).filter((e) => e.type === "warn")) consoleEl.appendChild(el(`<div class="warnline">⚠ ${esc(e.text)}</div>`));
    for (const h of res.hints || []) consoleEl.appendChild(el(`<div class="sys">💡 ${esc(h)}</div>`));
    if (res.error) showError(res.error);
    else if (!lines.length) consoleEl.appendChild(el(`<div class="sys">(Your program didn't print anything. Try print(robot.distance()) to see a sensor value.)</div>`));
    const s = res.summary || {};
    consoleEl.appendChild(el(`<div class="sys">— ${res.end_reason === "time_limit" ? "time's up" : res.error ? "stopped by an error" : "program finished"} at ${Number(s.time || 0).toFixed(1)} s —</div>`));
    syncConsole();
  }
  function syncConsole() {
    const t = view.t, done = view.t >= (view.duration || 0) - 1e-6;
    consoleEl.querySelectorAll(".ln").forEach((d) => d.classList.toggle("future", !done && d._t > t + 1e-6));
  }
  function showError(m) {
    sfx("error");
    const card = el(`<div class="bugcard"><div class="m">${m.monster?.emoji || "🐛"}</div>
      <div><b>${esc(m.monster?.name || m.type)}${m.line ? ` on line ${m.line}` : ""}</b>
        <div>${esc(m.friendly || m.msg)}</div>
        ${m.code_line ? `<div class="raw">line ${m.line}: ${esc(m.code_line.trim())}</div>` : ""}
        <div class="raw">${esc(m.text || m.type)}</div>
        ${tutor ? `<button class="btn small soft" data-act="explain" style="margin-top:8px">Ask Sprocket about this bug</button>` : ""}</div></div>`);
    consoleEl.appendChild(card);
    if (m.line && m.line <= cm.lineCount()) {
      errorMark = m.line - 1;
      cm.addLineClass(errorMark, "background", "cm-error-line");
      cm.scrollIntoView({ line: errorMark, ch: 0 }, 80);
    }
  }
  function summaryStrip(res) {
    const s = res.summary || {};
    const pills = [`<span class="pill">⏱ ${Number(s.time || 0).toFixed(1)} s</span>`];
    if (res.kind === "arm") {
      pills.push(`<span class="pill">hand (${s.hand?.[0]}, ${s.hand?.[1]})</span>`, `<span class="pill">shoulder ${s.shoulder}° · elbow ${s.elbow}°</span>`);
      if (s.tower > 1) pills.push(`<span class="pill">tower ${s.tower}</span>`);
    } else {
      pills.push(`<span class="pill">📏 ${Math.round(s.distance || 0)} cm driven</span>`, `<span class="pill">📍 (${Math.round(s.x)}, ${Math.round(s.y)}) · ${Math.round(s.heading)}°</span>`);
      if (s.gems_total) pills.push(`<span class="pill">💎 ${s.gems}/${s.gems_total}</span>`);
      if (s.laps) pills.push(`<span class="pill">🏁 ${s.laps} laps ${s.lap_times?.length ? "· best " + Math.min(...s.lap_times).toFixed(1) + " s" : ""}</span>`);
    }
    pills.push(`<span class="pill ${s.crashes ? "bad" : "good"}">💥 ${s.crashes || 0} crashes</span>`);
    return `<div class="summary-strip">${pills.join("")}</div>`;
  }

  // ---------- replay controls ----------
  const scrub = $("[data-scrub]");
  function updateTime() {
    const d = view.duration || 0;
    $("[data-tlabel]").textContent = `${view.t.toFixed(1)} / ${d.toFixed(1)} s`;
    if (!scrubbing) scrub.value = d ? Math.round(view.t / d * 1000) : 0;
    $("[data-act=play]").textContent = view.playing ? "⏸" : "▶";
    syncConsole();
  }
  let scrubbing = false;
  view.onTime(updateTime);
  scrub.addEventListener("input", () => { scrubbing = true; view.pause(); view.seek(scrub.value / 1000 * (view.duration || 0)); });
  scrub.addEventListener("change", () => { scrubbing = false; uiEvent("replay.scrub", `${project}/${step}`); });
  host.querySelectorAll("[data-speed] button").forEach((b) => b.onclick = () => {
    host.querySelectorAll("[data-speed] button").forEach((x) => x.classList.toggle("on", x === b));
    view.speed = +b.dataset.s;
    uiEvent("replay.speed", `${project}/${step}`, { speed: view.speed });
  });

  function show(res, label) {
    view.setResult(res);
    renderConsole(res, label);
    tele.load(res);
    updateTime();
  }

  // ---------- run ----------
  async function run() {
    if (running) return;
    running = true;
    const btn = $("[data-act=run]");
    btn.disabled = true; btn.textContent = "Running…";
    save();
    clearError();
    sfx("run");
    try {
      const res = await api(`/api/learners/${state.learner.id}/run`, { method: "POST",
        body: { project, step, mode, code: cm.getValue(), arena: currentRef, seed: mode === "playground" ? Math.floor(Math.random() * 1e6) : undefined } });
      lastRun = { output: res.output, error: res.error, summary: res.summary, end_reason: res.end_reason, hints: res.hints };
      tab("console");
      show(res);
      $("[data-panel=result]").innerHTML = summaryStrip(res) + `<p class="faint small" style="padding:4px 12px">That was a practice run. ${checkable ? "Press <b>Test my robot</b> to check the goals." : ""}</p>`
        + (res.badge_count ? `<div style="padding:4px 12px 12px;max-width:520px">${badgeProgress(
          Array.from({ length: res.badge_count.total }, (_, i) => ({ earned_at: i < res.badge_count.earned ? 1 : null })))}
          ${mode === "playground" ? `<p class="faint small" style="margin:0">${res.playground_runs >= 10 ? "🧭 Explorer earned — keep experimenting!"
            : `${res.playground_runs}/10 playground experiments towards 🧭 Explorer.`}</p>` : ""}</div>` : "");
      (res.badges || []).forEach(showBadge);
    } catch (e) {
      toast("Couldn't run: " + esc(e.message));
    } finally {
      running = false;
      btn.disabled = false; btn.textContent = "▶ Run";
    }
  }

  const badgeBlock = (r) => r.badge_count ? `<div style="padding:4px 12px 12px;max-width:520px">${badgeProgress(
    Array.from({ length: r.badge_count.total }, (_, i) => ({ earned_at: i < r.badge_count.earned ? 1 : null })))}
    ${r.rewards?.badges?.length ? `<p class="faint small" style="margin:0">New: ${r.rewards.badges.map((b) => `${b.emoji} ${esc(b.name)}`).join(", ")}</p>` : ""}</div>` : "";

  // ---------- check ----------
  async function check() {
    await save();
    const btn = $("[data-act=check]");
    btn.disabled = true; btn.textContent = "Testing…";
    try {
      const r = await api(`/api/learners/${state.learner.id}/check`, { method: "POST", body: { project, step, code: cm.getValue() } });
      const box = $("[data-panel=result]");
      tab("result");
      const tests = r.runs ? `<span class="faint small">(${r.runs} test run${r.runs > 1 ? "s" : ""})</span>` : "";
      if (r.passed) {
        box.innerHTML = `<div class="check-result pass">✓ ${esc(r.message || "Mission complete!")} ${tests}</div>${r.replay ? summaryStrip(r.replay) : ""}${badgeBlock(r)}`;
        host.closest(".workspace")?.querySelector(".goals")?.classList.add("passed");
        if (r.replay) { show(r.replay, "Test run (passed):"); lastRun = { output: r.replay.output, error: r.replay.error, summary: r.replay.summary, end_reason: r.replay.end_reason }; tab("result"); }
        rewards(r);
        onPassed && onPassed(r);
      } else {
        sfx("fail");
        box.innerHTML = `<div class="check-result fail">Not yet — ${esc(r.message)} ${tests}
          <div class="row" style="margin-top:8px">${r.replay ? `<button class="btn small" data-watch>▶ Watch that test run${r.scenario ? `: ${esc(r.scenario)}` : ""}</button>` : ""}
          ${tutor && r.attempts >= 2 ? `<button class="btn small soft" data-askcheck>Ask Sprocket why</button>` : ""}
          <span class="faint small">Attempt ${r.attempts}. ${r.attempts >= 3 ? "Stuck? Open a hint — that's what they're for." : "Tweak it and test again."}</span></div></div>
          ${r.replay ? summaryStrip(r.replay) : ""}${badgeBlock(r)}`;
        box.querySelector("[data-watch]")?.addEventListener("click", () => {
          show(r.replay, `Replaying the test${r.scenario ? ` "${r.scenario}"` : ""} that didn't pass:`);
          lastRun = { output: r.replay.output, error: r.replay.error, summary: r.replay.summary, end_reason: r.replay.end_reason, hints: r.replay.hints };
        });
        box.querySelector("[data-askcheck]")?.addEventListener("click", () => tutor.ask(`The test says: "${r.message}". What am I missing? Just give me a clue!`));
        box.firstElementChild.classList.add("shake");
        if (r.replay) { show(r.replay, `Test run${r.scenario ? ` "${r.scenario}"` : ""}:`); lastRun = { output: r.replay.output, error: r.replay.error, summary: r.replay.summary, end_reason: r.replay.end_reason }; tab("result"); }
      }
      host.dispatchEvent(new CustomEvent("checked", { detail: r }));
    } catch (e) {
      toast("⚠️ " + esc(e.message));
    } finally {
      btn.disabled = false; btn.textContent = "✓ Test my robot";
    }
  }

  const onKey = (e) => {
    if (e.target.closest?.(".CodeMirror") || /INPUT|TEXTAREA|SELECT/.test(e.target.tagName)) return;
    if (e.code === "Space") { e.preventDefault(); view.toggle(); updateTime(); }
  };
  document.addEventListener("keydown", onKey);

  host.addEventListener("click", async (e) => {
    const act = e.target.closest("[data-act]")?.dataset.act;
    if (act === "run") run();
    else if (act === "check") check();
    else if (act === "play") { view.toggle(); updateTime(); }
    else if (act === "restart") { view.seek(0); view.play(); }
    else if (act === "rays") { view.showRays = !view.showRays; view.draw(); }
    else if (act === "manual") toggleManual();
    else if (act === "tutor") tutor?.toggle();
    else if (act === "review") tutor?.review();
    else if (act === "explain") tutor?.explainError(lastRun?.error || {});
    else if (act === "font") {
      fontSize = fontSize >= 19 ? 12 : fontSize + 2;
      host.querySelector(".CodeMirror").style.fontSize = fontSize + "px";
      cm.refresh();
    } else if (act === "reset") {
      if (!confirm("Start over with the mission's starter code? (Your current code will be replaced.)")) return;
      const r = await api(`/api/learners/${state.learner.id}/code/reset`, { method: "POST", body: { project, step } });
      loaded = false; cm.setValue(r.code); loaded = true;
      save();
    }
  });

  load();
  loadArena();
  return {
    cm, view, run, save, getCode: () => cm.getValue(), setCode: (c) => cm.setValue(c), tutor,
    arenaRef: () => currentRef || defaultRef(),
    dispose: () => { document.removeEventListener("keydown", onKey); view.dispose(); tutor?.dispose(); save(); },
  };
}

export function showBadge(b) {
  sfx("badge");
  toast(`${b.emoji} Badge unlocked: <b>${esc(b.name)}</b> <span class="muted">— ${esc(b.desc)}</span>`, 4500);
}

export function rewards(r) {
  const rw = r.rewards || {};
  if (!rw.xp) { sfx("ok"); return; }
  sfx("pass");
  celebrate(r.project_complete ? 1.6 : 0.8);
  const bonus = (rw.bonuses || []).map((b) => esc(b)).join(" · ");
  toast(`<b>+${rw.xp} XP</b>${bonus ? ` <span class="muted">${bonus}</span>` : ""}`);
  (rw.badges || []).forEach((b, i) => setTimeout(() => showBadge(b), 600 + i * 700));
  if (rw.level_up) {
    setTimeout(() => {
      sfx("level");
      modal(`<div class="big">⬆️</div><h2>Level ${rw.level_up.level}</h2>
        <p>You are now a <b>${esc(rw.level_up.title)}</b>.</p>
        ${r.badge_count ? `<div style="text-align:left;margin:14px 0">${badgeProgress(
          Array.from({ length: r.badge_count.total }, (_, i) => ({ earned_at: i < r.badge_count.earned ? 1 : null })))}</div>` : ""}
        <button class="btn primary big" data-close>Nice!</button>`);
    }, 900);
  }
  document.dispatchEvent(new CustomEvent("xp-changed"));
}
