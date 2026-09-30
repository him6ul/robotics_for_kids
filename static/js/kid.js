// Kid-facing screens.
import { api, applyTheme, celebrate, chartDefaults, el, esc, fmtMin, makeChart, modal, seriesColors, setContext, sfx, state, store, toast } from "./core.js";
import { createWorkspace, rewards, showBadge } from "./workspace.js";
import { closeManual, manualHTML } from "./manual.js";

const AVATARS = ["🤖", "🦾", "🛸", "🚀", "🦊", "🐙", "🦉", "🐧", "🦖", "🐢", "🦈", "🐝"];
const ROBOT_COLORS = ["#5b8def", "#5f9b76", "#c98a52", "#8f74a8", "#c0625c", "#5d8f96", "#8d9197", "#b89a4a"];
const ACCENTS = { blue: "#50709e", sage: "#5b8570", clay: "#a2694e", plum: "#7d6591" };
const WEEK_NAMES = { 1: "Make it move", 2: "Robots that sense", 3: "Follow the line", 4: "Know where you are", 5: "Grab & build", 6: "Smart robots" };
let currentWs = null;

export function disposeWorkspace() {
  closeManual();
  if (currentWs) { currentWs.dispose(); currentWs = null; }
}
export function setWorkspace(ws) { currentWs = ws; }

const project = (id) => state.curriculum.projects.find((p) => p.id === id);
const progressOf = (pid, sid) => state.kidState?.progress.find((r) => r.project_id === pid && r.step_id === sid);
const isDone = (pid, sid) => progressOf(pid, sid)?.status === "done";
const pstatus = (pid) => state.kidState?.projects.find((p) => p.id === pid);
const isOpen = (pid, sid) => !!state.kidState?.open?.[pid]?.includes(sid);
function lockedRedirect(pid, why) {
  toast(`🔒 ${esc(why)}`);
  location.hash = pid ? `#/project/${pid}` : "#/map";
}
const concept = (c) => esc(state.curriculum.concepts[c] || c);

export async function refreshState() {
  state.kidState = await api(`/api/learners/${state.learner.id}/state`);
  state.learner = state.kidState.learner;
  renderTopbar();
  return state.kidState;
}

export function renderTopbar() {
  const s = state.kidState;
  if (!s) return;
  const L = s.level;
  document.getElementById("xpchip").innerHTML =
    `<span class="lvl">Lv ${L.level}</span><span class="faint">${esc(L.title)}</span><span class="bar"><i style="width:${Math.round((L.into / L.needed) * 100)}%"></i></span>`;
  document.getElementById("xpchip").title = `${L.xp} XP total — ${L.needed - L.into} XP to the next level`;
  document.getElementById("streakchip").textContent = `🔥 ${s.streak.current}`;
  document.getElementById("whoami").textContent = state.learner.avatar;
  document.getElementById("soundbtn").textContent = state.learner.sound ? "🔊" : "🔇";
}

export function learnerTheme(l) {
  const [mode, accent] = String(l?.theme || "system|blue").split("|");
  applyTheme(["system", "light", "dark"].includes(mode) ? mode : "system", ACCENTS[accent] ? accent : "blue");
}

