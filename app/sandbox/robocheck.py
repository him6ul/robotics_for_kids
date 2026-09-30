"""Automated check harness. Runs in its own subprocess.

stdin:  JSON {"source": <learner code>, "check": <python check snippet>, "arena": <mission arena>}
stdout: JSON {"passed": bool, "message": str, "output": str, "replay": <payload of the last simulation>,
              "runs": n, "scenario": label}

Names available inside a check snippet (see app/curriculum/CONTENT_SPEC.md):
    source, tree, ARENA
    sim(arena=None, seed=None, label=None, allow_error=False, **overrides) -> Result
    arena(**overrides) -> a copy of ARENA with overrides applied
    expect(condition, message), CheckFail
    uses(concept), calls(name), defines(name), imports(module), norm(text)
"""
import ast
import copy
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kidast  # noqa: E402
import robosim  # noqa: E402

_real_stdout = sys.stdout
SOURCE = ""
ARENA = {}
LAST = None
RUNS = 0


class CheckFail(Exception):
    pass


def norm(text):
    return " ".join(str(text).lower().split())


def expect(condition, message):
    if not condition:
        raise CheckFail(message)


def arena(**overrides):
    a = copy.deepcopy(ARENA)
    for k, v in overrides.items():
        a[k] = copy.deepcopy(v)
    return a


class Result:
    """What happened in one simulated run."""

    def __init__(self, world, info, label):
        self.world = world
        self.info = info
        self.label = label
        self.s = world.summary()
        self.output = info["output"]
        self.error = info["error"]["type"] if info["error"] else None
        self.error_msg = info["error"]["msg"] if info["error"] else ""
        self.error_line = info["error"]["line"] if info["error"] else None
        self.end_reason = info["end_reason"]
        self.events = world.events
        self.frames = world.frames
        self.time = self.s["time"]
        self.kind = world.kind
        if world.kind == "drive":
            for k in ("x", "y", "heading", "crashes", "distance", "gems", "gems_total", "line_ratio", "laps",
                      "lap_times", "min_gap", "max_speed", "moving_time", "last_move_t", "blocks", "held"):
                setattr(self, k, self.s[k])
            self._trail()
        else:
            for k in ("shoulder", "elbow", "hand", "crashes", "blocks", "held", "tower", "path"):
                setattr(self, k, self.s[k])

    # ----- text -----
    @property
    def lines(self):
        return [l for l in self.output.splitlines() if l.strip()]

    def has(self, text):
        return norm(text) in norm(self.output)

    def said(self, text=None):
        says = [e["text"] for e in self.events if e["type"] == "say"]
        return bool(says) if text is None else any(norm(text) in norm(s) for s in says)

    def count(self, event_type):
        return sum(1 for e in self.events if e["type"] == event_type)

    def led_colors(self):
        return [e["color"] for e in self.events if e["type"] == "led"]

    # ----- drive world -----
    def _trail(self):
        pen_events = [e for e in self.events if e["type"] == "pen"]
        strokes, cur, pi, down = [], [], 0, False
        f = self.frames
        for i, t in enumerate(f["t"]):
            while pi < len(pen_events) and pen_events[pi]["t"] <= t + 1e-9:
                down = pen_events[pi]["down"]
                pi += 1
                if not down and cur:
                    strokes.append(cur)
                    cur = []
            if down:
                p = (f["x"][i], f["y"][i])
                if not cur or math.hypot(p[0] - cur[-1][0], p[1] - cur[-1][1]) > 0.05:
                    cur.append(p)
        if cur:
            strokes.append(cur)
        self.strokes = strokes
        self.trail = [p for s in strokes for p in s]
        self.pen_length = round(sum(math.hypot(b[0] - a[0], b[1] - a[1]) for s in strokes for a, b in zip(s, s[1:])), 1)
        if self.trail:
            xs, ys = [p[0] for p in self.trail], [p[1] for p in self.trail]
            self.trail_bbox = (round(max(xs) - min(xs), 1), round(max(ys) - min(ys), 1))
            self.closed = len(self.trail) > 5 and math.hypot(self.trail[0][0] - self.trail[-1][0],
                                                             self.trail[0][1] - self.trail[-1][1]) < 6
        else:
            self.trail_bbox = (0, 0)
            self.closed = False

    def corners(self, min_turn=35):
        """How many sharp corners the pen drew (direction changes bigger than min_turn degrees)."""
        n = 0
        for s in self.strokes:
            pts = [s[0]]
            for p in s[1:]:
                if math.hypot(p[0] - pts[-1][0], p[1] - pts[-1][1]) >= 3:
                    pts.append(p)
            if len(pts) > 2 and self.closed and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 6:
                pts = pts + [pts[1]]
            hs = [math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) for a, b in zip(pts, pts[1:])]
            for a, b in zip(hs, hs[1:]):
                if abs(robosim._wrap(b - a)) >= min_turn:
                    n += 1
        return n

    def in_zone(self, name):
        """Is the robot (drive) / a block (arm: pass a colour) in this zone at the end?"""
        return name in self.s.get("zone_now", [])

    def visited(self, name):
        return name in self.s.get("visited", [])

    def zone_time(self, name):
        return self.s.get("zone_time", {}).get(name, 0.0)

    def dist_to(self, x, y):
        return math.hypot(self.x - x, self.y - y)

    @property
    def stopped(self):
        """True if the robot had stopped moving before the end (and wasn't still driving)."""
        return self.time - self.last_move_t >= 0.3 or self.end_reason == "done"

    def used(self, channel):
        return channel in self.world.used

    def blocks_in(self, zone, color=None):
        return sum(1 for b in self.blocks if zone in b.get("zones", b.get("targets", [])) and not b["held"]
                   and (color is None or b["color"] == color))

    def min_front_distance(self):
        """Closest the robot's front got to a wall during the run (cm from the front edge)."""
        best = 1e9
        w = self.world
        for x, y, h in zip(self.frames["x"], self.frames["y"], self.frames["h"]):
            ang = math.radians(h)
            dx, dy = math.cos(ang), math.sin(ang)
            ox, oy = x + robosim.R * dx, y + robosim.R * dy
            for (ax, ay, bx, by) in w.walls:
                t = robosim.ray_seg(ox, oy, dx, dy, ax, ay, bx, by)
                if t is not None:
                    best = min(best, t)
        return round(best, 1)

    def series(self, name):
        """A recorded telemetry series: 'x', 'y', 'h', or a sensor like 'distance_front', or your plot name."""
        f = self.frames
        for key in (name, "s:" + name, "p:" + name):
            if key in f:
                return f[key]
        return []


