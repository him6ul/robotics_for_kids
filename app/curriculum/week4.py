"""Week 4 — Know where you are: encoders, gyros, dead reckoning and state machines."""
import math

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _road(pts, stations, closed=True, gap=20, width=2.5):
    """Black-tape road through `pts` with a gap (a coloured station zone) at every station.

    stations: [(name, color, x, y, label)] — each point must lie on a horizontal or vertical piece of road.
    Returns (lines, zones) ready for an arena dict.
    """
    P = [list(p) for p in pts] + ([list(pts[0])] if closed else [])
    zones = []
    for (name, color, sx, sy, label) in stations:
        for a, b in zip(P, P[1:]):
            if a[1] == b[1] == sy and min(a[0], b[0]) < sx < max(a[0], b[0]):
                zones.append({"name": name, "rect": [sx - gap / 2, sy - 15, gap, 30], "color": color, "label": label})
                break
            if a[0] == b[0] == sx and min(a[1], b[1]) < sy < max(a[1], b[1]):
                zones.append({"name": name, "rect": [sx - 15, sy - gap / 2, 30, gap], "color": color, "label": label})
                break
        else:
            raise ValueError(f"station {name} is not on a straight piece of road")
    lines, cur = [], [P[0]]
    for a, b in zip(P, P[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        cuts = []
        for (_n, _c, sx, sy, _l) in stations:
            t = (sx - a[0]) * ux + (sy - a[1]) * uy
            if 0 < t < L and abs((sx - a[0]) * uy - (sy - a[1]) * ux) < 1e-6:
                cuts.append(t)
        for t in sorted(cuts):
            cur.append([a[0] + ux * (t - gap / 2), a[1] + uy * (t - gap / 2)])
            lines.append({"pts": cur, "width": width})
            cur = [[a[0] + ux * (t + gap / 2), a[1] + uy * (t + gap / 2)]]
        cur.append(list(b))
    if closed and lines:
        lines[0]["pts"] = cur[:-1] + lines[0]["pts"]     # join the last piece onto the first
    else:
        lines.append({"pts": cur, "width": width})
    return lines, zones


# A check prelude: "is robot.<name>() called inside a loop?"
LOOP_HELPER = '''import ast as _ast
def in_loop(name):
    for n in _ast.walk(tree):
        if isinstance(n, (_ast.While, _ast.For)):
            for c in _ast.walk(n):
                if isinstance(c, _ast.Call) and getattr(c.func, "attr", getattr(c.func, "id", "")) == name:
                    return True
    return False
'''

# A check prelude for the delivery robot: where did the robot stand still, and for how long?
STOP_HELPER = '''def stops(r, min_s=1.0):
    t, xs, ys = r.frames["t"], r.frames["x"], r.frames["y"]
    out, i = [], 0
    while i < len(t) - 1:
        j = i
        while j + 1 < len(t) and abs(xs[j + 1] - xs[i]) < 0.05 and abs(ys[j + 1] - ys[i]) < 0.05:
            j += 1
        if t[j] - t[i] >= min_s:
            out.append((xs[i], ys[i], t[i], t[j] - t[i]))
        i = j + 1
    return out

def near(x, y, zone_name, arena_, pad=12):
    z = next(z for z in arena_["zones"] if z["name"] == zone_name)
    zx, zy, zw, zh = z["rect"]
    return zx - pad <= x <= zx + zw + pad and zy - pad <= y <= zy + zh + pad

def stopped_at(r, zone_name, arena_, min_s=1.0):
    return any(near(x, y, zone_name, arena_) for (x, y, t0, d) in stops(r, min_s))
'''

# ---------------------------------------------------------------------------
# arenas — Precision Pilot (noisy!)
# ---------------------------------------------------------------------------
NOISE = 0.6

DRIFT_LAB = {"name": "Drift Lab", "size": [260, 200], "start": [30, 100, 0], "time_limit": 15, "noise": NOISE,
             "zones": [{"name": "finish", "rect": [110, 40, 90, 120], "color": "green", "label": "finish area"}],
             "lines": [{"pts": [[30, 100], [150, 100]], "width": 0.8}],
             "labels": [[30, 80, "start"], [150, 108, "straight ahead = 120 cm"]]}

LANE100 = {"name": "100 cm Lane", "size": [240, 180], "start": [30, 90, 0], "time_limit": 20, "noise": NOISE,
           "zones": [{"name": "mark", "rect": [126, 40, 8, 100], "color": "yellow", "label": "100 cm"}],
           "labels": [[30, 70, "start"]]}

COMPASS_LANE = {**LANE100, "name": "Compass Lane",
                "labels": [[30, 70, "start"], [130, 160, "N ↑ face north (90°)"]]}

CORRIDOR = {"name": "Long Corridor", "size": [320, 140], "start": [30, 70, 0], "time_limit": 30, "noise": NOISE,
            "boxes": [[60, 92, 190, 10], [60, 38, 190, 10]],
            "zones": [{"name": "dock", "rect": [250, 50, 40, 40], "color": "green", "label": "dock"}],
            "labels": [[30, 50, "start"], [155, 70, "240 cm, no walls touched!"]]}

TREASURE = {"name": "Treasure Run (no GPS)", "size": [280, 200], "start": [40, 40, 0], "time_limit": 50, "noise": NOISE,
            "zones": [{"name": "home", "rect": [20, 20, 40, 40], "color": "blue", "label": "🏠 (40, 40)"},
                      {"name": "treasure", "rect": [206, 126, 28, 28], "color": "yellow", "label": "💰 (220, 140)"}],
            "boxes": [[95, 135, 40, 40], [170, 25, 40, 40]]}

RALLY = {"name": "Waypoint Rally", "size": [320, 220], "start": [40, 40, 0], "time_limit": 90, "noise": 0.8,
         "zones": [{"name": "home", "rect": [20, 20, 40, 40], "color": "blue", "label": "🏠"},
                   {"name": "A", "rect": [246, 36, 28, 28], "color": "yellow", "label": "A (260, 50)"},
                   {"name": "B", "rect": [246, 156, 28, 28], "color": "orange", "label": "B (260, 170)"},
                   {"name": "C", "rect": [116, 146, 28, 28], "color": "purple", "label": "C (130, 160)"}],
         "boxes": [[140, 70, 50, 50]]}

MARS_YARD = {"name": "Mars Yard", "size": [340, 240], "start": [40, 40, 0], "time_limit": 180, "noise": 0.8,
             "zones": [{"name": "lander", "rect": [15, 15, 50, 50], "color": "blue", "label": "🚀 lander"}],
             "gems": [[120, 200], [300, 60], [300, 200], [200, 120], [80, 130]],
             "boxes": [[140, 40, 40, 30], [230, 150, 30, 40], [110, 150, 30, 20]]}

# ---------------------------------------------------------------------------
# Project 7 — Precision Pilot
# ---------------------------------------------------------------------------
PP_S1 = '''# 🧭 How straight is "straight"?
robot.forward(120)
# TODO: read the encoders and the compass, print them,
#       and make the robot say which way it drifted ("left" or "right")
'''

PP_S1_SOL = '''# 🧭 How straight is "straight"?
robot.forward(120)

left, right = robot.encoders()
print("left wheel rolled", left, "cm")
print("right wheel rolled", right, "cm")
h = robot.heading()
print("heading:", h)

if h > 0:
    robot.say("I drifted left")
else:
    robot.say("I drifted right")
'''

PP_S2 = PP_S1_SOL + '''
# TODO: new arena! Delete the forward(120) above and drive exactly 100 cm
#       with drive() + a while loop that watches the encoders
'''

PP_S2_SOL = '''# 📏 Drive exactly 100 cm, measured by the wheels
robot.reset_encoders()
robot.drive(50, 50)
travelled = 0
while travelled < 100:
    left, right = robot.encoders()
    travelled = (left + right) / 2     # the average of both wheels
    robot.wait(0.02)
robot.stop()
print("I drove", travelled, "cm")
'''

PP_S3 = PP_S2_SOL + '''
# TODO: turn to face north (heading 90) with a while loop on robot.heading()
'''

PP_S3_SOL = PP_S2_SOL + '''
# 🧭 Turn until the compass says 90 (north)
while robot.heading() < 90:
    error = 90 - robot.heading()
    if error > 30:
        robot.drive(-40, 40)      # far away: turn fast
    else:
        robot.drive(-10, 10)      # nearly there: creep
    robot.wait(0.02)
robot.stop()
print("heading now", robot.heading())
'''

PP_S4 = '''def drive_straight(cm, target):
    robot.reset_encoders()
    robot.drive(50, 50)
    travelled = 0
    while travelled < cm:
        # TODO: steer! error = target - heading, then change the two wheel powers
        left, right = robot.encoders()
        travelled = (left + right) / 2
        robot.wait(0.02)
    robot.stop()

drive_straight(240, 0)
'''

PP_S4_SOL = '''def drive_straight(cm, target):
    robot.reset_encoders()
    travelled = 0
    while travelled < cm:
        error = target - robot.heading()    # + means I'm pointing too far right
        steer = 2 * error                   # P control: Kp = 2
        robot.drive(50 - steer, 50 + steer)
        left, right = robot.encoders()
        travelled = (left + right) / 2
        robot.wait(0.02)
    robot.stop()

drive_straight(240, 0)
'''

PP_S5 = PP_S4_SOL + '''
# TODO: new arena, no GPS! Keep track of x and y with dead reckoning,
#       drive to the treasure at (220, 140) and come home to (40, 40)
'''

PP_S5_SOL = '''import math

x, y = 40, 40        # dead reckoning: where I THINK I am (cm)
last = 0             # the wheel distance I had last time round the loop
robot.reset_encoders()

for (tx, ty) in [(220, 140), (40, 40)]:
    while math.hypot(tx - x, ty - y) > 4:
        # 1. SENSE: how far did I roll since last time, and which way am I facing?
        left, right = robot.encoders()
        travelled = (left + right) / 2
        d = travelled - last
        last = travelled
        h = robot.heading()
        # 2. UPDATE my position (dead reckoning)
        x = x + d * math.cos(math.radians(h))
        y = y + d * math.sin(math.radians(h))
        # 3. THINK: which way is the target, and how wrong is my heading?
        want = math.degrees(math.atan2(ty - y, tx - x))
        error = (want - h + 180) % 360 - 180
        steer = max(-40, min(40, 1.5 * error))
        # 4. ACT
        robot.drive(45 - steer, 45 + steer)
        robot.wait(0.02)
    robot.stop()
    robot.beep()
    print("I think I'm at", round(x), round(y))
'''

PP_BOSS_SOL = '''import math

x, y = 40, 40
last = 0
robot.reset_encoders()

def go_to(tx, ty):
    global x, y, last
    while math.hypot(tx - x, ty - y) > 4:
        left, right = robot.encoders()
        travelled = (left + right) / 2
        d = travelled - last
        last = travelled
        h = robot.heading()
        x = x + d * math.cos(math.radians(h))
        y = y + d * math.sin(math.radians(h))
        want = math.degrees(math.atan2(ty - y, tx - x))
        error = (want - h + 180) % 360 - 180
        steer = max(-40, min(40, 1.5 * error))
        robot.drive(50 - steer, 50 + steer)
        robot.wait(0.02)
    robot.stop()

for (name, tx, ty) in [("A", 260, 50), ("B", 260, 170), ("C", 130, 160), ("home", 40, 40)]:
    go_to(tx, ty)
    robot.beep()
    robot.say("Waypoint " + name)
    print(name, "- I think I'm at", round(x), round(y))
'''

PP_S1_CHECK = '''expect(calls("encoders") >= 1, "After driving, read the wheel encoders: left, right = robot.encoders()")
expect(calls("heading") >= 1, "Read the compass too: h = robot.heading()")
expect(calls("print") >= 1, "print() the numbers so you can see them in the console.")
for seed, lab in ((1, "robot #1"), (2, "robot #2")):
    r = sim(seed=seed, label=lab)
    expect(r.crashes == 0, f"{lab} hit a wall. Just forward(120) this time — no extra moves needed.")
    expect(r.in_zone("finish"), f"{lab} ended at ({r.x:.0f}, {r.y:.0f}), outside the green finish area. Keep robot.forward(120).")
    expect(any(ch.isdigit() for ch in r.output), "I don't see any numbers in the console. print(left, right) and print(h).")
    way = "left" if r.heading > 0 else "right"
    other = "right" if way == "left" else "left"
    expect(r.said(), f"{lab}: make the robot say which way it drifted, with robot.say(...).")
    expect(r.said(way) and not r.said(other), f"{lab} curved to the {way} (it ended facing {r.heading:+.0f}°) but its bubble said something else. "
           "Positive heading = it turned left, negative = right. Use an if on the heading!")
SUCCESS = "You caught the drift! Same program, two robots, two different curves. 🕵️"
'''

PP_S2_CHECK = LOOP_HELPER + '''expect(calls("forward") == 0, "No robot.forward() in this mission — drive with robot.drive(...) and let the encoders tell you when to stop.")
expect(calls("encoders") >= 1 and in_loop("encoders"), "Read robot.encoders() INSIDE a while loop, so the robot keeps checking how far it has gone.")
for seed, lab in ((1, "robot #1"), (2, "robot #2"), (5, "robot #3")):
    r = sim(seed=seed, label=lab)
    expect(r.crashes == 0, f"{lab} crashed. Stop after 100 cm!")
    expect(r.distance > 20, f"{lab} hardly moved ({r.distance:.0f} cm). Start the motors with robot.drive(50, 50) before the loop.")
    expect(r.stopped, f"{lab} was still driving at the end. After the loop, robot.stop().")
    expect(abs(r.distance - 100) <= 3, f"{lab} rolled {r.distance:.0f} cm, but the target is 100 cm (±3). "
           "Keep looping while the average of the two encoders is less than 100.")
SUCCESS = "100 cm on the nose — measured by the wheels themselves! 📏"
'''

PP_S3_CHECK = LOOP_HELPER + '''expect(calls("heading") >= 1 and in_loop("heading"), "Read robot.heading() inside a while loop and keep turning until it says 90.")
expect(calls("encoders") >= 1, "Keep your 100 cm encoder drive at the start.")
for seed, lab in ((1, "robot #1"), (2, "robot #2"), (5, "robot #3")):
    r = sim(seed=seed, label=lab)
    expect(r.crashes == 0, f"{lab} crashed.")
    expect(abs(r.distance - 100) <= 6, f"{lab} rolled {r.distance:.0f} cm. First drive 100 cm with the encoders, then turn on the spot.")
    expect(r.stopped, f"{lab} was still moving at the end. robot.stop() after the turn.")
    hs, ts = r.series("h"), r.series("t")
    rates = [abs(hs[i + 1] - hs[i]) / (ts[i + 1] - ts[i]) for i in range(len(hs) - 1)]
    spin = [i for i, v in enumerate(rates) if v > 3]
    final = max([rates[i] for i in spin if ts[i] >= ts[spin[-1]] - 0.2] or [0]) if spin else 0
    expect(abs(r.heading - 90) <= 3, f"{lab} ended facing {r.heading:.1f}°, but north is 90° (±3). "
           + ("That's way off. After the wobbly drive the robot wasn't facing exactly 0°, so turn(90) misses. Keep turning until robot.heading() says 90."
              if abs(r.heading - 90) > 10 else "It overshot — slow down when the error gets small!" if r.heading > 90
              else "Keep turning until robot.heading() reaches 90."))
    expect(final <= 60, f"{lab} was still spinning at {final:.0f}°/s when it reached north. Like a lunar lander, slow down "
           "for the last part: when the error is small (under 30°), turn with low power like robot.drive(-10, 10).")
SUCCESS = "Due north! 🧭 The gyro doesn't care which way your robot drifted."
'''

PP_S4_CHECK = LOOP_HELPER + '''expect(calls("heading") >= 1 and in_loop("heading"), "Inside the driving loop, read robot.heading() and steer to fix the error.")
expect(calls("encoders") >= 1, "Keep using the encoders to know when you've gone 240 cm.")
for seed, lab in ((1, "robot #1"), (2, "robot #2"), (5, "robot #3")):
    r = sim(seed=seed, label=lab)
    ys = r.series("y")
    worst = max(abs(v - 70) for v in ys)
    expect(r.crashes == 0, f"{lab} scraped the corridor wall (it wandered {worst:.0f} cm off the middle line). "
           "Steer with the heading error: robot.drive(50 - steer, 50 + steer).")
    expect(worst <= 12, f"{lab} wandered {worst:.0f} cm off the middle line. Make the steering stronger (bigger Kp).")
    expect(r.in_zone("dock"), f"{lab} stopped at ({r.x:.0f}, {r.y:.0f}), not in the green dock. Drive 240 cm.")
SUCCESS = "Straight as a laser! That's feedback control beating the drift. 🎯"
'''

PP_S5_CHECK = '''expect(calls("encoders") >= 1 and calls("heading") >= 1, "Dead reckoning needs BOTH sensors: robot.encoders() for distance and robot.heading() for direction.")
expect(calls("cos") >= 1 and calls("sin") >= 1, "Update your position with trig: x += d * math.cos(...) and y += d * math.sin(...).")
for seed, lab in ((1, "robot #1"), (2, "robot #2"), (5, "robot #3")):
    r = sim(seed=seed, label=lab)
    expect(r.crashes == 0, f"{lab} bumped into something. Is your x, y estimate correct? print(x, y) to find out.")
    expect(r.visited("treasure"), f"{lab} never reached the 💰 treasure at (220, 140). Check your atan2(ty - y, tx - x).")
    expect(r.in_zone("home"), f"{lab} ended at ({r.x:.0f}, {r.y:.0f}), not back home at (40, 40).")
    expect(r.stopped, f"{lab} was still driving at the end. Stop when you're close to the target.")
SUCCESS = "There and back again — with no GPS! That's how rovers find their way. 🗺️"
'''

PP_BOSS_CHECK = '''expect(calls("encoders") >= 1 and calls("heading") >= 1, "Navigate with dead reckoning: encoders + heading.")
for seed, lab in ((1, "robot #1"), (2, "robot #2"), (5, "robot #3")):
    r = sim(seed=seed, label=lab)
    expect(r.crashes == 0, f"{lab} crashed {r.crashes} time(s). Plan straight legs that miss the rock.")
    got = [z for z in r.s.get("visited", []) if z in ("A", "B", "C")]
    expect(got == ["A", "B", "C"], f"{lab} visited {got or 'no waypoints'} — it must touch A, then B, then C.")
    expect(r.in_zone("home"), f"{lab} ended at ({r.x:.0f}, {r.y:.0f}). Finish back in the 🏠 zone.")
SUCCESS = "RALLY CHAMPION! Three waypoints, three robots, zero GPS. 🏆"
'''

PRECISION_PILOT = {
    "id": "precision_pilot", "week": 4, "order": 7, "title": "Precision Pilot", "emoji": "🧭",
    "tagline": "Wheel encoders, a gyro compass and some trig: know exactly where you are",
    "story": "Uh-oh: the lab robots have got a bit worn out. Their wheels aren't quite the same size any more, so "
             "when you tell them 'go straight', they curve! Real robots have this problem too. Your mission: "
             "teach Bolt to measure its own wheels and heading and correct itself, until it can find its way to "
             "treasure and back with no GPS at all.",
    "concepts": ["odometry", "feedback", "kinematics"],
    "expected_minutes": 120,
    "real_world": "Mars rovers count wheel turns and read gyros to work out where they are ('visual odometry' helps too), "
                  "because there's no GPS on Mars. Warehouse robots and robot lawn-mowers use exactly the same dead reckoning.",
    "build_it": "LEGO SPIKE motors have built-in encoders (motor degrees) and the hub has a gyro — the same programs work "
                "with 'motor position' and 'yaw angle' blocks. A micro:bit has a compass too!",
    "steps": [
        {
            "id": "s1", "title": "Spot the drift",
            "learn": "<p>Until now your programs were <b>open loop</b>: you tell the motors what to do and just hope it works "
                     "out. <code>forward(120)</code> doesn't measure anything, it just switches the motors on for the right "
                     "number of seconds.</p>"
                     "<p>Real robots are never perfect. One wheel is a tiny bit bigger, the battery is getting weak, the carpet "
                     "is thicker on one side, a tyre is slippery… So one wheel goes a little faster and the robot "
                     "<b>drifts</b> in a curve. In this arena the robots have worn wheels — and every robot is different!</p>"
                     "<p>Two new sensors help. <b>Wheel encoders</b> count how far each wheel really rolled. A <b>gyro / compass</b> "
                     "tells you which way you're facing:</p>"
                     "<pre>left, right = robot.encoders()   # two numbers at once, in cm\nprint(left, right)\n"
                     "h = robot.heading()               # 0 = east, + = turned left, - = turned right\nprint(h)</pre>"
                     "<p>The line <code>left, right = …</code> is Python <b>unpacking</b>: <code>encoders()</code> gives back a pair, and "
                     "Python puts the first number into <code>left</code> and the second into <code>right</code>.</p>",
            "task": "<p>Drive <code>forward(120)</code>, then <b>print</b> both encoder values and the heading. Then make the robot "
                    "<b>say which way it drifted</b>: if the heading is positive it curved <i>left</i>, if negative it curved "
                    "<i>right</i>. (Put the word <code>left</code> or <code>right</code> in the bubble — not both!) "
                    "Press ▶ Run a few times and look at the numbers. Which wheel rolled further?</p>",
            "goals": ["Print both encoders and the heading", "Say which way the robot drifted", "Works on two different robots"],
            "arena": DRIFT_LAB, "starter": PP_S1, "solution": PP_S1_SOL,
            "hints": ["left, right = robot.encoders() gives you both wheels. Then print(left, right).",
                      "The heading after driving tells you the drift: bigger than 0 means it turned left.",
                      "h = robot.heading()\nif h > 0:\n    robot.say(\"I drifted left\")\nelse:\n    robot.say(\"I drifted right\")"],
            "check": PP_S1_CHECK,
            "concepts": ["odometry", "sensors"], "xp": 20,
        },
        {
            "id": "s2", "title": "Exactly 100 cm",
            "learn": "<p>An encoder is a little disc on the motor shaft with slots in it. A light sensor counts the slots as "
                     "they flash past — so the robot knows how many times the wheel turned.</p>"
                     "<p>Turning into distance is circle maths: one full turn of a wheel rolls it one <b>circumference</b> "
                     "along the floor, <b>2 × π × r</b>. A wheel with radius 3 cm rolls 2 × 3.14 × 3 ≈ <b>18.8 cm</b> per turn. "
                     "Your robot does this maths for you and gives you centimetres.</p>"
                     "<p>If the wheels roll different amounts, which one is right? Neither! The middle of the robot travels the "
                     "<b>average</b>:</p>"
                     "<pre>robot.reset_encoders()      # start counting from 0\nrobot.drive(50, 50)\ntravelled = 0\n"
                     "while travelled &lt; 100:\n    left, right = robot.encoders()\n    travelled = (left + right) / 2\n"
                     "    robot.wait(0.02)\nrobot.stop()</pre>"
                     "<p>This is <b>closed loop</b>: sense → decide → act, again and again, until the job is done. It works even "
                     "if the battery is weak or the floor is sticky, because it <i>measures</i> instead of guessing.</p>",
            "task": "<p>Replace your <code>forward(120)</code> with an <b>encoder drive</b>: switch the motors on with "
                    "<code>drive()</code>, loop until the average of both encoders reaches <b>100 cm</b>, then stop and print how "
                    "far you went. (You can keep or delete the drift report.)</p>",
            "goals": ["No forward() — use drive()", "Read the encoders in a while loop", "Roll 100 cm (±3) on every robot"],
            "arena": LANE100, "starter": PP_S2, "solution": PP_S2_SOL,
            "hints": ["Start with robot.reset_encoders() and robot.drive(50, 50), then a while loop.",
                      "Inside the loop: left, right = robot.encoders() and travelled = (left + right) / 2.",
                      "while travelled < 100:\n    left, right = robot.encoders()\n    travelled = (left + right) / 2\n    robot.wait(0.02)\nrobot.stop()"],
            "check": PP_S2_CHECK,
            "concepts": ["odometry", "feedback", "kinematics"], "xp": 25,
        },
        {
            "id": "s3", "title": "Turn by the compass",
            "learn": "<p>Your robot has a <b>gyro</b>: a tiny chip that feels rotation (the same chip that flips the screen on "
                     "your phone). From it the robot works out its <b>heading</b>, like a compass: 0° = east →, 90° = north ↑, "
                     "-90° = south ↓, 180° = west ←.</p>"
                     "<p>After a wobbly 100 cm drive your robot might be pointing at 20° or -15°. So <code>turn(90)</code> would "
                     "NOT make it face north. Instead, keep turning <b>until the compass says 90</b>:</p>"
                     "<pre>while robot.heading() &lt; 90:\n    robot.drive(-40, 40)    # spin left\n    robot.wait(0.02)\nrobot.stop()</pre>"
                     "<p>One problem: at full speed the robot overshoots before the loop notices. A lunar lander slows down before "
                     "touch-down — do the same! Work out the <b>error</b> (how far is left to go) and turn slowly when it is small:</p>"
                     "<pre>error = 90 - robot.heading()\nif error &gt; 30:\n    robot.drive(-40, 40)   # far: fast\nelse:\n    robot.drive(-10, 10)   # close: creep</pre>",
            "task": "<p>Keep your 100 cm encoder drive. Then <b>turn on the spot until the robot faces north (90°)</b>, using a "
                    "<code>while</code> loop on <code>robot.heading()</code>. Slow down near the target so you land within ±3°.</p>",
            "goals": ["Drive 100 cm first", "Turn with a heading loop (no turn())", "Face 90° ±3 on every robot"],
            "arena": COMPASS_LANE, "starter": PP_S3, "solution": PP_S3_SOL,
            "hints": ["Spin left on the spot with robot.drive(-40, 40) while the heading is less than 90.",
                      "Compute error = 90 - robot.heading(). When the error is small (say under 30), spin slowly.",
                      "while robot.heading() < 90:\n    error = 90 - robot.heading()\n    if error > 30:\n        robot.drive(-40, 40)\n    else:\n        robot.drive(-10, 10)\n    robot.wait(0.02)\nrobot.stop()"],
            "check": PP_S3_CHECK,
            "concepts": ["odometry", "feedback"], "xp": 25,
        },
        {
            "id": "s4", "title": "Laser-straight",
            "learn": "<p>Checking the heading only at the end is too late — by then you've drifted into a wall. Let's fix the "
                     "heading <b>while driving</b>, many times a second.</p>"
                     "<p>If you want heading 0 and the gyro says -5°, you're pointing 5° too far right. The <b>error</b> is "
                     "<code>target - heading</code> = +5. To turn left, speed up the right wheel and slow the left one — by an "
                     "amount <b>proportional</b> to the error. That's the P controller you met on the race track:</p>"
                     "<pre>error = target - robot.heading()\nsteer = 2 * error              # Kp = 2\nrobot.drive(50 - steer, 50 + steer)</pre>"
                     "<p>Big error → big correction, tiny error → tiny correction. Self-driving cars do this to stay in their lane, "
                     "and aeroplane autopilots do it to hold a compass course.</p>"
                     "<p>Put it in a <b>function</b> so you can reuse it: <code>def drive_straight(cm, target):</code>.</p>",
            "task": "<p>New arena: a narrow 240 cm corridor. Finish <code>drive_straight(cm, target)</code>: inside the encoder loop, "
                    "steer with the heading error. Drive 240 cm to the green dock without touching the walls — on every robot.</p>",
            "goals": ["Steer with the heading error inside the loop", "No wall touches", "Stop in the dock"],
            "arena": CORRIDOR, "starter": PP_S4, "solution": PP_S4_SOL,
            "hints": ["Inside the loop, before the encoder read: error = target - robot.heading().",
                      "If error is positive you need to turn left, so the RIGHT wheel should get more power.",
                      "error = target - robot.heading()\nsteer = 2 * error\nrobot.drive(50 - steer, 50 + steer)"],
            "check": PP_S4_CHECK,
            "concepts": ["feedback", "odometry", "pid"], "xp": 30,
        },
        {
            "id": "s5", "title": "There and back (no GPS!)",
            "learn": "<p>Sailors in the old days had no GPS. They knew their <b>speed</b>, their <b>compass heading</b> and the "
                     "<b>time</b>, and worked out their position on the map. That's <b>dead reckoning</b> — and robots do it too.</p>"
                     "<p>Every time round the loop: how far did I roll since last time (<code>d</code>), and which way am I facing "
                     "(<code>h</code>)? Split that little step into an east part and a north part with trig:</p>"
                     "<pre>import math\nx = x + d * math.cos(math.radians(h))   # east-west part\ny = y + d * math.sin(math.radians(h))   # north-south part</pre>"
                     "<p>(<code>math.radians</code> converts degrees, because Python's <code>cos</code> and <code>sin</code> use radians.)</p>"
                     "<p>Now you always know where you are, so steer toward any target: the direction to it is "
                     "<code>math.degrees(math.atan2(ty - y, tx - x))</code> and the distance is <code>math.hypot(tx - x, ty - y)</code>. "
                     "The heading error must be wrapped into -180…180 so the robot turns the short way:</p>"
                     "<pre>error = (want - h + 180) % 360 - 180</pre>"
                     "<p>Small errors add up over time, so dead reckoning gets worse the longer you drive. Mars rovers stop now and "
                     "then to take photos and fix their position.</p>",
            "task": "<p>This arena has no GPS. Start at (40, 40) facing east. Track <code>x</code> and <code>y</code> with dead "
                    "reckoning, drive to the 💰 treasure at <b>(220, 140)</b>, then come back and stop in the 🏠 home zone. "
                    "Tip: a <code>for</code> loop over a list of targets <code>[(220, 140), (40, 40)]</code> does both legs.</p>",
            "goals": ["Track x, y from encoders + heading", "Reach the treasure", "Come home and stop", "Works on 3 robots"],
            "arena": TREASURE, "starter": PP_S5, "solution": PP_S5_SOL,
            "hints": ["Keep last = the travelled distance from last time; d = travelled - last is the little step.",
                      "Steer like in drive_straight, but your target heading is want = math.degrees(math.atan2(ty - y, tx - x)).",
                      "x = x + d * math.cos(math.radians(h))\ny = y + d * math.sin(math.radians(h))\n"
                      "want = math.degrees(math.atan2(ty - y, tx - x))\nerror = (want - h + 180) % 360 - 180"],
            "check": PP_S5_CHECK,
            "concepts": ["odometry", "kinematics", "feedback"], "xp": 40,
        },
    ],
    "boss": {
        "id": "boss", "title": "Waypoint Rally",
        "learn": "<p>Delivery drones and rovers are given a list of <b>waypoints</b> and visit them one by one. With your dead "
                 "reckoning loop that's just a longer list!</p>"
                 "<p>This arena is extra noisy (really worn wheels) and there's a big rock in the middle. The straight lines "
                 "between the waypoints miss the rock — as long as you know where you are.</p>"
                 "<p>Want to turn your navigation loop into a function <code>go_to(tx, ty)</code>? Then it needs to change "
                 "<code>x</code>, <code>y</code> and <code>last</code> that live outside it. Write <code>global x, y, last</code> as "
                 "the first line inside the function so Python lets you.</p>",
        "task": "<p>Start at (40, 40) facing east. Visit <b>A (260, 50)</b>, then <b>B (260, 170)</b>, then <b>C (130, 160)</b>, "
                "and finish back in the 🏠 zone. No crashes!</p>",
        "goals": ["A → B → C in order", "Back home", "No crashes", "Works on 3 noisy robots"],
        "arena": RALLY, "starter": PP_S5_SOL.replace("for (tx, ty) in [(220, 140), (40, 40)]:\n", "# TODO: change the list to the rally waypoints\nfor (tx, ty) in [(220, 140), (40, 40)]:\n"),
        "solution": PP_BOSS_SOL,
        "hints": ["Your treasure program already visits a list of targets. Change the list!",
                  "The list is [(260, 50), (260, 170), (130, 160), (40, 40)].",
                  "for (tx, ty) in [(260, 50), (260, 170), (130, 160), (40, 40)]:"],
        "check": PP_BOSS_CHECK,
        "concepts": ["odometry", "navigation", "feedback"], "xp": 90,
    },
    "remix": {
        "prompt": "Welcome to the Mars Yard! No GPS, worn wheels, rocks everywhere. Plan a mission for your rover.",
        "ideas": ["Visit one gem and return to the lander",
                  "Print your dead-reckoning x, y every second and compare with the replay",
                  "Collect all 5 gems with a list of waypoints that dodges the rocks",
                  "Use robot.plot('x', x) and robot.plot('y', y) to graph your estimate — how big does the error get?"],
        "arena": MARS_YARD,
    },
}

# ---------------------------------------------------------------------------
# arenas — Delivery Bot (the road is a black line, stations are coloured gaps in it)
# ---------------------------------------------------------------------------
LOOP = [[70, 45], [210, 45], [230, 65], [230, 135], [210, 155], [70, 155], [50, 135], [50, 65]]


def _loop_arena(name, stations, start=(80, 45, 0), time_limit=60, boxes=()):
    lines, zones = _road(LOOP, stations)
    return {"name": name, "size": [280, 200], "start": list(start), "time_limit": time_limit,
            "lines": lines, "zones": zones, "boxes": [list(b) for b in boxes]}


def _street(station_x):
    lines, zones = _road([[30, 60], [250, 60]], [("station", "yellow", station_x, 60, "📦")], closed=False)
    return {"name": "Depot Street", "size": [280, 120], "start": [30, 60, 0], "time_limit": 25,
            "lines": lines, "zones": zones}


STREET = _street(150)
STREET_FAR = _street(205)

ROAD_B = _loop_arena("Ring Road", [("B", "yellow", 230, 100, "📦 B")], time_limit=40)
ROAD_C = _loop_arena("Ring Road (station moved)", [("C", "yellow", 140, 155, "📦 C")], time_limit=40)
ROAD_AB = _loop_arena("Two Stops", [("A", "yellow", 140, 45, "📦 A"), ("B", "yellow", 230, 100, "📦 B")], time_limit=40)
THREE = [("A", "yellow", 140, 45, "📦 A"), ("B", "yellow", 230, 100, "📦 B"), ("C", "yellow", 140, 155, "📦 C")]
ROAD_ABC = _loop_arena("Three Stops", THREE, time_limit=60)
ROAD_ABC_LATE = _loop_arena("Three Stops (later start)", THREE, start=(230, 70, 90), time_limit=60)
ROAD_BLOCKED = _loop_arena("Roadworks!", THREE, time_limit=40, boxes=[[186, 40, 10, 10]])

ROUTE_STATIONS = [("depot", "green", 50, 100, "🏠 depot"), ("A", "yellow", 140, 45, "A"),
                  ("B", "orange", 230, 100, "B"), ("C", "blue", 140, 155, "C")]
ROUTE = _loop_arena("Delivery Route", ROUTE_STATIONS, time_limit=90)
ROUTE_SWAP = _loop_arena("Delivery Route (shuffled)",
                         [("depot", "green", 50, 100, "🏠 depot"), ("A", "blue", 140, 45, "A"),
                          ("B", "yellow", 230, 100, "B"), ("C", "orange", 140, 155, "C")], time_limit=90)

CITY_LINES, CITY_ZONES = _road([[60, 50], [270, 50], [290, 70], [290, 190], [270, 210], [60, 210], [40, 190], [40, 70]],
                               [("depot", "green", 40, 130, "🏠"), ("s1", "yellow", 160, 50, "1"),
                                ("s2", "orange", 290, 130, "2"), ("s3", "blue", 200, 210, "3"),
                                ("s4", "yellow", 110, 210, "4")])
CITY = {"name": "Delivery City", "size": [340, 260], "start": [70, 50, 0], "time_limit": 180,
        "lines": CITY_LINES, "zones": CITY_ZONES, "boxes": [[120, 110, 60, 50], [210, 100, 40, 60]]}

# ---------------------------------------------------------------------------
# Project 8 — Delivery Bot
# ---------------------------------------------------------------------------
DB_S1 = '''# 🚚 A robot with moods: its STATE
state = "DRIVE"
robot.led("green")

while True:
    if state == "DRIVE":
        robot.drive(30, 30)
        # TODO: when the floor turns yellow, switch to the "STOP" state (LED red)
    # TODO: add the STOP state: stop the motors and end the loop with break
    robot.wait(0.02)
'''

DB_S1_SOL = '''# 🚚 A robot with moods: its STATE
state = "DRIVE"
robot.led("green")

while True:
    if state == "DRIVE":
        robot.drive(30, 30)
        if robot.color() == "yellow":
            state = "STOP"
            robot.led("red")
    elif state == "STOP":
        robot.stop()
        robot.say("Arrived!")
        break
    robot.wait(0.02)
'''

DB_S2 = DB_S1_SOL.replace("        robot.drive(30, 30)\n",
                          "        robot.drive(30, 30)   # TODO: follow the road line instead of driving straight\n")

DB_S2_SOL = '''# 🚚 Follow the road, stop at the station
state = "DRIVE"
robot.led("green")

while True:
    if state == "DRIVE":
        error = robot.floor_left() - robot.floor_right()
        robot.drive(40 + 0.4 * error, 40 - 0.4 * error)
        if robot.color() == "yellow":
            state = "STOP"
            robot.led("red")
    elif state == "STOP":
        robot.stop()
        robot.say("Arrived!")
        break
    robot.wait(0.02)
'''

DB_S3 = DB_S2_SOL.replace('''    elif state == "STOP":
        robot.stop()
        robot.say("Arrived!")
        break
''', '''    elif state == "STOP":
        robot.stop()
        robot.say("Arrived!")
        break
    # TODO: instead of STOP, a DELIVER state (stop, beep, wait 2 s)
    #       and a LEAVE state (drive straight until the floor isn't yellow any more)
''')

DB_S3_SOL = '''# 🚚 Deliver, then keep going
state = "DRIVE"
robot.led("green")

while True:
    if state == "DRIVE":
        error = robot.floor_left() - robot.floor_right()
        robot.drive(40 + 0.4 * error, 40 - 0.4 * error)
        if robot.color() == "yellow":
            state = "DELIVER"
    elif state == "DELIVER":
        robot.stop()
        robot.led("red")
        robot.beep(660)
        robot.say("Package delivered!")
        robot.wait(2)
        state = "LEAVE"
        robot.led("yellow")
    elif state == "LEAVE":
        robot.drive(40, 40)
        if robot.color() != "yellow":
            state = "DRIVE"
            robot.led("green")
    robot.wait(0.02)
'''

DB_S4 = DB_S3_SOL.replace('state = "DRIVE"\nrobot.led("green")\n',
                          'state = "DRIVE"\nrobot.led("green")\n# TODO: count the stations and PARK at the 3rd one\n', 1)

DB_S4_SOL = '''# 🚚 Count the stations, park at number 3
state = "DRIVE"
count = 0
robot.led("green")

while True:
    if state == "DRIVE":
        error = robot.floor_left() - robot.floor_right()
        robot.drive(40 + 0.4 * error, 40 - 0.4 * error)
        if robot.color() == "yellow":
            count = count + 1
            if count == 3:
                state = "PARK"
            else:
                state = "DELIVER"
    elif state == "DELIVER":
        robot.stop()
        robot.led("red")
        robot.beep(660)
        robot.say("Delivery " + str(count))
        robot.wait(2)
        state = "LEAVE"
        robot.led("yellow")
    elif state == "LEAVE":
        robot.drive(40, 40)
        if robot.color() != "yellow":
            state = "DRIVE"
            robot.led("green")
    elif state == "PARK":
        robot.stop()
        robot.led("blue")
        robot.say("Parked at station 3")
        break
    robot.wait(0.02)
'''

DB_S5 = DB_S4_SOL.replace('''    elif state == "PARK":''', '''    # TODO: a WAIT state — if something blocks the road, stop and wait until it's clear
    elif state == "PARK":''')

DB_S5_SOL = '''# 🚚 Count the stations, park at number 3 — and never hit anything
state = "DRIVE"
count = 0
robot.led("green")

while True:
    if state == "DRIVE":
        error = robot.floor_left() - robot.floor_right()
        robot.drive(40 + 0.4 * error, 40 - 0.4 * error)
        if robot.distance() < 20:
            state = "WAIT"
            robot.stop()
            robot.led("purple")
            robot.say("Road blocked!")
        elif robot.color() == "yellow":
            count = count + 1
            if count == 3:
                state = "PARK"
            else:
                state = "DELIVER"
    elif state == "WAIT":
        robot.stop()
        if robot.distance() > 25:
            state = "DRIVE"
            robot.led("green")
    elif state == "DELIVER":
        robot.stop()
        robot.led("red")
        robot.beep(660)
        robot.say("Delivery " + str(count))
        robot.wait(2)
        state = "LEAVE"
        robot.led("yellow")
    elif state == "LEAVE":
        robot.drive(40, 40)
        if robot.color() != "yellow":
            state = "DRIVE"
            robot.led("green")
    elif state == "PARK":
        robot.stop()
        robot.led("blue")
        robot.say("Parked at station 3")
        break
    robot.wait(0.02)
'''

DB_BOSS_SOL = '''# 🚚 The full delivery route
packages = ["yellow", "blue"]       # the stations that get a parcel today
state = "DRIVE"
robot.led("green")
here = "white"

while True:
    if state == "DRIVE":
        error = robot.floor_left() - robot.floor_right()
        robot.drive(40 + 0.4 * error, 40 - 0.4 * error)
        here = robot.color()
        if robot.distance() < 20:
            state = "WAIT"
            robot.stop()
            robot.led("purple")
        elif here in packages:
            state = "DELIVER"
        elif here == "green" and len(packages) == 0:
            state = "PARK"
        elif here not in ("white", "black"):
            state = "LEAVE"                # a station with no parcel today: drive through
    elif state == "WAIT":
        robot.stop()
        if robot.distance() > 25:
            state = "DRIVE"
            robot.led("green")
    elif state == "DELIVER":
        robot.stop()
        robot.led("red")
        robot.beep(660)
        robot.say("Parcel for " + here + "!")
        packages.remove(here)
        robot.wait(2)
        state = "LEAVE"
    elif state == "LEAVE":
        robot.drive(40, 40)
        if robot.color() in ("white", "black"):
            state = "DRIVE"
            robot.led("green")
    elif state == "PARK":
        robot.stop()
        robot.led("blue")
        robot.say("Back at the depot!")
        break
    robot.wait(0.02)
'''

DB_S1_CHECK = STOP_HELPER + '''expect(uses("state_machines") or "state ==" in source, "Keep a state variable and check it with if state == \\"DRIVE\\": … elif state == \\"STOP\\": …")
expect(calls("color") >= 1, "Watch the floor colour with robot.color() to spot the yellow station.")
for a, lab in ((ARENA, "station at 150 cm"), (arena_far, "station further away")):
    r = sim(a, label=lab)
    expect(r.crashes == 0, f"({lab}) the robot drove into the wall — it never switched to STOP at the yellow station.")
    expect(near(r.x, r.y, "station", a), f"({lab}) the robot stopped at x = {r.x:.0f}, but the station is at x = {a['zones'][0]['rect'][0]:.0f}–{a['zones'][0]['rect'][0] + 20:.0f}.")
    expect(r.stopped, f"({lab}) the robot was still moving at the end. In the STOP state: robot.stop().")
    cols = r.led_colors()
    expect(len(set(cols)) >= 2, "Give each state its own LED colour, e.g. green for DRIVE and red for STOP.")
    expect(cols[-1] != cols[0], "Change the LED colour when you switch to STOP, so everyone can see the robot's state.")
SUCCESS = "Two states, one clean stop. Your robot has moods now! 🚦"
'''.replace("arena_far", "STREET_FAR_")

DB_S2_CHECK = STOP_HELPER + '''expect(calls("floor_left") + calls("floor_right") + calls("floor") >= 1, "Follow the road with the floor sensors (like on the race track).")
for a, lab in ((ARENA, "station B"), (ROAD_C_, "station moved")):
    r = sim(a, label=lab)
    expect(r.crashes == 0, f"({lab}) the robot left the road and crashed. Follow the line in the DRIVE state.")
    expect(r.line_ratio >= 0.7, f"({lab}) the robot was on the road only {r.line_ratio:.0%} of the time. Steer with floor_left() - floor_right().")
    stn = a["zones"][0]["name"]
    expect(near(r.x, r.y, stn, a), f"({lab}) the robot ended at ({r.x:.0f}, {r.y:.0f}), not at the yellow station {stn}.")
    expect(r.stopped, f"({lab}) the robot was still moving at the end — STOP should stop the motors.")
SUCCESS = "Road followed, station found! 🛣️📦"
'''

DB_S3_CHECK = STOP_HELPER + '''r = sim(label="two stations")
expect(r.crashes == 0, "The robot crashed. Stay on the road!")
expect(not (r.end_reason == "done" and near(r.x, r.y, "A", ARENA)), "The robot stopped at station A and the program ended (that's the old STOP "
       "state with break). A delivery robot keeps going: DELIVER (stop, beep, wait 2 s), then LEAVE, then back to DRIVE — no break this time.")
expect(stopped_at(r, "A", ARENA, 1.5), "The robot didn't stand still at station A for a delivery (stop and wait 2 s).")
expect(r.count("beep") >= 1, "Beep when you deliver, so the customer knows!")
expect(stopped_at(r, "B", ARENA, 1.5), "The robot delivered at A but never delivered at B. After DELIVER, a LEAVE state must drive off the "
       "yellow zone before going back to DRIVE — otherwise it keeps seeing yellow and delivers at A forever.")
expect(r.count("beep") >= 2, f"I heard {r.count('beep')} beep(s) — one per delivery, please (A and B).")
SUCCESS = "Deliver → leave → drive → deliver. That's a real state machine! 🔁"
'''

DB_S4_CHECK = STOP_HELPER + '''for a, lab, order in ((ARENA, "start before A", ["A", "B", "C"]), (ROAD_ABC_LATE_, "start before B", ["B", "C", "A"])):
    r = sim(a, label=lab)
    expect(r.crashes == 0, f"({lab}) the robot crashed.")
    for stn in order[:2]:
        expect(stopped_at(r, stn, a, 1.5), f"({lab}) no delivery stop at station {stn} (it's station number {order.index(stn) + 1} on this trip).")
    last = order[2]
    expect(r.end_reason == "done" and r.stopped, f"({lab}) the robot was still going when time ran out. At the 3rd station switch to PARK: stop and break.")
    expect(near(r.x, r.y, last, a), f"({lab}) the robot parked at ({r.x:.0f}, {r.y:.0f}). The 3rd station on this trip is {last}. Count the stations!")
SUCCESS = "Counting like a pro — it parks at the 3rd stop wherever it starts! 🔢"
'''

DB_S5_CHECK = STOP_HELPER + '''expect(calls("distance") >= 1, "Use robot.distance() to see if something blocks the road.")
expect("WAIT" in source, "Add a state called \\"WAIT\\" for when the road is blocked.")
r = sim(label="roadworks after station A")
expect(r.crashes == 0 and r.min_front_distance() > 3, "The robot bumped into the roadworks box! Switch to WAIT when robot.distance() gets small.")
expect(stopped_at(r, "A", ARENA, 1.5), "The robot should still deliver at station A before it reaches the roadworks.")
bx = 186
expect(r.x < bx - 8 and r.x > bx - 45, f"The robot stopped at x = {r.x:.0f}. Wait just before the box (it starts at x = {bx}), about 20 cm away.")
expect(r.stopped, "The robot kept moving — in WAIT, keep the motors stopped.")
cols = r.led_colors()
expect(cols and cols[-1] not in ("green",), "Show the WAIT state with its own LED colour.")
for a, lab, last in ((ROAD_ABC_, "clear road", "C"), (ROAD_ABC_LATE_, "clear road, later start", "A")):
    r = sim(a, label=lab)
    expect(r.crashes == 0, f"({lab}) the robot crashed.")
    expect(near(r.x, r.y, last, a) and r.end_reason == "done", f"({lab}) on a clear road the robot should still park at the 3rd station ({last}), "
           f"but it ended at ({r.x:.0f}, {r.y:.0f}). Is WAIT only used when something is really close?")
SUCCESS = "Safety first! Your robot waits patiently instead of crashing. 🚧"
'''

DB_BOSS_CHECK = STOP_HELPER + '''for a, lab in ((ARENA, "today's route"), (ROUTE_SWAP_, "shuffled stations")):
    col = {z["name"]: z["color"] for z in a["zones"]}
    r = sim(a, label=lab)
    expect(r.crashes == 0, f"({lab}) the robot crashed.")
    for stn in ("A", "B", "C"):
        if col[stn] in ("yellow", "blue"):
            expect(stopped_at(r, stn, a, 1.5), f"({lab}) station {stn} is {col[stn]} and gets a parcel — but the robot didn't stop there to deliver.")
        else:
            expect(not stopped_at(r, stn, a, 0.5), f"({lab}) station {stn} is {col[stn]}: no parcel for it today, so drive straight through without stopping.")
    expect(r.count("beep") >= 2, f"({lab}) beep at each delivery (I heard {r.count('beep')}).")
    expect(r.end_reason == "done" and r.stopped and near(r.x, r.y, "depot", a),
           f"({lab}) after the last delivery, drive on and PARK at the green depot (ended at ({r.x:.0f}, {r.y:.0f})).")
SUCCESS = "Every parcel delivered, back at the depot. Employee of the month! 🏆🚚"
'''


def _with(check, **arenas):
    """Make extra arenas available to a check snippet as NAME_ variables."""
    head = "".join(f"{k}_ = {v!r}\n" for k, v in arenas.items())
    return head + check


DELIVERY_BOT = {
    "id": "delivery_bot", "week": 4, "order": 8, "title": "Delivery Bot", "emoji": "🚚",
    "tagline": "Give your robot states — DRIVE, DELIVER, WAIT, PARK — and run a delivery route",
    "story": "Robo-Parcels Ltd. has hired Bolt! Parcels need to go to the yellow stations along the ring road. A delivery "
             "robot has to do different things at different moments: drive, stop, deliver, wait for roadworks, park. "
             "The trick that keeps all of that tidy is called a state machine.",
    "concepts": ["state_machines", "behaviors", "sensors"],
    "expected_minutes": 120,
    "real_world": "Warehouse robots (like Amazon's Kiva robots) and hospital delivery robots switch between states such as "
                  "GO TO SHELF, LIFT, CARRY, WAIT and CHARGE. Lunar landers run a state machine too: DESCENT → HOVER → TOUCHDOWN.",
    "build_it": "A LEGO SPIKE or micro:bit car with a colour sensor and an ultrasonic sensor can follow black tape on the floor, "
                "stop at coloured paper 'stations' and wait when you put your hand in front of it.",
    "steps": [
        {
            "id": "s1", "title": "A robot with moods",
            "learn": "<p>A traffic light is always in exactly one <b>state</b>: GREEN, YELLOW or RED. It stays in a state until "
                     "something happens (a timer runs out), then it <b>switches</b> to the next state. That's a "
                     "<b>state machine</b>. Vending machines (WAITING → PAID → DROPPING) and game characters "
                     "(IDLE → CHASE → ATTACK) work the same way.</p>"
                     "<p>In Python a state is just a variable holding a word. The loop looks at the state and does that state's "
                     "job. Inside, an <code>if</code> decides when to switch:</p>"
                     "<pre>state = \"DRIVE\"\nwhile True:\n    if state == \"DRIVE\":\n        robot.drive(30, 30)\n"
                     "        if robot.color() == \"yellow\":\n            state = \"STOP\"      # switch!\n"
                     "    elif state == \"STOP\":\n        robot.stop()\n        break               # leave the loop\n    robot.wait(0.02)</pre>"
                     "<p>Give every state its own LED colour, so people nearby can see what the robot is \"thinking\". Real "
                     "robots do this all the time!</p>",
            "task": "<p>Finish the state machine: in <b>DRIVE</b> (LED green) drive along the street; when "
                    "<code>robot.color()</code> is <code>\"yellow\"</code>, switch to <b>STOP</b> (LED red), stop the motors and "
                    "<code>break</code>.</p>",
            "goals": ["A state variable: DRIVE and STOP", "A different LED colour per state", "Stop at the yellow station"],
            "arena": STREET, "starter": DB_S1, "solution": DB_S1_SOL,
            "hints": ["In the DRIVE part, add an if that checks robot.color() == \"yellow\".",
                      "When it's yellow: state = \"STOP\" and robot.led(\"red\"). Then add an elif state == \"STOP\": part.",
                      "    elif state == \"STOP\":\n        robot.stop()\n        break"],
            "check": _with(DB_S1_CHECK, STREET_FAR=STREET_FAR),
            "concepts": ["state_machines", "sensors"], "xp": 20,
        },
        {
            "id": "s2", "title": "Follow the road",
            "learn": "<p>Real roads bend. Your robot already knows how to follow a line from the race track! Put the "
                     "line-follower <i>inside</i> the DRIVE state:</p>"
                     "<pre>error = robot.floor_left() - robot.floor_right()\nrobot.drive(40 + 0.4 * error, 40 - 0.4 * error)</pre>"
                     "<p>If the line slides under the left sensor, <code>floor_left()</code> gets darker (smaller), the error goes "
                     "negative, the left wheel slows down and the robot steers back onto the road.</p>"
                     "<p>The stations are <b>coloured gaps</b> in the road. Inside a station both side sensors see the same colour, "
                     "so the error is 0 and the robot rolls straight — and <code>robot.color()</code> tells you which station it "
                     "is. Notice how the state machine keeps things tidy: the follower lives in DRIVE, and you didn't have to "
                     "touch the STOP state at all.</p>",
            "task": "<p>New arena: a ring road! In the DRIVE state, <b>follow the line</b> instead of driving straight. Stop "
                    "at the yellow 📦 station, wherever it is on the road.</p>",
            "goals": ["Follow the road line in DRIVE", "Stop at the station", "Works when the station moves"],
            "arena": ROAD_B, "starter": DB_S2, "solution": DB_S2_SOL,
            "hints": ["Replace robot.drive(30, 30) in the DRIVE state with a line follower.",
                      "error = robot.floor_left() - robot.floor_right() is 0 when the line is in the middle.",
                      "error = robot.floor_left() - robot.floor_right()\nrobot.drive(40 + 0.4 * error, 40 - 0.4 * error)"],
            "check": _with(DB_S2_CHECK, ROAD_C=ROAD_C),
            "concepts": ["state_machines", "sensors", "feedback"], "xp": 25,
        },
        {
            "id": "s3", "title": "Deliver and move on",
            "learn": "<p>A delivery robot doesn't stop forever: it hands over the parcel and drives on. So STOP becomes "
                     "<b>DELIVER</b>: stop, beep, wait 2 seconds.</p>"
                     "<p>But careful! After DELIVER, if you go straight back to DRIVE, the robot is <i>still standing on "
                     "yellow</i>… so DRIVE sees yellow and delivers again. And again. Forever! 😵</p>"
                     "<p>The fix is a third state, <b>LEAVE</b>: drive straight ahead until the floor is <i>not</i> yellow any "
                     "more, then switch back to DRIVE:</p>"
                     "<pre>DRIVE --(yellow)--&gt; DELIVER --(after 2 s)--&gt; LEAVE --(not yellow)--&gt; DRIVE</pre>"
                     "<p>Drawing states as boxes and arrows like this is how engineers design robot behaviour before writing any "
                     "code. Each arrow is one <code>state = …</code> line.</p>",
            "task": "<p>Two stations this time, A and B. Turn STOP into <b>DELIVER</b> (stop, beep, wait 2 s) and add a "
                    "<b>LEAVE</b> state, so the robot delivers at A, drives on, and delivers at B too.</p>",
            "goals": ["DELIVER: stop, beep, wait", "LEAVE the station without re-triggering", "Deliver at A and B"],
            "arena": ROAD_AB, "starter": DB_S3, "solution": DB_S3_SOL,
            "hints": ["In DRIVE, when you see yellow switch to \"DELIVER\" instead of \"STOP\".",
                      "DELIVER: robot.stop(), robot.beep(660), robot.wait(2), then state = \"LEAVE\".",
                      "    elif state == \"LEAVE\":\n        robot.drive(40, 40)\n        if robot.color() != \"yellow\":\n            state = \"DRIVE\""],
            "check": DB_S3_CHECK,
            "concepts": ["state_machines", "sensors"], "xp": 30,
        },
        {
            "id": "s4", "title": "Park at stop number 3",
            "learn": "<p>Robots often need to <b>remember</b> things. A counter is the simplest memory: a variable that goes up "
                     "by one every time something happens.</p>"
                     "<pre>count = 0\n...\ncount = count + 1     # one more station!\nif count == 3:\n    state = \"PARK\"</pre>"
                     "<p>Where do you add 1? At the moment you <i>arrive</i> at a station — the switch from DRIVE to DELIVER. "
                     "That happens exactly once per station (thanks to LEAVE!). If you counted inside DELIVER or LEAVE's loop, "
                     "you'd count lots of times per station.</p>"
                     "<p>A new state <b>PARK</b> (LED blue) stops the motors and <code>break</code>s out of the loop.</p>",
            "task": "<p>Count the stations. Deliver at the 1st and 2nd; at the <b>3rd station</b> switch to <b>PARK</b>: stop, "
                    "LED blue, end the program. The check also starts your robot at a different place on the ring — so count, "
                    "don't hard-code!</p>",
            "goals": ["Count stations with a variable", "Deliver at stations 1 and 2", "PARK at station 3"],
            "arena": ROAD_ABC, "starter": DB_S4, "solution": DB_S4_SOL,
            "hints": ["Make count = 0 before the loop.",
                      "When DRIVE sees yellow: count = count + 1, then choose PARK if count == 3, otherwise DELIVER.",
                      "    elif state == \"PARK\":\n        robot.stop()\n        robot.led(\"blue\")\n        break"],
            "check": _with(DB_S4_CHECK, ROAD_ABC_LATE=ROAD_ABC_LATE),
            "concepts": ["state_machines", "sensors"], "xp": 30,
        },
        {
            "id": "s5", "title": "Roadworks ahead!",
            "learn": "<p>Real roads have surprises: a box, a person, another robot. A good delivery robot never crashes — it "
                     "switches into a <b>WAIT</b> state, and goes back to DRIVE once the road is clear.</p>"
                     "<p>Now two things can happen while driving: you might see a station, or you might see an obstacle. Which wins? "
                     "<b>Safety first!</b> Check the distance sensor <i>before</i> the colour:</p>"
                     "<pre>if robot.distance() &lt; 20:\n    state = \"WAIT\"\nelif robot.color() == \"yellow\":\n    ...</pre>"
                     "<pre>elif state == \"WAIT\":\n    robot.stop()\n    if robot.distance() &gt; 25:   # clear again?\n        state = \"DRIVE\"</pre>"
                     "<p>See the two different numbers, 20 and 25? That gap stops the robot flickering between WAIT and DRIVE when "
                     "something is right at 20 cm. Thermostats and self-driving cars use the same trick.</p>",
            "task": "<p>Roadworks! Add a <b>WAIT</b> state (with its own LED colour): if something is closer than 20 cm, stop and "
                    "wait; drive on when the road is clear again. Your robot must still deliver at A, must not touch the box — "
                    "and on a clear road it must still park at station 3.</p>",
            "goals": ["A WAIT state using robot.distance()", "Never touch the box", "Still deliver and park on a clear road"],
            "arena": ROAD_BLOCKED, "starter": DB_S5, "solution": DB_S5_SOL,
            "hints": ["In DRIVE, check robot.distance() < 20 first, before the colour check.",
                      "WAIT: robot.stop(), and if robot.distance() > 25 switch back to DRIVE.",
                      "        if robot.distance() < 20:\n            state = \"WAIT\"\n            robot.led(\"purple\")\n        elif robot.color() == \"yellow\":"],
            "check": _with(DB_S5_CHECK, ROAD_ABC=ROAD_ABC, ROAD_ABC_LATE=ROAD_ABC_LATE),
            "concepts": ["state_machines", "behaviors", "sensors"], "xp": 35,
        },
    ],
    "boss": {
        "id": "boss", "title": "The full delivery route",
        "learn": "<p>Today's route has three coloured stations and a green 🏠 depot. Only some stations get a parcel. Keep the "
                 "list of parcels in a Python <b>list</b>:</p>"
                 "<pre>packages = [\"yellow\", \"blue\"]\n\"blue\" in packages       # True\npackages.remove(\"blue\")  # delivered!\n"
                 "len(packages)            # how many are left</pre>"
                 "<p>Your state machine now needs to decide: is this station on my list (DELIVER), or not (LEAVE — drive "
                 "through)? And once the list is empty, the green depot means PARK.</p>",
        "task": "<p>Deliver a parcel to the <b>yellow</b> and the <b>blue</b> station (stop, beep, wait), drive straight through "
                "any other station, and when all parcels are delivered <b>park at the green depot</b>. The check also shuffles "
                "the station colours!</p>",
        "goals": ["Deliver only to yellow and blue", "Drive through other stations", "Park at the depot when done", "No crashes"],
        "arena": ROUTE, "starter": DB_S5_SOL.replace('state = "DRIVE"\ncount = 0\n',
                                                     'packages = ["yellow", "blue"]   # TODO: use this list!\nstate = "DRIVE"\ncount = 0\n', 1),
        "solution": DB_BOSS_SOL,
        "hints": ["Save the colour once: here = robot.color(). Then check if here in packages.",
                  "After delivering, packages.remove(here). Any other colour (not white, not black): LEAVE to drive through.",
                  "elif here == \"green\" and len(packages) == 0:\n    state = \"PARK\""],
        "check": _with(DB_BOSS_CHECK, ROUTE_SWAP=ROUTE_SWAP),
        "concepts": ["state_machines", "behaviors", "sensors"], "xp": 90,
    },
    "remix": {
        "prompt": "Welcome to Delivery City! Design your own delivery company: routes, parcels, and robot personality.",
        "ideas": ["Say the station number out loud at every stop",
                  "Deliver to stations 2 and 4 only, then go home to the depot",
                  "Add a CHARGE state: after 3 deliveries, go to the depot for a 5-second 'recharge'",
                  "Honk (beep) every second while waiting, and give up after 10 s with a GIVE_UP state"],
        "arena": CITY,
    },
}

PROJECTS = [PRECISION_PILOT, DELIVERY_BOT]

# ---------------------------------------------------------------------------
# Practice side quests
# ---------------------------------------------------------------------------
BACK_LANE = {"name": "Reverse Lane", "size": [240, 140], "start": [180, 70, 0], "time_limit": 20, "noise": 0.4,
             "zones": [{"name": "mark", "rect": [116, 30, 8, 80], "color": "yellow", "label": "60 cm back"}]}

TURNTABLE = {"name": "Turntable", "size": [200, 200], "start": [100, 100, 0], "time_limit": 15, "noise": 0.5,
             "labels": [[100, 175, "N ↑ 90°"]]}

BANG_CORRIDOR = {**CORRIDOR, "name": "Bang-Bang Corridor"}

WHEEL_LANE = {"name": "Wheel Counter", "size": [240, 140], "start": [30, 70, 0], "time_limit": 20, "noise": 0.4,
              "zones": [{"name": "mark", "rect": [120, 30, 8, 80], "color": "yellow", "label": "5 turns"}]}

SQUARE_PAD = {"name": "Square Pad", "size": [220, 220], "start": [60, 60, 0], "time_limit": 60, "noise": 0.6,
              "zones": [{"name": "start", "rect": [50, 50, 20, 20], "color": "green", "label": "start"}]}

SIGNAL_LANE = {"name": "Signal Street", "size": [300, 120], "start": [30, 60, 0], "time_limit": 30,
               "lines": [{"pts": [[20, 60], [290, 60]], "width": 1.0}]}

PATROL = {"name": "Patrol Hall", "size": [260, 100], "start": [60, 50, 0], "time_limit": 60}

HONK_LINES, _ = _road([[30, 60], [290, 60]], [], closed=False)
HONK_ROAD = {"name": "Traffic Jam", "size": [320, 120], "start": [30, 60, 0], "time_limit": 20,
             "lines": HONK_LINES, "boxes": [[200, 50, 12, 20]]}

PRACTICE = [
    {
        "id": "p_odometry_1", "concept": "odometry", "title": "Reverse by the wheels", "difficulty": 1,
        "task": "<p>Back up <b>exactly 60 cm</b> using <code>drive()</code> and the encoders (no <code>backward()</code>). "
                "Going backwards, the encoders count <b>down</b> — so the average becomes negative!</p>",
        "goals": ["Use drive() with negative power", "Watch the encoders in a loop", "Back up 60 cm (±3)"],
        "arena": BACK_LANE,
        "starter": "robot.reset_encoders()\nrobot.drive(-50, -50)\n# TODO: loop until the average encoder reaches -60\nrobot.wait(4)\nrobot.stop()\n",
        "solution": "robot.reset_encoders()\nrobot.drive(-50, -50)\ntravelled = 0\nwhile travelled > -60:\n"
                    "    left, right = robot.encoders()\n    travelled = (left + right) / 2\n    robot.wait(0.02)\nrobot.stop()\n",
        "hints": ["While going backwards, (left + right) / 2 goes 0, -1, -2 … -60.",
                  "Loop while travelled > -60.",
                  "while travelled > -60:\n    left, right = robot.encoders()\n    travelled = (left + right) / 2\n    robot.wait(0.02)"],
        "check": LOOP_HELPER + '''expect(calls("backward") == 0, "No robot.backward() — use drive(-50, -50) and the encoders.")
expect(in_loop("encoders"), "Read robot.encoders() inside a while loop.")
for seed in (1, 2):
    r = sim(seed=seed, label=f"robot #{seed}")
    expect(r.x < 180, "The robot should drive backwards (to the left).")
    expect(abs(r.distance - 60) <= 3, f"The robot backed up {r.distance:.0f} cm — aim for 60 cm (±3).")
SUCCESS = "Beep… beep… beep… Perfect reverse! 🚛"
''',
        "xp": 15,
    },
    {
        "id": "p_odometry_2", "concept": "odometry", "title": "Always face north", "difficulty": 2,
        "task": "<p>The robot starts facing a <b>random</b> direction. Spin on the spot until it faces <b>north (90°)</b> "
                "±3°, whichever way it started. Tip: <code>error = 90 - robot.heading()</code> tells you which way to turn "
                "(positive = turn left) and how far.</p>",
        "goals": ["Loop on robot.heading()", "Face 90° ±3 from any start"],
        "arena": TURNTABLE,
        "starter": "robot.turn(90)\n",
        "solution": "while True:\n    error = 90 - robot.heading()\n    if abs(error) < 1:\n        break\n"
                    "    power = max(-40, min(40, 0.8 * error))\n    if abs(power) < 8:\n        power = 8 if error > 0 else -8\n"
                    "    robot.drive(-power, power)\n    robot.wait(0.02)\nrobot.stop()\n",
        "hints": ["If error is positive, spin left: drive(-p, p). If negative, spin right.",
                  "Make the power proportional to the error, but never less than about 8 (or it creeps forever).",
                  "error = 90 - robot.heading()\npower = max(-40, min(40, 0.8 * error))\nrobot.drive(-power, power)"],
        "check": LOOP_HELPER + '''expect(in_loop("heading"), "Read robot.heading() inside a loop.")
for start, seed in ((0, 1), (-60, 2), (150, 5)):
    r = sim(start=[100, 100, start], seed=seed, label=f"starting at {start}°")
    expect(abs(r.heading - 90) <= 3, f"Starting at {start}°, the robot ended facing {r.heading:.0f}°. It should face 90° (±3).")
SUCCESS = "A robot compass needle! 🧭"
''',
        "xp": 20,
    },
    {
        "id": "p_feedback_1", "concept": "feedback", "title": "Bang-bang straight", "difficulty": 2,
        "task": "<p>Drive 240 cm down the corridor with the simplest feedback there is — <b>bang-bang</b>: if the heading is "
                "above 0, steer a bit right; otherwise steer a bit left. No multiplying by Kp allowed: just two fixed "
                "choices. Use the encoders to know when to stop.</p>",
        "goals": ["if/else on the heading", "No wall touches", "Stop in the dock"],
        "arena": BANG_CORRIDOR,
        "starter": "robot.reset_encoders()\ntravelled = 0\nwhile travelled < 240:\n    robot.drive(50, 50)   # TODO: bang-bang steering\n"
                   "    left, right = robot.encoders()\n    travelled = (left + right) / 2\n    robot.wait(0.02)\nrobot.stop()\n",
        "solution": "robot.reset_encoders()\ntravelled = 0\nwhile travelled < 240:\n    if robot.heading() > 0:\n        robot.drive(50, 40)\n"
                    "    else:\n        robot.drive(40, 50)\n    left, right = robot.encoders()\n    travelled = (left + right) / 2\n"
                    "    robot.wait(0.02)\nrobot.stop()\n",
        "hints": ["Heading above 0 means you're pointing left of straight — so turn right.",
                  "Turning right = left wheel faster: robot.drive(50, 40).",
                  "if robot.heading() > 0:\n    robot.drive(50, 40)\nelse:\n    robot.drive(40, 50)"],
        "check": LOOP_HELPER + '''expect(in_loop("heading"), "Read robot.heading() inside the loop and steer with if/else.")
for seed in (1, 2, 5):
    r = sim(seed=seed, label=f"robot #{seed}")
    expect(r.crashes == 0, f"Robot #{seed} touched the corridor wall. Steer back whenever the heading isn't 0.")
    expect(r.in_zone("dock"), f"Robot #{seed} stopped at ({r.x:.0f}, {r.y:.0f}), not in the dock.")
SUCCESS = "Wiggly but straight — bang-bang control works! 〰️"
''',
        "xp": 20,
    },
    {
        "id": "p_kinematics_wheels", "concept": "kinematics", "title": "Five wheel turns", "difficulty": 1,
        "task": "<p>This robot's wheels have a <b>radius of 3 cm</b>. Drive exactly <b>5 full wheel turns</b> using the encoders. "
                "Let Python do the maths: one turn rolls <code>2 * math.pi * 3</code> cm.</p>",
        "goals": ["Work out the distance with 2 × π × r", "Stop after 5 turns (±3 cm)"],
        "arena": WHEEL_LANE,
        "starter": "import math\nturn_cm = 0   # TODO: how far does one wheel turn roll?\n",
        "solution": "import math\nturn_cm = 2 * math.pi * 3\ngoal = 5 * turn_cm\nrobot.reset_encoders()\nrobot.drive(50, 50)\n"
                    "travelled = 0\nwhile travelled < goal:\n    left, right = robot.encoders()\n    travelled = (left + right) / 2\n"
                    "    robot.wait(0.02)\nrobot.stop()\nprint(\"5 turns =\", round(goal, 1), \"cm\")\n",
        "hints": ["The circumference of a circle is 2 × π × r.", "5 turns is 5 × 2 × π × 3 ≈ 94 cm.",
                  "goal = 5 * 2 * math.pi * 3\n# then an encoder loop: while travelled < goal: ..."],
        "check": '''expect("pi" in source or "3.14" in source, "Use π (math.pi) to work out the wheel's circumference.")
expect(calls("encoders") >= 1, "Measure with robot.encoders().")
for seed in (1, 2):
    r = sim(seed=seed, label=f"robot #{seed}")
    expect(abs(r.distance - 94.2) <= 3, f"The robot rolled {r.distance:.0f} cm. 5 turns of a 3 cm wheel is 5 × 2π × 3 ≈ 94 cm.")
SUCCESS = "2πr for the win! 🛞"
''',
        "xp": 15,
    },
    {
        "id": "p_odometry_3", "concept": "odometry", "title": "Gyro square", "difficulty": 3,
        "task": "<p>Draw a <b>60 cm square</b> with the pen in a noisy arena — and make it close up! Use encoders for the "
                "sides and the <b>compass for the corners</b>: turn to the absolute headings 90, 180, -90 and 0, instead of "
                "\"turn 90 more\" (which adds up errors).</p>",
        "goals": ["Encoder sides", "Turn to absolute headings", "Finish back at the start (±10 cm)"],
        "arena": SQUARE_PAD,
        "starter": "robot.pen_down(\"blue\")\nfor side in range(4):\n    robot.forward(60)\n    robot.turn(90)\n",
        "solution": "def side(cm, target):\n    robot.reset_encoders()\n    travelled = 0\n    while travelled < cm:\n"
                    "        error = (target - robot.heading() + 180) % 360 - 180\n        robot.drive(40 - 2 * error, 40 + 2 * error)\n"
                    "        left, right = robot.encoders()\n        travelled = (left + right) / 2\n        robot.wait(0.02)\n    robot.stop()\n\n"
                    "def face(target):\n    while True:\n        error = (target - robot.heading() + 180) % 360 - 180\n"
                    "        if abs(error) < 1:\n            break\n        p = max(-40, min(40, error))\n        if abs(p) < 8:\n"
                    "            p = 8 if error > 0 else -8\n        robot.drive(-p, p)\n        robot.wait(0.02)\n    robot.stop()\n\n"
                    "robot.pen_down(\"blue\")\nfor target in [0, 90, 180, -90]:\n    face(target)\n    side(60, target)\nface(0)\n",
        "hints": ["Write face(target): spin until the heading error is less than 1°.",
                  "Wrap the error so 180 and -180 count as the same: error = (target - h + 180) % 360 - 180.",
                  "for target in [0, 90, 180, -90]:\n    face(target)\n    side(60, target)"],
        "check": LOOP_HELPER + '''expect(in_loop("heading"), "Use robot.heading() in a loop for the corners.")
for seed in (1, 2):
    r = sim(seed=seed, label=f"robot #{seed}")
    w, h = r.trail_bbox
    expect(r.pen_length > 200, "Put the pen down and draw all 4 sides!")
    expect(abs(w - 60) <= 10 and abs(h - 60) <= 10, f"Robot #{seed}'s square is {w:.0f} × {h:.0f} cm — it should be about 60 × 60.")
    expect(r.dist_to(60, 60) <= 10, f"Robot #{seed} finished {r.dist_to(60, 60):.0f} cm from the start. A square should close up (±10 cm).")
SUCCESS = "A square that closes, even with wobbly wheels! ⬛"
''',
        "xp": 30,
    },
    {
        "id": "p_state_machines_1", "concept": "state_machines", "title": "Traffic-light robot", "difficulty": 1,
        "task": "<p>Be your own traffic light, twice round: <b>GO</b> (LED green, drive at power 40 for 2 s) → <b>SLOW</b> "
                "(LED yellow, power 15 for 1 s) → <b>STOP</b> (LED red, stopped for 2 s) → back to GO. Use a "
                "<code>state</code> variable and <code>robot.time()</code> to know how long you've been in a state.</p>",
        "goals": ["States GO, SLOW, STOP", "green → yellow → red, twice", "Stand still on red, slower on yellow"],
        "arena": SIGNAL_LANE,
        "starter": "state = \"GO\"\nrobot.led(\"green\")\nrobot.drive(40, 40)\nrobot.wait(2)\n# TODO: a state machine with GO, SLOW and STOP\n",
        "solution": "state = \"GO\"\nrobot.led(\"green\")\nstart = robot.time()\ncycles = 0\nwhile cycles < 2:\n"
                    "    t = robot.time() - start\n    if state == \"GO\":\n        robot.drive(40, 40)\n        if t > 2:\n"
                    "            state = \"SLOW\"\n            robot.led(\"yellow\")\n            start = robot.time()\n"
                    "    elif state == \"SLOW\":\n        robot.drive(15, 15)\n        if t > 1:\n            state = \"STOP\"\n"
                    "            robot.led(\"red\")\n            start = robot.time()\n    elif state == \"STOP\":\n        robot.stop()\n"
                    "        if t > 2:\n            state = \"GO\"\n            robot.led(\"green\")\n            start = robot.time()\n"
                    "            cycles = cycles + 1\n    robot.wait(0.02)\nrobot.stop()\n",
        "hints": ["Remember when you entered a state: start = robot.time(). Then t = robot.time() - start.",
                  "Each state checks its own timer and switches: if t > 2: state = \"SLOW\" …",
                  "    elif state == \"STOP\":\n        robot.stop()\n        if t > 2:\n            state = \"GO\"\n            start = robot.time()"],
        "check": '''expect(uses("state_machines") or "state ==" in source, "Use a state variable: if state == \\"GO\\": … elif state == \\"SLOW\\": …")
r = sim()
leds = [(e["t"], e["color"]) for e in r.events if e["type"] == "led"]
seq = "".join(c[0] for _, c in leds)
expect(seq.count("gyr") >= 2, f"I saw the LED colours {[c for _, c in leds]}. I need green → yellow → red twice.")
ts, xs = r.series("t"), r.series("x")
def moved(t0, t1):
    pts = [x for tt, x in zip(ts, xs) if t0 + 0.1 <= tt <= t1]
    return (max(pts) - min(pts)) if len(pts) > 1 else 0.0
speed = {"g": [], "y": []}
for (t0, c), (t1, _) in zip(leds, leds[1:]):
    if c == "red":
        expect(moved(t0, t1) < 1, f"The robot moved {moved(t0, t1):.0f} cm while the light was red! 🚨")
        expect(t1 - t0 >= 1.8, f"Red only lasted {t1 - t0:.1f} s — stay stopped for 2 s.")
    if c in ("green", "yellow") and t1 - t0 > 0.3:
        speed[c[0]].append(moved(t0, t1) / (t1 - t0))
expect(speed["g"] and speed["y"] and min(speed["g"]) > max(speed["y"]) * 1.5, "Drive slower on yellow than on green (power 15 vs 40).")
expect(min(speed["y"]) > 1, "On yellow, keep rolling slowly (power 15) — don't stop yet.")
SUCCESS = "Green, yellow, red, repeat — a perfect state machine! 🚦"
''',
        "xp": 15,
    },
    {
        "id": "p_state_machines_2", "concept": "state_machines", "title": "Patrol guard", "difficulty": 2,
        "task": "<p>A security robot patrols a hall. State <b>PATROL</b>: drive forward until a wall is closer than 20 cm, then "
                "switch to <b>TURN</b>: spin 180° and go back to PATROL. After <b>4 turns</b>, stop and say \"Patrol done\". "
                "The check uses halls of different lengths!</p>",
        "goals": ["States PATROL and TURN", "Turn around at each wall", "Stop after 4 turns, no crashes"],
        "arena": PATROL,
        "starter": "state = \"PATROL\"\nwhile robot.distance() > 20:\n    robot.drive(50, 50)\n    robot.wait(0.02)\nrobot.stop()\n",
        "solution": "state = \"PATROL\"\nturns = 0\nwhile turns < 4:\n    if state == \"PATROL\":\n        robot.drive(50, 50)\n"
                    "        if robot.distance() < 20:\n            state = \"TURN\"\n    elif state == \"TURN\":\n        robot.stop()\n"
                    "        robot.turn(180)\n        turns = turns + 1\n        state = \"PATROL\"\n    robot.wait(0.02)\n"
                    "robot.stop()\nrobot.say(\"Patrol done\")\n",
        "hints": ["Keep a counter turns = 0 and loop while turns < 4.",
                  "In TURN: robot.turn(180), turns = turns + 1, state = \"PATROL\".",
                  "    elif state == \"TURN\":\n        robot.stop()\n        robot.turn(180)\n        turns = turns + 1\n        state = \"PATROL\""],
        "check": '''expect(uses("state_machines") or "state ==" in source, "Use a state variable with PATROL and TURN.")
expect(calls("distance") >= 1, "Use robot.distance() to find the walls.")
for size, lab in (([260, 100], "long hall"), ([180, 100], "short hall")):
    r = sim(size=size, label=lab)
    expect(r.crashes == 0, f"({lab}) the robot hit a wall. Turn when the distance is under 20 cm.")
    xs = r.series("x")
    flips, direction, anchor = 0, 0, xs[0]
    for x in xs:
        if direction >= 0 and x < anchor - 5:
            flips += direction > 0
            direction, anchor = -1, x
        elif direction <= 0 and x > anchor + 5:
            flips += direction < 0
            direction, anchor = 1, x
        elif (direction > 0 and x > anchor) or (direction < 0 and x < anchor):
            anchor = x
    expect(flips >= 3, f"({lab}) the robot turned back only {flips} time(s). Patrol back and forth!")
    expect(r.end_reason == "done", f"({lab}) the robot was still patrolling when time ran out. Stop after 4 turns.")
    expect(flips <= 4, f"({lab}) the robot patrolled too many laps ({flips} turn-backs). Stop after 4 turns.")
    expect(r.said("patrol done"), "Say \\"Patrol done\\" at the end.")
SUCCESS = "Hall secured! 💂"
''',
        "xp": 20,
    },
    {
        "id": "p_behaviors_jam", "concept": "behaviors", "title": "Honk in the traffic jam", "difficulty": 3,
        "task": "<p>Follow the road. A truck is parked on it! Switch to a <b>WAIT</b> state about 20 cm before it (never touch "
                "it), turn the LED red and <b>honk (beep) once every second</b> while you wait. Use <code>robot.time()</code> "
                "to space out the honks.</p>",
        "goals": ["Follow the line, stop before the truck", "WAIT state with a red LED", "Honk about once per second"],
        "arena": HONK_ROAD,
        "starter": "state = \"DRIVE\"\nwhile True:\n    if state == \"DRIVE\":\n        error = robot.floor_left() - robot.floor_right()\n"
                   "        robot.drive(40 + 0.4 * error, 40 - 0.4 * error)\n        # TODO: WAIT when something is close\n    robot.wait(0.02)\n",
        "solution": "state = \"DRIVE\"\nlast_honk = 0\nwhile True:\n    if state == \"DRIVE\":\n        error = robot.floor_left() - robot.floor_right()\n"
                    "        robot.drive(40 + 0.4 * error, 40 - 0.4 * error)\n        if robot.distance() < 20:\n            state = \"WAIT\"\n"
                    "            robot.led(\"red\")\n    elif state == \"WAIT\":\n        robot.stop()\n        if robot.time() - last_honk >= 1:\n"
                    "            robot.beep(440)\n            last_honk = robot.time()\n        if robot.distance() > 25:\n"
                    "            state = \"DRIVE\"\n            robot.led(\"green\")\n    robot.wait(0.02)\n",
        "hints": ["In DRIVE: if robot.distance() < 20, switch to WAIT and set the LED red.",
                  "Remember when you last honked: last_honk = robot.time(). Honk again when a second has passed.",
                  "if robot.time() - last_honk >= 1:\n    robot.beep(440)\n    last_honk = robot.time()"],
        "check": '''expect(calls("distance") >= 1, "Use robot.distance() to see the truck.")
for box, lab in (([[200, 50, 12, 20]], "truck at 200"), ([[140, 50, 12, 20]], "truck closer")):
    r = sim(boxes=box, label=lab)
    bx = box[0][0]
    expect(r.crashes == 0, f"({lab}) you hit the truck!")
    expect(bx - 40 <= r.x <= bx - 10, f"({lab}) the robot waited at x = {r.x:.0f}. Stop about 20 cm before the truck (it starts at x = {bx}).")
    expect(r.led_colors() and r.led_colors()[-1] == "red", f"({lab}) show WAIT with a red LED.")
    beeps = [e["t"] for e in r.events if e["type"] == "beep"]
    expect(len(beeps) >= 5, f"({lab}) I heard {len(beeps)} honk(s) while waiting. Honk once every second!")
    gaps = [b - a for a, b in zip(beeps, beeps[1:])]
    expect(min(gaps) >= 0.8, f"({lab}) some honks were only {min(gaps):.2f} s apart. Space them about 1 second apart with robot.time().")
SUCCESS = "HONK… HONK… Patient and loud! 🚚📢"
''',
        "xp": 30,
    },
]