// ---------------------------------------------------------------- welcome
export async function viewWelcome(app) {
  setContext("_home", "welcome");
  const learners = await api("/api/learners");
  app.innerHTML = `<div class="welcome">
    <div class="hero"><div class="logo">🤖</div><div><h1 style="margin:0">RoboQuest</h1>
      <div class="muted">Six weeks, twelve robots. Learn robotics by programming a robot to drive, sense, follow lines, grab things and solve mazes.</div></div></div>
    ${learners.length ? `<h3>Who's building today?</h3><div class="learners">${learners.map((l) => `
      <div class="learner-card" data-id="${l.id}"><div class="av">${l.avatar}</div><div><b>${esc(l.name)}</b>
      <div class="faint small">Level ${l.level.level} · ${esc(l.level.title)}</div></div></div>`).join("")}</div>` : ""}
    <div class="card">
      <h2>${learners.length ? "New engineer" : "Set up your robot lab"}</h2>
      <div class="form-grid">
        <label for="nm">Your name</label><input id="nm" maxlength="40" placeholder="e.g. Aarav">
        <label for="rn">Robot's name</label><input id="rn" maxlength="20" value="Bolt">
        <label>Avatar</label><div class="choice-grid" data-g="av">${AVATARS.map((a, i) => `<button data-v="${a}" class="${i ? "" : "sel"}">${a}</button>`).join("")}</div>
        <label>Robot colour</label><div class="choice-grid" data-g="rc">${ROBOT_COLORS.map((c, i) => `<button class="swatch ${i ? "" : "sel"}" data-v="${c}" style="background:${c}" aria-label="colour ${c}"></button>`).join("")}</div>
        <label>Look</label><div class="row"><div class="seg" data-g="mode">${["system", "light", "dark"].map((m) => `<button data-v="${m}" class="${m === "system" ? "on" : ""}">${m[0].toUpperCase() + m.slice(1)}</button>`).join("")}</div>
          <div class="choice-grid" data-g="ac">${Object.entries(ACCENTS).map(([k, c], i) => `<button class="swatch ${i ? "" : "sel"}" data-v="${k}" style="background:${c}" aria-label="${k}"></button>`).join("")}</div></div>
      </div>
      <p style="margin-top:18px"><button class="btn primary big" id="go">Start building →</button></p>
    </div></div>`;
  const pick = { av: AVATARS[0], rc: ROBOT_COLORS[0], mode: "system", ac: "blue" };
  app.querySelectorAll("[data-g]").forEach((grp) => grp.querySelectorAll("button").forEach((b) => b.onclick = () => {
    pick[grp.dataset.g] = b.dataset.v;
    grp.querySelectorAll("button").forEach((x) => x.classList.toggle(grp.classList.contains("seg") ? "on" : "sel", x === b));
    if (grp.dataset.g === "mode" || grp.dataset.g === "ac") applyTheme(pick.mode, pick.ac);
  }));
  app.querySelectorAll(".learner-card").forEach((c) => c.onclick = () => pickLearner(learners.find((l) => l.id == c.dataset.id)));
  app.querySelector("#go").onclick = async () => {
    const name = app.querySelector("#nm").value.trim();
    if (!name) { app.querySelector("#nm").focus(); app.querySelector("#nm").classList.add("shake"); return; }
    const l = await api("/api/learners", { method: "POST", body: { name, avatar: pick.av, robot_color: pick.rc,
      robot_name: app.querySelector("#rn").value.trim() || "Bolt", theme: `${pick.mode}|${pick.ac}` } });
    celebrate(1);
    pickLearner(l);
  };
}

function pickLearner(l) {
  state.learner = l;
  store.set("rq_learner", l.id);
  learnerTheme(l);
  location.hash = "#/home";
}

// ---------------------------------------------------------------- home
export async function viewHome(app) {
  setContext("_home", "home");
  const s = await refreshState();
  const g = s.guide, pos = g.position;
  const total = state.curriculum.projects.length;
  const done = s.projects.filter((p) => p.complete).length;
  const steps = s.projects.reduce((a, p) => a + p.steps_done, 0), all = s.projects.reduce((a, p) => a + p.steps_total, 0);
  const isQuest = pos?.project === "_practice";
  const cur = pos ? (isQuest ? { emoji: "🗡️", week: pos.week, title: pos.project_title } : project(pos.project)) : null;
  const statusPill = { ahead: "good", "on track": "good", behind: "warn" }[g.schedule.status] || "";
  app.innerHTML = `
    <div class="hello"><div class="av">${state.learner.avatar}</div>
      <div><h1 style="margin:0">Hi ${esc(state.learner.name)}</h1><div class="muted">${esc(state.learner.robot_name)} is charged and ready.</div></div></div>
    <div class="grid g2">
      ${cur ? `<div class="card continue-card"><div class="big-emoji">${cur.emoji}</div>
        <div style="flex:1"><div class="faint small">Week ${cur.week} · ${esc(cur.title)}</div>
        <h2 style="margin:2px 0 8px">${esc(pos.step_title)}</h2><a class="btn primary" href="${isQuest ? `#/practice/${pos.step}` : pos.step === "remix" ? `#/remix/${pos.project}` : `#/code/${pos.project}/${pos.step}`}">Continue →</a>
        ${isQuest ? `<div class="faint small" style="margin-top:6px">Finish every week ${pos.week} side quest to unlock week ${pos.week + 1}.</div>` : ""}</div></div>`
      : `<div class="card continue-card"><div class="big-emoji">🎓</div><div><h2>RoboQuest complete!</h2><p class="muted">All 12 robots built. Design your own arena and challenge a friend.</p>
        <a class="btn primary" href="#/builder">Arena builder</a></div></div>`}
      <div class="card"><div class="stats">
        <div class="stat"><div class="num">${done}/${total}</div><div class="lbl">Robots built</div></div>
        <div class="stat"><div class="num">${s.level.xp}</div><div class="lbl">XP</div></div>
        <div class="stat"><div class="num">${s.streak.current}</div><div class="lbl">Day streak</div></div>
        <div class="stat"><div class="num">${s.today_minutes}</div><div class="lbl">Minutes today</div></div></div>
        <div style="margin-top:14px"><div class="row"><b>Quest progress</b><span class="spacer"></span><span class="faint small">${steps}/${all} missions</span>
          <span class="pill ${statusPill}">${esc(g.schedule.status)}</span></div>
        <div class="progress" style="margin-top:6px"><i style="width:${all ? (steps / all) * 100 : 0}%"></i></div></div>
      </div>
    </div>
    <div class="grid g2" style="margin-top:16px">
      <div class="card"><h3>Your guide suggests</h3><div class="guide-list">${g.kid.map(guideItem).join("")}</div></div>
      <div class="card"><h3>Recent badges</h3>${badgeProgress(s.badges)}${badgeGrid(s.badges.filter((b) => b.earned_at).sort((a, b) => b.earned_at - a.earned_at).slice(0, 6), true)}
        <p class="small"><a href="#/journey">All badges and your stats →</a></p></div>
    </div>
    <h2 style="margin-top:26px">The 6-week quest</h2>
    ${questMap(s)}`;
  bindGuide(app);
}

function guideItem(r) {
  return `<div class="guide-item"><span class="e">${r.emoji || "→"}</span><div style="flex:1"><b>${esc(r.title)}</b><span class="muted">${esc(r.text)}</span></div>
    ${r.action ? `<button class="btn small" data-action='${esc(JSON.stringify(r.action))}'>Go</button>` : ""}</div>`;
}

function bindGuide(app) {
  app.querySelectorAll("[data-action]").forEach((b) => b.onclick = () => {
    const a = JSON.parse(b.dataset.action);
    if (a.type === "step") location.hash = `#/code/${a.project}/${a.step}`;
    else if (a.type === "practice") location.hash = `#/practice/${a.id}`;
    else if (a.type === "remix") location.hash = `#/remix/${a.project}`;
    else if (a.type === "playground") location.hash = "#/playground";
    else if (a.type === "drive") location.hash = "#/drive";
    else if (a.type === "bestiary") location.hash = "#/journey";
    else if (a.type === "reflect") reflect(a.project);
  });
}

const BADGE_ORDER = ["Quest milestones", "Bosses", "Remixes", "Side quests", "Skills & habits"];
function badgeSections(badges) {
  return BADGE_ORDER.map((cat) => {
    // earned first (most recent first), then the rest in their original order
    const items = badges.filter((b) => (b.category || "Skills & habits") === cat)
      .map((b, i) => [b, i]).sort(([a, i], [b, j]) => (b.earned_at ? 1 : 0) - (a.earned_at ? 1 : 0) || (b.earned_at || 0) - (a.earned_at || 0) || i - j)
      .map(([b]) => b);
    if (!items.length) return "";
    const got = items.filter((b) => b.earned_at).length;
    return `<div style="margin-top:14px"><div class="row" style="margin-bottom:8px"><b>${esc(cat)}</b>
      <span class="pill ${got === items.length ? "good" : ""}">${got}/${items.length}</span></div>${badgeGrid(items)}</div>`;
  }).join("");
}

export function badgeProgress(badges) {
  const got = badges.filter((b) => b.earned_at).length, total = badges.length;
  return `<div style="margin-bottom:12px"><div class="row"><span class="muted small">Badges collected</span><span class="spacer"></span>
    <b class="small">${got}/${total}</b></div>
    <div class="progress" style="margin-top:5px" title="${Math.round(got / total * 100)}% of all badges"><i style="width:${total ? got / total * 100 : 0}%"></i></div></div>`;
}

