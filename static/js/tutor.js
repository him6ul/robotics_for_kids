// Sprocket, the AI tutor: a chat drawer attached to a robot workspace (hints, bug help, code reviews).
import { api, el, esc, sfx, state, toast } from "./core.js";

// Minimal, safe formatting for tutor replies: escape first, then ``` blocks, `code`, **bold**, newlines.
export function fmt(text) {
  let s = esc(text || "");
  s = s.replace(/```(?:python)?\n?([\s\S]*?)```/g, (_, c) => `<pre>${c.replace(/\n$/, "")}</pre>`);
  s = s.replace(/`([^`\n]+)`/g, "<code>$1</code>");
  s = s.replace(/\*\*([^*\n]+)\*\*/g, "<b>$1</b>");
  return s.replace(/\n/g, "<br>").replace(/<pre>([\s\S]*?)<\/pre>/g, (m, c) => `<pre>${c.replace(/<br>/g, "\n")}</pre>`);
}

export async function refreshTutorStatus() {
  try { state.tutor = await api(`/api/tutor/status?learner=${state.learner?.id ?? ""}`); }
  catch (e) { state.tutor = { available: false }; }
  return state.tutor;
}

const CHIPS = [
  ["I'm stuck", "I'm stuck on this mission. Can you give me a clue?"],
  ["Why doesn't it work?", "My robot doesn't do what I want. Can you help me find the problem?"],
  ["Explain the lesson", "Can you explain the idea from this lesson in a different way?"],
  ["Make it smarter", "My robot works! How could I make it smarter or smoother?"],
];

export function createTutor({ project, step, getCode, getRun, cm }) {
  document.querySelectorAll("aside.tutor").forEach((x) => x.remove());   // only ever one tutor on screen
  const panel = el(`<aside class="tutor hidden" aria-label="Sprocket the AI tutor">
    <header><span class="pix">🔧</span><div><b>Sprocket</b><div class="faint" data-usage></div></div><span class="spacer"></span>
      <button class="iconbtn" data-close title="Close">✕</button></header>
    <div class="tutor-log" aria-live="polite"></div>
    <div class="tutor-chips">${CHIPS.map(([l, q]) => `<button class="btn small ghost" data-q="${esc(q)}">${l}</button>`).join("")}</div>
    <form class="tutor-form"><textarea rows="2" placeholder="Ask Sprocket about your robot…" maxlength="1000"></textarea>
      <button class="btn primary" type="submit">Send</button></form>
    <div class="faint tutor-note">Sprocket gives clues, not answers. Your parent can read these chats.</div>
  </aside>`);
  document.body.appendChild(panel);
  const log = panel.querySelector(".tutor-log"), ta = panel.querySelector("textarea");
  let busy = false, marks = [];

  const usage = (used, limit) => { panel.querySelector("[data-usage]").textContent = `${used}/${limit} questions today`; };
  if (state.tutor) usage(state.tutor.used_today ?? 0, state.tutor.daily_limit);

  function bubble(role, html, cls = "") {
    const b = el(`<div class="tb tb-${role} ${cls}"><div class="tb-body">${html}</div></div>`);
    log.appendChild(b);
    log.scrollTop = log.scrollHeight;
    return b;
  }
  function typing() {
    return bubble("tutor", `<span class="dots"><i></i><i></i><i></i></span>`, "typing");
  }

  function reviewCard(r) {
    const kindIcon = { bug: "🐛", readability: "📖", idea: "💡" };
    const html = `<div class="review"><div class="stars">${"⭐".repeat(r.stars)}${"☆".repeat(3 - r.stars)}</div>
      <p><b>👍 ${esc(r.praise)}</b></p><p>${fmt(r.summary)}</p>
      ${r.suggestions.length ? `<ul>${r.suggestions.map((s) => `<li ${s.line ? `data-line="${s.line}" class="jump" title="Show line ${s.line}"` : ""}>
        ${kindIcon[s.kind] || "•"} ${s.line ? `<b>Line ${s.line}:</b> ` : ""}${fmt(s.tip)}</li>`).join("")}</ul>` : ""}
      <p class="challenge"><b>Challenge:</b> ${fmt(r.challenge)}</p></div>`;
    const b = bubble("tutor", html);
    b.querySelectorAll("[data-line]").forEach((li) => li.onclick = () => {
      const n = +li.dataset.line - 1;
      cm.setCursor({ line: n, ch: 0 }); cm.scrollIntoView({ line: n, ch: 0 }, 80); cm.focus();
    });
    clearMarks();
    r.suggestions.filter((s) => s.line > 0 && s.line <= cm.lineCount()).forEach((s) => {
      cm.addLineClass(s.line - 1, "background", s.kind === "bug" ? "cm-tutor-bug" : "cm-tutor-tip");
      marks.push(s.line - 1);
    });
  }
  function clearMarks() {
    marks.forEach((l) => { cm.removeLineClass(l, "background", "cm-tutor-bug"); cm.removeLineClass(l, "background", "cm-tutor-tip"); });
    marks = [];
  }
  cm.on("change", () => marks.length && clearMarks());

  let historyPromise = null;
  function loadHistory() {
    historyPromise = historyPromise || fetchHistory();
    return historyPromise;
  }
  async function fetchHistory() {
    const rows = await api(`/api/learners/${state.learner.id}/tutor/history?project=${encodeURIComponent(project)}&step=${encodeURIComponent(step)}`);
    if (!rows.length) {
      bubble("tutor", `Hi! I'm <b>Sprocket</b>, the robot mechanic 🔧. Stuck, confused, or curious? Ask me about your robot — I'll give you clues so <i>you</i> can crack it.`);
      return;
    }
    for (const r of rows) {
      if (r.role === "kid") bubble("kid", fmt(r.text));
      else if (r.kind === "review" && r.status === "ok" && r.meta) reviewCard(r.meta);
      else bubble("tutor", fmt(r.text), r.status !== "ok" ? "warn" : "");
    }
  }

  async function ask(question, kind = "chat") {
    if (busy || !question.trim()) return;
    busy = true;
    await open();
    bubble("kid", fmt(question));
    const t = typing();
    try {
      const r = await api(`/api/learners/${state.learner.id}/tutor/chat`, {
        method: "POST", body: { project, step, question, code: getCode(), run: getRun(), kind } });
      t.remove();
      if (!r.ok) { bubble("tutor", esc(r.error), "warn"); return; }
      sfx("ok");
      bubble("tutor", fmt(r.reply));
      usage(r.used_today, r.limit);
      if (state.tutor) state.tutor.used_today = r.used_today;
    } catch (e) {
      t.remove(); bubble("tutor", "Hmm, I couldn't connect. " + esc(e.message), "warn");
    } finally { busy = false; }
  }

  async function review() {
    if (busy) return;
    busy = true;
    await open();
    bubble("kid", "🔍 Review my code");
    const t = typing();
    try {
      const r = await api(`/api/learners/${state.learner.id}/tutor/review`, {
        method: "POST", body: { project, step, code: getCode(), run: getRun() } });
      t.remove();
      if (!r.ok) { bubble("tutor", esc(r.error), "warn"); return; }
      sfx("badge");
      reviewCard(r);
      usage(r.used_today, r.limit);
    } catch (e) {
      t.remove(); bubble("tutor", "Hmm, I couldn't connect. " + esc(e.message), "warn");
    } finally { busy = false; }
  }

  function open() {
    panel.classList.remove("hidden");
    setTimeout(() => ta.focus(), 50);
    return loadHistory().catch(() => {});
  }
  function close() { panel.classList.add("hidden"); }

  panel.querySelector("[data-close]").onclick = close;
  panel.querySelectorAll("[data-q]").forEach((b) => b.onclick = () => ask(b.dataset.q));
  panel.querySelector("form").onsubmit = (e) => { e.preventDefault(); const q = ta.value; ta.value = ""; ask(q); };
  ta.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); panel.querySelector("form").requestSubmit(); } });

  return {
    open, close, review, ask,
    toggle: () => (panel.classList.contains("hidden") ? open() : close()),
    explainError: (err) => ask(`My program crashed with ${err.type} on line ${err.line}: "${err.msg}". What does that mean, and where should I look?`, "error"),
    dispose: () => { clearMarks(); panel.remove(); },
  };
}

export function tutorUnavailableToast() {
  toast("🔧 Sprocket isn't switched on yet — ask a parent to enable the AI tutor in the Parent Zone.");
}
