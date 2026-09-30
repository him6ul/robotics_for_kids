// Parent Zone: learning analytics, coaching guide, audit log, monitoring and data management.
import { fmt } from "./tutor.js";
import { api, applyTheme, chartDefaults, esc, fmtMin, fmtTime, makeChart, modal, seriesColors, setContext, state, store, toast } from "./core.js";
import { ArenaView } from "./arena.js";

const TABS = [["overview", "Overview"], ["learning", "Learning analytics"], ["projects", "Projects & time"], ["robotics", "Robot skills"], ["guide", "Coaching guide"], ["tutor", "AI tutor"],
  ["timeline", "Activity timeline"], ["audit", "Audit log"], ["monitoring", "Monitoring"], ["data", "Data"], ["settings", "Settings"]];

let learners = [];
let sel = null;

export async function viewParent(app, tab = "overview", arg) {
  setContext("_parent", tab);
  document.body.classList.add("parent-mode");
  const st = await api("/api/parent/status");
  if (!st.logged_in) return pinGate(app, st.pin_set, tab);
  learners = await api("/api/learners");
  if (!sel || !learners.find((l) => l.id === sel)) sel = state.learner?.id || learners[0]?.id;
  app.innerHTML = `<div class="parent-zone">
    <div class="row" style="margin-bottom:10px"><h1 style="margin:0">👪 Parent Zone</h1><span class="spacer"></span>
      ${learners.length ? `<label class="muted">Learner <select id="lsel">${learners.map((l) => `<option value="${l.id}" ${l.id === sel ? "selected" : ""}>${l.avatar} ${esc(l.name)}</option>`).join("")}</select></label>` : ""}
      <a class="btn" href="#/home">← Back to RoboQuest</a><button class="btn" id="logout">Lock</button></div>
    <nav class="ptabs">${TABS.map(([k, n]) => `<a href="#/parent/${k}" class="${k === tab ? "active" : ""}">${n}</a>`).join("")}</nav>
    <div id="pbody"><p class="muted">Loading…</p></div></div>`;
  app.querySelector("#lsel")?.addEventListener("change", (e) => { sel = +e.target.value; viewParent(app, tab); });
  app.querySelector("#logout").onclick = async () => { await api("/api/parent/logout", { method: "POST" }); location.hash = "#/home"; };
  const body = app.querySelector("#pbody");
  const needsLearner = ["overview", "learning", "projects", "robotics", "guide", "timeline", "tutor"];
  if (needsLearner.includes(tab) && !sel) { body.innerHTML = `<p class="muted">No learners yet.</p>`; return; }
  try {
    await ({ overview, learning, projects, robotics, guide, tutor, timeline, audit, monitoring, data, settings }[tab] || overview)(body, arg);
  } catch (e) {
    body.innerHTML = `<div class="note"><b>Couldn't load this view</b>${esc(e.message)}</div>`;
  }
}

function pinGate(app, pinSet, tab) {
  app.innerHTML = `<div class="parent-zone"><div class="pinbox card"><h2>👪 Parent Zone</h2>
    <p class="muted">${pinSet ? "Enter your parent PIN." : "Create a parent PIN (4+ digits) to protect the dashboard, audit log and data tools."}</p>
    <input id="pin" type="password" inputmode="numeric" autocomplete="off" maxlength="12"><p><button class="btn primary" id="go">${pinSet ? "Unlock" : "Set PIN"}</button></p>
    <p><a href="#/home">← Back</a></p></div></div>`;
  const go = async () => {
    try { await api("/api/parent/login", { method: "POST", body: { pin: app.querySelector("#pin").value } }); viewParent(app, tab); }
    catch (e) { toast(esc(e.message)); app.querySelector("#pin").value = ""; }
  };
  app.querySelector("#go").onclick = go;
  app.querySelector("#pin").addEventListener("keydown", (e) => e.key === "Enter" && go());
  app.querySelector("#pin").focus();
}

const pct = (v) => (v === null || v === undefined ? "—" : `${Math.round(v * 100)}%`);
const kpi = (v, l, s = "") => `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div>${s ? `<div class="s">${s}</div>` : ""}</div>`;
let reportCache = {};
async function report() {
  const r = await api(`/api/parent/report/${sel}`);
  reportCache[sel] = r;
  return r;
}
function chartSetup() {
  const { grid } = chartDefaults();
  return { col: seriesColors(), grid };
}
const baseOpts = (grid, extra = {}) => ({
  maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
  plugins: { legend: { position: "bottom", labels: { boxWidth: 10, boxHeight: 10 } } },
  scales: { x: { grid: { display: false } }, y: { beginAtZero: true, grid: { color: grid } } }, ...extra,
});

// ---------------------------------------------------------------- overview
async function overview(body) {
  const r = await report();
  const s = r.schedule, a = r.activity, st = r.style;
  const done = r.projects.filter((p) => p.complete).length;
  const steps = r.projects.reduce((x, p) => x + p.steps_done, 0), total = r.projects.reduce((x, p) => x + p.steps_total, 0);
  const statusPill = { ahead: "good", "on track": "good", behind: "warn" }[s.status];
  body.innerHTML = `
    <div class="kpis">
      ${kpi(`${done}/${r.projects.length}`, "Robots built", `${steps}/${total} missions`)}
      ${kpi(`<span class="pill ${statusPill}" style="font-size:1rem">${esc(s.status)}</span>`, "Schedule", `Day ${s.days_in + 1} of 42 · week ${s.calendar_week}`)}
      ${kpi(fmtMin(a.total_minutes * 60), "Active building time", `${a.sessions} sessions · avg ${a.avg_session_minutes} min`)}
      ${kpi(`🔥 ${a.streak.current}`, "Day streak", `best ${a.streak.best}`)}
      ${kpi(`Lv ${r.level.level}`, esc(r.level.title), `${r.level.xp} XP`)}
      ${kpi(pct(st.raw.first_try_rate), "First-try pass rate", `${st.raw.hints_per_step} hints / step`)}
      ${kpi(r.errors.total, "Program errors", `${pct(r.errors.crash_rate)} of ${r.errors.runs} runs`)}
      ${kpi(pct(r.robot.crash_run_rate), "Runs with a robot crash", r.robot.crash_rate_early !== null ? `early ${pct(r.robot.crash_rate_early)} → recent ${pct(r.robot.crash_rate_late)}` : `${r.robot.crashes} bumps in total`)}
      ${kpi(`${r.robot.distance_m} m`, "Distance driven", `${r.robot.sensor_kinds} sensor types used`)}
      ${kpi(r.enjoyment.avg_fun ? `${r.enjoyment.avg_fun}/5` : "—", "Average fun rating", r.enjoyment.avg_difficulty ? `difficulty ${r.enjoyment.avg_difficulty}/5` : "no ratings yet")}
    </div>
    <div class="grid g2">
      <div class="card"><h3>Progress vs 6-week plan</h3>
        <p class="muted" style="margin-top:0">${s.actual_pct}% of missions done; the plan expects ${s.expected_pct}% by today. Planned finish ${s.planned_finish}${s.projected_finish ? ` · projected finish at current pace <b>${s.projected_finish}</b>` : ""}.</p>
        <div class="row"><span class="faint" style="width:70px">Actual</span><div class="progress" style="flex:1"><i style="width:${s.actual_pct}%"></i></div></div>
        <div class="row" style="margin-top:6px"><span class="faint" style="width:70px">Plan</span><div class="progress" style="flex:1"><i style="width:${s.expected_pct}%;background:var(--muted)"></i></div></div>
        <h3 style="margin-top:18px">Learner profile: ${st.persona.emoji} ${esc(st.persona.name)}</h3><p class="muted">${esc(st.persona.desc)}</p></div>
      <div class="card"><h3>Top coaching notes</h3>${r.guide.parent.slice(0, 4).map(note).join("") || `<p class="muted">Nothing needs your attention right now. 👍</p>`}
        <p><a href="#/parent/guide">All notes →</a></p></div>
    </div>
    <div class="card" style="margin-top:16px"><h3>Daily active minutes (last 6 weeks)</h3><div class="chart-box"><canvas id="p-daily"></canvas></div></div>`;
  const { col, grid } = chartSetup();
  makeChart(body.querySelector("#p-daily"), {
    type: "bar",
    data: { labels: a.daily.map((d) => d.day.slice(5)), datasets: [{ label: "Active minutes", data: a.daily.map((d) => d.minutes), backgroundColor: col[0], borderRadius: 4, maxBarThickness: 18 }] },
    options: baseOpts(grid, { plugins: { legend: { display: false } } }),
  });
}

