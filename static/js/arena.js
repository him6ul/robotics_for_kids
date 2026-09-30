// ArenaView: draws an arena and replays a simulation (or shows a live robot in Drive mode).
import { cssVar, state, tone } from "./core.js";

const ZONE = { red: "#dcaaa4", green: "#abcab5", blue: "#a9bdd8", yellow: "#e6d69e", orange: "#e5be98", purple: "#c1b3d4",
  gray: "#cacac4", black: "#3a3d42", white: "#ffffff", brown: "#bba58f" };
const SOLID = { red: "#c0625c", green: "#5f9b76", blue: "#5c80b1", yellow: "#c7a846", orange: "#c98a52", purple: "#8f74a8",
  gray: "#8d9197", black: "#33363b", white: "#f0f0ec", brown: "#8d6f55", gold: "#c9a646" };
const LED = { red: "#e0726b", green: "#6fbf8e", blue: "#6f9ad6", yellow: "#e8c95a", purple: "#a98bd0", white: "#f4f4f0",
  orange: "#e39a5c", cyan: "#6cc4cc", pink: "#e28fb0" };
export const colorOf = (c, table = SOLID) => table[c] || c || "#888";
const R = 8, BLOCK = 6, ARM_BLOCK = 8;

export class ArenaView {
  constructor(host, opts = {}) {
    this.host = host;
    this.opts = opts;
    host.classList.add("arena-canvas");
    host.innerHTML = `<canvas></canvas><div class="arena-title"></div><div class="arena-hud"></div>`;
    this.canvas = host.querySelector("canvas");
    this.ctx = this.canvas.getContext("2d");
    this.titleEl = host.querySelector(".arena-title");
    this.hud = host.querySelector(".arena-hud");
    this.arena = null;
    this.res = null;
    this.t = 0; this.speed = 1; this.playing = false; this.lastWall = 0;
    this.listeners = [];
    this.showRays = true;
    this.robotColor = opts.robotColor || state.learner?.robot_color || "#5b8def";
    this.overlay = null;
    this.readColors();
    this.ro = new ResizeObserver(() => this.resize());
    this.ro.observe(host);
    this.onTheme = () => { this.readColors(); this.draw(); };
    document.addEventListener("theme-changed", this.onTheme);
    this.loop = this.loop.bind(this);
    this.raf = requestAnimationFrame(this.loop);
  }

  readColors() {
    this.c = { floor: cssVar("--floor"), grid: cssVar("--floor-grid"), wall: cssVar("--wall"), box: cssVar("--box"), tape: cssVar("--tape"),
      text: cssVar("--text-2"), muted: cssVar("--muted"), accent: cssVar("--accent"), surface: cssVar("--surface"), bad: cssVar("--bad"),
      line: cssVar("--line-strong"), dark: document.documentElement.dataset.theme === "dark" };
  }

  dispose() {
    cancelAnimationFrame(this.raf);
    this.ro.disconnect();
    document.removeEventListener("theme-changed", this.onTheme);
  }

  onTime(cb) { this.listeners.push(cb); }
  emit() { this.listeners.forEach((cb) => cb(this.t, this)); }

  resize() {
    const r = this.host.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    this.W = r.width; this.H = r.height;
    this.canvas.width = Math.max(1, Math.round(r.width * dpr));
    this.canvas.height = Math.max(1, Math.round(r.height * dpr));
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.fit();
    this.draw();
  }

  fit() {
    if (!this.arena || !this.W) return;
    const [aw, ah] = this.arena.size;
    const pad = 12;
    this.s = Math.min((this.W - 2 * pad) / aw, (this.H - 2 * pad) / ah);
    this.ox = (this.W - aw * this.s) / 2;
    this.oy = (this.H + ah * this.s) / 2;
  }
  X(x) { return this.ox + x * this.s; }
  Y(y) { return this.oy - y * this.s; }
  toWorld(clientX, clientY) {
    const r = this.canvas.getBoundingClientRect();
    return [(clientX - r.left - this.ox) / this.s, (this.oy - (clientY - r.top)) / this.s];
  }

  setArena(a) {
    this.arena = a;
    this.titleEl.textContent = a?.name || "";
    this.res = null;
    this.live = null;
    this.t = 0;
    this.fit();
    this.draw();
  }