def _friendly_crash(r):
    where = f" on line {r.error_line}" if r.error_line else ""
    return f"Your program crashed{where} with {r.error}: {r.error_msg}"


def sim(arena_=None, seed=None, label=None, allow_error=False, **overrides):
    global LAST, RUNS
    a = copy.deepcopy(arena_ if arena_ is not None else ARENA)
    for k, v in overrides.items():
        a[k] = copy.deepcopy(v)
    world, info = robosim.run_program(SOURCE, a, 12345 if seed is None else seed)
    r = Result(world, info, label)
    LAST = r
    RUNS += 1
    if r.error and not allow_error:
        raise CheckFail(_friendly_crash(r) + (f" (in test: {label})" if label else ""))
    return r


def main():
    global SOURCE, ARENA
    payload = json.loads(sys.stdin.read())
    SOURCE = payload["source"]
    ARENA = payload.get("arena") or {}
    out = {"passed": False, "message": "", "output": "", "runs": 0}
    tree = kidast.parse(SOURCE)
    if tree is None:
        try:
            compile(SOURCE, "main.py", "exec")
        except SyntaxError as e:
            out["message"] = f"Python can't read line {e.lineno} yet: {e.msg}. Fix that first, then check again."
            out["error"] = "SyntaxError"
        _real_stdout.write(json.dumps(out))
        return
    concepts = kidast.detect_concepts(SOURCE, tree)
    call_counts, defined, imported = {}, set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            n = kidast._call_name(node)
            if n:
                call_counts[n] = call_counts.get(n, 0) + 1
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            defined.add(node.name)
        elif isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    scope = {
        "source": SOURCE, "tree": tree, "ARENA": ARENA, "sim": sim, "arena": arena, "expect": expect,
        "CheckFail": CheckFail, "norm": norm, "math": math,
        "uses": lambda c: concepts.get(c, 0) > 0,
        "calls": lambda name: call_counts.get(name, 0),
        "defines": lambda name: name in defined,
        "imports": lambda m: m in imported,
        "loops": lambda: sum(1 for n in ast.walk(tree) if isinstance(n, (ast.For, ast.While))),
    }
    try:
        exec(compile(payload["check"], "check", "exec"), scope)
        out["passed"] = True
        out["message"] = scope.get("SUCCESS", "")
    except CheckFail as e:
        out["message"] = str(e)
    except Exception as e:  # noqa: BLE001 - a broken check should not look like the kid's fault
        out["message"] = f"(The checker itself had a problem: {type(e).__name__}: {e})"
        out["checker_error"] = True
    out["runs"] = RUNS
    if LAST is not None:
        out["output"] = LAST.output[-3000:]
        out["scenario"] = LAST.label
        out["replay"] = robosim.result_payload(LAST.world, LAST.info)
    _real_stdout.write(json.dumps(out, separators=(",", ":")))


if __name__ == "__main__":
    main()