function note(n) {
  return `<div class="note"><b>${esc(n.title)}</b><span class="muted">${esc(n.text)}</span></div>`;
}

// ---------------------------------------------------------------- learning analytics
async function learning(body) {
  const r = reportCache[sel] || await report();
  const st = r.style, m = r.mastery, e = r.errors;
  body.innerHTML = `
    <div class="grid g2">
      <div class="card"><h3>Concept mastery</h3><p class="muted" style="margin-top:0">Combines missions completed, quality (attempts, hints, time), practice side quests and independent use in the Playground/remixes.</p>
        <div class="chart-box tall"><canvas id="p-mastery"></canvas></div></div>
      <div class="card"><h3>Learning style</h3><p class="muted" style="margin-top:0">${st.persona.emoji} <b>${esc(st.persona.name)}</b> — ${esc(st.persona.desc)}</p>
        <div class="chart-box tall"><canvas id="p-style"></canvas></div></div>
    </div>
    <div class="card" style="margin-top:16px"><h3>How he learns — raw signals</h3><div class="kpis" style="margin:0">
      ${kpi(pct(st.raw.first_try_rate), "First-try passes", "Precision")}
      ${kpi(st.raw.hints_per_step, "Hints per step", "Independence")}
      ${kpi(st.raw.runs_per_check, "Runs per test", "Experimenting — how often he tries before testing")}
      ${kpi(pct(st.raw.persistence), "Recovered after a failed check", "Persistence")}
      ${kpi(st.raw.avg_error_recovery_sec ? `${st.raw.avg_error_recovery_sec}s` : "—", "Avg time to fix a crash", "Debugging speed")}
      ${kpi(st.raw.pace_ratio ?? "—", "Time vs expected", "1.0 = on estimate, <1 faster")}
      ${kpi(st.raw.beyond_reference_ratio ?? "—", "His code vs reference complexity", ">1 means he goes beyond what's asked")}
      ${kpi(`${st.raw.remixes} / ${st.raw.ideas} / ${st.raw.playground_runs}`, "Remixes / ideas / playground runs", "Creativity signals")}
      ${kpi(st.raw.tutor_questions ?? 0, "Questions to AI tutor", `${st.raw.tutor_per_step ?? 0} per mission`)}
      ${kpi(`${st.raw.tune_edits ?? 0} / ${st.raw.small_edits ?? 0} / ${st.raw.rewrites ?? 0}`, "Tunes / edits / rewrites", "How he changes code between runs")}
    </div></div>
    <div class="grid g2" style="margin-top:16px">
      <div class="card"><h3>Idea complexity over time</h3><p class="muted" style="margin-top:0">Each idea in his journal is scored 0–100 on features, concept breadth and ambition (Spark → Mastermind). Remix code complexity is shown against the original project.</p>
        ${r.ideas.ideas.length || r.ideas.remixes.length ? `<div class="chart-box"><canvas id="p-ideas"></canvas></div>` : `<p class="faint">No ideas or remixes yet.</p>`}
        ${r.ideas.ideas.slice(-4).reverse().map((i) => `<div class="note"><b>${i.analysis.level_emoji} ${esc(i.analysis.level_name)} · ${i.score}/100 ${i.status === "built" ? "· built ✅" : ""}</b><span class="muted">"${esc(i.text)}"</span></div>`).join("")}</div>
      <div class="card"><h3>Code growth</h3><p class="muted" style="margin-top:0">Complexity (0–100) and lines of the code he passed each mission with.</p>
        <div class="chart-box"><canvas id="p-growth"></canvas></div></div>
    </div>
    <div class="grid g2" style="margin-top:16px">
      <div class="card"><h3>Errors by type</h3><div class="tscroll" style="max-height:300px"><table class="t"><thead><tr><th>Bug</th><th class="num">Total</th><th class="num">Last 7 days</th><th>Fixed?</th></tr></thead>
        <tbody>${e.by_type.map((x) => `<tr><td>${x.emoji} ${esc(x.type)}<div class="faint">${esc(x.tip)}</div></td><td class="num">${x.count}</td><td class="num">${x.recent}</td><td>${x.defeated ? "✅" : "—"}</td></tr>`).join("") || `<tr><td colspan="4" class="faint">No crashes yet.</td></tr>`}</tbody></table></div></div>
      <div class="card"><h3>Recent error messages</h3><div class="tscroll" style="max-height:300px"><table class="t"><thead><tr><th>When</th><th>Where</th><th>Error</th></tr></thead>
        <tbody>${e.recent_messages.map((x) => `<tr><td>${fmtTime(x.ts)}</td><td>${esc(x.project_id)}/${esc(x.step_id)}${x.error_line ? ` L${x.error_line}` : ""}</td><td><b>${esc(x.error_type)}</b> ${esc(x.error_msg)}</td></tr>`).join("") || `<tr><td colspan="3" class="faint">—</td></tr>`}</tbody></table></div></div>
    </div>
    <div class="card" style="margin-top:16px"><h3>Mastery detail</h3><div class="tscroll"><table class="t"><thead><tr><th>Concept</th><th>Status</th><th class="num">Score</th><th class="num">Missions</th><th class="num">Avg quality</th><th class="num">Independent uses</th><th class="num">Practice</th><th class="num">Errors on related steps</th><th class="num">Asked Sprocket</th></tr></thead>
      <tbody>${m.map((x) => `<tr><td>${esc(x.label)}</td><td>${esc(x.status)}</td><td class="num">${pct(x.score)}</td><td class="num">${x.steps_done}/${x.steps_total}</td><td class="num">${x.avg_quality}</td><td class="num">${x.independent_uses}</td><td class="num">${x.practice_done}</td><td class="num">${x.errors}</td><td class="num">${x.tutor_questions ?? 0}</td></tr>`).join("")}</tbody></table></div></div>`;
  const { col, grid } = chartSetup();
  makeChart(body.querySelector("#p-mastery"), {
    type: "bar",
    data: { labels: m.map((x) => x.label), datasets: [{ label: "Mastery %", data: m.map((x) => Math.round(x.score * 100)), backgroundColor: col[0], borderRadius: 4, maxBarThickness: 16 }] },
    options: baseOpts(grid, { indexAxis: "y", plugins: { legend: { display: false } }, scales: { x: { min: 0, max: 100, grid: { color: grid } }, y: { grid: { display: false } } } }),
  });
  makeChart(body.querySelector("#p-style"), {
    type: "radar",
    data: { labels: Object.keys(st.traits), datasets: [{ label: "Learning traits", data: Object.values(st.traits).map((v) => Math.round(v * 100)), borderColor: col[6], backgroundColor: col[6] + "26", borderWidth: 2, pointRadius: 4, pointBackgroundColor: col[6] }] },
    options: { maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { r: { min: 0, max: 100, ticks: { display: false }, grid: { color: grid }, angleLines: { color: grid } } } },
  });
  if (body.querySelector("#p-ideas")) makeChart(body.querySelector("#p-ideas"), {
    type: "scatter",
    data: { datasets: [
      { label: "Idea score", data: r.ideas.ideas.map((i) => ({ x: i.ts * 1000, y: i.score })), backgroundColor: col[0], pointRadius: 6, showLine: true, borderColor: col[0], borderWidth: 2 },
      { label: "Remix complexity", data: r.ideas.remixes.map((i) => ({ x: i.ts * 1000, y: i.complexity })), backgroundColor: col[1], pointRadius: 6, pointStyle: "rectRot" },
      { label: "Original project complexity", data: r.ideas.remixes.map((i) => ({ x: i.ts * 1000, y: i.base_complexity })), backgroundColor: col[2], pointRadius: 5, pointStyle: "triangle" },
    ] },
    options: baseOpts(grid, { scales: { x: { type: "linear", ticks: { callback: (v) => new Date(v).toLocaleDateString([], { month: "short", day: "numeric" }) }, grid: { display: false } }, y: { min: 0, max: 100, grid: { color: grid } } } }),
  });
  const g = r.code_growth;
  makeChart(body.querySelector("#p-growth"), {
    type: "line",
    data: { labels: g.map((x) => `${x.project_id.slice(0, 10)}/${x.step_id}`), datasets: [
      { label: "Complexity (0–100)", data: g.map((x) => x.complexity), borderColor: col[0], backgroundColor: col[0], borderWidth: 2, pointRadius: 3, tension: 0.25 },
      { label: "Lines of code", data: g.map((x) => x.lines), borderColor: col[1], backgroundColor: col[1], borderWidth: 2, pointRadius: 3, tension: 0.25, borderDash: [5, 4] },
    ] },
    options: baseOpts(grid, { scales: { x: { ticks: { display: false }, grid: { display: false } }, y: { beginAtZero: true, grid: { color: grid } } } }),
  });
}

