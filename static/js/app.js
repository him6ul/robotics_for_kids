// Router & boot.
import { api, destroyCharts, state, store } from "./core.js";
import * as kid from "./kid.js";
import { disposeDrive, viewDrive } from "./drive.js";
import { disposeBuilder, viewBuilder } from "./builder.js";
import { viewParent } from "./parent.js";
import { refreshTutorStatus } from "./tutor.js";

const app = document.getElementById("app");

let routeSeq = 0;
async function route() {
  const seq = ++routeSeq;
  state.isStale = () => seq !== routeSeq;
  const [path] = location.hash.replace(/^#\/?/, "").split("?");
  const [page, a, b] = path.split("/").filter(Boolean);
  kid.disposeWorkspace();
  disposeDrive();
  disposeBuilder();
  destroyCharts();
  document.querySelectorAll("aside.tutor").forEach((x) => x.remove());
  window.scrollTo(0, 0);

  if (page === "parent") {
    state.tutorFor = null;
    document.getElementById("topbar").classList.add("hidden");
    return viewParent(app, a || "overview", b);
  }
  if (state.learner && state.tutorFor !== state.learner.id) { state.tutorFor = state.learner.id; await refreshTutorStatus(); }
  if (!state.learner || page === "welcome") {
    document.getElementById("topbar").classList.add("hidden");
    return kid.viewWelcome(app);
  }
  document.getElementById("topbar").classList.remove("hidden");
  document.querySelectorAll("#kidnav a").forEach((x) => x.classList.toggle("active", x.dataset.nav === (page || "home")));
  try {
    switch (page) {
      case "map": return await kid.viewMap(app);
      case "project": return await kid.viewProject(app, a);
      case "code": return await kid.viewCode(app, a, b);
      case "practice": return await kid.viewPractice(app, a);
      case "playground": return await kid.viewPlayground(app, a);
      case "drive": return await viewDrive(app);
      case "builder": return await viewBuilder(app, a);
      case "ideas": return await kid.viewIdeas(app);
      case "remix": return await kid.viewRemix(app, a);
      case "journey": return await kid.viewJourney(app);
      case "manual": return await kid.viewManual(app);
      default: return await kid.viewHome(app);
    }
  } catch (e) {
    console.error(e);
    app.innerHTML = `<div class="card"><h2>Something went wrong</h2><p class="muted">${e.message}</p><a class="btn" href="#/home">Home</a></div>`;
  }
}

async function boot() {
  state.curriculum = await api("/api/curriculum");
  const saved = store.get("rq_learner", "");
  if (saved) {
    const learners = await api("/api/learners");
    state.learner = learners.find((l) => String(l.id) === saved) || null;
    if (state.learner) kid.learnerTheme(state.learner);
  }
  document.getElementById("whoami").onclick = () => { state.learner = null; location.hash = "#/welcome"; };
  document.getElementById("soundbtn").onclick = async () => {
    state.learner = await api(`/api/learners/${state.learner.id}`, { method: "PATCH", body: { sound: state.learner.sound ? 0 : 1 } });
    kid.renderTopbar();
  };
  document.getElementById("themebtn").onclick = async () => {
    const [mode, accent] = String(state.learner?.theme || "system|blue").split("|");
    const dark = document.documentElement.dataset.theme === "dark";
    const next = `${dark ? "light" : "dark"}|${accent || "blue"}`;
    state.learner = await api(`/api/learners/${state.learner.id}`, { method: "PATCH", body: { theme: next } });
    kid.learnerTheme(state.learner);
  };
  document.addEventListener("xp-changed", () => kid.refreshState());
  window.addEventListener("hashchange", route);
  route();
}

boot();
