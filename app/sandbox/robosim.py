"""RoboSim: a small, deterministic 2-D robot simulator.

Two kinds of worlds:

* ``World``    - a top-down arena with a differential-drive robot (two motors), walls, black tape
                 lines, coloured floor zones, gems, pushable blocks and lights. The robot has an
                 ultrasonic distance sensor (5 directions), a bumper, three floor (reflected-light)
                 sensors, a colour sensor, two light sensors, a compass/gyro, wheel encoders, a
                 camera, a pen and an optional gripper.
* ``ArmWorld`` - a side view of a table with a two-joint robot arm (shoulder + elbow servos) and a
                 gripper that can pick up and stack blocks.

Units are centimetres, seconds and degrees. y points *up*, heading 0 points east (→) and
positive angles turn left (counter-clockwise), like in maths class.

The learner's program runs in normal Python and talks to a ``Robot`` / ``Arm`` object. Time only
moves forward when the program waits or calls the robot (every call costs 2 ms of robot time, like
a real sensor read), so the whole run is computed quickly and then replayed in the browser.

Standard library only: this module is imported by the sandbox subprocesses *and* by the server
(for teleop), so it must stay dependency free and must not print.
"""
import math
import random
import sys
import traceback

DT = 0.02                 # physics tick (50 Hz)
FRAME_EVERY = 2           # record every 2nd tick (25 frames per second)
CALL_COST_TICKS = 0.1     # each robot call costs 1/10 tick = 2 ms of robot time
R = 8.0                   # robot body radius
WHEEL_BASE = 14.0         # distance between the two wheels
MAX_SPEED = 30.0          # cm/s at power 100
SENSOR_RANGE = 200.0      # ultrasonic range
BLOCK_R = 3.0             # blocks are 6 cm cubes (circles for physics)
GEM_R = 2.5
MAX_OUTPUT = 60_000
MAX_TIME = 180.0

FLOOR_REFLECT = {"white": 92, "black": 6, "red": 46, "green": 40, "blue": 30, "yellow": 76,
                 "orange": 58, "purple": 26, "gray": 64, "brown": 34}
LINE_REFLECT = 6
DIRECTIONS = {"front": 0, "left": 90, "right": -90, "front_left": 45, "front_right": -45, "back": 180}
FLOOR_SENSORS = {"left": (6.5, 2.4), "center": (6.5, 0.0), "right": (6.5, -2.4)}
SPOT = 0.8                # floor sensor spot radius (gives a smooth edge)
LIGHT_SENSORS = {"left": 40, "right": -40}


# ---------------------------------------------------------------------------
# errors the learner may see
# ---------------------------------------------------------------------------
class RobotError(Exception):
    """A friendly error about using the robot wrongly (bad sensor name, wrong kind of value…)."""


class TimeUp(BaseException):
    """Raised inside the learner's program when the arena's time limit is reached.
    BaseException so that a bare ``except Exception`` in kid code doesn't swallow it."""


class OutputFlood(BaseException):
    pass


def _num(v, what, example):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise RobotError(f"{what} needs a number, but got {v!r}. Example: {example}")
    if v != v or v in (float("inf"), float("-inf")):
        raise RobotError(f"{what} got a number that isn't real ({v}).")
    return float(v)


def _wrap(deg):
    d = (deg + 180.0) % 360.0 - 180.0
    return 180.0 if d == -180.0 else d


# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------
def closest_on_seg(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    cx, cy = ax + t * dx, ay + t * dy
    return cx, cy, math.hypot(px - cx, py - cy)


def ray_seg(ox, oy, dx, dy, ax, ay, bx, by):
    """Distance along the unit ray (ox,oy)+t(dx,dy) to segment ab, or None."""
    ex, ey = bx - ax, by - ay
    den = dx * ey - dy * ex
    if abs(den) < 1e-12:
        return None
    t = ((ax - ox) * ey - (ay - oy) * ex) / den
    u = ((ax - ox) * dy - (ay - oy) * dx) / den
    if t >= 0 and 0 <= u <= 1:
        return t
    return None


def ray_circle(ox, oy, dx, dy, cx, cy, r):
    fx, fy = ox - cx, oy - cy
    b = fx * dx + fy * dy
    c = fx * fx + fy * fy - r * r
    disc = b * b - c
    if disc < 0:
        return None
    s = math.sqrt(disc)
    t = -b - s
    if t >= 0:
        return t
    t = -b + s
    return 0.0 if t >= 0 else None


def seg_intersect(p1, p2, p3, p4):
    d1x, d1y = p2[0] - p1[0], p2[1] - p1[1]
    d2x, d2y = p4[0] - p3[0], p4[1] - p3[1]
    den = d1x * d2y - d1y * d2x
    if abs(den) < 1e-12:
        return False
    t = ((p3[0] - p1[0]) * d2y - (p3[1] - p1[1]) * d2x) / den
    u = ((p3[0] - p1[0]) * d1y - (p3[1] - p1[1]) * d1x) / den
    return 0 <= t <= 1 and 0 <= u <= 1


class SegGrid:
    """Buckets segments into square cells so point queries only look at nearby segments."""

    def __init__(self, segs, cell=20.0):
        self.cell = cell
        self.cells = {}
        for i, (ax, ay, bx, by, *_rest) in enumerate(segs):
            pad = (_rest[0] / 2 if _rest else 0) + 2
            x0, x1 = sorted((ax, bx))
            y0, y1 = sorted((ay, by))
            for cx in range(int((x0 - pad) // cell), int((x1 + pad) // cell) + 1):
                for cy in range(int((y0 - pad) // cell), int((y1 + pad) // cell) + 1):
                    self.cells.setdefault((cx, cy), []).append(i)
        self.segs = segs

    def near(self, x, y, radius):
        c = self.cell
        seen = set()
        for cx in range(int((x - radius) // c), int((x + radius) // c) + 1):
            for cy in range(int((y - radius) // c), int((y + radius) // c) + 1):
                for i in self.cells.get((cx, cy), ()):
                    if i not in seen:
                        seen.add(i)
                        yield self.segs[i]


# ---------------------------------------------------------------------------
# arena normalisation
# ---------------------------------------------------------------------------
def normalize(spec):
    """Fill defaults and derive wall segments. Returns a new dict (the 'public' arena the browser draws)."""
    spec = spec or {}
    if spec.get("type") == "arm":
        return normalize_arm(spec)
    w, h = spec.get("size", [240, 160])
    a = {
        "type": "drive",
        "name": spec.get("name", "Arena"),
        "size": [w, h],
        "start": list(spec.get("start", [30, h / 2, 0])),
        "walls": [list(s) for s in spec.get("walls", [])],
        "boxes": [list(b) for b in spec.get("boxes", [])],
        "lines": [{"pts": [list(p) for p in ln["pts"]], "closed": bool(ln.get("closed")),
                   "width": float(ln.get("width", 2.5))} for ln in spec.get("lines", [])],
        "zones": [{"name": z.get("name", f"zone{i}"), "rect": list(z["rect"]), "color": z.get("color", "green"),
                   "label": z.get("label", "")} for i, z in enumerate(spec.get("zones", []))],
        "gems": [list(g) for g in spec.get("gems", [])],
        "blocks": [{"pos": list(b["pos"]), "color": b.get("color", "red")} for b in spec.get("blocks", [])],
        "lights": [list(p) for p in spec.get("lights", [])],
        "finish": list(spec["finish"]) if spec.get("finish") else None,
        "noise": float(spec.get("noise", 0.0)),
        "gps": bool(spec.get("gps", False)),
        "gripper": bool(spec.get("gripper", False)),
        "time_limit": float(min(MAX_TIME, spec.get("time_limit", 60))),
        "border": spec.get("border", True),
        "grid": spec.get("grid"),          # optional {"cell": 40} to draw a maze grid
        "labels": spec.get("labels", []),  # [[x, y, "text"]]
    }
    segs = [tuple(s) for s in a["walls"]]
    for (x, y, bw, bh) in a["boxes"]:
        segs += [(x, y, x + bw, y), (x + bw, y, x + bw, y + bh), (x + bw, y + bh, x, y + bh), (x, y + bh, x, y)]
    if a["border"]:
        segs += [(0, 0, w, 0), (w, 0, w, h), (w, h, 0, h), (0, h, 0, 0)]
    a["_segs"] = segs
    lsegs = []
    for ln in a["lines"]:
        pts = ln["pts"] + ([ln["pts"][0]] if ln["closed"] and len(ln["pts"]) > 2 else [])
        for p, q in zip(pts, pts[1:]):
            lsegs.append((p[0], p[1], q[0], q[1], ln["width"]))
    a["_lsegs"] = lsegs
    return a


def public(a):
    return {k: v for k, v in a.items() if not k.startswith("_")}


# ---------------------------------------------------------------------------
# the drive world
# ---------------------------------------------------------------------------
class World:
    kind = "drive"

    def __init__(self, spec, seed=12345):
        self.a = normalize(spec)
        a = self.a
        self.rng = random.Random(seed)
        self.x, self.y = float(a["start"][0]), float(a["start"][1])
        self.th = math.radians(a["start"][2] if len(a["start"]) > 2 else 0)
        self.pl = self.pr = 0.0          # motor power -100..100
        self.enc = [0.0, 0.0]
        self.enc_zero = [0.0, 0.0]
        self.t = 0.0
        self.ticks = 0
        self.pending = 0.0
        self.noise = a["noise"]
        n = self.noise
        sgn = 1 if self.rng.random() < 0.5 else -1
        self.bias = (1 - sgn * 0.07 * n * self.rng.uniform(0.5, 1.0), 1 + sgn * 0.07 * n * self.rng.uniform(0.5, 1.0))
        self.gyro_drift = n * self.rng.uniform(-0.25, 0.25)          # degrees per second
        self.walls = a["_segs"]
        self.wgrid = SegGrid(self.walls)
        self.lsegs = a["_lsegs"]
        self.lgrid = SegGrid(self.lsegs) if self.lsegs else None
        self.blocks = [{"x": float(b["pos"][0]), "y": float(b["pos"][1]), "color": b["color"], "held": False}
                       for b in a["blocks"]]
        self.gems = [{"x": float(g[0]), "y": float(g[1]), "got": None} for g in a["gems"]]
        self.held = None
        self.contact = False
        self.bump = False
        self.events = []
        self.frames = {"t": [], "x": [], "y": [], "h": [], "pl": [], "pr": []}
        if self.blocks:
            self.frames["blocks"] = []
        self.used = []                    # sensor channels the program read (for telemetry)
        self.plots = {}
        self.pen = False
        self.output_chars = 0
        self.warned = set()
        self.st = {"crashes": 0, "distance": 0.0, "line_ticks": 0, "ticks": 0, "zone_time": {}, "visited": [],
                   "laps": 0, "lap_times": [], "min_gap": 1e9, "max_speed": 0.0, "moving_ticks": 0,
                   "last_move_t": 0.0, "first_move_t": None}
        self._last_lap_t = 0.0
        self._dist_since_lap = 0.0
        self._update_zones(0)
        self.record()

    # ----- time -------------------------------------------------------------
    def cost(self):
        self.pending += CALL_COST_TICKS
        if self.pending >= 1:
            self.pending -= 1
            self.tick()

    def advance(self, seconds):
        n = max(1, int(round(seconds / DT)))
        self.pending = 0.0
        for _ in range(n):
            self.tick()

    def tick(self):
        a = self.a
        vl = self.pl / 100.0 * MAX_SPEED * self.bias[0]
        vr = self.pr / 100.0 * MAX_SPEED * self.bias[1]
        if self.noise:
            if self.pl:
                vl += self.rng.gauss(0, 0.03 * self.noise * MAX_SPEED)
            if self.pr:
                vr += self.rng.gauss(0, 0.03 * self.noise * MAX_SPEED)
        ox, oy = self.x, self.y
        v = (vl + vr) / 2
        w = (vr - vl) / WHEEL_BASE
        th = self.th
        if abs(w) < 1e-9:
            self.x += v * math.cos(th) * DT
            self.y += v * math.sin(th) * DT
        else:
            self.x += v / w * (math.sin(th + w * DT) - math.sin(th))
            self.y -= v / w * (math.cos(th + w * DT) - math.cos(th))
        self.th = th + w * DT
        self.enc[0] += vl * DT
        self.enc[1] += vr * DT
        was = self.contact
        self._collide()
        if self.contact and not was:
            self.st["crashes"] += 1
            self.events.append({"t": round(self.t, 3), "type": "crash", "x": round(self.x, 1), "y": round(self.y, 1)})
        self._blocks()
        if self.held is not None:
            b = self.blocks[self.held]
            gx, gy = self._grip_point()
            b["x"], b["y"] = gx, gy
        moved = math.hypot(self.x - ox, self.y - oy)
        self.st["distance"] += moved
        self._dist_since_lap += moved
        speed = moved / DT
        self.st["max_speed"] = max(self.st["max_speed"], speed)
        if speed > 0.5:
            self.st["moving_ticks"] += 1
            self.st["last_move_t"] = self.t + DT
            if self.st["first_move_t"] is None:
                self.st["first_move_t"] = self.t
        for g_i, g in enumerate(self.gems):
            if g["got"] is None and math.hypot(g["x"] - self.x, g["y"] - self.y) < R + GEM_R:
                g["got"] = round(self.t, 3)
                self.events.append({"t": round(self.t, 3), "type": "gem", "i": g_i})
        if a["finish"]:
            f = a["finish"]
            if seg_intersect((ox, oy), (self.x, self.y), (f[0], f[1]), (f[2], f[3])):
                nx, ny = -(f[3] - f[1]), f[2] - f[0]     # left normal of the finish segment = racing direction
                # the robot starts just past the finish line, so every forward crossing is a finished lap
                if (self.x - ox) * nx + (self.y - oy) * ny > 0 and self.t - self._last_lap_t > 3 and self._dist_since_lap > 80:
                    lap_t = round(self.t - self._last_lap_t, 2)
                    self.st["laps"] += 1
                    self.st["lap_times"].append(lap_t)
                    self.events.append({"t": round(self.t, 3), "type": "lap", "n": self.st["laps"], "time": lap_t})
                    self._last_lap_t = self.t
                    self._dist_since_lap = 0.0
        if self.lgrid is not None and speed > 0.5:
            for (ax, ay, bx, by, lw) in self.lgrid.near(self.x, self.y, 6):
                if closest_on_seg(self.x, self.y, ax, ay, bx, by)[2] < lw / 2 + 3.5:
                    self.st["line_ticks"] += 1
                    break
        gap = self._wall_gap()
        self.st["min_gap"] = min(self.st["min_gap"], gap)
        self.st["ticks"] += 1
        self.t = round(self.t + DT, 6)
        self.ticks += 1
        self._update_zones(DT)
        if self.ticks % FRAME_EVERY == 0:
            self.record()
        if self.t >= a["time_limit"] - 1e-9:
            raise TimeUp()

    # ----- physics ----------------------------------------------------------
    def _collide(self):
        self.contact = False
        self.bump = False
        for _ in range(3):
            hit = False
            for (ax, ay, bx, by) in self.wgrid.near(self.x, self.y, R + 1):
                cx, cy, d = closest_on_seg(self.x, self.y, ax, ay, bx, by)
                if d < R:
                    if d < 1e-9:
                        nx, ny = -math.cos(self.th), -math.sin(self.th)
                    else:
                        nx, ny = (self.x - cx) / d, (self.y - cy) / d
                    self.x += nx * (R - d + 1e-6)
                    self.y += ny * (R - d + 1e-6)
                    self.contact = hit = True
                    ang = _wrap(math.degrees(math.atan2(cy - self.y, cx - self.x) - self.th))
                    if abs(ang) <= 70:
                        self.bump = True
            if not hit:
                break

    def _blocks(self):
        for i, b in enumerate(self.blocks):
            if b["held"]:
                continue
            dx, dy = b["x"] - self.x, b["y"] - self.y
            d = math.hypot(dx, dy)
            m = R + BLOCK_R
            if d < m:
                if d < 1e-9:
                    dx, dy, d = math.cos(self.th), math.sin(self.th), 1.0
                ang = _wrap(math.degrees(math.atan2(dy, dx) - self.th))
                if abs(ang) <= 70:
                    self.bump = True
                b["x"], b["y"] = self.x + dx / d * m, self.y + dy / d * m
                stuck = False
                for (ax, ay, bx, by) in self.wgrid.near(b["x"], b["y"], BLOCK_R + 1):
                    cx, cy, dd = closest_on_seg(b["x"], b["y"], ax, ay, bx, by)
                    if dd < BLOCK_R:
                        stuck = True
                        if dd > 1e-9:
                            b["x"] += (b["x"] - cx) / dd * (BLOCK_R - dd)
                            b["y"] += (b["y"] - cy) / dd * (BLOCK_R - dd)
                if stuck:
                    dx, dy = b["x"] - self.x, b["y"] - self.y
                    d = math.hypot(dx, dy) or 1.0
                    if d < m:
                        self.x, self.y = b["x"] - dx / d * m, b["y"] - dy / d * m
        # blocks don't overlap each other
        for i in range(len(self.blocks)):
            for j in range(i + 1, len(self.blocks)):
                p, q = self.blocks[i], self.blocks[j]
                if p["held"] or q["held"]:
                    continue
                dx, dy = q["x"] - p["x"], q["y"] - p["y"]
                d = math.hypot(dx, dy)
                if 1e-9 < d < 2 * BLOCK_R:
                    push = (2 * BLOCK_R - d) / 2
                    p["x"] -= dx / d * push
                    p["y"] -= dy / d * push
                    q["x"] += dx / d * push
                    q["y"] += dy / d * push

    def _wall_gap(self):
        best = 1e9
        for (ax, ay, bx, by) in self.wgrid.near(self.x, self.y, 40):
            best = min(best, closest_on_seg(self.x, self.y, ax, ay, bx, by)[2] - R)
        return best

    def _grip_point(self):
        return self.x + (R + BLOCK_R) * math.cos(self.th), self.y + (R + BLOCK_R) * math.sin(self.th)

    def _zones_at(self, x, y):
        return [z for z in self.a["zones"] if z["rect"][0] <= x <= z["rect"][0] + z["rect"][2]
                and z["rect"][1] <= y <= z["rect"][1] + z["rect"][3]]

    def _update_zones(self, dt):
        for z in self._zones_at(self.x, self.y):
            n = z["name"]
            self.st["zone_time"][n] = self.st["zone_time"].get(n, 0) + dt
            if n not in self.st["visited"]:
                self.st["visited"].append(n)

    # ----- sensors (pure: no time cost here) ---------------------------------
    def _local(self, fx, fy):
        c, s = math.cos(self.th), math.sin(self.th)
        return self.x + fx * c - fy * s, self.y + fx * s + fy * c

    def ray(self, off_deg):
        ang = self.th + math.radians(off_deg)
        dx, dy = math.cos(ang), math.sin(ang)
        ox, oy = self.x + R * dx, self.y + R * dy
        best = SENSOR_RANGE
        for (ax, ay, bx, by) in self.walls:
            t = ray_seg(ox, oy, dx, dy, ax, ay, bx, by)
            if t is not None and t < best:
                best = t
        for b in self.blocks:
            if not b["held"]:
                t = ray_circle(ox, oy, dx, dy, b["x"], b["y"], BLOCK_R)
                if t is not None and t < best:
                    best = t
        if self.noise:
            best += self.rng.gauss(0, 0.6 * self.noise)
        return round(max(0.0, min(SENSOR_RANGE, best)), 1)

    def floor_at(self, which):
        fx, fy = FLOOR_SENSORS[which]
        px, py = self._local(fx, fy)
        base = FLOOR_REFLECT["white"]
        zs = self._zones_at(px, py)
        if zs:
            base = FLOOR_REFLECT.get(zs[-1]["color"], 60)
        cover = 0.0
        if self.lgrid is not None:
            for (ax, ay, bx, by, lw) in self.lgrid.near(px, py, 4):
                d = closest_on_seg(px, py, ax, ay, bx, by)[2]
                c = (lw / 2 + SPOT - d) / (2 * SPOT)
                cover = max(cover, min(1.0, max(0.0, c)))
        val = base * (1 - cover) + LINE_REFLECT * cover
        if self.noise:
            val += self.rng.gauss(0, 1.5 * self.noise)
        return int(round(max(0, min(100, val))))

    def color_at(self):
        px, py = self._local(*FLOOR_SENSORS["center"])
        if self.lgrid is not None:
            for (ax, ay, bx, by, lw) in self.lgrid.near(px, py, 4):
                if closest_on_seg(px, py, ax, ay, bx, by)[2] < lw / 2:
                    return "black"
        zs = self._zones_at(px, py)
        return zs[-1]["color"] if zs else "white"

    def light_at(self, which):
        ang = self.th + math.radians(LIGHT_SENSORS[which])
        sx, sy = self._local(5, 3 if which == "left" else -3)
        total = 2.0
        for (lx, ly) in self.a["lights"]:
            dx, dy = lx - sx, ly - sy
            d = math.hypot(dx, dy) or 0.01
            cosang = (dx * math.cos(ang) + dy * math.sin(ang)) / d
            if cosang > 0:
                total += 100 * cosang / (1 + (d / 70) ** 2)
        if self.noise:
            total += self.rng.gauss(0, 1.0 * self.noise)
        return int(round(max(0, min(100, total))))

    def heading_deg(self):
        h = math.degrees(self.th) + self.gyro_drift * self.t
        if self.noise:
            h += self.rng.gauss(0, 0.3 * self.noise)
        return round(_wrap(h), 1)

    def encoders_cm(self):
        return (round(self.enc[0] - self.enc_zero[0], 1), round(self.enc[1] - self.enc_zero[1], 1))

    def camera(self):
        seen = []
        items = [("block", b["x"], b["y"], b["color"]) for b in self.blocks if not b["held"]]
        items += [("gem", g["x"], g["y"], "gold") for g in self.gems if g["got"] is None]
        for kind, x, y, color in items:
            dx, dy = x - self.x, y - self.y
            d = math.hypot(dx, dy)
            ang = _wrap(math.degrees(math.atan2(dy, dx) - self.th))
            if d > 160 or abs(ang) > 30:
                continue
            blocked = False
            ux, uy = dx / d, dy / d
            for (ax, ay, bx, by) in self.walls:
                t = ray_seg(self.x, self.y, ux, uy, ax, ay, bx, by)
                if t is not None and t < d - BLOCK_R:
                    blocked = True
                    break
            if not blocked:
                seen.append({"kind": kind, "color": color, "angle": round(ang, 1), "distance": round(max(0.0, d - R), 1)})
        seen.sort(key=lambda s: s["distance"])
        return seen

    # ----- recording ----------------------------------------------------------
    CHANNELS = {
        "distance_front": lambda w: w.ray(0), "distance_left": lambda w: w.ray(90),
        "distance_right": lambda w: w.ray(-90), "distance_front_left": lambda w: w.ray(45),
        "distance_front_right": lambda w: w.ray(-45), "distance_back": lambda w: w.ray(180),
        "floor_left": lambda w: w.floor_at("left"), "floor_center": lambda w: w.floor_at("center"),
        "floor_right": lambda w: w.floor_at("right"), "light_left": lambda w: w.light_at("left"),
        "light_right": lambda w: w.light_at("right"), "heading": lambda w: round(_wrap(math.degrees(w.th)), 1),
        "encoder_left": lambda w: w.encoders_cm()[0], "encoder_right": lambda w: w.encoders_cm()[1],
        "bumper": lambda w: int(w.bump),
    }

    def use(self, channel):
        if channel not in self.used:
            self.used.append(channel)
            n = len(self.frames["t"])
            self.frames["s:" + channel] = [None] * n

    def record(self):
        f = self.frames
        f["t"].append(round(self.t, 3))
        f["x"].append(round(self.x, 2))
        f["y"].append(round(self.y, 2))
        f["h"].append(round(math.degrees(self.th), 1))
        f["pl"].append(round(self.pl))
        f["pr"].append(round(self.pr))
        if self.blocks:
            f["blocks"].append([[round(b["x"], 1), round(b["y"], 1)] for b in self.blocks])
        noise, self.noise = self.noise, 0.0      # telemetry shows the clean value
        try:
            for ch in self.used:
                f["s:" + ch].append(self.CHANNELS[ch](self))
        finally:
            self.noise = noise
        for name, v in self.plots.items():
            f["p:" + name].append(v)

    def plot(self, name, value):
        key = "p:" + name
        if key not in self.frames:
            if len(self.plots) >= 6:
                raise RobotError("You can plot at most 6 different things at once.")
            self.frames[key] = [None] * len(self.frames["t"])
        self.plots[name] = round(value, 3)

    def event(self, kind, **kw):
        self.events.append({"t": round(self.t, 3), "type": kind, **kw})

    def warn_once(self, key, text):
        if key not in self.warned:
            self.warned.add(key)
            self.event("warn", text=text)

    # ----- results ------------------------------------------------------------
    def summary(self):
        st = self.st
        return {
            "time": round(self.t, 2), "x": round(self.x, 2), "y": round(self.y, 2),
            "heading": round(_wrap(math.degrees(self.th)), 1),
            "crashes": st["crashes"], "distance": round(st["distance"], 1),
            "gems": sum(1 for g in self.gems if g["got"] is not None), "gems_total": len(self.gems),
            "line_ratio": round(st["line_ticks"] / st["moving_ticks"], 3) if st["moving_ticks"] else 0.0,
            "zone_time": {k: round(v, 2) for k, v in st["zone_time"].items()},
            "visited": list(st["visited"]),
            "zone_now": [z["name"] for z in self._zones_at(self.x, self.y)],
            "laps": st["laps"], "lap_times": st["lap_times"],
            "min_gap": round(st["min_gap"], 1) if st["min_gap"] < 1e8 else None,
            "max_speed": round(st["max_speed"], 1),
            "moving_time": round(st["moving_ticks"] * DT, 2),
            "last_move_t": round(st["last_move_t"], 2),
            "blocks": [{"x": round(b["x"], 1), "y": round(b["y"], 1), "color": b["color"], "held": b["held"],
                        "zones": [z["name"] for z in self._zones_at(b["x"], b["y"])]} for b in self.blocks],
            "held": self.blocks[self.held]["color"] if self.held is not None else None,
            "sensors_used": list(self.used),
        }


# ---------------------------------------------------------------------------
# the learner-facing robot
# ---------------------------------------------------------------------------
class Robot:
    """Your robot! Motors, sensors, lights and sounds.

    Movement:   drive(left, right)  stop()  forward(cm)  backward(cm)  turn(degrees)
                turn_left(degrees)  turn_right(degrees)  wait(seconds)
    Sensors:    distance(direction)  bumper()  floor(which)  floor_left()  floor_right()
                color()  light(which)  heading()  encoders()  reset_encoders()  camera()
                position()  time()
    Fun:        led(color)  say(text)  beep(pitch, seconds)  pen_down(color)  pen_up()  plot(name, value)
    Gripper:    grab()  release()  holding()
    """

    def __init__(self, world):
        self._w = world

    def __repr__(self):
        return "<your robot 🤖>"

    # ----- movement -----
    def _power(self, v, name):
        v = _num(v, name, "robot.drive(50, 50)")
        if v > 100 or v < -100:
            self._w.warn_once(f"pow{name}", f"Motor power {v:g} is too much — motors only go from -100 to 100, so I used {max(-100, min(100, v)):g}.")
        return max(-100.0, min(100.0, v))

    def drive(self, left, right):
        """Set the left and right motor power (-100 … 100). The robot keeps driving until you change it."""
        self._w.pl = self._power(left, "drive() left power")
        self._w.pr = self._power(right, "drive() right power")
        self._w.cost()

    def stop(self):
        """Turn both motors off."""
        self._w.pl = self._w.pr = 0.0
        self._w.cost()

    def wait(self, seconds):
        """Let time pass (the motors keep doing what you told them)."""
        s = _num(seconds, "wait()", "robot.wait(1.5)")
        if s < 0:
            raise RobotError("wait() can't go back in time! Use a positive number of seconds.")
        self._w.advance(s)

    def forward(self, cm, power=50):
        """Drive straight for about `cm` centimetres (timed, then stop)."""
        cm = _num(cm, "forward()", "robot.forward(30)")
        self._straight(cm, power)

    def backward(self, cm, power=50):
        cm = _num(cm, "backward()", "robot.backward(30)")
        self._straight(-cm, power)

    def _straight(self, cm, power):
        power = abs(self._power(power, "power"))
        if power < 1:
            raise RobotError("forward() needs some power to move, e.g. power=50.")
        if abs(cm) < 1e-9:
            return
        speed = power / 100 * MAX_SPEED
        n = max(1, math.ceil(abs(cm) / speed / DT - 1e-9))
        p = abs(cm) / (n * DT) / MAX_SPEED * 100 * (1 if cm > 0 else -1)
        w = self._w
        w.pl = w.pr = p
        w.pending = 0.0
        for _ in range(n):
            w.tick()
        w.pl = w.pr = 0.0

    def turn(self, degrees, power=40):
        """Spin on the spot. Positive = left (counter-clockwise), negative = right."""
        deg = _num(degrees, "turn()", "robot.turn(90)")
        power = abs(self._power(power, "power"))
        if power < 1:
            raise RobotError("turn() needs some power, e.g. power=40.")
        if abs(deg) < 1e-9:
            return
        v = power / 100 * MAX_SPEED
        omega = 2 * v / WHEEL_BASE
        rad = math.radians(abs(deg))
        n = max(1, math.ceil(rad / omega / DT - 1e-9))
        v_exact = rad / (n * DT) * WHEEL_BASE / 2
        p = v_exact / MAX_SPEED * 100
        w = self._w
        w.pl, w.pr = (-p, p) if deg > 0 else (p, -p)
        w.pending = 0.0
        for _ in range(n):
            w.tick()
        w.pl = w.pr = 0.0

    def turn_left(self, degrees=90, power=40):
        self.turn(abs(_num(degrees, "turn_left()", "robot.turn_left(90)")), power)

    def turn_right(self, degrees=90, power=40):
        self.turn(-abs(_num(degrees, "turn_right()", "robot.turn_right(90)")), power)

    # ----- sensors -----
    def distance(self, direction="front"):
        """Ultrasonic distance in cm to the nearest wall or block (max 200).
        direction: "front", "left", "right", "front_left", "front_right" or "back"."""
        if direction not in DIRECTIONS:
            raise RobotError(f"There's no distance sensor called {direction!r}. Try one of: "
                             + ", ".join(repr(d) for d in DIRECTIONS))
        self._w.use("distance_" + direction)
        self._w.cost()
        return self._w.ray(DIRECTIONS[direction])

    def bumper(self):
        """True while the front bumper is pressed against something."""
        self._w.use("bumper")
        self._w.cost()
        return self._w.bump

    def floor(self, which="center"):
        """Reflected light from the floor, 0 (black) … 100 (white). which: "left", "center" or "right"."""
        if which not in FLOOR_SENSORS:
            raise RobotError(f"There's no floor sensor called {which!r}. Use 'left', 'center' or 'right'.")
        self._w.use("floor_" + which)
        self._w.cost()
        return self._w.floor_at(which)

    def floor_left(self):
        return self.floor("left")

    def floor_right(self):
        return self.floor("right")

    def color(self):
        """The colour of the floor under the robot: 'white', 'black', 'red', 'green', 'blue', 'yellow', …"""
        self._w.cost()
        return self._w.color_at()

    def light(self, which="left"):
        """Brightness 0 … 100 seen by the 'left' or 'right' light sensor."""
        if which not in LIGHT_SENSORS:
            raise RobotError(f"There's no light sensor called {which!r}. Use 'left' or 'right'.")
        self._w.use("light_" + which)
        self._w.cost()
        return self._w.light_at(which)

    def light_left(self):
        return self.light("left")

    def light_right(self):
        return self.light("right")

    def heading(self):
        """Compass heading in degrees: 0 = east (→), 90 = north (↑), 180 / -180 = west, -90 = south."""
        self._w.use("heading")
        self._w.cost()
        return self._w.heading_deg()

    def encoders(self):
        """(left_cm, right_cm): how far each wheel has rolled since the start (or reset_encoders())."""
        self._w.use("encoder_left")
        self._w.use("encoder_right")
        self._w.cost()
        return self._w.encoders_cm()

    def reset_encoders(self):
        self._w.enc_zero = list(self._w.enc)
        self._w.cost()

    def camera(self):
        """Things the camera sees (30° either side, up to 160 cm), nearest first. Each is a dict:
        {"kind": "block" or "gem", "color": ..., "angle": degrees (+ = left), "distance": cm}"""
        self._w.cost()
        return self._w.camera()

    def position(self):
        """(x, y) in cm — only in arenas that have GPS."""
        if not self._w.a["gps"]:
            raise RobotError("This arena has no GPS — and neither do most real indoor robots! "
                             "Use your encoders and heading to work out where you are.")
        self._w.cost()
        return (round(self._w.x, 1), round(self._w.y, 1))

    def time(self):
        """Seconds since the program started (robot time)."""
        self._w.cost()
        return round(self._w.t, 3)

    # ----- fun -----
    def led(self, color="off"):
        """Light up the robot's LED: 'red', 'green', 'blue', 'yellow', 'purple', 'white' or 'off'."""
        if color is None:
            color = "off"
        if not isinstance(color, str):
            raise RobotError("led() needs a colour name, like robot.led('green').")
        self._w.event("led", color=color.lower())
        self._w.cost()

    def say(self, text):
        """Show a speech bubble for 2 seconds."""
        self._w.event("say", text=str(text)[:80])
        self._w.cost()

    def beep(self, pitch=880, seconds=0.15):
        """Play a beep. pitch in Hz (200 … 2000)."""
        p = _num(pitch, "beep()", "robot.beep(440)")
        s = _num(seconds, "beep()", "robot.beep(440, 0.2)")
        self._w.event("beep", freq=max(100, min(3000, p)), dur=max(0.02, min(2.0, s)))
        self._w.cost()

    def pen_down(self, color="black"):
        """Lower a pen so the robot draws where it drives."""
        self._w.pen = True
        self._w.event("pen", down=True, color=str(color))
        self._w.cost()

    def pen_up(self):
        self._w.pen = False
        self._w.event("pen", down=False)
        self._w.cost()

    def plot(self, name, value):
        """Draw your own line on the telemetry graph, e.g. robot.plot("error", error)."""
        v = _num(value, "plot()", 'robot.plot("error", error)')
        self._w.plot(str(name)[:20], v)

    # ----- gripper -----
    def _need_gripper(self):
        if not self._w.a["gripper"]:
            raise RobotError("This robot has no gripper fitted in this arena.")

    def grab(self):
        """Close the gripper. Returns True if it caught a block right in front of the robot."""
        self._need_gripper()
        w = self._w
        w.cost()
        if w.held is not None:
            return True
        gx, gy = w._grip_point()
        best, bi = 4.5, None
        for i, b in enumerate(w.blocks):
            d = math.hypot(b["x"] - gx, b["y"] - gy)
            if d < best:
                best, bi = d, i
        w.event("grip", closed=True, got=bi is not None)
        if bi is None:
            return False
        w.held = bi
        w.blocks[bi]["held"] = True
        return True

    def release(self):
        """Open the gripper and drop whatever it holds."""
        self._need_gripper()
        w = self._w
        w.cost()
        if w.held is not None:
            w.blocks[w.held]["held"] = False
            w.held = None
        w.event("grip", closed=False)

    def holding(self):
        """The colour of the block in the gripper, or None."""
        self._need_gripper()
        self._w.cost()
        return self._w.blocks[self._w.held]["color"] if self._w.held is not None else None


# ---------------------------------------------------------------------------
# the arm world (side view)
# ---------------------------------------------------------------------------
BS = 8.0            # arm blocks are 8 cm cubes
SERVO_SPEED = 120.0  # degrees per second


def normalize_arm(spec):
    a = {
        "type": "arm",
        "name": spec.get("name", "Arm lab"),
        "size": list(spec.get("size", [160, 100])),
        "base": list(spec.get("base", [40, 12])),
        "links": list(spec.get("links", [45, 35])),
        "start": list(spec.get("start", [90, -90])),
        "blocks": [{"x": float(b["x"]), "color": b.get("color", "red"), "y": float(b.get("y", 0))}
                   for b in spec.get("blocks", [])],
        "targets": [{"name": t.get("name", t.get("color", "target")), "x": float(t["x"]), "w": float(t.get("w", 14)),
                     "color": t.get("color", "green")} for t in spec.get("targets", [])],
        "marks": [list(m) for m in spec.get("marks", [])],   # [[x, y, "label"]] dots to point at
        "time_limit": float(min(MAX_TIME, spec.get("time_limit", 60))),
        "noise": float(spec.get("noise", 0.0)),
    }
    return a


class ArmWorld:
    kind = "arm"

    def __init__(self, spec, seed=12345):
        self.a = normalize_arm(spec)
        a = self.a
        self.rng = random.Random(seed)
        self.s, self.e = float(a["start"][0]), float(a["start"][1])
        self.ts, self.te = self.s, self.e
        self.t = 0.0
        self.ticks = 0
        self.pending = 0.0
        self.blocks = [{"x": b["x"], "y": b["y"], "color": b["color"], "held": False} for b in a["blocks"]]
        self._settle_all()
        self.held = None
        self.events = []
        self.frames = {"t": [], "s": [], "e": [], "blocks": []}
        self.used = []
        self.plots = {}
        self.output_chars = 0
        self.warned = set()
        self.touching = False
        self.st = {"crashes": 0, "path": 0.0, "grabs": 0}
        self.record()

    def hand_xy(self, s=None, e=None):
        s = self.s if s is None else s
        e = self.e if e is None else e
        bx, by = self.a["base"]
        L1, L2 = self.a["links"]
        r1, r2 = math.radians(s), math.radians(s + e)
        ex, ey = bx + L1 * math.cos(r1), by + L1 * math.sin(r1)
        return (ex + L2 * math.cos(r2), ey + L2 * math.sin(r2)), (ex, ey)

    def cost(self):
        self.pending += CALL_COST_TICKS
        if self.pending >= 1:
            self.pending -= 1
            self.tick()

    def advance(self, seconds):
        n = max(1, int(round(seconds / DT)))
        self.pending = 0.0
        for _ in range(n):
            self.tick()

    def moving(self):
        return abs(self.ts - self.s) > 1e-6 or abs(self.te - self.e) > 1e-6

    def _blocked(self, s, e):
        (hx, hy), (ex, ey) = self.hand_xy(s, e)
        if hy < 0.5 or ey < 0.5:
            return True
        for i, b in enumerate(self.blocks):
            if b["held"]:
                continue
            if b["x"] - BS / 2 - 0.5 < hx < b["x"] + BS / 2 + 0.5 and b["y"] + 0.5 < hy < b["y"] + BS - 0.5:
                return True
        if self.held is not None:
            hb = self.blocks[self.held]
            bottom = hy - BS
            if bottom < -0.01:
                return True
            for i, b in enumerate(self.blocks):
                if i == self.held or b["held"]:
                    continue
                if abs(b["x"] - hx) < BS - 0.5 and bottom < b["y"] + BS - 0.5 and hy > b["y"] + 0.5:
                    return True
        return False

    def tick(self):
        step = SERVO_SPEED * DT
        ns = self.s + max(-step, min(step, self.ts - self.s))
        ne = self.e + max(-step, min(step, self.te - self.e))
        if (ns, ne) != (self.s, self.e):
            if self._blocked(ns, ne):
                if not self.touching:
                    self.st["crashes"] += 1
                    (hx, hy), _ = self.hand_xy()
                    self.events.append({"t": round(self.t, 3), "type": "crash", "x": round(hx, 1), "y": round(hy, 1)})
                self.touching = True
                self.ts, self.te = self.s, self.e       # a servo that is blocked stalls
            else:
                (ox, oy), _ = self.hand_xy()
                self.s, self.e = ns, ne
                (hx, hy), _ = self.hand_xy()
                self.st["path"] += math.hypot(hx - ox, hy - oy)
                self.touching = False
        if self.held is not None:
            (hx, hy), _ = self.hand_xy()
            b = self.blocks[self.held]
            b["x"], b["y"] = hx, hy - BS
        self.t = round(self.t + DT, 6)
        self.ticks += 1
        if self.ticks % FRAME_EVERY == 0:
            self.record()
        if self.t >= self.a["time_limit"] - 1e-9:
            raise TimeUp()

    def _support(self, i):
        b = self.blocks[i]
        top = 0.0
        for j, o in enumerate(self.blocks):
            if j == i or o["held"]:
                continue
            if abs(o["x"] - b["x"]) < BS - 0.01 and o["y"] + BS <= b["y"] + 1e-6:
                top = max(top, o["y"] + BS)
        return top

    def _settle_all(self):
        order = sorted(range(len(self.blocks)), key=lambda i: self.blocks[i]["y"])
        for i in order:
            if not self.blocks[i]["held"]:
                self.blocks[i]["y"] = self._support(i)

    def record(self):
        f = self.frames
        f["t"].append(round(self.t, 3))
        f["s"].append(round(self.s, 2))
        f["e"].append(round(self.e, 2))
        f["blocks"].append([[round(b["x"], 1), round(b["y"], 1)] for b in self.blocks])
        for name, v in self.plots.items():
            f["p:" + name].append(v)

    def plot(self, name, value):
        key = "p:" + name
        if key not in self.frames:
            if len(self.plots) >= 6:
                raise RobotError("You can plot at most 6 different things at once.")
            self.frames[key] = [None] * len(self.frames["t"])
        self.plots[name] = round(value, 3)

    def event(self, kind, **kw):
        self.events.append({"t": round(self.t, 3), "type": kind, **kw})

    def warn_once(self, key, text):
        if key not in self.warned:
            self.warned.add(key)
            self.event("warn", text=text)

    def summary(self):
        (hx, hy), _ = self.hand_xy()
        blocks = []
        for b in self.blocks:
            tg = [t["name"] for t in self.a["targets"] if abs(b["x"] - t["x"]) <= t["w"] / 2 and not b["held"]]
            blocks.append({"x": round(b["x"], 1), "y": round(b["y"], 1), "color": b["color"], "held": b["held"],
                           "targets": tg, "level": int(round(b["y"] / BS))})
        return {"time": round(self.t, 2), "shoulder": round(self.s, 1), "elbow": round(self.e, 1),
                "hand": [round(hx, 1), round(hy, 1)], "crashes": self.st["crashes"], "path": round(self.st["path"], 1),
                "blocks": blocks, "held": self.blocks[self.held]["color"] if self.held is not None else None,
                "tower": max([int(round(b["y"] / BS)) + 1 for b in self.blocks if not b["held"]] or [0]),
                "grabs": self.st["grabs"], "sensors_used": []}


class Arm:
    """Your robot arm! Two joints (shoulder and elbow) and a gripper.

    shoulder angle: 0 = pointing right, 90 = straight up (0 … 180)
    elbow angle:    bend relative to the upper arm, 0 = straight (-160 … 160, + = bends up/left)
    Movement:   move(shoulder, elbow)  shoulder(angle)  elbow(angle)  set(shoulder, elbow)  wait(seconds)
    Info:       angles()  hand()  links()  time()  is_moving()
    Gripper:    grab()  release()  holding()
    Fun:        say(text)  beep(pitch, seconds)  plot(name, value)
    """

    def __init__(self, world):
        self._w = world

    def __repr__(self):
        return "<your robot arm 🦾>"

    def _angles(self, s, e):
        s = _num(s, "shoulder angle", "arm.move(90, -45)")
        e = _num(e, "elbow angle", "arm.move(90, -45)")
        cs, ce = max(0.0, min(180.0, s)), max(-160.0, min(160.0, e))
        if (cs, ce) != (s, e):
            self._w.warn_once(f"lim{s}{e}", f"Joints have limits (shoulder 0…180, elbow -160…160) — I used ({cs:g}, {ce:g}).")
        return cs, ce

    def set(self, shoulder, elbow):
        """Start moving the joints toward these angles (doesn't wait)."""
        self._w.ts, self._w.te = self._angles(shoulder, elbow)
        self._w.cost()

    def move(self, shoulder, elbow):
        """Move both joints to these angles and wait until they get there."""
        self._w.ts, self._w.te = self._angles(shoulder, elbow)
        self._w.pending = 0.0
        guard = 0
        while self._w.moving() and guard < 2000:
            self._w.tick()
            guard += 1

    def shoulder(self, angle):
        self.move(angle, self._w.te)

    def elbow(self, angle):
        self.move(self._w.ts, angle)

    def wait(self, seconds):
        s = _num(seconds, "wait()", "arm.wait(1)")
        if s < 0:
            raise RobotError("wait() needs a positive number of seconds.")
        self._w.advance(s)

    def angles(self):
        """(shoulder, elbow) right now."""
        self._w.cost()
        return (round(self._w.s, 1), round(self._w.e, 1))

    def hand(self):
        """(x, y) of the gripper, in cm. The table top is y = 0."""
        self._w.cost()
        (hx, hy), _ = self._w.hand_xy()
        return (round(hx, 1), round(hy, 1))

    def links(self):
        """(upper arm length, forearm length) in cm, and the base is at arm.base()."""
        return tuple(self._w.a["links"])

    def base(self):
        return tuple(self._w.a["base"])

    def is_moving(self):
        self._w.cost()
        return self._w.moving()

    def time(self):
        self._w.cost()
        return round(self._w.t, 3)

    def grab(self):
        """Close the gripper. Returns True if it caught the top of a block."""
        w = self._w
        w.cost()
        if w.held is not None:
            return True
        (hx, hy), _ = w.hand_xy()
        for i, b in enumerate(w.blocks):
            on_top = any(j != i and not o["held"] and abs(o["x"] - b["x"]) < BS and abs(o["y"] - (b["y"] + BS)) < 0.5
                         for j, o in enumerate(w.blocks))
            if abs(hx - b["x"]) <= BS / 2 + 1 and abs(hy - (b["y"] + BS)) <= 3.5 and not on_top:
                w.held = i
                b["held"] = True
                w.st["grabs"] += 1
                w.event("grip", closed=True, got=True)
                return True
        w.event("grip", closed=True, got=False)
        return False

    def release(self):
        """Open the gripper; the block drops onto whatever is below it."""
        w = self._w
        w.cost()
        if w.held is not None:
            i = w.held
            w.blocks[i]["held"] = False
            w.held = None
            w.blocks[i]["y"] = w._support(i)
            w.event("drop", i=i)
        w.event("grip", closed=False)

    def holding(self):
        self._w.cost()
        return self._w.blocks[self._w.held]["color"] if self._w.held is not None else None

    def say(self, text):
        self._w.event("say", text=str(text)[:80])
        self._w.cost()

    def beep(self, pitch=880, seconds=0.15):
        p = _num(pitch, "beep()", "arm.beep(440)")
        s = _num(seconds, "beep()", "arm.beep(440, 0.2)")
        self._w.event("beep", freq=max(100, min(3000, p)), dur=max(0.02, min(2.0, s)))
        self._w.cost()

    def led(self, color="off"):
        self._w.event("led", color=str(color or "off").lower())
        self._w.cost()

    def plot(self, name, value):
        v = _num(value, "plot()", 'arm.plot("x", x)')
        self._w.plot(str(name)[:20], v)


# ---------------------------------------------------------------------------
# running a learner program
# ---------------------------------------------------------------------------
def make_world(arena, seed=12345):
    return ArmWorld(arena, seed) if (arena or {}).get("type") == "arm" else World(arena, seed)


class _Out:
    def __init__(self, world, sink):
        self.w = world
        self.sink = sink

    def write(self, s):
        if not s:
            return 0
        self.w.output_chars += len(s)
        if self.w.output_chars > MAX_OUTPUT:
            raise OutputFlood()
        self.sink.append((round(self.w.t, 3), s))
        return len(s)

    def flush(self):
        pass

    def isatty(self):
        return False


def run_program(source, arena, seed=12345, extra_globals=None):
    """Run learner code in a fresh world. Returns (world, info) where info has output/error/end_reason/hints."""
    world = make_world(arena, seed)
    out = []
    info = {"end_reason": "done", "error": None, "output": "", "prints": [], "hints": []}
    g = {"__name__": "__main__"}
    if world.kind == "arm":
        g["arm"] = Arm(world)
    else:
        g["robot"] = Robot(world)
    if extra_globals:
        g.update(extra_globals)
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = _Out(world, out)
    random.seed(seed)          # the learner's own `import random` is repeatable for a given seed too
    try:
        code = compile(source, "main.py", "exec")
        exec(code, g)
    except TimeUp:
        info["end_reason"] = "time_limit"
    except OutputFlood:
        info["end_reason"] = "output_limit"
        info["error"] = {"type": "OutputFlood", "msg": "your program printed way too much — is print() inside a fast loop?",
                         "line": None, "code_line": "", "text": "OutputFlood"}
    except SystemExit:
        pass
    except KeyboardInterrupt:
        info["end_reason"] = "stopped"
    except BaseException as e:  # noqa: BLE001 - report every crash kindly
        info["end_reason"] = "error"
        info["error"] = describe_error(e, source)
    finally:
        sys.stdout, sys.stderr = old_out, old_err
    if world.kind == "drive":
        moving_at_end = world.pl or world.pr
        world.pl = world.pr = 0.0
        if info["end_reason"] == "done" and moving_at_end and world.t < 0.2:
            info["hints"].append("Your program ended right after switching the motors on, so the robot never "
                                 "had time to move. Add robot.wait(2) after robot.drive(…) to let it drive!")
        elif info["end_reason"] == "done" and moving_at_end:
            info["hints"].append("The motors were still on when your program ended, so the robot stopped there. "
                                 "(Robots stop when their program finishes.)")
    if world.frames["t"][-1] != round(world.t, 3):
        world.record()
    elif world.kind == "drive":
        world.frames["pl"][-1] = 0          # the robot stops when the program ends
        world.frames["pr"][-1] = 0
    info["output"] = "".join(s for _, s in out)
    info["prints"] = [[t, s] for t, s in out][:2000]
    if info["end_reason"] == "time_limit":
        info["hints"].append(f"⏱ Time's up — this arena runs for {world.a['time_limit']:g} seconds.")
    return world, info


def describe_error(e, source):
    line = getattr(e, "lineno", None) if isinstance(e, SyntaxError) else None
    if line is None:
        for fr in reversed(traceback.extract_tb(e.__traceback__)):
            if fr.filename == "main.py":
                line = fr.lineno
                break
    lines = source.splitlines()
    code_line = lines[line - 1] if line and 0 < line <= len(lines) else ""
    exc_only = "".join(traceback.TracebackException.from_exception(e).format_exception_only()).strip()
    msg = e.msg if isinstance(e, SyntaxError) else str(e)
    return {"type": type(e).__name__, "msg": msg, "line": line, "code_line": code_line, "text": exc_only}


def result_payload(world, info, include_frames=True):
    """JSON-safe dict for the browser."""
    out = {"kind": world.kind, "arena": public(world.a), "summary": world.summary(), "events": world.events[:4000],
           "end_reason": info["end_reason"], "error": info["error"], "output": info["output"][-20000:],
           "prints": info["prints"], "hints": info["hints"], "used": list(world.used),
           "plots": list(world.plots.keys())}
    if include_frames:
        out["frames"] = world.frames
    return out