function badgeGrid(badges, onlyEarned = false) {
  if (onlyEarned && !badges.length) return `<p class="faint">No badges yet — run your first robot program to earn one.</p>`;
  return `<div class="badge-grid">${badges.map((b) => `<div class="badge ${b.earned_at ? "" : "locked"}" title="${esc(b.desc)}">
    <div class="e">${b.emoji}</div><div class="n">${esc(b.name)}</div><div class="d">${esc(b.desc)}</div></div>`).join("")}</div>`;
}

function questMap(s) {
  const pos = s.guide.position;
  return `<div class="weeks">${[1, 2, 3, 4, 5, 6].map((w) => `<div class="week">
    <div class="week-head"><span class="wk">WEEK ${w}</span><span class="muted">${WEEK_NAMES[w]}</span><span class="spacer"></span>
      ${s.week_quests?.[w]?.total ? `<a class="pill ${s.week_quests[w].done === s.week_quests[w].total ? "good" : ""}" href="#/practice">🗡️ side quests ${s.week_quests[w].done}/${s.week_quests[w].total}</a>` : ""}</div>
    <div class="proj-row">${s.projects.filter((p) => p.week === w).map((ps) => {
      const p = project(ps.id);
      if (!p) return "";
      const cls = !ps.unlocked ? "locked" : ps.complete ? "complete" : pos && pos.project === ps.id ? "current" : "";
      return `<a class="proj ${cls}" ${ps.unlocked ? `href="#/project/${ps.id}"` : ""} title="${ps.unlocked ? "" : "Finish the previous robot — missions, boss and remix — to unlock"}">
        <div class="pe">${ps.unlocked ? p.emoji : "🔒"}</div>
        <div style="flex:1;min-width:0"><b>${esc(p.title)}</b><div class="faint small">${esc(p.tagline)}</div>
        <div class="progress" style="margin-top:8px"><i style="width:${(ps.steps_done / ps.steps_total) * 100}%"></i></div></div>
        <div class="marks">${ps.complete ? "✓" : ""}${ps.boss_done ? " 👾" : ""}${ps.remixed ? " 🎛️" : ""}</div></a>`;
    }).join("") || `<div class="faint small">Coming soon</div>`}</div></div>`).join("")}</div>`;
}

export async function viewMap(app) {
  setContext("_home", "map");
  const s = await refreshState();
  const side = s.guide.kid.filter((r) => r.kind === "practice");
  app.innerHTML = `<h1>Quest map</h1><p class="muted">Twelve robots over six weeks. Beat a robot's boss and build a remix to unlock the next one. ✓ missions done · 👾 boss beaten · 🎛️ remixed</p>
    ${side.length ? `<div class="card" style="margin-bottom:16px"><h3>Recommended side quests</h3><div class="row">${side.map((r) =>
      `<a class="btn small" href="#/practice/${r.action.id}">${esc(r.title.replace("Side quest: ", ""))}</a>`).join("")}</div></div>` : ""}
    ${questMap(s)}`;
}

// ---------------------------------------------------------------- project page
export async function viewProject(app, pid) {
  const p = project(pid);
  if (!p) { app.innerHTML = "<p>Unknown project</p>"; return; }
  setContext(pid, "-");
  await refreshState();
  const ps = pstatus(pid);
  if (!ps.unlocked) { app.innerHTML = `<div class="card"><h2>🔒 Locked</h2><p>Finish the previous robot first.</p><a class="btn" href="#/map">Back to map</a></div>`; return; }
  const stepRows = p.steps.map((s, i) => {
    const done = isDone(pid, s.id), locked = !isOpen(pid, s.id);
    return `<a class="step-row ${done ? "done" : ""} ${locked ? "locked" : ""}" href="#/code/${pid}/${s.id}">
      <span class="num">${done ? "✓" : locked ? "🔒" : i + 1}</span><div style="flex:1"><b>${esc(s.title)}</b></div>
      <span class="faint small">${s.concepts.map(concept).join(" · ")}</span><span class="pill">+${s.xp} XP</span></a>`;
  }).join("");
  app.innerHTML = `
    <div class="crumbs"><a href="#/map">Quest map</a> › Week ${p.week}</div>
    <div class="proj-hero" style="margin-top:8px"><div class="pe">${p.emoji}</div><div><h1>${esc(p.title)}</h1><p class="muted" style="max-width:760px">${esc(p.story)}</p>
      <div class="row"><span class="pill">about ${p.expected_minutes} min</span><span class="pill">you've spent ${fmtMin(ps.seconds)}</span>
      ${p.concepts.map((c) => `<span class="pill accent">${concept(c)}</span>`).join("")}</div></div></div>
    <div class="grid g2" style="margin-top:20px">
      <div class="card"><h3>Missions</h3><div class="steps">${stepRows}</div>
        ${p.real_world ? `<p class="fact" style="margin-top:14px"><b>Real robots:</b> ${esc(p.real_world)}</p>` : ""}
        ${p.build_it ? `<p class="fact"><b>Build it for real:</b> ${esc(p.build_it)}</p>` : ""}</div>
      <div class="stack">
        <div class="card"><h3>👾 Boss challenge</h3><p class="muted">The final test for this robot, worth lots of XP. Unlocks when every mission is done — beat it (and build a remix) to unlock the next robot.</p>
          <a class="step-row boss ${isOpen(pid, "boss") ? "" : "locked"} ${isDone(pid, "boss") ? "done" : ""}" href="#/code/${pid}/boss"><span class="num">${isDone(pid, "boss") ? "✓" : "👾"}</span>
          <b style="flex:1">${esc(p.boss.title)}</b><span class="pill">+${p.boss.xp} XP</span></a></div>
        <div class="card"><h3>🎛️ Remix lab</h3><p class="muted">${esc(p.remix.prompt)}</p><p class="faint small">Required: build one remix to unlock the next robot. ${ps.remixed ? "✓ Done!" : ""}</p>
          ${ps.complete ? `<a class="btn primary" href="#/remix/${pid}">Open remix lab</a>` : `<button class="btn" disabled>🔒 Finish the missions first</button>`}</div>
        ${ps.complete ? `<div class="card"><h3>How was it?</h3><p class="muted">${ps.fun ? `You rated it ${ps.fun}/5 for fun.` : "Tell us how fun and how hard this robot was."}</p>
          <button class="btn" id="rate">${ps.fun ? "Rate again" : "Rate this robot"}</button></div>` : ""}
      </div></div>`;
  app.querySelector("#rate")?.addEventListener("click", () => reflect(pid));
}