// ---------------------------------------------------------------- projects & time
async function projects(body, arg) {
  const r = reportCache[sel] || await report();
  const cur = state.curriculum.projects;
  body.innerHTML = `
    <div class="card"><h3>Time per project — actual vs expected</h3><div class="chart-box tall"><canvas id="p-time"></canvas></div></div>
    <div class="grid g2" style="margin-top:16px">
      <div class="card"><h3>Where the time goes</h3><div class="chart-box"><canvas id="p-mode"></canvas></div></div>
      <div class="card"><h3>When he codes (hour of day)</h3><div class="chart-box"><canvas id="p-hour"></canvas></div></div>
    </div>
    <div class="card" style="margin-top:16px"><h3>Project details</h3><div class="tscroll"><table class="t"><thead><tr><th>Project</th><th>Missions</th><th class="num">Time</th><th class="num">Expected</th><th class="num">Runs</th><th class="num">Crashes</th><th class="num">Checks</th><th class="num">First-try</th><th class="num">Hints</th><th>Boss</th><th>Remix</th><th>Fun / Hard</th><th>Finished</th></tr></thead>
      <tbody>${r.projects.map((p) => `<tr><td>${p.emoji} <a href="#/parent/projects/${p.id}">${esc(p.title)}</a></td><td>${p.steps_done}/${p.steps_total}</td>
        <td class="num">${fmtMin(p.seconds)}</td><td class="num">${fmtMin(p.expected_seconds)}</td><td class="num">${p.runs}</td><td class="num">${p.errors}</td><td class="num">${p.attempts}</td>
        <td class="num">${p.first_try}</td><td class="num">${p.hints}</td><td>${p.boss_done ? "✅" : "—"}</td><td>${p.remixed ? "✅" : "—"}</td>
        <td>${p.fun ? `${p.fun} / ${p.difficulty}` : "—"}</td><td>${p.completed_at ? fmtTime(p.completed_at) : "—"}</td></tr>`).join("")}</tbody></table></div></div>
    <div id="pdetail"></div>`;
  const { col, grid } = chartSetup();
  makeChart(body.querySelector("#p-time"), {
    type: "bar",
    data: { labels: r.projects.map((p) => p.title), datasets: [
      { label: "Actual minutes", data: r.projects.map((p) => Math.round(p.seconds / 60)), backgroundColor: col[0], borderRadius: 4, maxBarThickness: 22 },
      { label: "Expected minutes", data: r.projects.map((p) => Math.round(p.expected_seconds / 60)), backgroundColor: col[2], borderRadius: 4, maxBarThickness: 22 },
    ] },
    options: baseOpts(grid),
  });
  const modes = r.activity.by_mode;
  const modeLabel = { projects: "Projects", _practice: "Side quests", _playground: "Playground", _home: "Home / map", _ideas: "Ideas", _journey: "My Journey", _parent: "Parent zone" };
  const mk = Object.keys(modes);
  makeChart(body.querySelector("#p-mode"), {
    type: "bar",
    data: { labels: mk.map((k) => modeLabel[k] || k), datasets: [{ label: "Minutes", data: mk.map((k) => modes[k]), backgroundColor: col[0], borderRadius: 4, maxBarThickness: 26 }] },
    options: baseOpts(grid, { indexAxis: "y", plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, grid: { color: grid } }, y: { grid: { display: false } } } }),
  });
  makeChart(body.querySelector("#p-hour"), {
    type: "bar",
    data: { labels: r.activity.by_hour.map((h) => `${h.hour}:00`), datasets: [{ label: "Minutes", data: r.activity.by_hour.map((h) => h.minutes), backgroundColor: col[0], borderRadius: 3 }] },
    options: baseOpts(grid, { plugins: { legend: { display: false } } }),
  });
  if (arg) projectDetail(body.querySelector("#pdetail"), cur.find((p) => p.id === arg));
}

async function projectDetail(host, p) {
  if (!p) return;
  const steps = [...p.steps, p.boss];
  host.innerHTML = `<div class="card" style="margin-top:16px"><h3>${p.emoji} ${esc(p.title)} — code history</h3>
    <p class="muted">Pick a mission to see every version of his code (each run and test) side by side with the reference solution — and replay any version in the simulator.</p>
    <div class="row">${steps.map((s) => `<button class="btn small" data-s="${s.id}">${esc(s.title)}</button>`).join("")}</div><div id="hist"></div></div>`;
  host.querySelectorAll("[data-s]").forEach((b) => b.onclick = async () => {
    const d = await api(`/api/parent/code/${sel}?project=${p.id}&step=${b.dataset.s}`);
    const h = host.querySelector("#hist");
    if (!d.snapshots.length) { h.innerHTML = `<p class="faint">No code yet for this mission.</p>`; return; }
    h.innerHTML = `<div class="row" style="margin:10px 0"><label>Version <input type="range" min="0" max="${d.snapshots.length - 1}" value="${d.snapshots.length - 1}" id="ver" style="width:260px"></label><span id="vinfo" class="muted"></span><button class="btn small" id="replay">▶ Replay this version</button></div>
      <div class="codecmp"><div><b>His code</b><pre id="mine"></pre></div><div><b>Reference solution</b><pre>${esc(d.reference || "")}</pre></div></div>`;
    const show = () => {
      const s = d.snapshots[+h.querySelector("#ver").value];
      h.querySelector("#mine").textContent = s.code;
      h.querySelector("#vinfo").textContent = `${fmtTime(s.ts)} · ${s.kind} · ${s.lines} lines · complexity ${s.complexity}`;
    };
    h.querySelector("#ver").oninput = show;
    h.querySelector("#replay").onclick = () => replayModal(d.snapshots[+h.querySelector("#ver").value]);
    show();
  });
}

