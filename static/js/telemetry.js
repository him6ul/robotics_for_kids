// Telemetry: small line charts of every sensor the program read (and robot.plot values), synced to the replay.
import { cssVar, esc, seriesColors } from "./core.js";

const NAMES = {
  "s:distance_front": "distance front", "s:distance_left": "distance left", "s:distance_right": "distance right",
  "s:distance_front_left": "distance front-left", "s:distance_front_right": "distance front-right", "s:distance_back": "distance back",
  "s:floor_left": "floor left", "s:floor_center": "floor centre", "s:floor_right": "floor right",
  "s:light_left": "light left", "s:light_right": "light right", "s:heading": "heading", "s:encoder_left": "encoder left",
  "s:encoder_right": "encoder right", "s:bumper": "bumper", pl: "left motor", pr: "right motor", s: "shoulder", e: "elbow",
};

export class Telemetry {
  constructor(host, view) {
    this.host = host;
    this.view = view;
    this.rows = [];
    view.onTime(() => this.cursor());
  }

  load(res) {
    const f = res.frames || {};
    const keys = Object.keys(f).filter((k) => k.startsWith("p:") || k.startsWith("s:"));
    if (res.kind === "arm") keys.push("s", "e"); else keys.push("pl", "pr");
    const cols = seriesColors();
    this.frames = f;
    this.dur = f.t?.[f.t.length - 1] || 0;
    if (!f.t || f.t.length < 2) { this.host.innerHTML = `<p class="faint small" style="padding:10px 12px">Run your robot to see its sensor readings over time.</p>`; this.rows = []; return; }
    this.host.innerHTML = `<div class="tele">${keys.map((k, i) => `<div class="tele-row" data-k="${esc(k)}">
      <div class="nm"><i style="background:${cols[i % cols.length]}"></i>${esc(k.startsWith("p:") ? "📈 " + k.slice(2) : NAMES[k] || k)}</div>
      <canvas></canvas><div class="val"></div></div>`).join("")}
      <p class="faint small" style="margin:4px 0 0">Click a graph to jump there in the replay. Plot your own values with <code>robot.plot("error", error)</code>.</p></div>`;
    this.rows = [...this.host.querySelectorAll(".tele-row")].map((row, i) => {
      const k = row.dataset.k, cv = row.querySelector("canvas");
      cv.addEventListener("click", (e) => {
        const r = cv.getBoundingClientRect();
        this.view.seek((e.clientX - r.left) / r.width * this.dur);
        this.view.pause();
      });
      return { k, cv, val: row.querySelector(".val"), color: cols[i % cols.length] };
    });
    requestAnimationFrame(() => { this.rows.forEach((r) => this.plot(r)); this.cursor(); });
  }

  plot(r) {
    const cv = r.cv, dpr = window.devicePixelRatio || 1, W = cv.clientWidth, H = cv.clientHeight;
    if (!W) return;
    cv.width = W * dpr; cv.height = H * dpr;
    const g = cv.getContext("2d");
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    const T = this.frames.t, V = this.frames[r.k] || [];
    const vals = V.filter((v) => v !== null && v !== undefined);
    if (!vals.length) return;
    let lo = Math.min(...vals), hi = Math.max(...vals);
    if (hi - lo < 1e-6) { lo -= 1; hi += 1; }
    const pad = (hi - lo) * 0.1;
    lo -= pad; hi += pad;
    r.lo = lo; r.hi = hi;
    if (lo < 0 && hi > 0) {
      g.strokeStyle = cssVar("--line"); g.lineWidth = 1;
      const y0 = H - (0 - lo) / (hi - lo) * H;
      g.beginPath(); g.moveTo(0, y0); g.lineTo(W, y0); g.stroke();
    }
    g.strokeStyle = r.color; g.lineWidth = 1.6; g.beginPath();
    let started = false;
    for (let i = 0; i < T.length; i++) {
      const v = V[i];
      if (v === null || v === undefined) { started = false; continue; }
      const x = T[i] / (this.dur || 1) * W, y = H - (v - lo) / (hi - lo) * H;
      if (!started) { g.moveTo(x, y); started = true; } else g.lineTo(x, y);
    }
    g.stroke();
    r.base = g.getImageData(0, 0, cv.width, cv.height);
  }

  cursor() {
    if (!this.rows.length) return;
    const t = this.view.t;
    for (const r of this.rows) {
      const cv = r.cv, g = cv.getContext("2d");
      if (!r.base) continue;
      g.putImageData(r.base, 0, 0);
      const dpr = window.devicePixelRatio || 1, W = cv.width / dpr, H = cv.height / dpr;
      const x = t / (this.dur || 1) * W;
      g.strokeStyle = cssVar("--text-2"); g.lineWidth = 1;
      g.beginPath(); g.moveTo(x, 0); g.lineTo(x, H); g.stroke();
      const v = this.view.valueAt(r.k, t);
      r.val.textContent = v === null || v === undefined ? "—" : typeof v === "number" ? (Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(1)) : String(v);
    }
  }
}
