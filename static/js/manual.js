// The Robot Manual: every command the robot and arm understand, unlocked week by week.
import { badgeProgress, el, esc, state, uiEvent } from "./core.js";

export const API = [
  // group, signature, description, week
  ["Move", "robot.drive(left, right)", "Set each motor's power, -100 … 100. Keeps going until you change it. Same power = straight, different = curve.", 1],
  ["Move", "robot.wait(seconds)", "Let time pass while the motors keep doing what you said.", 1],
  ["Move", "robot.stop()", "Both motors off.", 1],
  ["Move", "robot.forward(cm, power=50)", "Drive straight about cm centimetres, then stop (timed — no sensors!).", 1],
  ["Move", "robot.backward(cm, power=50)", "Same, backwards.", 1],
  ["Move", "robot.turn(degrees, power=40)", "Spin on the spot. + is left (counter-clockwise), − is right.", 1],
  ["Move", "robot.turn_left(90) / robot.turn_right(90)", "Friendlier spin commands.", 1],
  ["Show", "robot.say(text)", "Speech bubble for 2 seconds.", 1],
  ["Show", "robot.led(color)", "'red', 'green', 'blue', 'yellow', 'purple', 'white' or 'off'.", 1],
  ["Show", "robot.beep(pitch=880, seconds=0.15)", "Play a note (Hz). C = 523, E = 659, G = 784.", 1],
  ["Show", "robot.pen_down(color) / robot.pen_up()", "Draw where the robot drives.", 1],
  ["Info", "robot.time()", "Seconds since the program started (robot time).", 1],
  ["Sense", "robot.distance(direction='front')", "Ultrasonic distance in cm (max 200) to a wall or block. Directions: 'front', 'left', 'right', 'front_left', 'front_right', 'back'.", 2],
  ["Sense", "robot.bumper()", "True while the front bumper is pressed.", 2],
  ["Sense", "robot.light('left') / robot.light('right')", "Brightness 0 … 100 from the two light sensors (for light bulbs in some arenas).", 2],
  ["Sense", "robot.floor(which='center')", "Reflected light from the floor: black tape ≈ 6, white ≈ 92. which = 'left', 'center', 'right'.", 3],
  ["Sense", "robot.floor_left() / robot.floor_right()", "Shortcuts for the side floor sensors.", 3],
  ["Sense", "robot.color()", "Floor colour under the robot: 'white', 'black', 'red', 'green', 'blue', 'yellow'…", 3],
  ["Info", "robot.plot(name, value)", "Draw your own line on the Telemetry tab — great for tuning!", 3],
  ["Sense", "robot.heading()", "Compass in degrees: 0 = east →, 90 = north ↑, 180 = west, −90 = south.", 4],
  ["Sense", "robot.encoders()", "(left_cm, right_cm): how far each wheel has rolled.", 4],
  ["Sense", "robot.reset_encoders()", "Set both encoders back to 0.", 4],
  ["Grip", "robot.grab()", "Close the gripper. True if a block was right in front.", 5],
  ["Grip", "robot.release()", "Open the gripper.", 5],
  ["Grip", "robot.holding()", "Colour of the block you're holding, or None.", 5],
  ["Sense", "robot.camera()", "List of things the camera sees: {'kind', 'color', 'angle', 'distance'}, nearest first.", 5],
  ["Arm", "arm.move(shoulder, elbow)", "Move both joints and wait until they arrive. Shoulder 0 = right, 90 = up. Elbow 0 = straight.", 5],
  ["Arm", "arm.set(shoulder, elbow)", "Start moving the joints without waiting.", 5],
  ["Arm", "arm.shoulder(a) / arm.elbow(a)", "Move just one joint.", 5],
  ["Arm", "arm.hand()", "(x, y) of the gripper tip. The table top is y = 0.", 5],
  ["Arm", "arm.angles() / arm.links() / arm.base()", "Current angles, link lengths, base position.", 5],
  ["Arm", "arm.grab() / arm.release() / arm.holding()", "Pick up the top of a block, drop it, check what you hold.", 5],
  ["Sense", "robot.position()", "(x, y) in cm — only in arenas with GPS.", 6],
];

export function unlockedWeek() {
  const ps = state.kidState?.projects || [];
  return Math.max(1, ...ps.filter((p) => p.unlocked).map((p) => p.week));
}

export function manualHTML(compact = false) {
  const wk = unlockedWeek();
  const groups = {};
  API.forEach((a) => (groups[a[0]] = groups[a[0]] || []).push(a));
  return `<div class="manual">
    ${compact ? "" : `<p class="muted">Every command your robot understands. Faded ones unlock later in the quest (you can still try them in the Playground).</p>`}
    <div class="card flat"><h3>Robot facts</h3><dl class="kv">
      <dt>Size</dt><dd>16 cm wide (radius 8 cm), wheels 14 cm apart</dd>
      <dt>Top speed</dt><dd>power 100 = 30 cm/s (power 50 = 15 cm/s)</dd>
      <dt>Directions</dt><dd>0° = east →, 90° = north ↑, + turns are left</dd>
      <dt>Units</dt><dd>centimetres, seconds, degrees</dd>
      <dt>Time</dt><dd>each robot command takes 2 ms; <code>wait()</code> lets time pass</dd></dl></div>
    ${Object.entries(groups).map(([g, items]) => `<div class="api-group"><h3>${esc(g)}</h3>${items.map(([, sig, desc, w]) =>
      `<div class="api ${w > wk ? "locked" : ""}"><code>${esc(sig)}</code><span class="muted">${esc(desc)}${w > wk ? ` <span class="pill">week ${w}</span>` : ""}</span></div>`).join("")}</div>`).join("")}
  </div>`;
}

let open = null;
export function toggleManual() {
  if (open) { open.remove(); open = null; return; }
  uiEvent("manual.open", state.context.project + "/" + state.context.step);
  open = el(`<aside class="drawer"><header><b>📘 Robot manual</b><span class="spacer"></span><button class="iconbtn" data-x>✕</button></header>
    <div class="body">${state.kidState?.badges ? `<div style="margin-bottom:12px">${badgeProgress(state.kidState.badges)}</div>` : ""}${manualHTML(true)}</div></aside>`);
  open.querySelector("[data-x]").onclick = toggleManual;
  document.body.appendChild(open);
}
export function closeManual() { if (open) { open.remove(); open = null; } }

// autocomplete after "robot." / "arm."
export function robotHint(cm) {
  const cur = cm.getCursor(), line = cm.getLine(cur.line).slice(0, cur.ch);
  const m = line.match(/\b(robot|arm)\.(\w*)$/);
  if (!m) return null;
  const list = API.map((a) => a[1]).flatMap((s) => s.split(" / "))
    .filter((s) => s.startsWith(m[1] + "."))
    .map((s) => s.slice(m[1].length + 1)).filter((s) => s.startsWith(m[2]));
  const uniq = [...new Set(list)];
  return { list: uniq.map((s) => ({ text: s.replace(/\(.*\)$/, "("), displayText: s })),
    from: CodeMirror.Pos(cur.line, cur.ch - m[2].length), to: cur };
}