// ---------------------------------------------------------------- coaching guide
async function guide(body) {
  const r = reportCache[sel] || await report();
  const g = r.guide;
  body.innerHTML = `<div class="grid g2">
    <div class="card"><h3>Coaching notes for you</h3><p class="muted" style="margin-top:0">Generated from his progress, errors, pace, hint use, ideas and fun ratings. Updated live.</p>
      ${g.parent.map(note).join("") || `<p class="muted">Nothing needs attention — he's doing great. Ask him to demo his latest project!</p>`}
      <h3 style="margin-top:16px">Conversation starters</h3><ul class="muted">
      <li>"Show me the coolest robot you built this week — run it for me!"</li><li>"What was the hardest bug? How did you find it in the replay?"</li>
      <li>"If you could add one feature to ${esc(r.projects.filter((p) => p.complete).slice(-1)[0]?.title || "your next project")}, what would it be?"</li>
      <li>"Explain ${esc((r.mastery.filter((m) => m.started).sort((a, b) => a.score - b.score)[0] || { label: "sensors" }).label.toLowerCase())} to me like I'm 5."</li>
      <li>"Where do you see this idea in real life?" (Roombas, self-driving cars, warehouse robots, Mars rovers)</li></ul></div>
    <div class="card"><h3>What he sees (his guide)</h3>${g.kid.map((k) => `<div class="note"><b>${k.emoji || ""} ${esc(k.title)}</b><span class="muted">${esc(k.text)}</span></div>`).join("")}
      <h3 style="margin-top:16px">Adaptive path</h3><ol>${g.path.map((p) => p.type === "project"
        ? `<li>${p.emoji} ${esc(p.title)} — ${p.complete ? "✅ done" : p.unlocked ? `${p.steps_done}/${p.steps_total} missions` : "🔒 locked"}</li>`
        : `<li style="list-style:'↳ '">🗡️ ${esc(p.title)} <span class="pill">recommended</span></li>`).join("")}</ol></div></div>`;
}

// ---------------------------------------------------------------- AI tutor
async function tutor(body) {
  const d = await api(`/api/parent/tutor/${sel}`);
  const st = d.status, s = d.stats;
  const setup = !st.configured
    ? `<div class="note warn"><b>Not connected yet</b><span class="muted">Sprocket uses the Claude API (model <code>${esc(st.model)}</code>).
       Create an API key at console.anthropic.com, then start RoboQuest with it, e.g. <code>ANTHROPIC_API_KEY=… ./run.sh</code>.
       ${st.sdk ? "" : "The <code>anthropic</code> package is also missing — run <code>.venv/bin/pip install anthropic</code>."}</span></div>` : "";
  const kindLabel = { concept_question: "Concept questions", debugging: "Debugging help", stuck: "Stuck", idea: "Ideas", check_my_work: "Check my work", off_topic: "Off topic", other: "Other" };
  body.innerHTML = `${setup}
    <div class="grid g2">
      <div class="card"><h3>🔧 Sprocket settings</h3>
        <p class="muted" style="margin-top:0">Sprocket is an AI tutor that gives Socratic hints and code reviews, but never full answers. When it's on, his questions, code and program output are sent to Anthropic's API. His name is not sent. Every conversation is saved here for you to read.</p>
        <p><label><input type="checkbox" id="t-en" ${st.enabled ? "checked" : ""}> Enable the AI tutor</label></p>
        <p><label>Daily question limit <input type="number" id="t-lim" min="1" max="500" value="${st.daily_limit}" style="width:90px"></label></p>
        <p><label><input type="checkbox" id="t-snip" ${st.allow_snippets ? "checked" : ""}> Allow tiny 1–2 line code examples (never his answer)</label></p>
        <div class="row"><button class="btn primary" id="t-save">Save</button><button class="btn" id="t-test" ${st.configured ? "" : "disabled"}>Test connection</button>
          <span class="pill ${st.available ? "good" : "warn"}">${st.available ? "Active" : st.configured ? "Off" : "Not connected"}</span></div>
        <p id="t-testout" class="muted"></p></div>
      <div class="card"><h3>Usage</h3><div class="kpis" style="margin:0">
        ${kpi(s.questions, "Questions asked", `${s.error_help} about crashes`)}
        ${kpi(s.reviews, "Code reviews")}
        ${kpi(`${s.used_today}/${st.daily_limit}`, "Today")}
        ${kpi(`$${s.est_cost_usd.toFixed(2)}`, "Estimated API cost", `${(s.tokens_in + s.tokens_out).toLocaleString()} tokens`)}
        ${kpi(s.avg_latency_ms ? `${(s.avg_latency_ms / 1000).toFixed(1)}s` : "—", "Avg reply time", `${s.errors} errors · ${s.refused} declined`)}
        ${kpi(s.steps_with_questions, "Missions he asked about")}</div></div>
    </div>
    ${s.flagged.length ? `<div class="card alert" style="margin-top:16px"><h3>⚠️ Messages flagged for a parent</h3>
      <p class="muted" style="margin-top:0">Sprocket flags messages about safety, feeling unsafe, bullying or similar, and tells him to talk to a trusted adult.</p>
      ${s.flagged.map((f) => `<div class="note alert"><b>${fmtTime(f.ts)} · ${esc(f.project_id)}/${esc(f.step_id)}</b><span>${esc(f.text)}</span></div>`).join("")}</div>` : ""}
    <div class="grid g2" style="margin-top:16px">
      <div class="card"><h3>What he asks about</h3><p class="muted" style="margin-top:0">Sprocket tags each question with a type and the concept it's about. Concepts he asks about often are good ones to review together.</p>
        ${Object.keys(s.by_concept).length ? `<div class="chart-box"><canvas id="t-concepts"></canvas></div>` : `<p class="faint">No questions yet.</p>`}</div>
      <div class="card"><h3>Question types & mood</h3>
        ${Object.keys(s.by_kind).length ? `<div class="chart-box"><canvas id="t-kinds"></canvas></div>` : `<p class="faint">No questions yet.</p>`}
        <p class="muted">Mood read from his messages: ${Object.entries(s.moods).map(([k, v]) => `<span class="pill">${esc(k)} ${v}</span>`).join(" ") || "—"}</p></div>
    </div>
    <div class="card" style="margin-top:16px"><h3>Conversations</h3><div class="tscroll" style="max-height:640px"><table class="t"><thead><tr><th>When</th><th>Where</th><th>Who</th><th>Message</th><th>Tags</th></tr></thead>
      <tbody>${d.transcripts.map((m) => `<tr><td style="white-space:nowrap">${fmtTime(m.ts)}</td><td>${esc(m.project_id)}/${esc(m.step_id)}</td>
        <td>${m.role === "kid" ? "🧒 him" : "🔧 Sprocket"}${m.status !== "ok" ? ` <span class="pill warn">${esc(m.status)}</span>` : ""}</td>
        <td style="max-width:560px">${m.kind === "review" && m.role === "tutor" && m.meta?.suggestions ? `<b>${"⭐".repeat(m.meta.stars || 0)}</b> ${fmt(m.text)}<ul>${m.meta.suggestions.map((x) => `<li>${x.line ? `L${x.line}: ` : ""}${fmt(x.tip)}</li>`).join("")}</ul>` : fmt(m.text)}</td>
        <td class="faint">${m.role === "kid" && m.meta ? `${esc(m.meta.question_kind || "")} · ${esc(m.meta.concept || "")} · ${esc(m.meta.learner_mood || "")}${m.meta.needs_adult ? " · ⚠️" : ""}` : m.role === "tutor" && m.output_tokens ? `${m.input_tokens}+${m.output_tokens} tok · ${m.latency_ms} ms` : ""}</td></tr>`).join("") || `<tr><td colspan="5" class="faint">No conversations yet.</td></tr>`}</tbody></table></div>
      <p><a class="btn" href="/api/parent/export/tutor_messages.csv">⬇ Export CSV</a></p></div>`;
  body.querySelector("#t-save").onclick = async () => {
    await api("/api/parent/tutor/settings", { method: "POST", body: { enabled: body.querySelector("#t-en").checked,
      daily_limit: +body.querySelector("#t-lim").value, allow_snippets: body.querySelector("#t-snip").checked } });
    toast("Tutor settings saved"); tutor(body);
  };
  body.querySelector("#t-test").onclick = async () => {
    const out = body.querySelector("#t-testout"); out.textContent = "Testing…";
    const r = await api("/api/parent/tutor/test", { method: "POST" });
    out.textContent = r.ok ? `✅ Connected (${r.model}, ${r.ms} ms): "${r.reply}"` : `❌ ${r.error}`;
  };
  const { col, grid } = chartSetup();
  if (body.querySelector("#t-concepts")) {
    const ks = Object.keys(s.by_concept);
    makeChart(body.querySelector("#t-concepts"), { type: "bar",
      data: { labels: ks.map((k) => state.curriculum.concepts[k] || k), datasets: [{ label: "Questions", data: ks.map((k) => s.by_concept[k]), backgroundColor: col[0], borderRadius: 4, maxBarThickness: 18 }] },
      options: baseOpts(grid, { indexAxis: "y", plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: grid } }, y: { grid: { display: false } } } }) });
  }
  if (body.querySelector("#t-kinds")) {
    const ks = Object.keys(s.by_kind);
    makeChart(body.querySelector("#t-kinds"), { type: "bar",
      data: { labels: ks.map((k) => kindLabel[k] || k), datasets: [{ label: "Questions", data: ks.map((k) => s.by_kind[k]), backgroundColor: col[0], borderRadius: 4, maxBarThickness: 18 }] },
      options: baseOpts(grid, { indexAxis: "y", plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: grid } }, y: { grid: { display: false } } } }) });
  }
}

// ---------------------------------------------------------------- activity timeline (learner's audit trail)
async function timeline(body) {
  const d = await api(`/api/parent/timeline/${sel}?limit=300`);
  const icon = { "code.run": "▶", "check.pass": "✅", "check.fail": "❌", "hint.open": "💡", "solution.peek": "🫣", "idea.add": "💭", "remix.submit": "🎛️", "reflection.add": "⭐", "session.start": "🟢", "code.reset": "↺", "learner.update": "✏️", "learner.create": "🐣", "tutor.chat": "🔧", "tutor.review": "🔍", "tutor.error_help": "🐛", "drive.start": "🎮", "drive.end": "🏁", "arena.create": "🏗️", "arena.update": "🏗️", "ui.replay.scrub": "⏯", "ui.telemetry.open": "📈", "ui.manual.open": "📘" };
  body.innerHTML = `<div class="card"><h3>Everything he did, newest first</h3><div class="tscroll" style="max-height:700px"><table class="t"><thead><tr><th>When</th><th>Action</th><th>Where</th><th>Details</th></tr></thead>
    <tbody>${d.rows.map((a) => `<tr><td style="white-space:nowrap">${fmtTime(a.ts)}</td><td>${icon[a.action] || "•"} ${esc(a.action)}</td><td>${esc(a.entity_id || "")}</td><td class="faint">${esc(a.details || "")}</td></tr>`).join("")}</tbody></table></div></div>`;
}

// ---------------------------------------------------------------- audit log
async function audit(body) {
  const params = new URLSearchParams(location.hash.split("?")[1] || "");
  const q = new URLSearchParams();
  ["actor", "action", "text"].forEach((k) => params.get(k) && q.set(k, params.get(k)));
  const days = +(params.get("days") || 0);
  if (days) q.set("since", Date.now() / 1000 - days * 86400);
  const page = +(params.get("page") || 0);
  q.set("limit", 100); q.set("offset", page * 100);
  const d = await api(`/api/parent/audit?${q}`);
  body.innerHTML = `<div class="card"><h3>Audit log</h3><p class="muted" style="margin-top:0">Append-only, hash-chained record of every meaningful action by learners, the parent, and the system — with timestamp, actor, IP and browser.</p>
    <form class="row" id="af">
      <select name="actor"><option value="">All actors</option>${d.facets.actors.map((a) => `<option ${params.get("actor") === a.actor ? "selected" : ""}>${esc(a.actor)}</option>`).join("")}</select>
      <select name="action"><option value="">All actions</option>${d.facets.actions.map((a) => `<option value="${esc(a.action)}" ${params.get("action") === a.action ? "selected" : ""}>${esc(a.action)} (${a.n})</option>`).join("")}</select>
      <select name="days"><option value="0">All time</option>${[1, 7, 30].map((n) => `<option value="${n}" ${days === n ? "selected" : ""}>Last ${n} day${n > 1 ? "s" : ""}</option>`).join("")}</select>
      <input name="text" placeholder="Search details…" value="${esc(params.get("text") || "")}"><button class="btn primary">Filter</button>
      <span class="spacer"></span><button class="btn" type="button" id="verify">Verify integrity</button><a class="btn" href="/api/parent/export/audit_log.csv">⬇ Export CSV</a></form>
    <div id="verifyout"></div>
    <p class="faint">${d.total} matching events</p>
    <div class="tscroll" style="max-height:640px"><table class="t"><thead><tr><th>#</th><th>Time</th><th>Actor</th><th>Action</th><th>Entity</th><th>Details</th><th>IP</th></tr></thead>
      <tbody>${d.rows.map((a) => `<tr><td class="num faint">${a.id}</td><td style="white-space:nowrap">${fmtTime(a.ts)}</td><td>${esc(a.actor)}</td><td><b>${esc(a.action)}</b></td>
        <td>${esc(a.entity || "")} ${esc(a.entity_id || "")}</td><td class="faint" style="max-width:420px;word-break:break-word">${esc(a.details || "")}</td><td class="faint">${esc(a.ip || "")}</td></tr>`).join("")}</tbody></table></div>
    <div class="row" style="margin-top:10px">${page ? `<button class="btn" data-pg="${page - 1}">← Newer</button>` : ""}${(page + 1) * 100 < d.total ? `<button class="btn" data-pg="${page + 1}">Older →</button>` : ""}</div></div>`;
  const nav = (extra) => {
    const f = new FormData(body.querySelector("#af"));
    const p = new URLSearchParams();
    for (const [k, v] of f) if (v && v !== "0") p.set(k, v);
    Object.entries(extra).forEach(([k, v]) => p.set(k, v));
    location.hash = `#/parent/audit?${p}`;
  };
  body.querySelector("#af").onsubmit = (e) => { e.preventDefault(); nav({}); };
  body.querySelector("#verify").onclick = async () => {
    const v = await api("/api/parent/audit/verify");
    body.querySelector("#verifyout").innerHTML = v.ok
      ? `<div class="note good"><b>Audit chain intact</b><span class="muted">All ${v.rows} entries verified — each row's SHA-256 hash links to the one before it, so nothing has been edited or deleted.</span></div>`
      : `<div class="note bad"><b>Audit chain broken at entry #${v.first_bad_id}</b><span class="muted">An entry was changed or removed outside the app after it was written.</span></div>`;
  };
  body.querySelectorAll("[data-pg]").forEach((b) => b.onclick = () => nav({ page: b.dataset.pg }));
}