// ---------------------------------------------------------------- mission workspace
// Lessons call the robot "Bolt"; use the name he gave his own robot.
const named = (html) => {
  const n = state.learner?.robot_name;
  return n && n !== "Bolt" ? String(html || "").replace(/\bBolt\b/g, esc(n)) : html || "";
};

function missionShell(app, { crumbs, dots = "", title, learn, task, goals, concepts, xp, hintBox = true }) {
  title = named(title); learn = named(learn); task = named(task); goals = (goals || []).map(named);
  app.innerHTML = `<div class="workspace">
    <aside class="mission">
      <div class="row"><div class="crumbs">${crumbs}</div><span class="spacer"></span><button class="btn ghost small" data-collapse title="Hide the mission panel">⟨</button></div>
      ${dots}
      <div class="card"><h2>${title}</h2><div class="learn">${learn || ""}</div></div>
      <div class="card task"><h3>Your task</h3>${task}
        ${goals?.length ? `<ul class="goals">${goals.map((g) => `<li>${g}</li>`).join("")}</ul>` : ""}
        <div class="row" style="margin-top:10px">${(concepts || []).map((c) => `<span class="pill">${concept(c)}</span>`).join("")}${xp ? `<span class="pill accent">+${xp} XP</span>` : ""}</div></div>
      ${hintBox ? `<div class="card"><h3>Hints</h3><div data-hints></div>
        <div class="row"><button class="btn small" data-hint>Show a hint</button><button class="btn small ghost hidden" data-peek>Show an answer</button></div>
        <p class="faint small" style="margin:.5em 0 0">Tip: watch the replay and open the Telemetry tab first — the clue is usually there.</p></div>` : ""}
    </aside>
    <section data-ws style="min-width:0;min-height:0"></section></div>`;
  const ws = app.querySelector(".workspace");
  app.querySelector("[data-collapse]").onclick = () => {
    ws.classList.add("collapsed");
    const b = el(`<button class="btn small" style="position:fixed;left:10px;bottom:14px;z-index:30">⟩ Mission</button>`);
    b.onclick = () => { ws.classList.remove("collapsed"); b.remove(); };
    document.body.appendChild(b);
    setTimeout(() => currentWs?.cm.refresh(), 50);
  };
}

export async function viewCode(app, pid, sid) {
  const p = project(pid);
  const s = sid === "boss" ? p?.boss : p?.steps.find((x) => x.id === sid);
  if (!s) { app.innerHTML = "<p>Unknown mission</p>"; return; }
  setContext(pid, sid);
  await refreshState();
  if (state.isStale?.()) return;
  if (!pstatus(pid)?.unlocked) { lockedRedirect(null, "Finish the previous robot — missions, boss and a remix — first."); return; }
  if (!isOpen(pid, sid)) { lockedRedirect(pid, sid === "boss" ? "Finish all five missions to unlock the boss." : "Finish the missions before this one first."); return; }
  const idx = p.steps.findIndex((x) => x.id === sid);
  missionShell(app, {
    crumbs: `<a href="#/map">Map</a> › <a href="#/project/${pid}">${p.emoji} ${esc(p.title)}</a>`,
    dots: `<div class="stepdots">${[...p.steps.map((x, i) => [x.id, String(i + 1), x.title]), ["boss", "👾", "Boss"]].map(([id, label, title]) => isOpen(pid, id)
      ? `<a href="#/code/${pid}/${id}" class="${isDone(pid, id) ? "done" : ""} ${id === sid ? "cur" : ""}" title="${esc(title)}">${label}</a>`
      : `<span class="locked" title="🔒 ${esc(title)} — finish the earlier missions first">🔒</span>`).join("")}</div>`,
    title: `${sid === "boss" ? "Boss: " : `Mission ${idx + 1}: `}${esc(s.title)}`,
    learn: s.learn, task: s.task, goals: (s.goals || []).map(esc), concepts: s.concepts, xp: s.xp,
  });
  if (isDone(pid, sid)) app.querySelector(".goals")?.classList.add("passed");
  disposeWorkspace();
  currentWs = createWorkspace(app.querySelector("[data-ws]"), { project: pid, step: sid, mode: "step", onPassed: (r) => afterPass(app, p, s, r) });
  setupHints(app, pid, sid, s.hint_count);
}

async function setupHints(app, pid, sid, count) {
  const box = app.querySelector("[data-hints]");
  const btn = app.querySelector("[data-hint]"), peek = app.querySelector("[data-peek]");
  const info = await api(`/api/learners/${state.learner.id}/hints?project=${pid}&step=${sid}`);
  let used = info.used;
  const render = (text, level) => {
    const b = el(`<div class="hint-box"><b>Hint ${level}:</b> </div>`);
    b.append(...hintNodes(text));
    box.appendChild(b);
  };
  info.opened.forEach((t, i) => render(t, i + 1));
  if (info.solution) showSolution(box, info.solution);
  const refresh = (attempts) => {
    btn.classList.toggle("hidden", used >= count);
    peek.classList.toggle("hidden", !(used >= count && used < 4 && attempts >= 3));
  };
  refresh(info.attempts);
  btn.onclick = async () => {
    const r = await api(`/api/learners/${state.learner.id}/hint`, { method: "POST", body: { project: pid, step: sid, level: used + 1 } });
    used = r.level;
    render(r.text, r.level);
    refresh(info.attempts);
  };
  peek.onclick = async () => {
    if (!confirm("Peek at an answer? You'll still learn — but this mission gives less XP.")) return;
    try {
      const r = await api(`/api/learners/${state.learner.id}/hint`, { method: "POST", body: { project: pid, step: sid, level: 4 } });
      used = 4; showSolution(box, r.text); refresh(99);
    } catch (e) { toast(esc(e.message)); }
  };
  app.querySelector("[data-ws]").addEventListener("checked", (e) => { info.attempts = e.detail.attempts; refresh(info.attempts); });
}

function hintNodes(text) {
  if (/\n/.test(text) || /^\s*(robot|arm)\.|^\s*(for|while|if|def|import)\b.*[:()]/.test(text)) {
    const pre = document.createElement("pre"); pre.textContent = text; return [pre];
  }
  return [document.createTextNode(text)];
}

function showSolution(box, code) {
  const b = el(`<div class="hint-box"><b>One possible answer</b> <span class="faint">(yours can be different)</span><pre></pre></div>`);
  b.querySelector("pre").textContent = code;
  box.appendChild(b);
}