  // ---------- replay ----------
  setResult(res, { autoplay = true } = {}) {
    if (res.arena) this.setArena(res.arena);
    this.res = res;
    const f = res.frames || { t: [0] };
    this.duration = f.t[f.t.length - 1] || 0;
    this.events = res.events || [];
    this.buildStrokes();
    this.t = 0;
    this.lastBeepT = -1;
    this.playing = autoplay && this.duration > 0;
    this.lastWall = performance.now();
    this.emit();
    this.draw();
  }

  buildStrokes() {
    const f = this.res.frames, pens = this.events.filter((e) => e.type === "pen");
    this.strokes = [];
    if (!f || !f.x) return;
    let pi = 0, down = false, cur = null;
    for (let i = 0; i < f.t.length; i++) {
      while (pi < pens.length && pens[pi].t <= f.t[i] + 1e-9) {
        const p = pens[pi++];
        if (p.down && !down) { cur = { color: p.color || "black", pts: [] }; this.strokes.push(cur); }
        down = p.down;
        if (!down) cur = null;
      }
      if (down && cur) cur.pts.push([f.x[i], f.y[i], f.t[i]]);
    }
  }

  play() { if (this.res && this.duration > 0) { if (this.t >= this.duration) this.seek(0); this.playing = true; this.lastWall = performance.now(); } }
  pause() { this.playing = false; this.draw(); }
  toggle() { this.playing ? this.pause() : this.play(); }
  seek(t) { this.t = Math.max(0, Math.min(this.duration || 0, t)); this.lastBeepT = this.t; this.emit(); this.draw(); }
  finish() { this.seek(this.duration || 0); this.playing = false; }

  loop(now) {
    if (this.playing && this.res) {
      const dt = Math.min(0.1, (now - this.lastWall) / 1000);
      this.lastWall = now;
      const prev = this.t;
      this.t = Math.min(this.duration, this.t + dt * this.speed);
      this.beeps(prev, this.t);
      if (this.t >= this.duration) this.playing = false;
      this.emit();
      this.draw();
    } else {
      this.lastWall = now;
    }
    this.raf = requestAnimationFrame(this.loop);
  }

  beeps(a, b) {
    if (this.speed > 2) return;
    for (const e of this.events) if (e.type === "beep" && e.t > a && e.t <= b) tone(e.freq, Math.min(e.dur, .5), 0.05, "triangle");
  }