// ---------------------------------------------------------------- monitoring
async function monitoring(body) {
  const params = new URLSearchParams(location.hash.split("?")[1] || "");
  const hours = +(params.get("hours") || 24);
  const m = await api(`/api/parent/monitoring?hours=${hours}`);
  const h = m.health;
  const up = h.uptime_sec > 86400 ? `${Math.floor(h.uptime_sec / 86400)}d ${Math.floor((h.uptime_sec % 86400) / 3600)}h` : `${Math.floor(h.uptime_sec / 3600)}h ${Math.floor((h.uptime_sec % 3600) / 60)}m`;
  body.innerHTML = `
    <div class="row" style="margin-bottom:12px"><span><span class="health-dot"></span><b>System healthy</b></span><span class="faint">auto-refreshes every 15s</span><span class="spacer"></span>
      <select id="hrs">${[1, 6, 24, 168].map((n) => `<option value="${n}" ${n === hours ? "selected" : ""}>Last ${n < 168 ? n + "h" : "7 days"}</option>`).join("")}</select></div>
    <div class="kpis">
      ${kpi(up, "Uptime", `since ${fmtTime(h.started_at)}`)}
      ${kpi(m.http.total, "API requests", `${m.http_5xx} server errors`)}
      ${kpi(m.runner.runs, "Simulations run", `p50 ${m.runner.p50_ms ?? "—"} ms · p95 ${m.runner.p95_ms ?? "—"} ms`)}
      ${kpi(`${m.runner.sim_seconds} s`, "Robot time simulated", `${m.runner.frames.toLocaleString()} frames · payload p95 ${m.runner.payload_kb_p95 ?? "—"} KB`)}
      ${kpi(m.teleop.sessions, "Drive-mode sessions", `${m.teleop.ticks} ticks · p95 ${m.teleop.p95_ms ?? "—"} ms`)}
      ${kpi(m.checker.checks, "Checks", `pass rate ${pct(m.checker.pass_rate)} · p95 ${m.checker.p95_ms ?? "—"} ms`)}
      ${kpi(m.runner.killed + m.runner.output_limit + m.checker.timeouts, "Runaway programs stopped", `${m.runner.killed} frozen loops · ${m.runner.output_limit} print floods · ${m.checker.timeouts} test timeouts`)}
      ${kpi(m.error_count_24h, "Server exceptions (24h)", `${m.checker.internal_errors} checker errors`)}
      ${kpi(`${(h.db_bytes / 1e6).toFixed(2)} MB`, "Database size", `${h.disk_free_gb} GB disk free`)}
      ${kpi(h.rss_mb ? `${h.rss_mb} MB` : "—", "Server memory (peak)", `Python ${h.python} · pid ${h.pid}`)}
      ${kpi(m.tutor.calls, "AI tutor calls", `avg ${m.tutor.avg_ms ?? "—"} ms · p95 ${m.tutor.p95_ms ?? "—"} ms · ${m.tutor.errors} errors · ${m.tutor.refused} declined`)}
      ${kpi((m.tutor.tokens_in + m.tutor.tokens_out).toLocaleString(), "AI tutor tokens", `${m.tutor.tokens_in.toLocaleString()} in · ${m.tutor.tokens_out.toLocaleString()} out`)}
    </div>
    <div class="grid g2">
      <div class="card"><h3>API requests (per 10 min)</h3><div class="chart-box"><canvas id="m-http"></canvas></div></div>
      <div class="card"><h3>Simulations & tests (per 10 min)</h3><div class="chart-box"><canvas id="m-run"></canvas></div></div>
    </div>
    <div class="grid g2" style="margin-top:16px">
      <div class="card"><h3>Endpoints</h3><div class="tscroll" style="max-height:360px"><table class="t"><thead><tr><th>Route</th><th class="num">Count</th><th class="num">Avg ms</th><th class="num">p95 ms</th><th class="num">Max ms</th></tr></thead>
        <tbody>${m.http.routes.map((r) => `<tr><td><code>${esc(r.route)}</code></td><td class="num">${r.count}</td><td class="num">${r.avg_ms}</td><td class="num">${r.p95_ms ?? "—"}</td><td class="num">${r.max_ms}</td></tr>`).join("")}</tbody></table></div></div>
      <div class="card"><h3>Server exceptions</h3><div class="tscroll" style="max-height:360px"><table class="t"><thead><tr><th>Time</th><th>Where</th><th>Message</th></tr></thead>
        <tbody>${m.errors.map((e) => `<tr><td>${fmtTime(e.ts)}</td><td>${esc(e.source)}</td><td><a href="#" data-err="${e.id}">${esc(e.message)}</a></td></tr>`).join("") || `<tr><td colspan="3" class="faint">No exceptions. 🎉</td></tr>`}</tbody></table></div>
        <pre id="errdetail" class="hidden" style="max-height:260px"></pre></div>
    </div>
    <div class="card" style="margin-top:16px"><h3>Runtime</h3><table class="t"><tbody>
      <tr><td>Platform</td><td>${esc(h.platform)}</td></tr><tr><td>Database</td><td><code>${esc(h.db_path)}</code></td></tr>
      <tr><td>Active right now</td><td>${m.active_now.runs} simulations · ${m.active_now.checks} tests</td></tr>
      <tr><td>Health endpoint</td><td><a href="/api/health" target="_blank">/api/health</a></td></tr></tbody></table></div>`;
  const { col, grid } = chartSetup();
  const ts = (arr) => arr.map((p) => ({ x: p.t * 1000, y: p.v }));
  const xTime = { type: "linear", ticks: { callback: (v) => new Date(v).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }), maxTicksLimit: 8 }, grid: { display: false } };
  makeChart(body.querySelector("#m-http"), {
    type: "line", data: { datasets: [{ label: "Requests", data: ts(m.http.series), borderColor: col[0], backgroundColor: col[0], borderWidth: 2, pointRadius: 0, tension: 0.2 }] },
    options: baseOpts(grid, { plugins: { legend: { display: false } }, scales: { x: xTime, y: { beginAtZero: true, grid: { color: grid } } } }),
  });
  makeChart(body.querySelector("#m-run"), {
    type: "line", data: { datasets: [
      { label: "Simulations", data: ts(m.runner_series), borderColor: col[0], backgroundColor: col[0], borderWidth: 2, pointRadius: 0, tension: 0.2 },
      { label: "Tests", data: ts(m.checker_series), borderColor: col[1], backgroundColor: col[1], borderWidth: 2, pointRadius: 0, tension: 0.2, borderDash: [5, 4] }] },
    options: baseOpts(grid, { scales: { x: xTime, y: { beginAtZero: true, grid: { color: grid } } } }),
  });
  body.querySelector("#hrs").onchange = (e) => { location.hash = `#/parent/monitoring?hours=${e.target.value}`; };
  body.querySelectorAll("[data-err]").forEach((a) => a.onclick = async (e) => {
    e.preventDefault();
    const d = await api(`/api/parent/errors/${a.dataset.err}`);
    const pre = body.querySelector("#errdetail"); pre.classList.remove("hidden"); pre.textContent = d.detail;
  });
  const timer = setInterval(() => {
    if (!location.hash.startsWith("#/parent/monitoring")) return clearInterval(timer);
    if (document.visibilityState === "visible") monitoring(body).then(() => clearInterval(timer));
  }, 15000);
}