async function afterPass(app, p, s, r) {
  app.querySelector(".stepdots a.cur")?.classList.add("done");
  await refreshState();
  const box = app.querySelector("[data-panel=result]");
  if (r.project_complete) {
    setTimeout(() => {
      celebrate(1.6);
      const m = modal(`<div class="big">${p.emoji}</div><h2>You built ${esc(p.title)}!</h2>
        <p class="muted">Every mission done. Show someone what your robot can do.</p>
        <div class="row" style="justify-content:center"><button class="btn primary big" id="rateit">Rate it & continue</button></div>`);
      m.node.querySelector("#rateit").onclick = () => { m.close(); reflect(p.id, true); };
    }, 600);
  } else if (r.rewards?.xp || r.next) {
    box.insertAdjacentHTML("beforeend", `<div class="row" style="padding:0 12px 12px">
      ${r.next ? `<a class="btn primary" href="#/code/${r.next.project}/${r.next.step}">Next mission →</a>` : ""}
      ${s.id === "boss" ? `<a class="btn" href="#/project/${p.id}">Back to project</a>` : ""}</div>`);
  }
}

export function reflect(pid, thenRoute = false) {
  const p = project(pid);
  const fun = ["😴", "😐", "🙂", "😃", "🤩"], hard = ["🍰", "🙂", "🤔", "😅", "🥵"];
  let f = 0, d = 0;
  const m = modal(`<div class="big">${p.emoji}</div><h2>How was ${esc(p.title)}?</h2>
    <p><b>How fun was it?</b></p><div class="rating" data-r="fun">${fun.map((e, i) => `<button data-v="${i + 1}">${e}</button>`).join("")}</div>
    <p><b>How hard was it?</b></p><div class="rating" data-r="hard">${hard.map((e, i) => `<button data-v="${i + 1}">${e}</button>`).join("")}</div>
    <textarea id="note" rows="2" placeholder="Anything you loved or hated? (optional)"></textarea>
    <p class="row" style="justify-content:center;margin-top:12px"><button class="btn primary" id="send">Send</button><button class="btn ghost" data-close>Skip</button></p>`);
  m.node.querySelectorAll(".rating").forEach((row) => row.querySelectorAll("button").forEach((b) => b.onclick = () => {
    row.querySelectorAll("button").forEach((x) => x.classList.toggle("sel", x === b));
    if (row.dataset.r === "fun") f = +b.dataset.v; else d = +b.dataset.v;
    sfx("click");
  }));
  m.node.querySelector("#send").onclick = async () => {
    if (!f || !d) { toast("Pick one in each row"); return; }
    const r = await api(`/api/learners/${state.learner.id}/reflection`, { method: "POST", body: { project: pid, fun: f, difficulty: d, note: m.node.querySelector("#note").value } });
    m.close();
    if (r.xp) toast(`+${r.xp} XP for reflecting`);
    document.dispatchEvent(new CustomEvent("xp-changed"));
    if (thenRoute) {
      const bossDone = isDone(pid, "boss"), remixed = pstatus(pid)?.remixed;
      const m2 = modal(`<h2>What next?</h2>${bossDone && remixed ? "" : `<p class="muted">Beat the boss and build a remix to unlock the next robot.</p>`}<div class="grid" style="margin-top:12px">
        ${!bossDone ? `<a class="btn primary big" href="#/code/${pid}/boss">👾 Take on the boss</a>` : ""}
        ${!remixed ? `<a class="btn ${bossDone ? "primary" : ""} big" href="#/remix/${pid}">🎛️ Remix it your way</a>` : ""}
        ${bossDone && remixed ? `<a class="btn primary big" href="#/map">Next robot →</a>` : ""}</div>`);
      m2.node.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => m2.close()));
    }
  };
}

// ---------------------------------------------------------------- side quests
export async function viewPractice(app, id) {
  const list = state.curriculum.practice;
  if (id) {
    const pr = list.find((x) => x.id === id);
    if (!pr) { app.innerHTML = "<p>Unknown side quest</p>"; return; }
    setContext("_practice", id);
    const st = await refreshState();
    const openWeek = Math.max(1, ...st.projects.filter((p) => p.unlocked).map((p) => p.week));
    if (pr.week > openWeek) { toast(`🔒 This side quest unlocks in week ${pr.week}.`); location.hash = "#/practice"; return; }
    if (state.isStale?.()) return;
    missionShell(app, {
      crumbs: `<a href="#/practice">Side quests</a> › ${concept(pr.concept)}`,
      title: `${esc(pr.title)} <span class="faint small">${"★".repeat(pr.difficulty)}</span>`, learn: "", task: pr.task, goals: (pr.goals || []).map(esc),
      concepts: [pr.concept], xp: pr.xp,
    });
    if (isDone("_practice", id)) app.querySelector(".goals")?.classList.add("passed");
    disposeWorkspace();
    currentWs = createWorkspace(app.querySelector("[data-ws]"), {
      project: "_practice", step: id, mode: "practice",
      onPassed: async () => {
        await refreshState();
        app.querySelector("[data-panel=result]").insertAdjacentHTML("beforeend", `<div class="row" style="padding:0 12px 12px"><a class="btn primary" href="#/practice">More side quests</a><a class="btn" href="#/home">Home</a></div>`);
      },
    });
    setupHints(app, "_practice", id, pr.hint_count);
    return;
  }
  setContext("_practice", "-");
  const s = await refreshState();
  const rec = new Set(s.guide.kid.filter((r) => r.kind === "practice").map((r) => r.action.id));
  const openWeek = Math.max(1, ...s.projects.filter((p) => p.unlocked).map((p) => p.week));
  const weeks = [...new Set(list.map((p) => p.week))].sort((a, b) => a - b);
  app.innerHTML = `<h1>Side quests</h1><p class="muted">Short challenges to sharpen one skill. Every side quest in a week must be done
    (in any order) before the next week unlocks. The ones your guide recommends are marked ★.</p>
    <div class="weeks">${weeks.map((w) => {
      const items = list.filter((p) => p.week === w), q = s.week_quests?.[w] || { done: 0, total: items.length };
      const locked = w > openWeek;
      return `<div class="card ${locked ? "faint" : ""}"><div class="card-head"><h3>Week ${w} · ${WEEK_NAMES[w] || ""} ${locked ? "🔒" : ""}</h3><span class="spacer"></span>
        <span class="pill ${q.done === q.total ? "good" : ""}">${q.done}/${q.total} done</span></div>
        ${locked ? `<p class="faint">Unlocks in week ${w}.</p>` : `${q.done < q.total ? `<p class="faint small" style="margin-top:0">Required to unlock week ${w + 1}.</p>` : ""}
        <div class="grid g3" style="gap:8px">${items.sort((a, b) => a.difficulty - b.difficulty).map((p) => `
          <a class="step-row ${isDone("_practice", p.id) ? "done" : ""}" href="#/practice/${p.id}"><span class="num">${isDone("_practice", p.id) ? "✓" : p.difficulty}</span>
          <div style="flex:1;min-width:0"><b>${esc(p.title)} ${rec.has(p.id) ? "★" : ""}</b><div class="faint small">${concept(p.concept)}</div></div>
          <span class="faint small">${"★".repeat(p.difficulty)}</span></a>`).join("")}</div>`}</div>`;
    }).join("")}</div>`;
}