  frameAt(t) {
    const f = this.res?.frames;
    if (!f || !f.t.length) return null;
    const T = f.t;
    let lo = 0, hi = T.length - 1;
    if (t >= T[hi]) return { i: hi, j: hi, a: 0 };
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (T[m] <= t) lo = m; else hi = m; }
    const a = T[hi] > T[lo] ? (t - T[lo]) / (T[hi] - T[lo]) : 0;
    return { i: lo, j: hi, a };
  }

  valueAt(key, t = this.t) {
    const fr = this.frameAt(t), arr = this.res?.frames?.[key];
    if (!fr || !arr) return null;
    return arr[fr.a < 0.5 ? fr.i : fr.j];
  }

  lastEvent(type, t, filter) {
    let found = null;
    for (const e of this.events || []) { if (e.t > t + 1e-9) break; if (e.type === type && (!filter || filter(e))) found = e; }
    return found;
  }

  // ---------- live (Drive mode) ----------
  startLive(arena) {
    this.setArena(arena);
    this.live = { frames: { t: [], x: [], y: [], h: [], pl: [], pr: [] }, events: [], blocks: null };
    this.res = { frames: this.live.frames, events: this.live.events };
    this.events = this.live.events;
    this.strokes = [];
    this.penDown = false;
  }
  pushLive(st) {
    const f = this.live.frames;
    f.t.push(st.time); f.x.push(st.x); f.y.push(st.y); f.h.push(st.h); f.pl.push(st.pl); f.pr.push(st.pr);
    if (f.t.length > 6000) for (const k of Object.keys(f)) f[k].splice(0, 1000);
    for (const e of st.events) {
      this.live.events.push(e);
      if (e.type === "pen") { this.penDown = e.down; if (e.down) this.strokes.push({ color: e.color || "black", pts: [] }); }
      if (e.type === "beep") tone(e.freq, .15, .05, "triangle");
    }
    if (this.penDown && this.strokes.length) this.strokes[this.strokes.length - 1].pts.push([st.x, st.y, st.time]);
    this.live.blocks = st.blocks;
    this.live.sensors = st.sensors;
    this.duration = st.time;
    this.t = st.time;
    this.draw();
  }

  // ---------- drawing ----------
  draw() {
    const g = this.ctx;
    if (!this.W) return;
    g.clearRect(0, 0, this.W, this.H);
    if (!this.arena) return;
    if (this.arena.type === "arm") this.drawArm(g);
    else this.drawDrive(g);
    if (this.overlay) this.overlay(g, this);
    this.renderHud();
  }

  renderHud() {
    if (!this.res || this.opts.noHud) { this.hud.innerHTML = ""; return; }
    const t = this.t, ev = this.events || [];
    const upto = (type) => ev.filter((e) => e.type === type && e.t <= t + 1e-9).length;
    const parts = [`<span class="pill">${t.toFixed(1)} s</span>`];
    if (this.arena.type !== "arm" && (this.arena.gems || []).length) parts.push(`<span class="pill">💎 ${upto("gem")}/${this.arena.gems.length}</span>`);
    const crashes = upto("crash");
    if (crashes) parts.push(`<span class="pill bad">💥 ${crashes}</span>`);
    const laps = upto("lap");
    if (this.arena.finish) parts.push(`<span class="pill">🏁 ${laps}</span>`);
    this.hud.innerHTML = parts.join("");
  }

  drawDrive(g) {
    const a = this.arena, c = this.c, s = this.s;
    const [aw, ah] = a.size;
    g.fillStyle = c.floor;
    g.fillRect(this.X(0), this.Y(ah), aw * s, ah * s);
    // grid
    const cell = a.grid?.cell || 20;
    g.strokeStyle = c.grid; g.lineWidth = 1;
    g.beginPath();
    for (let x = cell; x < aw; x += cell) { g.moveTo(this.X(x), this.Y(0)); g.lineTo(this.X(x), this.Y(ah)); }
    for (let y = cell; y < ah; y += cell) { g.moveTo(this.X(0), this.Y(y)); g.lineTo(this.X(aw), this.Y(y)); }
    g.stroke();
    // zones
    for (const z of a.zones || []) {
      const [x, y, w, h] = z.rect;
      g.globalAlpha = c.dark ? 0.55 : 0.85;
      g.fillStyle = colorOf(z.color, ZONE);
      g.fillRect(this.X(x), this.Y(y + h), w * s, h * s);
      g.globalAlpha = 1;
      if (z.label || z.name) {
        g.fillStyle = c.dark ? "#e8e8e4" : "#3b3f45";
        g.font = `600 ${Math.max(9, Math.min(13, 4 * s))}px Inter, sans-serif`;
        g.textAlign = "center"; g.textBaseline = "middle";
        g.fillText(z.label || z.name, this.X(x + w / 2), this.Y(y + h / 2));
      }
    }
    // tape lines
    g.strokeStyle = c.tape; g.lineCap = "round"; g.lineJoin = "round";
    for (const ln of a.lines || []) {
      if (!ln.pts.length) continue;
      g.lineWidth = Math.max(1.5, ln.width * s);
      g.beginPath();
      g.moveTo(this.X(ln.pts[0][0]), this.Y(ln.pts[0][1]));
      for (const p of ln.pts.slice(1)) g.lineTo(this.X(p[0]), this.Y(p[1]));
      if (ln.closed) g.closePath();
      g.stroke();
    }
    // finish line (checkered)
    if (a.finish) {
      const [x1, y1, x2, y2] = a.finish;
      const n = 8;
      g.lineWidth = Math.max(3, 2.5 * s); g.lineCap = "butt";
      for (let i = 0; i < n; i++) {
        g.strokeStyle = i % 2 ? "#f2f2ee" : "#2d3035";
        g.beginPath();
        g.moveTo(this.X(x1 + (x2 - x1) * i / n), this.Y(y1 + (y2 - y1) * i / n));
        g.lineTo(this.X(x1 + (x2 - x1) * (i + 1) / n), this.Y(y1 + (y2 - y1) * (i + 1) / n));
        g.stroke();
      }
    }
    // labels
    g.fillStyle = c.muted; g.font = `500 ${Math.max(9, Math.min(12, 3.4 * s))}px Inter, sans-serif`; g.textAlign = "center"; g.textBaseline = "middle";
    for (const [x, y, text] of a.labels || []) g.fillText(text, this.X(x), this.Y(y));
    // lights
    for (const [x, y] of a.lights || []) {
      const rg = g.createRadialGradient(this.X(x), this.Y(y), 0, this.X(x), this.Y(y), 60 * s);
      rg.addColorStop(0, "rgba(240, 210, 120, .55)"); rg.addColorStop(1, "rgba(240, 210, 120, 0)");
      g.fillStyle = rg; g.beginPath(); g.arc(this.X(x), this.Y(y), 60 * s, 0, 7); g.fill();
      g.fillStyle = "#e7c65e"; g.beginPath(); g.arc(this.X(x), this.Y(y), 3.5 * s, 0, 7); g.fill();
    }
    // gems
    const got = new Set((this.events || []).filter((e) => e.type === "gem" && e.t <= this.t + 1e-9).map((e) => e.i));
    (a.gems || []).forEach(([x, y], i) => {
      if (got.has(i)) {
        g.strokeStyle = c.line; g.lineWidth = 1; g.setLineDash([2, 2]);
        g.beginPath(); g.arc(this.X(x), this.Y(y), 2.5 * s, 0, 7); g.stroke(); g.setLineDash([]);
        return;
      }
      const r = 3 * s;
      g.fillStyle = "#c9a646"; g.strokeStyle = "#a3842f"; g.lineWidth = 1;
      g.beginPath(); g.moveTo(this.X(x), this.Y(y) - r); g.lineTo(this.X(x) + r * .8, this.Y(y)); g.lineTo(this.X(x), this.Y(y) + r); g.lineTo(this.X(x) - r * .8, this.Y(y)); g.closePath();
      g.fill(); g.stroke();
    });
    // walls & boxes
    g.fillStyle = c.box;
    for (const [x, y, w, h] of a.boxes || []) g.fillRect(this.X(x), this.Y(y + h), w * s, h * s);
    g.strokeStyle = c.wall; g.lineWidth = Math.max(2, 1.6 * s); g.lineCap = "round";
    g.beginPath();
    for (const [x1, y1, x2, y2] of a.walls || []) { g.moveTo(this.X(x1), this.Y(y1)); g.lineTo(this.X(x2), this.Y(y2)); }
    g.stroke();
    if (a.border !== false) { g.lineWidth = 2; g.strokeRect(this.X(0), this.Y(ah), aw * s, ah * s); }
    // pen trail
    this.drawTrail(g);
    // blocks
    const fr = this.frameAt(this.t);
    const bpos = this.live ? this.live.blocks : fr && this.res?.frames?.blocks ? this.res.frames.blocks[fr.a < .5 ? fr.i : fr.j] : null;
    (a.blocks || []).forEach((b, i) => {
      const [x, y] = bpos?.[i] || b.pos;
      g.fillStyle = colorOf(b.color);
      g.strokeStyle = "rgba(0,0,0,.25)"; g.lineWidth = 1;
      g.fillRect(this.X(x - BLOCK / 2), this.Y(y + BLOCK / 2), BLOCK * s, BLOCK * s);
      g.strokeRect(this.X(x - BLOCK / 2), this.Y(y + BLOCK / 2), BLOCK * s, BLOCK * s);
    });
    // robot
    let x, y, h;
    if (fr && this.res.frames.x?.length) {
      const f = this.res.frames, A = fr.a;
      x = f.x[fr.i] + (f.x[fr.j] - f.x[fr.i]) * A;
      y = f.y[fr.i] + (f.y[fr.j] - f.y[fr.i]) * A;
      h = f.h[fr.i] + (f.h[fr.j] - f.h[fr.i]) * A;
    } else {
      [x, y, h] = a.start;
    }
    this.drawRobot(g, x, y, h || 0, fr);
  }

  drawTrail(g) {
    if (!this.strokes?.length) return;
    g.lineWidth = Math.max(1.5, 0.9 * this.s); g.lineCap = "round"; g.lineJoin = "round";
    for (const st of this.strokes) {
      g.strokeStyle = colorOf(st.color, { ...SOLID, black: this.c.dark ? "#d8d8d4" : "#33363b" });
      g.beginPath();
      let started = false;
      for (const [x, y, t] of st.pts) {
        if (t > this.t + 1e-9) break;
        if (!started) { g.moveTo(this.X(x), this.Y(y)); started = true; } else g.lineTo(this.X(x), this.Y(y));
      }
      g.stroke();
    }
  }

  drawRobot(g, x, y, hDeg, fr) {
    const s = this.s, c = this.c, th = hDeg * Math.PI / 180;
    const cx = this.X(x), cy = this.Y(y);
    const idx = fr ? (fr.a < .5 ? fr.i : fr.j) : null;
    // sensor beams
    if (this.showRays && this.res) {
      const dirs = { distance_front: 0, distance_left: 90, distance_right: -90, distance_front_left: 45, distance_front_right: -45, distance_back: 180 };
      for (const [ch, off] of Object.entries(dirs)) {
        const v = this.live ? this.live.sensors?.[ch] : idx !== null ? this.res.frames["s:" + ch]?.[idx] : null;
        if (v === null || v === undefined) continue;
        const ang = th + off * Math.PI / 180;
        const sx = x + R * Math.cos(ang), sy = y + R * Math.sin(ang);
        const ex = sx + v * Math.cos(ang), ey = sy + v * Math.sin(ang);
        g.strokeStyle = c.dark ? "rgba(134,162,201,.45)" : "rgba(80,112,158,.35)"; g.lineWidth = 1.2; g.setLineDash([4, 3]);
        g.beginPath(); g.moveTo(this.X(sx), this.Y(sy)); g.lineTo(this.X(ex), this.Y(ey)); g.stroke(); g.setLineDash([]);
        if (v < 199) { g.fillStyle = c.accent; g.beginPath(); g.arc(this.X(ex), this.Y(ey), 2.2, 0, 7); g.fill(); }
      }
    }
    g.save();
    g.translate(cx, cy);
    g.rotate(-th);
    // wheels
    g.fillStyle = c.dark ? "#0f1113" : "#2f3237";
    g.fillRect(-4 * s, -8.6 * s, 8 * s, 2.6 * s);
    g.fillRect(-4 * s, 6 * s, 8 * s, 2.6 * s);
    // body
    g.fillStyle = this.robotColor;
    g.strokeStyle = "rgba(0,0,0,.28)"; g.lineWidth = 1;
    g.beginPath(); g.arc(0, 0, (R - 0.8) * s, 0, 7); g.fill(); g.stroke();
    // top plate
    g.fillStyle = "rgba(255,255,255,.18)";
    g.beginPath(); g.arc(-1.2 * s, 0, 4.2 * s, 0, 7); g.fill();
    // nose / sensor
    g.fillStyle = c.dark ? "#e6e6e2" : "#ffffff";
    g.beginPath(); g.moveTo(7.6 * s, 0); g.lineTo(4.4 * s, 2.3 * s); g.lineTo(4.4 * s, -2.3 * s); g.closePath(); g.fill();
    // floor sensor dots
    if (this.res) {
      [["floor_left", 2.4], ["floor_center", 0], ["floor_right", -2.4]].forEach(([ch, fy]) => {
        const v = this.live ? this.live.sensors?.[ch] : idx !== null ? this.res.frames["s:" + ch]?.[idx] : null;
        if (v === null || v === undefined) return;
        const k = Math.round(40 + v * 2.1);
        g.fillStyle = `rgb(${k},${k},${k})`; g.strokeStyle = "rgba(0,0,0,.4)";
        g.beginPath(); g.arc(6.5 * s, -fy * s, 1.1 * s, 0, 7); g.fill(); g.stroke();
      });
    }
    // gripper
    if (this.arena.gripper) {
      const grip = this.lastEvent("grip", this.t);
      const closed = grip?.closed;
      g.strokeStyle = c.dark ? "#cfd2d6" : "#4a4e55"; g.lineWidth = Math.max(1.5, s * .9);
      const spread = closed ? 2.6 : 4.2;
      g.beginPath(); g.moveTo(7 * s, spread * s); g.lineTo(11.5 * s, spread * s); g.moveTo(7 * s, -spread * s); g.lineTo(11.5 * s, -spread * s); g.stroke();
    }
    // LED
    const led = this.lastEvent("led", this.t);
    if (led && led.color !== "off") {
      g.fillStyle = LED[led.color] || led.color;
      g.shadowColor = LED[led.color] || led.color; g.shadowBlur = 8;
      g.beginPath(); g.arc(-3.4 * s, 0, 1.8 * s, 0, 7); g.fill();
      g.shadowBlur = 0;
    }
    g.restore();
    // crash flash
    const crash = this.lastEvent("crash", this.t);
    if (crash && this.t - crash.t < 0.45) {
      g.strokeStyle = c.bad; g.lineWidth = 2; g.globalAlpha = 1 - (this.t - crash.t) / 0.45;
      g.beginPath(); g.arc(cx, cy, (R + 3 + (this.t - crash.t) * 20) * s, 0, 7); g.stroke(); g.globalAlpha = 1;
    }
    // speech bubble
    const say = this.lastEvent("say", this.t);
    if (say && this.t - say.t < 2.2) this.bubble(g, cx, cy - (R + 4) * s, say.text);
    const warn = this.lastEvent("warn", this.t);
    if (warn && this.t - warn.t < 2.5 && !(say && this.t - say.t < 2.2)) this.bubble(g, cx, cy - (R + 4) * s, "⚠ " + warn.text.slice(0, 48));
  }

  bubble(g, x, y, text) {
    g.font = "500 12px Inter, sans-serif";
    const w = Math.min(260, g.measureText(text).width + 16), h = 24;
    let bx = Math.max(4, Math.min(this.W - w - 4, x - w / 2)), by = Math.max(4, y - h - 6);
    g.fillStyle = this.c.surface; g.strokeStyle = this.c.line; g.lineWidth = 1;
    g.beginPath(); g.roundRect(bx, by, w, h, 7); g.fill(); g.stroke();
    g.fillStyle = this.c.dark ? "#e4e4e0" : "#22252a"; g.textAlign = "left"; g.textBaseline = "middle";
    g.save(); g.beginPath(); g.rect(bx, by, w, h); g.clip();
    g.fillText(text, bx + 8, by + h / 2);
    g.restore();
  }

  // ---------- arm (side view) ----------
  drawArm(g) {
    const a = this.arena, c = this.c, s = this.s;
    const [aw, ah] = a.size;
    g.fillStyle = c.floor;
    g.fillRect(this.X(0), this.Y(ah), aw * s, ah * s);
    g.strokeStyle = c.grid; g.lineWidth = 1; g.beginPath();
    for (let x = 10; x < aw; x += 10) { g.moveTo(this.X(x), this.Y(0)); g.lineTo(this.X(x), this.Y(ah)); }
    for (let y = 10; y < ah; y += 10) { g.moveTo(this.X(0), this.Y(y)); g.lineTo(this.X(aw), this.Y(y)); }
    g.stroke();
    g.fillStyle = c.muted; g.font = "500 10px Inter, sans-serif"; g.textAlign = "center"; g.textBaseline = "top";
    for (let x = 0; x <= aw; x += 20) g.fillText(String(x), this.X(x), this.Y(0) + 4);
    // table
    g.strokeStyle = c.wall; g.lineWidth = 3;
    g.beginPath(); g.moveTo(this.X(0), this.Y(0)); g.lineTo(this.X(aw), this.Y(0)); g.stroke();
    // targets
    for (const tg of a.targets || []) {
      g.fillStyle = colorOf(tg.color, ZONE);
      g.fillRect(this.X(tg.x - tg.w / 2), this.Y(0) - 5, tg.w * s, 5);
      g.fillStyle = c.text; g.textBaseline = "top"; g.font = "600 10px Inter, sans-serif";
      g.fillText(tg.name, this.X(tg.x), this.Y(0) + 16);
    }
    // marks
    for (const [mx, my, label] of a.marks || []) {
      g.strokeStyle = c.accent; g.lineWidth = 1.5;
      g.beginPath(); g.moveTo(this.X(mx) - 5, this.Y(my)); g.lineTo(this.X(mx) + 5, this.Y(my)); g.moveTo(this.X(mx), this.Y(my) - 5); g.lineTo(this.X(mx), this.Y(my) + 5); g.stroke();
      g.fillStyle = c.accent; g.font = "600 11px Inter, sans-serif"; g.textAlign = "left"; g.textBaseline = "bottom";
      g.fillText(label || "", this.X(mx) + 6, this.Y(my) - 3);
    }
    // blocks
    const fr = this.frameAt(this.t);
    const idx = fr ? (fr.a < .5 ? fr.i : fr.j) : null;
    const bpos = idx !== null && this.res?.frames?.blocks ? this.res.frames.blocks[idx] : null;
    (a.blocks || []).forEach((b, i) => {
      const [x, y] = bpos?.[i] || [b.x, b.y || 0];
      g.fillStyle = colorOf(b.color); g.strokeStyle = "rgba(0,0,0,.25)"; g.lineWidth = 1;
      g.fillRect(this.X(x - ARM_BLOCK / 2), this.Y(y + ARM_BLOCK), ARM_BLOCK * s, ARM_BLOCK * s);
      g.strokeRect(this.X(x - ARM_BLOCK / 2), this.Y(y + ARM_BLOCK), ARM_BLOCK * s, ARM_BLOCK * s);
    });
    // arm
    let sh = a.start[0], el = a.start[1];
    if (fr && this.res.frames.s) {
      const f = this.res.frames, A = fr.a;
      sh = f.s[fr.i] + (f.s[fr.j] - f.s[fr.i]) * A;
      el = f.e[fr.i] + (f.e[fr.j] - f.e[fr.i]) * A;
    }
    const [bx, by] = a.base, [L1, L2] = a.links;
    const r1 = sh * Math.PI / 180, r2 = (sh + el) * Math.PI / 180;
    const ex = bx + L1 * Math.cos(r1), ey = by + L1 * Math.sin(r1);
    const hx = ex + L2 * Math.cos(r2), hy = ey + L2 * Math.sin(r2);
    g.fillStyle = c.box;
    g.fillRect(this.X(bx - 7), this.Y(by), 14 * s, by * s);
    g.lineCap = "round";
    g.strokeStyle = this.robotColor; g.lineWidth = Math.max(5, 4 * s);
    g.beginPath(); g.moveTo(this.X(bx), this.Y(by)); g.lineTo(this.X(ex), this.Y(ey)); g.stroke();
    g.lineWidth = Math.max(4, 3.2 * s);
    g.beginPath(); g.moveTo(this.X(ex), this.Y(ey)); g.lineTo(this.X(hx), this.Y(hy)); g.stroke();
    g.fillStyle = c.dark ? "#d8dadd" : "#3a3e44";
    for (const [px, py] of [[bx, by], [ex, ey]]) { g.beginPath(); g.arc(this.X(px), this.Y(py), Math.max(4, 2.4 * s), 0, 7); g.fill(); }
    const grip = this.lastEvent("grip", this.t);
    const spread = grip?.closed ? 3.6 : 5.5;
    g.strokeStyle = c.dark ? "#d8dadd" : "#3a3e44"; g.lineWidth = 2;
    g.beginPath();
    g.moveTo(this.X(hx - spread), this.Y(hy)); g.lineTo(this.X(hx + spread), this.Y(hy));
    g.moveTo(this.X(hx - spread), this.Y(hy)); g.lineTo(this.X(hx - spread), this.Y(hy - 3));
    g.moveTo(this.X(hx + spread), this.Y(hy)); g.lineTo(this.X(hx + spread), this.Y(hy - 3));
    g.stroke();
    const crash = this.lastEvent("crash", this.t);
    if (crash && this.t - crash.t < 0.45) {
      g.strokeStyle = c.bad; g.lineWidth = 2; g.globalAlpha = 1 - (this.t - crash.t) / 0.45;
      g.beginPath(); g.arc(this.X(hx), this.Y(hy), 10 + (this.t - crash.t) * 30, 0, 7); g.stroke(); g.globalAlpha = 1;
    }
    const say = this.lastEvent("say", this.t);
    if (say && this.t - say.t < 2.2) this.bubble(g, this.X(hx), this.Y(hy) - 12, say.text);
  }
}