// ---------------------------------------------------------------- data
async function data(body) {
  const d = await api("/api/parent/data");
  body.innerHTML = `
    <div class="card"><h3>Data catalog</h3><p class="muted" style="margin-top:0">Everything RoboQuest stores, all locally in one SQLite file on this computer. Nothing is sent anywhere (except AI tutor messages, if you turn Sprocket on).</p>
      <div class="tscroll"><table class="t"><thead><tr><th>Table</th><th>What it holds</th><th class="num">Rows</th><th>First</th><th>Last</th><th>Export</th></tr></thead>
      <tbody>${d.tables.map((t) => `<tr><td><a href="#" data-t="${t.table}"><code>${t.table}</code></a></td><td class="muted">${esc(t.description)}</td><td class="num">${t.rows}</td>
        <td>${t.first ? fmtTime(t.first) : "—"}</td><td>${t.last ? fmtTime(t.last) : "—"}</td>
        <td>${t.table === "settings" ? "—" : `<a href="/api/parent/export/${t.table}.csv">CSV</a> · <a href="/api/parent/export/${t.table}.json">JSON</a>`}</td></tr>`).join("")}</tbody></table></div>
      <div class="row" style="margin-top:12px"><a class="btn primary" href="/api/parent/backup">⬇ Download full backup (.db)</a></div></div>
    <div class="grid g2" style="margin-top:16px">
      <div class="card"><h3>Data collected per day</h3><div class="chart-box"><canvas id="d-daily"></canvas></div></div>
      <div class="card"><h3>Data quality</h3><table class="t"><tbody>
        <tr><td>Runs without a learner</td><td class="num">${d.quality.runs_without_learner}</td></tr>
        <tr><td>Orphaned progress rows</td><td class="num">${d.quality.orphan_progress}</td></tr>
        <tr><td>Learning sessions active now</td><td class="num">${d.quality.sessions_open}</td></tr>
        <tr><td>Tests without a mission row</td><td class="num">${d.quality.checks_without_step}</td></tr>
        <tr><td>Runs with negative durations</td><td class="num">${d.quality.negative_durations}</td></tr>
        <tr><td>Audit id gaps (24h)</td><td class="num">${d.quality.audit_gaps_24h}</td></tr></tbody></table>
        <h3 style="margin-top:16px">Retention</h3><p class="muted">Prune bulky telemetry (run-time code snapshots and system metrics) older than N days. Progress, checks, ideas, and the audit log are kept.</p>
        <div class="row"><input id="ret" type="number" min="7" value="90" style="width:100px"> days <button class="btn" id="prune">Prune now</button></div></div>
    </div>
    <div class="card" style="margin-top:16px" id="browser"><h3>Browse a table</h3><p class="faint">Click a table name above.</p></div>`;
  const { col, grid } = chartSetup();
  const days = [...new Set(d.daily.map((r) => r.d))].sort();
  const kinds = ["runs", "checks", "hints", "snapshots", "audit", "drives"];
  makeChart(body.querySelector("#d-daily"), {
    type: "bar",
    data: { labels: days.map((x) => x.slice(5)), datasets: kinds.map((k, i) => ({ label: k, data: days.map((day) => d.daily.find((r) => r.d === day && r.k === k)?.n || 0), backgroundColor: col[i], borderRadius: 2, maxBarThickness: 22 })) },
    options: baseOpts(grid, { scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, beginAtZero: true, grid: { color: grid } } } }),
  });
  body.querySelector("#prune").onclick = async () => {
    const n = +body.querySelector("#ret").value;
    if (!confirm(`Delete run snapshots and metrics older than ${n} days?`)) return;
    const r = await api("/api/parent/retention", { method: "POST", body: { days: n } });
    toast(`Pruned ${r.snapshots_deleted} snapshots and ${r.metrics_deleted} metric rows.`);
    data(body);
  };
  body.querySelectorAll("[data-t]").forEach((a) => a.onclick = (e) => { e.preventDefault(); browse(body.querySelector("#browser"), a.dataset.t, 0); });
}