// ---------------------------------------------------------------- playground
function arenaOptions(list, selected) {
  const groups = {};
  list.built_in.forEach((a) => (groups[a.group] = groups[a.group] || []).push(a));
  return (list.mine.length ? `<optgroup label="My arenas">${list.mine.map((a) => `<option value="${a.ref}" ${a.ref === selected ? "selected" : ""}>🏗️ ${esc(a.name)}</option>`).join("")}</optgroup>` : "")
    + Object.entries(groups).map(([g, items]) => `<optgroup label="${esc(g)}">${items.map((a) => `<option value="${a.ref}" ${a.ref === selected ? "selected" : ""}>${esc(a.name)}</option>`).join("")}</optgroup>`).join("");
}

export async function viewPlayground(app, ref) {
  setContext("_playground", "main");
  await refreshState();
  const list = await api(`/api/learners/${state.learner.id}/arenas`);
  if (state.isStale?.()) return;
  const selected = ref ? decodeURIComponent(ref) : store.get("rq_pg_arena", "sandbox:open_lab");
  missionShell(app, {
    crumbs: "Playground", title: "Playground",
    learn: `<p>Your own lab — no goals, no tests. Pick any arena you've unlocked (or one you designed) and try whatever you like.</p>
      <p class="faint">Everything you build here counts toward your skills in <b>My journey</b>.</p>`,
    task: `<div class="guide-list">${[
      ["Wall radar", "robot.drive(40, 40)\nwhile robot.distance() > 20:\n    robot.led('green')\nrobot.stop()\nrobot.led('red')\nrobot.say('Wall!')\n"],
      ["Spirograph", "robot.pen_down('purple')\nfor i in range(12):\n    for side in range(4):\n        robot.forward(30, power=100)\n        robot.turn(90, power=100)\n    robot.turn(30, power=100)\n"],
      ["Tune player", "notes = [523, 587, 659, 523, 659, 587, 523]\nfor n in notes:\n    robot.beep(n, 0.25)\n    robot.wait(0.3)\n"],
      ["Sensor print-out", "for i in range(10):\n    print(robot.time(), robot.distance(), robot.floor(), robot.heading())\n    robot.forward(10)\n"],
    ].map(([t, c]) => `<div class="guide-item"><div style="flex:1"><b>${t}</b></div><button class="btn small" data-code="${esc(c)}">Load</button></div>`).join("")}</div>
    <p class="small" style="margin-top:10px"><a href="#/builder">Design your own arena →</a></p>
    <div style="margin-top:14px;padding-top:12px;border-top:1px solid var(--line)">${badgeProgress(state.kidState.badges)}
      <p class="faint small" style="margin:0">${state.kidState.badges.find((b) => b.id === "explorer")?.earned_at
        ? "🧭 Explorer earned — keep experimenting!" : "Run 10 experiments here to earn 🧭 Explorer."}</p></div>`,
    hintBox: false,
  });
  disposeWorkspace();
  currentWs = createWorkspace(app.querySelector("[data-ws]"), { project: "_playground", step: "main", mode: "playground", checkable: false,
    arenaRef: selected, arenaChoices: arenaOptions(list, selected), onArenaChange: (r) => store.set("rq_pg_arena", r) });
  app.querySelectorAll("[data-code]").forEach((b) => b.onclick = () => {
    if (currentWs.getCode().trim().length > 120 && !confirm("Replace your playground code?")) return;
    currentWs.setCode(b.dataset.code);
  });
}

// ---------------------------------------------------------------- ideas & remix
function ideaMeter(a) {
  const names = ["Spark", "Builder", "Inventor", "Architect", "Mastermind"];
  return `<div class="idea-meter"><i style="width:${Math.max(4, a.score)}%"></i></div>
    <div class="idea-levels">${names.map((n, i) => `<span style="${a.level === i + 1 ? "color:var(--accent);font-weight:650" : ""}">${n}</span>`).join("")}</div>
    <div class="row" style="margin-top:8px">${Object.keys(a.concepts).map((c) => `<span class="pill ${a.new_concepts.includes(c) ? "warn" : "good"}">${concept(c)}</span>`).join("")}</div>
    ${a.tips.map((t) => `<p class="muted small" style="margin:.4em 0">💬 ${esc(t)}</p>`).join("")}`;
}

function ideaComposer(host, pid, onSaved) {
  host.innerHTML = `<textarea rows="4" placeholder="Describe your robot idea… What does it sense? What does it decide? What happens when something gets in the way?"></textarea>
    <div data-meter style="margin-top:10px"></div>
    <div class="row" style="margin-top:10px"><button class="btn primary" data-save>Save idea</button><span class="faint small">Ideas earn XP — bigger ideas earn more.</span></div>`;
  const ta = host.querySelector("textarea"), meter = host.querySelector("[data-meter]");
  let t = null;
  ta.addEventListener("input", () => {
    clearTimeout(t);
    t = setTimeout(async () => {
      if (ta.value.trim().length < 5) { meter.innerHTML = ""; return; }
      meter.innerHTML = ideaMeter(await api(`/api/learners/${state.learner.id}/ideas/analyze`, { method: "POST", body: { text: ta.value } }));
    }, 350);
  });
  host.querySelector("[data-save]").onclick = async () => {
    try {
      const r = await api(`/api/learners/${state.learner.id}/ideas`, { method: "POST", body: { text: ta.value, project: pid } });
      sfx("ok");
      toast(`${esc(r.analysis.level_name)}-level idea saved · +${r.xp} XP`);
      r.badges.forEach(showBadge);
      ta.value = ""; meter.innerHTML = "";
      document.dispatchEvent(new CustomEvent("xp-changed"));
      onSaved && onSaved(r);
    } catch (e) { toast(esc(e.message)); }
  };
}