async function browse(host, table, offset) {
  const d = await api(`/api/parent/data/${table}?limit=50&offset=${offset}`);
  const cell = (v) => { const s = v === null ? "" : String(v); return esc(s.length > 140 ? s.slice(0, 140) + "…" : s); };
  host.innerHTML = `<div class="row"><h3 style="margin:0">${esc(table)}</h3><span class="faint">${offset + 1}–${Math.min(offset + 50, d.total)} of ${d.total}</span><span class="spacer"></span>
    ${offset ? `<button class="btn small" data-o="${offset - 50}">← Prev</button>` : ""}${offset + 50 < d.total ? `<button class="btn small" data-o="${offset + 50}">Next →</button>` : ""}</div>
    <div class="tscroll" style="margin-top:10px"><table class="t"><thead><tr>${d.columns.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead>
    <tbody>${d.rows.map((r) => `<tr>${d.columns.map((c) => `<td>${c === "ts" || c.endsWith("_at") || c === "last_seen" ? (r[c] ? fmtTime(r[c]) : "") : cell(r[c])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  host.querySelectorAll("[data-o]").forEach((b) => b.onclick = () => browse(host, table, +b.dataset.o));
  host.scrollIntoView({ behavior: "smooth" });
}

// ---------------------------------------------------------------- settings
async function settings(body) {
  const l = learners.find((x) => x.id === sel);
  body.innerHTML = `<div class="grid g2">
    ${l ? `<div class="card"><h3>${l.avatar} ${esc(l.name)}</h3>
      <p><label>Plan start date<br><input type="date" id="sd" value="${l.start_date}"></label></p>
      <p class="muted">The 6-week schedule (and "ahead / behind") is measured from this date.</p>
      <p><button class="btn primary" id="save">Save</button></p>
      <h3 style="margin-top:24px">Danger zone</h3><p class="muted">Permanently delete this learner and all of their progress, code and analytics. The audit log keeps a record that it happened.</p>
      <button class="btn danger" id="del">Delete ${esc(l.name)}'s data</button></div>` : ""}
    <div class="card"><h3>Parent PIN</h3><p><input type="password" id="np" placeholder="New PIN" inputmode="numeric"> <button class="btn" id="chg">Change PIN</button></p>
      <h3 style="margin-top:20px">Appearance</h3><p><select id="pt"><option value="system">Follow system</option><option value="light">Light</option><option value="dark">Dark</option></select>
        <label style="margin-left:10px"><input type="checkbox" id="cel"> Confetti on success</label></p>
      <h3 style="margin-top:20px">Curriculum reference</h3><p class="muted">Every mission's reference solution and hints (for helping when he's stuck).</p>
      <select id="sol">${state.curriculum.projects.flatMap((p) => [...p.steps, p.boss].map((s) => `<option value="${p.id}/${s.id}">${p.emoji} ${esc(p.title)} — ${esc(s.title)}</option>`)).join("")}</select>
      <button class="btn" id="showsol">Show</button><pre id="solout" class="hidden"></pre></div></div>`;
  body.querySelector("#save")?.addEventListener("click", async () => {
    await api(`/api/learners/${sel}`, { method: "PATCH", body: { start_date: body.querySelector("#sd").value } });
    toast("Saved"); reportCache = {};
  });
  body.querySelector("#del")?.addEventListener("click", async () => {
    if (prompt(`Type ${l.name} to confirm deleting all of their data`) !== l.name) return;
    await api(`/api/parent/learners/${sel}`, { method: "DELETE" });
    if (state.learner?.id === sel) { state.learner = null; store.set("rq_learner", ""); }
    toast("Deleted"); sel = null; location.hash = "#/parent/overview";
  });
  body.querySelector("#chg").onclick = async () => {
    try { await api("/api/parent/pin", { method: "POST", body: { pin: body.querySelector("#np").value } }); toast("PIN changed"); } catch (e) { toast(esc(e.message)); }
  };
  const pt = body.querySelector("#pt");
  pt.value = store.get("rq_theme", "system");
  pt.onchange = () => applyTheme(pt.value);
  const cel = body.querySelector("#cel");
  cel.checked = store.get("rq_celebrate", "on") !== "off";
  cel.onchange = () => store.set("rq_celebrate", cel.checked ? "on" : "off");
  body.querySelector("#showsol").onclick = async () => {
    const [p, s] = body.querySelector("#sol").value.split("/");
    const d = await api(`/api/parent/solution/${p}/${s}`);
    const pre = body.querySelector("#solout"); pre.classList.remove("hidden");
    pre.textContent = `${d.solution}\n\n# Hints:\n${d.hints.map((h, i) => `# ${i + 1}. ${h}`).join("\n")}`;
  };
}

// ---------------------------------------------------------------- robot skills (robotics-specific analytics)
async function robotics(body) {
  const r = reportCache[sel] || await report();
  const rb = r.robot, ex = r.style.experiments;
  const names = { distance: "Ultrasonic (distance)", floor: "Floor light", light: "Light", heading: "Compass / gyro", encoder: "Wheel encoders", bumper: "Bumper" };
  body.innerHTML = `
    <div class="kpis">
      ${kpi(rb.runs, "Simulations run", `${rb.robot_seconds} s of robot time`)}
      ${kpi(`${rb.distance_m} m`, "Distance his robots drove", `${rb.gems} gems collected`)}
      ${kpi(pct(rb.crash_run_rate), "Runs that bumped something", rb.crash_rate_early !== null ? `first half ${pct(rb.crash_rate_early)} → second half ${pct(rb.crash_rate_late)}` : "")}
      ${kpi(rb.sensor_kinds, "Sensor types used", Object.keys(rb.sensors).map((k) => names[k] || k).join(", "))}
      ${kpi(rb.drive.sessions, "Drive-mode sessions", `${rb.drive.minutes} min · ${rb.drive.distance_m} m · ${rb.drive.crashes} bumps`)}
      ${kpi(rb.arenas_built, "Arenas he designed", rb.arena_complexity.length ? `design scores ${rb.arena_complexity.join(", ")}` : "")}
    </div>
    <div class="grid g2">
      <div class="card"><h3>How he changes code between runs</h3><p class="muted" style="margin-top:0">A <b>tune</b> changes only numbers (like Kp or a threshold) — classic engineering iteration. A small edit changes a few lines; a rewrite changes most of the program.</p>
        <div class="chart-box short"><canvas id="r-exp"></canvas></div>
        ${ex.most_tuned.length ? `<p class="muted small">Most-tuned missions: ${ex.most_tuned.map((m) => `${esc(m.project_id)}/${esc(m.step_id)} (${m.tunes})`).join(", ")}</p>` : ""}</div>
      <div class="card"><h3>Safety over time</h3><p class="muted" style="margin-top:0">Share of runs each week in which the robot bumped into something. Falling = he's predicting his robot better.</p>
        <div class="chart-box short"><canvas id="r-safe"></canvas></div></div>
    </div>
    <div class="grid g2" style="margin-top:16px">
      <div class="card"><h3>Sensors he reads</h3><div class="chart-box short"><canvas id="r-sens"></canvas></div>
        <p class="muted small">First used: ${rb.sensor_timeline.map((s) => `${names[s.sensor] || s.sensor} (${fmtTime(s.first)})`).join(" · ") || "—"}</p></div>
      <div class="card"><h3>Robotics concepts</h3><div class="tscroll" style="max-height:320px"><table class="t"><thead><tr><th>Concept</th><th>Status</th><th class="num">Score</th><th class="num">On his own</th></tr></thead>
        <tbody>${r.mastery.map((m) => `<tr><td>${esc(m.label)}</td><td>${esc(m.status)}</td><td class="num">${pct(m.score)}</td><td class="num">${m.independent_uses}</td></tr>`).join("")}</tbody></table></div></div>
    </div>`;
  const { col, grid } = chartSetup();
  makeChart(body.querySelector("#r-exp"), { type: "bar",
    data: { labels: ["Tunes (numbers only)", "Small edits", "Rewrites", "Re-runs, no change"], datasets: [{ data: [ex.tune, ex.small, ex.rewrite, ex.reruns_unchanged], backgroundColor: col[0], borderRadius: 4, maxBarThickness: 26 }] },
    options: baseOpts(grid, { indexAxis: "y", plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: grid } }, y: { grid: { display: false } } } }) });
  makeChart(body.querySelector("#r-safe"), { type: "line",
    data: { labels: rb.weekly.map((w) => `Week ${w.week}`), datasets: [{ label: "Runs with a crash", data: rb.weekly.map((w) => w.runs ? Math.round(w.crash_runs / w.runs * 100) : 0), borderColor: col[1], backgroundColor: col[1], borderWidth: 2, pointRadius: 3, tension: 0.25 }] },
    options: baseOpts(grid, { plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } }, y: { min: 0, max: 100, ticks: { callback: (v) => v + "%" }, grid: { color: grid } } } }) });
  const sk = Object.keys(rb.sensors);
  makeChart(body.querySelector("#r-sens"), { type: "bar",
    data: { labels: sk.map((k) => names[k] || k), datasets: [{ label: "Runs that read it", data: sk.map((k) => rb.sensors[k]), backgroundColor: col[2], borderRadius: 4, maxBarThickness: 22 }] },
    options: baseOpts(grid, { indexAxis: "y", plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: grid } }, y: { grid: { display: false } } } }) });
}

async function replayModal(snap) {
  const m = modal(`<div class="row"><h3 style="margin:0">Replay · ${esc(snap.kind)} · ${fmtTime(snap.ts)}</h3><span class="spacer"></span><button class="btn small" data-close>Close</button></div>
    <div data-a style="height:420px;margin-top:10px"></div><div class="row" style="margin-top:8px"><button class="btn small" data-p>⏯</button><span class="faint small" data-info>Simulating…</span></div>`, { wide: true });
  const v = new ArenaView(m.node.querySelector("[data-a]"));
  const res = await api(`/api/parent/replay/${sel}`, { method: "POST", body: { snapshot: snap.id } });
  v.setResult(res);
  const s = res.summary || {};
  m.node.querySelector("[data-info]").textContent = res.error ? `Stopped by ${res.error.type} on line ${res.error.line}` :
    `${Number(s.time || 0).toFixed(1)} s · ${s.crashes || 0} crashes${s.gems_total ? ` · ${s.gems}/${s.gems_total} gems` : ""}`;
  m.node.querySelector("[data-p]").onclick = () => v.toggle();
  const obs = new MutationObserver(() => { if (!document.body.contains(m.node)) { v.dispose(); obs.disconnect(); } });
  obs.observe(document.getElementById("modal-root"), { childList: true });
}