export async function viewIdeas(app) {
  setContext("_ideas", "-");
  const [data, st] = await Promise.all([api(`/api/learners/${state.learner.id}/ideas`), refreshState()]);
  const thinker = st.badges.find((b) => b.id === "big_thinker");
  app.innerHTML = `<h1>Idea journal</h1><p class="muted">Every great robot starts as an idea. Write yours down — the meter shows how ambitious it is and what you'll need to learn.</p>
    <div class="grid g2"><div class="stack"><div class="card"><h3>New idea</h3><div data-comp></div></div>
      <div class="card"><h3>Badges</h3>${badgeProgress(st.badges)}<p class="faint small" style="margin:0">${thinker?.earned_at
        ? "💡 Big Thinker earned — dream even bigger!" : "Save an idea rated 🏗️ Architect or higher to earn 💡 Big Thinker."}</p></div></div>
    <div class="card"><h3>Your ideas (${data.ideas.length})</h3><div class="grid">${data.ideas.slice().reverse().map((i) => `<div class="idea">
      <div class="row"><b>${esc(i.analysis.level_name || "")}</b><span class="pill">${i.score}/100</span>
      ${i.status === "built" ? `<span class="pill good">built</span>` : ""}<span class="spacer"></span><span class="faint small">${new Date(i.ts * 1000).toLocaleDateString()}</span></div>
      <p style="margin:.4em 0">${esc(i.text)}</p></div>`).join("") || `<p class="faint">No ideas yet. What would YOUR robot do?</p>`}</div></div></div>`;
  ideaComposer(app.querySelector("[data-comp]"), null, () => viewIdeas(app));
}

export async function viewRemix(app, pid) {
  const p = project(pid);
  setContext(pid, "remix");
  await refreshState();
  if (!isOpen(pid, "remix")) { lockedRedirect(pid, "Finish all five missions to open the remix lab."); return; }
  const [ideas, list] = await Promise.all([api(`/api/learners/${state.learner.id}/ideas`), api(`/api/learners/${state.learner.id}/arenas`)]);
  const mine = ideas.ideas.filter((i) => i.project_id === pid);
  if (state.isStale?.()) return;
  const choices = `<option value="remix:${pid}">${p.emoji} Remix arena</option>` + arenaOptions(list, null);
  missionShell(app, {
    crumbs: `<a href="#/project/${pid}">${p.emoji} ${esc(p.title)}</a> › Remix lab`, title: `Remix ${esc(p.title)}`,
    learn: `<p>${esc(p.remix.prompt)}</p><ul>${p.remix.ideas.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>`,
    task: `<p><b>1. Plan your twist</b></p>${mine.length ? `<p class="faint small">Your idea: <i>${esc(mine[mine.length - 1].text)}</i></p>` : ""}<div data-comp></div>
      <p style="margin-top:14px"><b>2. Build it, then submit.</b> <span class="muted">Pick any arena (your own designs earn a bonus). Bigger remixes earn more XP.</span></p><div data-remixres></div>`,
    hintBox: false,
  });
  let ideaId = mine.length ? mine[mine.length - 1].id : null;
  ideaComposer(app.querySelector("[data-comp]"), pid, (r) => { ideaId = r.id; });
  disposeWorkspace();
  const host = app.querySelector("[data-ws]");
  currentWs = createWorkspace(host, { project: pid, step: "remix", mode: "remix", checkable: false, arenaRef: `remix:${pid}`, arenaChoices: choices,
    extraButtons: `<button class="btn" data-submit>Submit remix</button>` });
  host.querySelector("[data-submit]").onclick = async () => {
    await currentWs.save();
    const r = await api(`/api/learners/${state.learner.id}/remix`, { method: "POST", body: { project: pid, code: currentWs.getCode(), idea_id: ideaId, arena: currentWs.arenaRef() } });
    const box = app.querySelector("[data-remixres]");
    if (!r.accepted) { sfx("fail"); box.innerHTML = `<div class="check-result fail" style="margin:8px 0">${esc(r.message)}</div>`; return; }
    sfx("pass"); celebrate(1.2);
    box.innerHTML = `<div class="check-result pass" style="margin:8px 0">✓ ${esc(r.message)}<br><span class="muted">Complexity: original ${r.base_complexity} → yours <b>${r.complexity}</b></span>
      ${r.xp ? `<br><b>+${r.xp} XP</b>` : "<br><span class='muted'>(Make it even bigger to earn more XP.)</span>"}</div>`;
    r.badges.forEach(showBadge);
    document.dispatchEvent(new CustomEvent("xp-changed"));
  };
}

// ---------------------------------------------------------------- manual
export async function viewManual(app) {
  setContext("_manual", "-");
  await refreshState();
  app.innerHTML = `<h1>Robot manual</h1>${manualHTML()}`;
}

// ---------------------------------------------------------------- my journey (kid analytics)
export async function viewJourney(app) {
  setContext("_journey", "-");
  const [s, j] = await Promise.all([refreshState(), api(`/api/learners/${state.learner.id}/journey`)]);
  const st = j.style, rb = j.robot;
  const seen = Object.fromEntries(j.errors.by_type.map((e) => [e.type, e]));
  const allMonsters = Object.values(state.curriculum.bestiary).filter((m, i, arr) => arr.findIndex((x) => x.name === m.name) === i);
  const sensorNames = { distance: "Ultrasonic", floor: "Floor light", light: "Light", heading: "Compass", encoder: "Encoders", bumper: "Bumper" };
  app.innerHTML = `<h1>My journey</h1>
    <div class="kpis">
      <div class="kpi"><div class="v">${rb.distance_m} m</div><div class="l">Driven by your robots</div></div>
      <div class="kpi"><div class="v">${rb.runs}</div><div class="l">Programs run</div><div class="s">${rb.robot_seconds} s of robot time</div></div>
      <div class="kpi"><div class="v">${rb.sensor_kinds}</div><div class="l">Sensor types used</div><div class="s">${Object.keys(rb.sensors).map((k) => sensorNames[k] || k).join(", ") || "none yet"}</div></div>
      <div class="kpi"><div class="v">${rb.gems}</div><div class="l">Gems collected</div></div>
      <div class="kpi"><div class="v">${Math.round((1 - rb.crash_run_rate) * 100)}%</div><div class="l">Runs without a crash</div></div>
      <div class="kpi"><div class="v">${rb.drive.minutes}</div><div class="l">Minutes in Drive mode</div></div>
    </div>
    <div class="grid g2">
      <div class="card"><h3>Your engineer type</h3><div class="persona"><div class="e">${st.persona.emoji}</div>
        <div><h2 style="margin:0">${esc(st.persona.name)}</h2><p class="muted">${esc(st.persona.desc)}</p></div></div>
        <div class="chart-box"><canvas id="c-style"></canvas></div></div>
      <div class="card"><h3>Skill tree</h3><p class="muted small" style="margin-top:0">Rings fill as you use a skill — especially when you use it on your own in the Playground or a remix.</p>
        <div class="skills">${j.mastery.map((m) => `<div class="skill ${m.started ? "" : "not-started"}" title="${m.steps_done}/${m.steps_total} missions · used on your own ${m.independent_uses}×">
        <div class="ring" style="--p:${Math.round(m.score * 100)}"><span>${Math.round(m.score * 100)}%</span></div><b>${esc(m.label)}</b><div class="faint small">${esc(m.status)}</div></div>`).join("")}</div></div>
    </div>
    <div class="grid g2" style="margin-top:16px">
      <div class="card"><h3>Building time (last 4 weeks)</h3><p class="muted small" style="margin-top:0">${j.activity.total_minutes} minutes · ${j.activity.sessions} sessions · best streak ${j.activity.streak.best} days</p>
        <div class="heat">${heat(j.activity.daily)}</div></div>
      <div class="card"><h3>Your programs are growing</h3><p class="muted small" style="margin-top:0">Complexity of the code that passed each mission.</p>
        <div class="chart-box short"><canvas id="c-growth"></canvas></div></div>
    </div>
    <div class="card" style="margin-top:16px"><h3>Bug bestiary</h3><p class="muted small" style="margin-top:0">Every bug is a monster. Fix one and it's defeated (${j.errors.by_type.filter((e) => e.defeated).length} of ${allMonsters.length}).</p>
      <div class="bestiary">${allMonsters.map((m) => { const e = seen[m.type] || Object.values(seen).find((x) => x.name === m.name);
        return `<div class="monster ${e ? (e.defeated ? "defeated" : "") : "unseen"}"><div class="e">${e ? m.emoji : "?"}</div>
        <div><b>${e ? esc(m.name) : "???"}</b> ${e?.defeated ? "✓" : ""}<div class="faint small">${e ? `Met ${e.count}× · ` + esc(m.desc) : "Not met yet"}</div></div></div>`; }).join("")}</div></div>
    <div class="grid g2" style="margin-top:16px">
      <div class="card"><h3>Idea power</h3>${j.ideas.ideas.length ? `<div class="chart-box short"><canvas id="c-ideas"></canvas></div>` : `<p class="faint">Save ideas in your <a href="#/ideas">journal</a> to see your idea power grow.</p>`}</div>
      <div class="card"><h3>Robot time</h3><dl class="kv"><dt>Robots built</dt><dd>${s.projects.filter((p) => p.complete).length}/${s.projects.length}</dd>
        <dt>Bosses beaten</dt><dd>${s.projects.filter((p) => p.boss_done).length}/${s.projects.length}</dd>
        <dt>Remixes built</dt><dd>${s.projects.filter((p) => p.remixed).length}/${s.projects.length}</dd>
        <dt>Side quests</dt><dd>${Object.values(s.week_quests || {}).reduce((a, q) => a + q.done, 0)}/${state.curriculum.practice.length}</dd></dl></div>
    </div>
    <div class="card" style="margin-top:16px"><div class="card-head"><h3>Badges</h3><span class="spacer"></span>
      <span class="pill">${s.badges.filter((b) => b.earned_at).length}/${s.badges.length} earned</span></div>
      ${badgeProgress(s.badges)}${badgeSections(s.badges)}</div>`;
  const { grid } = chartDefaults();
  const col = seriesColors();
  makeChart(app.querySelector("#c-style"), {
    type: "radar",
    data: { labels: Object.keys(st.traits), datasets: [{ label: "You", data: Object.values(st.traits).map((v) => Math.round(v * 100)),
      borderColor: col[0], backgroundColor: col[0] + "22", borderWidth: 2, pointRadius: 3, pointBackgroundColor: col[0] }] },
    options: { maintainAspectRatio: false, plugins: { legend: { display: false } },
      scales: { r: { min: 0, max: 100, ticks: { display: false }, grid: { color: grid }, angleLines: { color: grid }, pointLabels: { font: { size: 12, weight: 600 } } } } },
  });
  makeChart(app.querySelector("#c-growth"), {
    type: "line",
    data: { labels: j.code_growth.map((r, i) => i + 1), datasets: [{ label: "Complexity", data: j.code_growth.map((r) => r.complexity),
      borderColor: col[2], backgroundColor: col[2], borderWidth: 2, pointRadius: 3, tension: 0.3 }] },
    options: { maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { title: (it) => `${j.code_growth[it[0].dataIndex].project_id} / ${j.code_growth[it[0].dataIndex].step_id}` } } },
      scales: { x: { title: { display: true, text: "Missions passed" }, grid: { display: false } }, y: { beginAtZero: true, grid: { color: grid } } } },
  });
  if (j.ideas.ideas.length) makeChart(app.querySelector("#c-ideas"), {
    type: "line",
    data: { labels: j.ideas.ideas.map((i) => new Date(i.ts * 1000).toLocaleDateString()), datasets: [{ label: "Idea score", data: j.ideas.ideas.map((i) => i.score),
      borderColor: col[4], backgroundColor: col[4], borderWidth: 2, pointRadius: 4, tension: 0.3 }] },
    options: { maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { min: 0, max: 100, grid: { color: grid } }, x: { grid: { display: false } } } },
  });
}

function heat(daily) {
  const max = Math.max(10, ...daily.map((d) => d.minutes));
  return daily.map((d) => {
    const a = d.minutes ? 0.2 + 0.8 * (d.minutes / max) : 0;
    return `<div data-tip="${d.day}: ${d.minutes} min" style="${a ? `background:color-mix(in srgb, var(--accent) ${Math.round(a * 100)}%, var(--sunken))` : ""}"></div>`;
  }).join("");
}
