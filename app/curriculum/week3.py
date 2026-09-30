"""Week 3 — Follow the line: floor sensors, thresholds, bang-bang and P/PD control."""
import copy
import math


# ---------------------------------------------------------------------------
# track-building helpers (run once at import time; the arenas are plain dicts)
# ---------------------------------------------------------------------------
def _arc(cx, cy, r, a0, a1, n):
    return [[round(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), 1),
             round(cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)), 1)] for i in range(n + 1)]


def _stadium(cx, cy, length, r, n=14):
    """A running-track oval (two straights + two half circles), counter-clockwise."""
    h = length / 2
    return _arc(cx + h, cy, r, -90, 90, n) + _arc(cx - h, cy, r, 90, 270, n)


def _turtle(x, y, h, moves, step=4.0):
    """Lay tape like a turtle: ("s", length) goes straight, ("a", radius, degrees) arcs (+ = left)."""
    pts = [[round(x, 1), round(y, 1)]]
    for m in moves:
        if m[0] == "s":
            n = max(1, int(m[1] // 20))
            for _ in range(n):
                x += m[1] / n * math.cos(math.radians(h))
                y += m[1] / n * math.sin(math.radians(h))
                pts.append([round(x, 1), round(y, 1)])
        else:
            r, deg = m[1], m[2]
            n = max(2, int(abs(deg) * math.pi / 180 * r / step))
            side = 1 if deg > 0 else -1
            cx = x - side * r * math.sin(math.radians(h))
            cy = y + side * r * math.cos(math.radians(h))
            a0 = h - side * 90
            for i in range(1, n + 1):
                a = a0 + deg * i / n
                pts.append([round(cx + r * math.cos(math.radians(a)), 1), round(cy + r * math.sin(math.radians(a)), 1)])
            x = cx + r * math.cos(math.radians(a0 + deg))
            y = cy + r * math.sin(math.radians(a0 + deg))
            h += deg
    return pts


def _loop(x, y, moves):
    """A closed track: the turtle ends where it started, so drop the duplicate last point."""
    return _turtle(x, y, 0, moves)[:-1]


def _along(pts, every, skip):
    """Points every `every` cm along a path, starting `skip` cm in (for gems on the tape)."""
    out, acc = [], every - skip
    for a, b in zip(pts, pts[1:]):
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        d = 0.0
        while acc + (seg - d) >= every:
            d += every - acc
            acc = 0.0
            out.append([round(a[0] + (b[0] - a[0]) * d / seg, 1), round(a[1] + (b[1] - a[1]) * d / seg, 1)])
        acc += seg - d
    return out


def _mirror(a, name):
    """Flip an arena upside down (y -> H - y): every left turn becomes a right turn."""
    H = a["size"][1]
    m = copy.deepcopy(a)
    m["name"] = name
    m["start"] = [a["start"][0], H - a["start"][1], -a["start"][2]]
    m["lines"] = [{**ln, "pts": [[x, round(H - y, 1)] for x, y in ln["pts"]]} for ln in a.get("lines", [])]
    if "gems" in a:
        m["gems"] = [[x, round(H - y, 1)] for x, y in a["gems"]]
    if "zones" in a:
        m["zones"] = [{**z, "rect": [z["rect"][0], H - z["rect"][1] - z["rect"][3], z["rect"][2], z["rect"][3]]}
                      for z in a["zones"]]
    if "labels" in a:
        m["labels"] = [[x, H - y, t] for x, y, t in a["labels"]]
    if a.get("finish"):
        x1, y1, x2, y2 = a["finish"]
        m["finish"] = [x2, H - y2, x1, H - y1]     # swap ends so "forward" still points along the track
    return m


def _with_alt(alt, body):
    """Put a second (mirrored) test arena into a check snippet as ALT."""
    return "ALT = " + repr(alt) + "\n" + body


# ---------------------------------------------------------------------------
# Project 5 — Line Tracker arenas
# ---------------------------------------------------------------------------
CALIB = {"name": "Sensor Lab", "size": [240, 160], "start": [40, 80, 0], "time_limit": 15,
         "lines": [{"pts": [[90, 40], [90, 120]], "width": 12}],
         "labels": [[90, 128, "black band"], [40, 60, "start"]]}

GRAY_FLOOR = [{"name": "gray floor", "rect": [0, 0, 240, 160], "color": "gray"}]

STOPLINE = {"name": "Stop Line", "size": [260, 140], "start": [30, 70, 0], "time_limit": 20,
            "lines": [{"pts": [[170, 30], [170, 110]]}],
            "labels": [[170, 118, "stop here"]]}

_BEAN = _turtle(70, 40, 0, [("s", 130), ("a", 40, 180), ("s", 25.4), ("a", 28, 45), ("a", 28, -90),
                            ("a", 28, 45), ("s", 25.4), ("a", 40, 180)])
BEAN = {"name": "Bean Loop", "size": [270, 160], "start": [90, 40, 0], "time_limit": 60,
        "lines": [{"pts": _BEAN[:-1], "closed": True}],
        "gems": _along(_BEAN, 60, 20)[1:]}
BEAN_FLIP = _mirror(BEAN, "Bean Loop (flipped)")
BEAN_FAST = {**BEAN, "time_limit": 45}
BEAN_FAST_FLIP = _mirror(BEAN_FAST, "Bean Loop (flipped)")

FINISH = {"name": "Finish Line", "size": [300, 180], "start": [40, 50, 0], "time_limit": 40,
          "lines": [{"pts": _turtle(30, 50, 0, [("s", 80), ("a", 35, 90), ("s", 20), ("a", 35, -90), ("s", 50),
                                                ("a", 30, -90), ("s", 40)])}],
          "gems": [[141.8, 70.5], [150.6, 124.0], [200.1, 140.0], [252.3, 130.0]],
          "zones": [{"name": "finish", "rect": [245, 30, 30, 40], "color": "red", "label": "🏁"}]}
FINISH_FLIP = _mirror(FINISH, "Finish Line (flipped)")

SHARP = {"name": "Sharp Turns", "size": [300, 180], "start": [40, 40, 0], "time_limit": 60,
         "lines": [{"pts": [[25, 40], [130, 40], [130, 140], [180, 140]]},
                   {"pts": [[192, 140], [260, 140], [260, 70], [190, 70]]}],
         "gems": [[100, 40], [130, 100], [225, 140], [260, 105]],
         "zones": [{"name": "finish", "rect": [150, 55, 40, 30], "color": "red", "label": "🏁"}],
         "labels": [[186, 150, "gap!"]]}
SHARP_FLIP = _mirror(SHARP, "Sharp Turns (flipped)")

LINE_CITY = {"name": "Line City", "size": [320, 220], "start": [60, 40, 0], "time_limit": 120,
             "lines": [{"pts": _loop(60, 40, [("s", 200), ("a", 40, 180), ("s", 40), ("a", 15, 90), ("s", 25),
                                              ("a", 15, -180), ("s", 25), ("a", 15, 90), ("s", 100), ("a", 40, 180)]),
                        "closed": True},
                       {"pts": [[110, 120], [110, 175]]}],
             "zones": [{"name": "finish", "rect": [95, 175, 30, 30], "color": "red", "label": "🏁"}],
             "gems": [[160, 40], [300, 80], [60, 120]]}

# ---------------------------------------------------------------------------
# Project 5 — Line Tracker code
# ---------------------------------------------------------------------------
LT_S1 = '''# 🔦 Floor sensor lab
white = robot.floor()
print("white:", white)

# TODO: drive 44 cm onto the black band, read the floor again,
#       then print the threshold (halfway between the two)
'''

LT_S1_SOL = '''# 🔦 Floor sensor lab
white = robot.floor()
print("white:", white)

robot.forward(44)            # the sensor is now over the black band
black = robot.floor()
print("black:", black)

threshold = (white + black) / 2
print("threshold:", threshold)
'''

LT_S2 = '''# 🛑 Stop at the line
threshold = 49       # halfway between white (92) and black (6)

robot.drive(40, 40)
# TODO: keep driving while the floor is brighter than the threshold,
#       then stop
'''

LT_S2_SOL = '''# 🛑 Stop at the line
threshold = 49       # halfway between white (92) and black (6)

robot.drive(40, 40)
while robot.floor() > threshold:     # still white: keep going
    robot.wait(0.02)
robot.stop()
robot.say("Line!")
'''

LT_S3 = LT_S2_SOL + '''
# TODO: new arena! Replace the code above with a loop that follows
#       the RIGHT edge of the tape using only the centre sensor
'''

LT_S3_SOL = '''# 〰️ Zig-zag edge follower (bang-bang, one sensor)
threshold = 49

while True:
    if robot.floor() < threshold:
        robot.drive(50, 20)     # on black: steer right, off the tape
    else:
        robot.drive(20, 50)     # on white: steer left, back to the tape
    robot.wait(0.02)
'''

LT_S4 = LT_S3_SOL + '''
# TODO: use TWO sensors instead: floor("left") and floor("right")
'''

LT_S4_SOL = '''# 👀 Two-sensor line follower
threshold = 49

while True:
    left = robot.floor("left")
    right = robot.floor("right")
    if left < threshold:            # tape under the left eye: turn left
        robot.drive(10, 50)
    elif right < threshold:         # tape under the right eye: turn right
        robot.drive(50, 10)
    else:                           # tape between the eyes: full speed ahead
        robot.drive(50, 50)
    robot.wait(0.02)
'''

LT_S5 = LT_S4_SOL.replace("while True:\n", "while True:\n    # TODO: stop in the red finish box\n", 1)

LT_S5_SOL = '''# 🏁 Two-sensor line follower that stops at the finish
threshold = 49

while True:
    if robot.color() == "red":      # the colour sensor knows red from black
        robot.forward(10)           # roll the wheels into the box too
        robot.stop()
        robot.led("green")
        robot.say("Finished!")
        break
    left = robot.floor("left")
    right = robot.floor("right")
    if left < threshold:
        robot.drive(10, 50)
    elif right < threshold:
        robot.drive(50, 10)
    else:
        robot.drive(50, 50)
    robot.wait(0.02)
'''

LT_BOSS_SOL = LT_S5_SOL.replace("# 🏁 Two-sensor line follower that stops at the finish",
                                "# 👾 Sharp turns + a gap: pivot hard, and go straight over the gap").replace(
    "robot.drive(10, 50)", "robot.drive(-20, 50)     # inside wheel backwards = sharp pivot").replace(
    "robot.drive(50, 10)", "robot.drive(50, -20)")

STILL = '''
def still(r):
    """Did the robot really stop (not just spin on the spot)?"""
    if r.end_reason == "done":
        return True
    f = r.frames
    k = max(0, len(f["t"]) - 25)
    return (max(f["x"][k:]) - min(f["x"][k:]) < 0.5 and max(f["y"][k:]) - min(f["y"][k:]) < 0.5
            and max(f["h"][k:]) - min(f["h"][k:]) < 2)
'''

LT_S1_CHECK = '''import re as _re

def threshold_of(r):
    rows = [l for l in r.lines if "threshold" in l.lower()]
    if not rows:
        return None
    nums = _re.findall(r"-?\\d+(?:\\.\\d+)?", rows[-1])
    return float(nums[-1]) if nums else None

expect(calls("floor") >= 2, "Read the floor sensor twice: once on the white floor and once on the black band.")
r = sim(label="white floor")
t = threshold_of(r)
expect(t is not None, 'I can\\'t find your threshold. Print it on its own line, e.g. print("threshold:", threshold)')
expect(abs(t - 49) <= 4, f"On the white floor your threshold is {t:g}, but halfway between white (about 92) and black "
       f"(about 6) is about 49. Is the sensor really over the black band when you read it?")
r = sim(arena(zones=[{"name": "gray floor", "rect": [0, 0, 240, 160], "color": "gray"}]), label="gray floor")
t2 = threshold_of(r)
expect(t2 is not None and abs(t2 - 35) <= 4, f"In a lab with a GRAY floor your program printed threshold {t2}. The gray floor "
       f"reads about 64, so halfway to black is about 35. Work the threshold out from your two readings — don't type the number in!")
SUCCESS = f"Calibrated! White lab → {t:g}, gray lab → {t2:g}. Same code, different floors 🔦"
'''

LT_S2_CHECK = '''expect(calls("floor") >= 1, "Read the floor sensor with robot.floor() so the robot knows when it reaches the line.")
expect(loops() >= 1, "Use a while loop that keeps checking the floor while the robot drives.")
for x, label in ((170, "line at 170 cm"), (115, "line moved to 115 cm")):
    r = sim(arena(lines=[{"pts": [[x, 30], [x, 110]]}], labels=[[x, 118, "stop here"]]), label=label)
    sensor = r.x + 6.5
    expect(r.crashes == 0, f"With the {label} the robot crashed into the wall — it never noticed the black line.")
    expect(r.x > 40, f"With the {label} the robot hardly moved. Keep driving WHILE the floor is brighter than the threshold.")
    expect(abs(sensor - x) <= 3, f"With the {label} the sensor stopped at x = {sensor:.0f} cm, but the line is at {x} cm. "
           f"Stop as soon as robot.floor() drops below the threshold.")
SUCCESS = "Stopped right on the line both times — that's a sensor doing its job 🛑"
'''

LT_S3_CHECK = _with_alt(BEAN_FLIP, '''expect(calls("floor") >= 1, "Use robot.floor() to look at the tape.")
expect(loops() >= 1, "Use a while True: loop so the robot keeps checking and correcting.")
for a, label in ((ARENA, "Bean Loop"), (ALT, "flipped Bean Loop")):
    r = sim(a, label=label)
    expect(r.crashes == 0, f"On the {label} the robot crashed — it lost the line. Make the turns in your if/else stronger.")
    expect(r.gems == r.gems_total, f"On the {label} you collected {r.gems}/{r.gems_total} gems in {a['time_limit']:g} s. "
           f"Watch the replay: does the robot lose the line, or is it just too slow? (try powers like 50 and 20)")
    expect(r.line_ratio >= 0.8, f"On the {label} the robot was near the tape only {r.line_ratio:.0%} of the time. Stay on the edge!")
SUCCESS = "Zig, zag, zig, zag… all the way round! That's bang-bang control 〰️"
''')

LT_S4_CHECK = _with_alt(BEAN_FAST_FLIP, '''import ast as _ast
sides = set()
for n in _ast.walk(tree):
    if isinstance(n, _ast.Call):
        name = getattr(n.func, "attr", getattr(n.func, "id", ""))
        if name == "floor":
            for a in list(n.args) + [k.value for k in n.keywords]:
                if isinstance(a, _ast.Constant):
                    sides.add(a.value)
        elif name in ("floor_left", "floor_right"):
            sides.add(name[6:])
expect("left" in sides and "right" in sides, 'Use both side sensors: robot.floor("left") and robot.floor("right").')
for a, label in ((ARENA, "Bean Loop"), (ALT, "flipped Bean Loop")):
    r = sim(a, label=label)
    expect(r.crashes == 0, f"On the {label} the robot crashed — it lost the line.")
    expect(r.gems == r.gems_total, f"On the {label} you got {r.gems}/{r.gems_total} gems in {a['time_limit']:g} s. "
           f"When the tape is between the sensors, drive straight at full cruising speed!")
    t = max(e["t"] for e in r.events if e["type"] == "gem")
    expect(t <= 40, f"On the {label} the last gem took {t:.0f} s. Beat 40 s — drive straight (e.g. 50, 50) when neither sensor sees black.")
    expect(r.line_ratio >= 0.85, f"On the {label} the robot was on the tape only {r.line_ratio:.0%} of the time.")
SUCCESS = f"Two eyes, no zig-zag: the lap took {t:.0f} s 👀"
''')

LT_S5_CHECK = _with_alt(FINISH_FLIP, STILL + '''for a, label in ((ARENA, "Finish Line"), (ALT, "flipped Finish Line")):
    r = sim(a, label=label)
    expect(r.crashes == 0, f"On the {label} the robot crashed.")
    expect(r.gems == r.gems_total, f"On the {label} you only got {r.gems}/{r.gems_total} gems — follow the line all the way to the finish.")
    expect(r.visited("finish"), f"On the {label} the robot's body never got into the red 🏁 box. The sensor is 6.5 cm in "
           f"FRONT of the wheels, so after you see red, roll about 10 cm further before stopping.")
    expect(still(r), f"On the {label} the robot reached the red box but kept moving. Red reads about 46 — nearly as dark as "
           f"your threshold! Check robot.color() == \\"red\\" first in the loop and stop.")
    expect(r.in_zone("finish"), f"On the {label} the robot stopped at ({r.x:.0f}, {r.y:.0f}), not inside the red box. The sensor is "
           f"6.5 cm in FRONT of the wheels — roll about 10 cm more after you see red.")
    expect(r.line_ratio >= 0.8, f"On the {label} the robot was on the tape only {r.line_ratio:.0%} of the time.")
SUCCESS = "Chequered flag! Stopped right in the box 🏁"
''')

LT_BOSS_CHECK = _with_alt(SHARP_FLIP, STILL + '''for a, label in ((ARENA, "Sharp Turns"), (ALT, "flipped Sharp Turns")):
    r = sim(a, label=label)
    expect(r.crashes == 0, f"On the {label} the robot crashed.")
    expect(r.gems == r.gems_total, f"On the {label} you got {r.gems}/{r.gems_total} gems. Watch the replay: where does it lose the line — "
           f"a sharp corner (turn harder: one wheel backwards) or the gap (drive straight when both sensors see white)?")
    expect(r.visited("finish") and r.in_zone("finish") and still(r),
           f"On the {label} the robot didn't stop inside the red 🏁 box (ended at {r.x:.0f}, {r.y:.0f}).")
    expect(r.line_ratio >= 0.75, f"On the {label} the robot was near the tape only {r.line_ratio:.0%} of the time — no shortcuts!")
SUCCESS = "Sharp turns ✓ Gap ✓ Finish ✓ — LINE TRACKER CHAMPION 🏆"
''')

LINE_TRACKER = {
    "id": "line_tracker", "week": 3, "order": 5, "title": "Line Tracker", "emoji": "🛤️",
    "tagline": "Teach your robot to see black tape and follow it wherever it goes",
    "story": "The factory is getting robot carts, and they need to know where to drive. The engineers stuck black "
             "tape on the floor as a road. Your job: build the cart's brain — it has to see the tape, stay on it "
             "around every bend, and stop exactly at the red finish box.",
    "concepts": ["thresholds", "sensors", "feedback"],
    "expected_minutes": 110,
    "real_world": "Warehouse and hospital robots (and many factory carts) follow tape or painted lines on the floor, "
                  "and robot competitions like RoboCup Junior Rescue Line are all about fast, reliable line following.",
    "build_it": "A micro:bit car like the Cutebot or a LEGO SPIKE colour sensor pointed at the floor works exactly the "
                "same: stick black electrical tape on white paper and run these programs.",
    "steps": [
        {
            "id": "s1", "title": "Meet the floor sensor",
            "learn": "<p>Under the robot's nose are three <b>floor sensors</b>. Each one shines a tiny light at the floor and "
                     "measures how much bounces back: white floor reflects a lot (about <b>92</b>), black tape swallows the "
                     "light (about <b>6</b>).</p>"
                     "<pre>value = robot.floor()          # centre sensor, 0 (dark) … 100 (bright)\n"
                     "print(\"I see\", value)</pre>"
                     "<p>To decide \"is this black?\" the robot needs a <b>threshold</b> — a cut-off number. The safest one is "
                     "exactly <b>halfway</b> between white and black:</p>"
                     "<pre>threshold = (white + black) / 2</pre>"
                     "<p>But floors are different! A gray lab floor, a shiny table or a sunny room all change the numbers. That's "
                     "why real robots <b>calibrate</b>: they measure white and black first and work the threshold out. Your "
                     "phone does the same thing when it auto-adjusts the screen brightness.</p>",
            "task": "<p>Read the floor on the white start, drive <b>44 cm</b> so the sensor is over the black band, read it again, "
                    "and print the threshold: <code>print(\"threshold:\", threshold)</code>. Work it out from your two readings — "
                    "I'll also test your program in a lab with a <b>gray</b> floor!</p>",
            "goals": ["Read white and black", "Compute the halfway threshold", "Works on a gray floor too"],
            "arena": CALIB, "starter": LT_S1, "solution": LT_S1_SOL,
            "hints": ["After robot.forward(44) the sensor is right over the black band.",
                      "Save the second reading in a variable called black, just like white.",
                      "black = robot.floor()\nthreshold = (white + black) / 2\nprint(\"threshold:\", threshold)"],
            "check": LT_S1_CHECK,
            "concepts": ["sensors", "thresholds"], "xp": 20,
        },
        {
            "id": "s2", "title": "Stop at the line",
            "learn": "<p>Now let's use the threshold <i>while</i> driving. A <code>while</code> loop repeats as long as its "
                     "condition is true:</p>"
                     "<pre>robot.drive(40, 40)\nwhile robot.floor() > threshold:   # still bright = still white\n"
                     "    robot.wait(0.02)\nrobot.stop()</pre>"
                     "<p>Read it like a sentence: <i>\"while the floor is brighter than the threshold, keep waiting (and "
                     "driving)\"</i>. The moment the sensor sees the tape, the loop ends and the robot stops.</p>"
                     "<p>This is the first step from a <b>blind</b> robot to a <b>seeing</b> one. A <code>forward(133)</code> "
                     "only works if you measured perfectly. A sensor loop works wherever the line is.</p>",
            "task": "<p>Drive forward and stop <b>as soon as the sensor reaches the black line</b>. I'll move the line to test "
                    "you, so no measuring with a ruler!</p>",
            "goals": ["Use a while loop with robot.floor()", "Stop on the line", "Works when the line moves"],
            "arena": STOPLINE, "starter": LT_S2, "solution": LT_S2_SOL,
            "hints": ["The robot should keep going while robot.floor() is bigger than the threshold.",
                      "Inside the loop you only need robot.wait(0.02) — the motors are already on.",
                      "while robot.floor() > threshold:\n    robot.wait(0.02)\nrobot.stop()"],
            "check": LT_S2_CHECK,
            "concepts": ["sensors", "thresholds", "control_loop"], "xp": 20,
        },
        {
            "id": "s3", "title": "Zig-zag along the edge",
            "learn": "<p>A robot that follows a line never stops asking <i>\"where's the tape?\"</i> and correcting. That's "
                     "<b>closed-loop control</b>: sense → decide → act → sense again. Your week-1 programs were "
                     "<b>open-loop</b>: plan the moves, then hope. Closed loop is like riding a bike with your eyes open — "
                     "tiny wobbles get fixed all the time.</p>"
                     "<p>Trick: don't follow the <i>middle</i> of the tape, follow its <b>edge</b>. Keep the centre sensor "
                     "on the right edge of the tape:</p>"
                     "<pre>while True:\n    if robot.floor() < threshold:   # on black → too far left\n"
                     "        robot.drive(50, 20)          # steer right\n    else:                           # on white → too far right\n"
                     "        robot.drive(20, 50)          # steer left\n    robot.wait(0.02)</pre>"
                     "<p>There are only two answers — full left or full right — so this is called <b>bang-bang control</b>. "
                     "It works, but watch the replay: the robot <b>zig-zags</b> the whole way, wasting time going sideways.</p>",
            "task": "<p>New arena! Replace your code with a <b>one-sensor bang-bang edge follower</b> and collect all the gems "
                    "around the Bean Loop. I'll also test it on the loop flipped upside down (right turns become left turns).</p>",
            "goals": ["while True loop with if/else", "Collect every gem", "Works on the flipped loop too"],
            "arena": BEAN, "starter": LT_S3, "solution": LT_S3_SOL,
            "hints": ["The loop needs to decide every 0.02 s: black → steer one way, white → steer the other.",
                      "Steering right means the LEFT wheel goes faster: robot.drive(50, 20).",
                      "if robot.floor() < threshold:\n    robot.drive(50, 20)\nelse:\n    robot.drive(20, 50)"],
            "check": LT_S3_CHECK,
            "concepts": ["feedback", "thresholds", "control_loop"], "xp": 30,
        },
        {
            "id": "s4", "title": "Two eyes are better than one",
            "learn": "<p>With one sensor the robot can't tell <i>\"I'm on the edge\"</i> from <i>\"I'm drifting\"</i>, so it "
                     "must always be turning. With <b>two</b> sensors either side of the tape it can:</p>"
                     "<ul><li>both white → the tape is between my eyes → <b>go straight, fast</b></li>"
                     "<li>left sees black → the tape went left → <b>turn left</b></li>"
                     "<li>right sees black → <b>turn right</b></li></ul>"
                     "<pre>left = robot.floor(\"left\")\nright = robot.floor(\"right\")\nif left < threshold:\n"
                     "    robot.drive(10, 50)    # curve left\nelif right < threshold:\n"
                     "    robot.drive(50, 10)    # curve right\nelse:\n    robot.drive(50, 50)</pre>"
                     "<p>No more zig-zag on the straights, so the lap is much faster. Many real line-following robots use "
                     "a whole row of 5–8 sensors for the same reason.</p>",
            "task": "<p>Rewrite your follower to use <b>both side sensors</b> and collect every gem in <b>under 40 s</b> — on "
                    "the normal and the flipped loop.</p>",
            "goals": ["Use floor(\"left\") and floor(\"right\")", "All gems", "Under 40 seconds"],
            "arena": BEAN_FAST, "starter": LT_S4, "solution": LT_S4_SOL,
            "hints": ["Read both sensors into variables at the top of the loop.",
                      "Use if / elif / else: left black, right black, or neither.",
                      "if left < threshold:\n    robot.drive(10, 50)\nelif right < threshold:\n    robot.drive(50, 10)\nelse:\n    robot.drive(50, 50)"],
            "check": LT_S4_CHECK,
            "concepts": ["sensors", "feedback", "decisions"], "xp": 30,
        },
        {
            "id": "s5", "title": "Stop at the finish",
            "learn": "<p>The road ends in a red 🏁 box. Easy — stop when you see red? Careful! To a floor sensor red "
                     "reads about <b>46</b>, and our threshold is 49. Red looks <i>almost black</i>, so both side sensors "
                     "shout \"tape!\" and the robot spins around confused. Try it and watch!</p>"
                     "<p>That's a real engineering lesson: <b>a threshold only separates two things</b>. For colours, use the "
                     "colour sensor instead:</p>"
                     "<pre>if robot.color() == \"red\":\n    robot.forward(10)\n    robot.stop()\n    break      # jump out of the while loop</pre>"
                     "<p>Why <code>forward(10)</code>? The sensors sit <b>6.5 cm in front</b> of the wheels, so when the "
                     "sensor sees red the robot's body isn't in the box yet. <code>break</code> ends the loop and the "
                     "program.</p>",
            "task": "<p>New track! Follow the line and <b>stop inside the red 🏁 box</b> (whole robot in, motors off). Tested "
                    "on the normal and the flipped track.</p>",
            "goals": ["Follow the line, get the gems", "Stop inside the red box", "Works on the flipped track"],
            "arena": FINISH, "starter": LT_S5, "solution": LT_S5_SOL,
            "hints": ["Check the colour FIRST in your loop, before the line-following if/elif/else.",
                      "robot.color() returns a word like \"red\" or \"white\".",
                      "if robot.color() == \"red\":\n    robot.forward(10)\n    robot.stop()\n    break"],
            "check": LT_S5_CHECK,
            "concepts": ["sensors", "thresholds", "decisions"], "xp": 30,
        },
    ],
    "boss": {
        "id": "boss", "title": "Sharp turns and the gap",
        "learn": "<p>Real tape roads are messy: sharp corners, and places where the tape is torn. Two tricks help:</p>"
                 "<ul><li><b>Sharp corners</b>: a gentle turn like <code>drive(20, 50)</code> is too slow — the tape escapes. "
                 "Spin one wheel <b>backwards</b> (<code>drive(-20, 50)</code>) to pivot hard.</li>"
                 "<li><b>A gap</b>: when both side sensors see white, keep driving <b>straight</b>. The tape usually "
                 "continues on the other side.</li></ul>"
                 "<p>Your two-sensor follower might already do both. Run it and watch the replay closely!</p>",
        "task": "<p>Follow the Sharp Turns track — four 90° corners and a gap in the tape — collect the gems "
                "and stop in the red 🏁 box. Tested normal and flipped.</p>",
        "goals": ["All 4 gems", "Cross the gap", "Stop in the red box"],
        "arena": SHARP, "starter": LT_S5_SOL, "solution": LT_BOSS_SOL,
        "hints": ["Run your mission-5 program first and see where it goes wrong.",
                  "Turn harder in the corners: make the inside wheel go backwards.",
                  "if left < threshold:\n    robot.drive(-20, 50)\nelif right < threshold:\n    robot.drive(50, -20)\nelse:\n    robot.drive(50, 50)"],
        "check": LT_BOSS_CHECK,
        "concepts": ["feedback", "sensors", "thresholds"], "xp": 80,
    },
    "remix": {
        "prompt": "Make it yours! Line City has a loop, a hairpin and a spur road that ends at the finish.",
        "ideas": ["Change the LED colour depending on which way the robot is turning",
                  "Beep every time the robot finds the tape again after losing it",
                  "Count gems or laps with a variable and say the number",
                  "Use all THREE sensors (left, centre, right) for a smoother, faster follower"],
        "arena": LINE_CITY,
    },
}

# ---------------------------------------------------------------------------
# Project 6 — Race Track Pro arenas (all closed tracks with a finish line)
# ---------------------------------------------------------------------------
SPEEDWAY = {"name": "Speedway", "size": [320, 210], "start": [140, 55, 0], "time_limit": 45,
            "lines": [{"pts": _stadium(160, 105, 120, 50), "closed": True, "width": 3}],
            "finish": [130, 70, 130, 40], "labels": [[130, 30, "🏁"]]}
SPEEDWAY_FLIP = _mirror(SPEEDWAY, "Speedway (clockwise)")
SPEEDWAY_FAST = {**SPEEDWAY, "time_limit": 27}
SPEEDWAY_FAST_FLIP = _mirror(SPEEDWAY_FAST, "Speedway (clockwise)")

TWISTY = {"name": "Twisty Loop", "size": [300, 160], "start": [100, 40, 0], "time_limit": 45,
          "lines": [{"pts": _loop(90, 40, [("s", 140), ("a", 40, 180), ("s", 32), ("a", 22, 60), ("a", 22, -120),
                                           ("a", 22, 60), ("s", 32), ("a", 40, 180)]), "closed": True, "width": 3}],
          "finish": [95, 55, 95, 25], "labels": [[95, 18, "🏁"]]}
TWISTY_FLIP = _mirror(TWISTY, "Twisty Loop (flipped)")

HAIRPIN = {"name": "Hairpin Alley", "size": [310, 160], "start": [100, 40, 0], "time_limit": 30,
           "lines": [{"pts": _loop(80, 40, [("s", 150), ("a", 35, 180), ("s", 40), ("a", 12, 90), ("s", 30), ("a", 12, -180),
                                            ("s", 30), ("a", 12, 90), ("s", 62), ("a", 35, 180)]), "closed": True, "width": 3}],
           "finish": [95, 55, 95, 25], "labels": [[95, 18, "🏁"]]}
HAIRPIN_FLIP = _mirror(HAIRPIN, "Hairpin Alley (flipped)")

GRAND_PRIX = {"name": "Grand Prix", "size": [320, 160], "start": [100, 40, 0], "time_limit": 55,
              "lines": [{"pts": _loop(90, 40, [("s", 150), ("a", 35, 180), ("s", 20), ("a", 12, 90), ("s", 30), ("a", 12, -180),
                                               ("s", 30), ("a", 12, 90), ("s", 22), ("a", 25, 30), ("a", 25, -60), ("a", 25, 30),
                                               ("s", 10), ("a", 35, 180)]), "closed": True, "width": 3}],
              "finish": [95, 55, 95, 25], "labels": [[95, 18, "🏁"]]}
GRAND_PRIX_FLIP = _mirror(GRAND_PRIX, "Grand Prix (flipped)")


def _monaco(r, name="Monaco", limit=90):
    return {"name": name, "size": [290, 170], "start": [100, 40, 0], "time_limit": limit,
            "lines": [{"pts": _loop(80, 40, [("s", 90), ("a", 20, 90), ("a", 20, -90), ("s", 20), ("a", 30, 180),
                                             ("s", 6), ("a", r, 90), ("s", 15), ("a", r, -180), ("s", 15), ("a", r, 90),
                                             ("s", 20), ("a", r, 90), ("s", 20), ("a", r, -180), ("s", 20), ("a", r, 90),
                                             ("s", 124 - 8 * r), ("a", 50, 180)]), "closed": True, "width": 3}],
            "finish": [95, 55, 95, 25], "labels": [[95, 18, "🏁"]]}


MONACO = _monaco(10)
MONACO_FLIP = _mirror(MONACO, "Monaco (flipped)")
DREAM_TRACK = {**_monaco(8, "Dream Circuit", 180), "size": [290, 170]}

# ---------------------------------------------------------------------------
# Project 6 — Race Track Pro code
# ---------------------------------------------------------------------------
RT_S1 = '''# 〰️ The zig-zag follower from Line Tracker
threshold = 49

while True:
    if robot.floor() < threshold:
        robot.drive(50, 20)     # on black: steer right
    else:
        robot.drive(20, 50)     # on white: steer left
    robot.wait(0.02)

# TODO: replace the if/else with proportional steering:
#       error = robot.floor() - target, turn = Kp * error
'''

RT_S1_SOL = '''# 🏎️ Proportional (P) edge follower
target = 49      # half white, half black = exactly on the right edge
Kp = 0.2         # steering strength: how much to turn per point of error
base = 50        # cruising power

while True:
    error = robot.floor() - target     # + = drifted onto white, - = drifted onto black
    turn = Kp * error
    robot.drive(base - turn, base + turn)
    robot.wait(0.02)
'''

RT_S2 = RT_S1_SOL.replace("    robot.wait(0.02)\n", "    # TODO: plot the error, then tune Kp for the twisty track\n    robot.wait(0.02)\n")

RT_S2_SOL = RT_S1_SOL.replace("Kp = 0.2 ", "Kp = 0.8 ").replace(
    "    robot.wait(0.02)\n", "    robot.plot(\"error\", error)       # watch it on the telemetry graph\n    robot.wait(0.02)\n")

RT_S3 = RT_S2_SOL.replace("base = 50        # cruising power", "base = 50        # TODO: faster! beat 25 s per lap")

RT_S3_SOL = RT_S2_SOL.replace("base = 50        # cruising power", "base = 80        # race pace!")

RT_S4 = RT_S3_SOL.replace("    turn = Kp * error\n", "    turn = Kp * error          # TODO: add a derivative term\n")

RT_S4_SOL = '''# 🏎️ PD edge follower
target = 49
Kp = 2           # P: steer toward the edge
Kd = 1           # D: damping — react to how FAST the error changes
base = 80
last_error = 0

while True:
    error = robot.floor() - target
    derivative = error - last_error      # how much the error changed since last time
    turn = Kp * error + Kd * derivative
    robot.drive(base - turn, base + turn)
    robot.plot("error", error)
    last_error = error                   # remember it for next time
    robot.wait(0.02)
'''

RT_S5 = RT_S4_SOL.replace("base = 80\n", "base = 80        # TODO: 2 laps in under 50 s\n")

RT_S5_SOL = RT_S4_SOL.replace("base = 80\n", "base = 100       # flat out!\n")

RT_BOSS = RT_S5_SOL

RT_BOSS_SOL = '''# 👾 Monaco: PD steering + brake for the corners
target = 49
Kp = 3
Kd = 1
top = 100        # speed on the straights
brake = 1        # slow down by this much per point of error
last_error = 0

while True:
    error = robot.floor() - target
    derivative = error - last_error
    turn = Kp * error + Kd * derivative
    base = top - brake * abs(error)      # big error = we're in a corner = slow down
    robot.drive(base - turn, base + turn)
    robot.plot("error", error)
    last_error = error
    robot.wait(0.02)
'''

PROP_CHECK = '''
def proportional(r, label):
    powers = set(r.series("pl"))
    expect(len(powers) >= 8, f"On the {label} your left motor only used {len(powers)} different powers — that's still bang-bang! "
           f"With turn = Kp * error the powers change smoothly with the error.")
'''

RT_S1_CHECK = _with_alt(SPEEDWAY_FLIP, PROP_CHECK + '''expect(calls("floor") >= 1, "Read the floor sensor with robot.floor() inside your loop.")
expect(uses("pid"), "Make an error variable (error = robot.floor() - target) and steer with Kp * error.")
for a, label in ((ARENA, "Speedway"), (ALT, "clockwise Speedway")):
    r = sim(a, label=label)
    proportional(r, label)
    expect(r.crashes == 0, f"On the {label} the robot crashed — it lost the edge.")
    expect(r.laps >= 1, f"On the {label} the robot didn't finish a lap in {a['time_limit']:g} s (it was on the tape "
           f"{r.line_ratio:.0%} of the time). Check the signs: on white (error > 0) it must steer LEFT.")
    expect(r.line_ratio >= 0.9, f"On the {label} the robot was on the tape only {r.line_ratio:.0%} of the time.")
SUCCESS = f"Smooth! Lap time {r.lap_times[0]:.1f} s — no zig-zag, just gentle corrections 🏎️"
''')

RT_S2_CHECK = _with_alt(TWISTY_FLIP, PROP_CHECK + '''r = sim(label="Twisty Loop")
e = [v for v in r.series("error") if v is not None]
expect(e, 'Plot your error: put robot.plot("error", error) inside the loop, then look at the graph under the arena.')
for a, label in ((ARENA, "Twisty Loop"), (ALT, "flipped Twisty Loop")):
    r = sim(a, label=label)
    proportional(r, label)
    expect(r.crashes == 0, f"On the {label} the robot crashed — it drifted right off the track.")
    expect(r.laps >= 1 and r.line_ratio >= 0.9, f"On the {label} the robot didn't make it round (on the tape "
           f"{r.line_ratio:.0%} of the time). If it drifts off in the tight bends, Kp is too SMALL — the steering is too gentle. Try 0.5, 1, 2…")
SUCCESS = f"Tuned! Lap {r.lap_times[0]:.1f} s. Look at your error graph — small wiggles around 0 mean good control 📈"
''')

RT_S3_CHECK = _with_alt(SPEEDWAY_FAST_FLIP, PROP_CHECK + '''for a, label in ((ARENA, "Speedway"), (ALT, "clockwise Speedway")):
    r = sim(a, label=label)
    proportional(r, label)
    expect(r.crashes == 0, f"On the {label} the robot crashed.")
    expect(r.laps >= 1, f"On the {label} the robot didn't finish a lap within {a['time_limit']:g} s. Turn up base, and if it "
           f"starts losing the line, turn up Kp too.")
    expect(r.lap_times[0] < 25, f"On the {label} your lap took {r.lap_times[0]:.1f} s. Beat 25 s — more base power!")
    expect(r.line_ratio >= 0.9, f"On the {label} the robot was on the tape only {r.line_ratio:.0%} of the time.")
SUCCESS = f"Zoom! {r.lap_times[0]:.1f} s a lap 💨"
''')

RT_S4_CHECK = _with_alt(HAIRPIN_FLIP, PROP_CHECK + '''import ast as _ast
names = {n.id.lower() for n in _ast.walk(tree) if isinstance(n, _ast.Name)}
diffs = [n for n in _ast.walk(tree) if isinstance(n, _ast.BinOp) and isinstance(n.op, _ast.Sub)
         and isinstance(n.left, _ast.Name) and isinstance(n.right, _ast.Name)]
remember = [n for n in _ast.walk(tree) if isinstance(n, _ast.Assign) and isinstance(n.value, _ast.Name)
            and "err" in n.value.id.lower()]
expect(diffs and remember, "Add the derivative: at the end of the loop remember last_error = error, and use "
       "(error - last_error) in your steering.")
expect("kd" in names, "Give the derivative its own gain Kd, e.g. turn = Kp * error + Kd * (error - last_error).")
for a, label in ((ARENA, "Hairpin Alley"), (ALT, "flipped Hairpin Alley")):
    r = sim(a, label=label)
    proportional(r, label)
    expect(r.crashes == 0, f"On the {label} the robot crashed.")
    expect(r.laps >= 1, f"On the {label} the robot didn't finish a lap in {a['time_limit']:g} s (on the tape {r.line_ratio:.0%} "
           f"of the time). Hairpins need strong steering: try a bigger Kp (like 2) with a little Kd (like 1).")
    expect(r.lap_times[0] < 28, f"On the {label} your lap took {r.lap_times[0]:.1f} s. Beat 28 s!")
    expect(r.line_ratio >= 0.9, f"On the {label} the robot was on the tape only {r.line_ratio:.0%} of the time.")
SUCCESS = f"Hairpins tamed with PD! {r.lap_times[0]:.1f} s 🌀"
''')

RT_S5_CHECK = _with_alt(GRAND_PRIX_FLIP, PROP_CHECK + '''for a, label in ((ARENA, "Grand Prix"), (ALT, "flipped Grand Prix")):
    r = sim(a, label=label)
    proportional(r, label)
    expect(r.crashes == 0, f"On the {label} the robot crashed.")
    expect(r.laps >= 2, f"On the {label} the robot finished {r.laps} lap(s) in {a['time_limit']:g} s — we need 2. "
           f"(On the tape {r.line_ratio:.0%} of the time.)")
    total = r.lap_times[0] + r.lap_times[1]
    expect(total < 50, f"On the {label} two laps took {total:.1f} s ({r.lap_times[0]:.1f} + {r.lap_times[1]:.1f}). "
           f"Beat 50 s: push base higher — and raise Kp if it can't hold the corners.")
    expect(r.line_ratio >= 0.9, f"On the {label} the robot was on the tape only {r.line_ratio:.0%} of the time.")
SUCCESS = f"Two laps in {total:.1f} s — podium finish! 🥇"
''')

RT_BOSS_CHECK = _with_alt(MONACO_FLIP, PROP_CHECK + '''for a, label in ((ARENA, "Monaco"), (ALT, "flipped Monaco")):
    r = sim(a, label=label)
    proportional(r, label)
    expect(r.crashes == 0, f"On the {label} the robot crashed.")
    expect(r.laps >= 3, f"On the {label} the robot finished {r.laps} of 3 laps in {a['time_limit']:g} s (on the tape {r.line_ratio:.0%} "
           f"of the time). If it flies off a hairpin, steer harder (bigger Kp) or brake in the corners: base = top - brake * abs(error).")
    worst = max(r.lap_times[:3])
    expect(worst < 28.5, f"On the {label} your slowest lap was {worst:.1f} s. Every lap must be under 28.5 s.")
    expect(r.line_ratio >= 0.95, f"On the {label} the robot left the track: on the tape only {r.line_ratio:.0%} of the time.")
SUCCESS = f"3 laps of Monaco, slowest {worst:.1f} s. WORLD CHAMPION 🏆🏎️"
''')

RACE_TRACK = {
    "id": "race_track", "week": 3, "order": 6, "title": "Race Track Pro", "emoji": "🏎️",
    "tagline": "Swap zig-zags for smooth proportional steering and race for the fastest lap",
    "story": "The Robo Grand Prix is coming! Bang-bang robots wobble around the track like shopping trolleys. "
             "To win you'll teach your robot to steer the way racing drivers do — a little for a small mistake, a lot "
             "for a big one — then tune it, add damping, and go flat out.",
    "concepts": ["pid", "feedback"],
    "expected_minutes": 120,
    "real_world": "Self-driving cars and 'lane keeping' in normal cars use the same idea: measure how far you are from the "
                  "centre of the lane (the error) and steer in proportion. PID controllers also fly drones, balance Segways "
                  "and keep cruise control at exactly 100 km/h.",
    "build_it": "Try it on a real line-follower (Cutebot, LEGO SPIKE, Arduino + IR sensor): print the sensor value, pick "
                "the edge target, and tune Kp on a tape oval on the floor.",
    "steps": [
        {
            "id": "s1", "title": "Steer in proportion",
            "learn": "<p>Bang-bang only knows <i>full left</i> or <i>full right</i>. Think about riding a bike: if you drift a "
                     "tiny bit, you steer a tiny bit. If you're way off, you steer a lot. That's <b>proportional control</b>.</p>"
                     "<p>Step 1 — measure the <b>error</b>: how far you are from where you want to be. On the edge of the tape "
                     "the sensor reads about 49 (half white, half black), so that's our <b>target</b>:</p>"
                     "<pre>error = robot.floor() - target   # 0 = perfect, + = on white, - = on black</pre>"
                     "<p>Step 2 — steer in proportion to the error. <b>Kp</b> (the <i>gain</i>) says how hard:</p>"
                     "<pre>turn = Kp * error\nrobot.drive(base - turn, base + turn)</pre>"
                     "<p>On white, error is positive, so the right wheel speeds up and the robot curves left back to the "
                     "edge. On black it's the other way. Near the edge the error is small, so the steering is gentle — "
                     "no more zig-zag! Start small: <code>Kp = 0.2</code>, <code>base = 50</code>.</p>",
            "task": "<p>Replace the bang-bang <code>if/else</code> with <b>proportional steering</b> and finish one lap of the "
                    "Speedway (tested both directions).</p>",
            "goals": ["error = robot.floor() - target", "Steer with Kp * error", "Finish a lap both ways"],
            "arena": SPEEDWAY, "starter": RT_S1, "solution": RT_S1_SOL,
            "hints": ["You don't need if/else any more — the maths does the deciding.",
                      "Set target = 49, Kp = 0.2 and base = 50 before the loop.",
                      "error = robot.floor() - target\nturn = Kp * error\nrobot.drive(base - turn, base + turn)"],
            "check": RT_S1_CHECK,
            "concepts": ["pid", "feedback"], "xp": 25,
        },
        {
            "id": "s2", "title": "Plot it and tune Kp",
            "learn": "<p>Engineers never tune blind — they look at <b>telemetry</b>. Add this inside your loop and a live graph "
                     "of your error appears under the arena:</p>"
                     "<pre>robot.plot(\"error\", error)</pre>"
                     "<p>Now tune <b>Kp</b>. It's like a shower tap:</p>"
                     "<ul><li><b>Kp too small</b> — you turn the tap so gently the water never gets warm. The robot steers too "
                     "softly and <b>drifts off</b> the outside of tight bends. The graph shows the error stuck far from 0.</li>"
                     "<li><b>Kp too big</b> — you yank the tap: too hot! too cold! too hot! The robot <b>wobbles</b> "
                     "(oscillates), and the graph jumps up and down fast.</li>"
                     "<li><b>Just right</b> — small wiggles hugging 0.</li></ul>"
                     "<p>Try Kp = 0.2, 0.5, 1, 2, 4 and watch the graph each time.</p>",
            "task": "<p>New, twisty track! Plot your error with <code>robot.plot(\"error\", error)</code> and <b>tune Kp</b> until "
                    "the robot gets round the tight bends (both directions).</p>",
            "goals": ["Plot the error", "Tune Kp", "Finish a lap of Twisty Loop both ways"],
            "arena": TWISTY, "starter": RT_S2, "solution": RT_S2_SOL,
            "hints": ["Run it with Kp = 0.2 first: where does it fly off?",
                      "Drifting off the outside of a bend means the steering is too weak — make Kp bigger.",
                      "robot.plot(\"error\", error)\n# and try Kp = 0.8"],
            "check": RT_S2_CHECK,
            "concepts": ["pid", "feedback"], "xp": 30,
        },
        {
            "id": "s3", "title": "Faster!",
            "learn": "<p>Time to race. Turn up <code>base</code>. What changes at higher speed?</p>"
                     "<ul><li>The robot travels further between two sensor readings, so it drifts further before it corrects.</li>"
                     "<li>Corners arrive sooner, so it needs to steer harder — you might have to raise Kp as well.</li></ul>"
                     "<p>If <code>base + turn</code> goes above 100, the motor just runs at 100 — that's fine. Real racing "
                     "drivers do the same: gas pedal on the floor, and the steering does the work.</p>"
                     "<p>Self-driving cars tune their lane-keeping differently for city streets and motorways for exactly "
                     "this reason: <b>good gains depend on speed</b>.</p>",
            "task": "<p>Back on the Speedway: finish a lap in <b>under 25 seconds</b>, both directions, without leaving the tape.</p>",
            "goals": ["Lap under 25 s", "Stay on the tape", "Both directions"],
            "arena": SPEEDWAY_FAST, "starter": RT_S3, "solution": RT_S3_SOL,
            "hints": ["The Speedway lap is about 5.5 m. At power 50 (15 cm/s) that's 37 s — too slow.",
                      "5.5 m in 25 s needs about 22 cm/s, so base must be at least about 75.",
                      "base = 80"],
            "check": RT_S3_CHECK,
            "concepts": ["pid", "feedback"], "xp": 30,
        },
        {
            "id": "s4", "title": "Derivative: the damper",
            "learn": "<p>P control looks at <i>where</i> the error is. The <b>derivative</b> looks at <i>how fast it's "
                     "changing</i>:</p>"
                     "<pre>derivative = error - last_error\nturn = Kp * error + Kd * derivative\nlast_error = error   # remember for next time</pre>"
                     "<p>Back to the shower: if the water is getting hotter <i>really quickly</i>, a clever person starts "
                     "turning the tap back <b>before</b> it's too hot. That's the D term. It acts like the <b>shock absorbers</b> "
                     "on a car — it <b>damps</b> the wobble, so you can use a big Kp for sharp hairpins without the robot "
                     "shaking itself off the track.</p>"
                     "<p>Together this is a <b>PD controller</b>. Add an I (integral) and you get PID — the most famous "
                     "controller in all of engineering. Start with <code>Kp = 2</code>, <code>Kd = 1</code>, and look at "
                     "your error graph: too much Kd makes the robot twitchy.</p>",
            "task": "<p>Hairpin Alley has 12 cm hairpin turns! Add a <b>derivative term</b> with its own gain <code>Kd</code> and "
                    "finish a lap in <b>under 28 s</b> (both directions).</p>",
            "goals": ["Remember last_error", "turn = Kp·error + Kd·(error − last_error)", "Lap under 28 s"],
            "arena": HAIRPIN, "starter": RT_S4, "solution": RT_S4_SOL,
            "hints": ["Create last_error = 0 before the loop and update it at the end of every loop.",
                      "Hairpins need strong steering: Kp around 2, then Kd around 1 to calm it down.",
                      "derivative = error - last_error\nturn = Kp * error + Kd * derivative\nlast_error = error"],
            "check": RT_S4_CHECK,
            "concepts": ["pid", "feedback"], "xp": 35,
        },
        {
            "id": "s5", "title": "Two-lap race",
            "learn": "<p>The Grand Prix has everything: long straights, hairpins and a chicane. Racing is about "
                     "<b>consistency</b> — a controller that's fast but loses the line once in 10 corners will lose the race.</p>"
                     "<p>Engineering method for tuning:</p>"
                     "<ol><li>Change <b>one</b> number at a time.</li><li>Run, watch the replay <i>and</i> the error graph.</li>"
                     "<li>Keep the change only if it made things better.</li></ol>"
                     "<p>Also look at your <b>lap times</b> in the result — the second lap is often a little different from the "
                     "first. Why do you think that is?</p>",
            "task": "<p>Finish <b>2 laps</b> of the Grand Prix with a total time <b>under 50 s</b>, both directions, staying on the tape.</p>",
            "goals": ["2 laps", "Total under 50 s", "Stay on the tape"],
            "arena": GRAND_PRIX, "starter": RT_S5, "solution": RT_S5_SOL,
            "hints": ["Two laps in 50 s means about 25 s per lap — faster than Hairpin Alley.",
                      "Push base up to 90–100. If it loses the hairpins, raise Kp a little.",
                      "base = 100"],
            "check": RT_S5_CHECK,
            "concepts": ["pid", "feedback"], "xp": 35,
        },
    ],
    "boss": {
        "id": "boss", "title": "Monaco: 3 perfect laps",
        "learn": "<p>Monaco is the slowest, twistiest race in Formula 1. Flat-out speed won't work here: the robot flies "
                 "off the hairpins. Real drivers <b>brake before corners</b> and accelerate on the straights.</p>"
                 "<p>Your robot can do that too. A big error means \"I'm in a corner\", so make the speed depend on it:</p>"
                 "<pre>base = top - brake * abs(error)   # abs() makes negatives positive</pre>"
                 "<p>On the straights the error is near 0, so you go at <code>top</code> speed. In a hairpin you "
                 "automatically slow down.</p>",
        "task": "<p>Drive <b>3 laps</b> of Monaco, <b>every lap under 28.5 s</b>, and <b>never leave the track</b> (on the tape at "
                "least 95% of the time). Both directions!</p>",
        "goals": ["3 laps", "Every lap under 28.5 s", "On the tape ≥ 95%"],
        "arena": MONACO, "starter": RT_BOSS, "solution": RT_BOSS_SOL,
        "hints": ["Run your Grand Prix program first: where does it lose the line?",
                  "Slow down in corners with base = top - brake * abs(error). Try top = 100, brake = 1.",
                  "base = top - brake * abs(error)\nrobot.drive(base - turn, base + turn)\n# and try Kp = 3"],
        "check": RT_BOSS_CHECK,
        "concepts": ["pid", "feedback"], "xp": 100,
    },
    "remix": {
        "prompt": "Make it yours! The Dream Circuit has even tighter hairpins. Build the ultimate race controller.",
        "ideas": ["Print each lap time and beep when you beat your best",
                  "Plot the motor powers and the derivative too — what do they look like in a hairpin?",
                  "Follow the tape with two sensors: error = floor(\"left\") - floor(\"right\")",
                  "Add an I term (integral = integral + error) and find out what it does"],
        "arena": DREAM_TRACK,
    },
}

PROJECTS = [LINE_TRACKER, RACE_TRACK]

# ---------------------------------------------------------------------------
# Practice side quests
# ---------------------------------------------------------------------------
MAT = {"name": "Gray Mat", "size": [240, 140], "start": [30, 70, 0], "time_limit": 20,
       "zones": [{"name": "mat", "rect": [150, 40, 40, 60], "color": "gray", "label": "mat"}]}

COUNTER = {"name": "Line Counter", "size": [300, 120], "start": [20, 60, 0], "time_limit": 20,
           "lines": [{"pts": [[x, 30], [x, 90]], "width": 3} for x in (80, 140, 200)]}

_RING = _arc(130, 90, 50, -90, 270, 40)[:-1]
RING = {"name": "Ring Road", "size": [260, 180], "start": [120, 40, 0], "time_limit": 25,
        "lines": [{"pts": _RING, "closed": True}]}

ENDLINE = {"name": "Dead End", "size": [300, 160], "start": [30, 50, 0], "time_limit": 30,
           "lines": [{"pts": _turtle(20, 50, 0, [("s", 90), ("a", 50, 60), ("s", 40)])}]}

PARK = {"name": "Parking Wall", "size": [260, 120], "start": [30, 60, 0], "time_limit": 15,
        "boxes": [[200, 20, 20, 80]]}

BLUE_LAB = {"name": "Blue Lab", "size": [260, 140], "start": [30, 70, 0], "time_limit": 20,
            "zones": [{"name": "blue floor", "rect": [0, 0, 260, 140], "color": "blue"}],
            "lines": [{"pts": [[160, 30], [160, 110]], "width": 3}]}

TWO_EYES = {**SPEEDWAY, "name": "Speedway", "time_limit": 40}

P_PID2_SOL = '''# P control using BOTH side sensors (centred on the tape)
Kp = 0.4
base = 60
while True:
    error = robot.floor("left") - robot.floor("right")   # 0 when the tape is in the middle
    turn = Kp * error
    robot.drive(base + turn, base - turn)
    robot.wait(0.02)
'''

PRACTICE = [
    {
        "id": "p_thresholds_3", "concept": "thresholds", "title": "Stop on the gray mat", "difficulty": 1,
        "task": "<p>Drive forward and stop as soon as the sensor reaches the <b>gray mat</b>. Gray reads about 64 and white "
                "about 92 — so where should your threshold be? (Hint: 49 won't work!) I'll move the mat to test you.</p>",
        "goals": ["Pick a threshold between white and gray", "Stop at the mat", "Works when the mat moves"],
        "arena": MAT, "starter": "robot.forward(120)\n",
        "solution": "threshold = (92 + 64) / 2     # halfway between white and gray = 78\nrobot.drive(40, 40)\n"
                    "while robot.floor() > threshold:\n    robot.wait(0.02)\nrobot.stop()\n",
        "hints": ["Halfway between white (92) and gray (64)…", "(92 + 64) / 2 = 78",
                  "robot.drive(40, 40)\nwhile robot.floor() > 78:\n    robot.wait(0.02)\nrobot.stop()"],
        "check": '''expect(calls("floor") >= 1, "Use robot.floor() to notice the mat.")
for x, label in ((150, "mat at 150 cm"), (100, "mat moved to 100 cm")):
    r = sim(arena(zones=[{"name": "mat", "rect": [x, 40, 40, 60], "color": "gray", "label": "mat"}]), label=label)
    sensor = r.x + 6.5
    expect(r.crashes == 0, f"With the {label} the robot drove into the wall. Gray (64) is brighter than 49 — your threshold must sit between 92 and 64.")
    expect(x - 1 <= sensor <= x + 6, f"With the {label} the sensor stopped at {sensor:.0f} cm. Stop right at the edge of the mat ({x} cm).")
SUCCESS = "Threshold 78 — perfectly between white and gray 🎯"
''',
        "xp": 15,
    },
    {
        "id": "p_sensors_3", "concept": "sensors", "title": "Line counter", "difficulty": 2,
        "task": "<p>Drive straight across the lab for 15 seconds and <b>count the black lines</b> you cross, then "
                "<code>robot.say()</code> the number. Careful: the sensor sees black for several readings in a row — count "
                "each line only <b>once</b> (when it changes from white to black). I'll test a lab with a different number of lines.</p>",
        "goals": ["Count each line once", "Say the right number", "Works with a different number of lines"],
        "arena": COUNTER, "starter": "robot.drive(50, 50)\nrobot.wait(15)\nrobot.stop()\nrobot.say(\"I counted 0 lines\")\n",
        "solution": "count = 0\nwas_black = False\nrobot.drive(50, 50)\nwhile robot.time() < 15:\n"
                    "    black = robot.floor() < 49\n    if black and not was_black:   # white -> black: a new line!\n"
                    "        count = count + 1\n    was_black = black\n    robot.wait(0.02)\nrobot.stop()\n"
                    "robot.say(\"I counted \" + str(count) + \" lines\")\n",
        "hints": ["Keep a variable that remembers whether the LAST reading was black.",
                  "Add 1 only when it's black now AND it wasn't black last time.",
                  "black = robot.floor() < 49\nif black and not was_black:\n    count = count + 1\nwas_black = black"],
        "check": '''import re as _re
def said_number(r):
    says = [e["text"] for e in r.events if e["type"] == "say"]
    nums = _re.findall(r"\\d+", says[-1]) if says else []
    return int(nums[-1]) if nums else None
expect(calls("floor") >= 1, "Use robot.floor() to see the lines.")
for xs, label in (((80, 140, 200), "3 lines"), ((60, 100, 140, 180, 220), "5 lines")):
    r = sim(arena(lines=[{"pts": [[x, 30], [x, 90]], "width": 3} for x in xs]), label=label)
    n = said_number(r)
    expect(n is not None, "Say the number with robot.say(), e.g. robot.say(\\"I counted \\" + str(count) + \\" lines\\")")
    expect(n == len(xs), f"In the lab with {label} you said {n}. Count only when white changes to black!")
SUCCESS = "Counted perfectly — that's edge detection 🔢"
''',
        "xp": 20,
    },
    {
        "id": "p_feedback_line", "concept": "feedback", "title": "Ring road", "difficulty": 1,
        "task": "<p>Keep driving around the circular Ring Road for the whole 25 seconds using a <b>bang-bang edge follower</b> "
                "(one sensor, if/else). I'll also start you facing the other way round.</p>",
        "goals": ["Stay on the ring", "Keep moving", "Works in both directions"],
        "arena": RING, "starter": "robot.drive(50, 50)\nrobot.wait(25)\n",
        "solution": "while True:\n    if robot.floor() < 49:\n        robot.drive(45, 20)\n    else:\n        robot.drive(20, 45)\n    robot.wait(0.02)\n",
        "hints": ["On black steer one way, on white steer the other.", "Put the if/else inside while True:.",
                  "if robot.floor() < 49:\n    robot.drive(45, 20)\nelse:\n    robot.drive(20, 45)"],
        "check": '''for start, label in (([120, 40, 0], "counter-clockwise"), ([140, 40, 180], "clockwise")):
    r = sim(start=start, label=label)
    expect(r.crashes == 0, f"Going {label}, the robot crashed.")
    expect(r.distance >= 150, f"Going {label}, the robot only drove {r.distance:.0f} cm. Keep going round!")
    expect(r.line_ratio >= 0.9, f"Going {label}, the robot was on the ring only {r.line_ratio:.0%} of the time.")
SUCCESS = "Round and round the ring road 🔁"
''',
        "xp": 15,
    },
    {
        "id": "p_sensors_4", "concept": "sensors", "title": "Dead end", "difficulty": 2,
        "task": "<p>Follow the road and <b>stop when it ends</b>. Use a two-sensor follower plus the centre sensor: when "
                "<i>all three</i> sensors see white, the tape is gone. I'll test a longer road too.</p>",
        "goals": ["Follow the line", "Stop within 12 cm of the end", "Works on a longer road"],
        "arena": ENDLINE, "starter": "while True:\n    robot.drive(40, 40)\n    robot.wait(0.02)\n",
        "solution": "t = 49\nwhile True:\n    left = robot.floor(\"left\")\n    mid = robot.floor(\"center\")\n    right = robot.floor(\"right\")\n"
                    "    if left > t and mid > t and right > t:\n        robot.stop()\n        break\n"
                    "    if left < t:\n        robot.drive(0, 40)\n    elif right < t:\n        robot.drive(40, 0)\n"
                    "    else:\n        robot.drive(40, 40)\n    robot.wait(0.02)\nrobot.say(\"End of the road\")\n",
        "hints": ["Read all three sensors at the top of the loop.", "If left, mid and right are ALL above the threshold, stop and break.",
                  "if left > t and mid > t and right > t:\n    robot.stop()\n    break"],
        "check": '''for moves, label in (([("s", 90), ("a", 50, 60), ("s", 40)], "short road"), ([("s", 90), ("a", 50, 60), ("s", 90)], "longer road")):
    pts = [[20.0, 50.0]]
    x, y, h = 20.0, 50.0, 0.0
    for m in moves:
        if m[0] == "s":
            for i in range(4):
                x += m[1] / 4 * math.cos(math.radians(h)); y += m[1] / 4 * math.sin(math.radians(h)); pts.append([x, y])
        else:
            cx, cy = x - m[1] * math.sin(math.radians(h)), y + m[1] * math.cos(math.radians(h))
            for i in range(1, 16):
                a = h - 90 + m[2] * i / 15
                pts.append([cx + m[1] * math.cos(math.radians(a)), cy + m[1] * math.sin(math.radians(a))])
            x, y, h = pts[-1][0], pts[-1][1], h + m[2]
    r = sim(lines=[{"pts": pts}], label=label)
    ex, ey = pts[-1]
    d = math.hypot(r.x - ex, r.y - ey)
    expect(r.crashes == 0, f"On the {label} the robot crashed — it didn't stop at the end.")
    expect(r.line_ratio >= 0.85, f"On the {label} the robot left the road ({r.line_ratio:.0%} on the tape).")
    expect(d <= 12 and r.stopped, f"On the {label} the robot ended {d:.0f} cm from the end of the tape. Stop when all three sensors see white.")
SUCCESS = "End of the road — stopped like a pro 🛑"
''',
        "xp": 20,
    },
    {
        "id": "p_pid_1", "concept": "pid", "title": "Smooth parking", "difficulty": 2,
        "task": "<p>Park <b>exactly 20 cm</b> from the wall with <b>proportional speed</b>: "
                "<code>error = robot.distance() - 20</code>, <code>power = Kp * error</code>. Far away = fast, close = slow. "
                "Keep the power between -100 and 100 with <code>min()</code>/<code>max()</code>. I'll try two start points.</p>",
        "goals": ["Speed ∝ error", "End 20 cm (±1.5) from the wall", "No crash"],
        "arena": PARK, "starter": "robot.forward(140)\n",
        "solution": "Kp = 3\nwhile robot.time() < 12:\n    error = robot.distance() - 20\n    power = max(-100, min(100, Kp * error))\n"
                    "    robot.drive(power, power)\n    robot.wait(0.02)\nrobot.stop()\n",
        "hints": ["The error is how far you still have to go: distance - 20.", "power = Kp * error, with Kp around 2–4.",
                  "error = robot.distance() - 20\npower = max(-100, min(100, Kp * error))\nrobot.drive(power, power)"],
        "check": '''expect(calls("distance") >= 1, "Use robot.distance() to measure the gap to the wall.")
for start, label in (([30, 60, 0], "far start"), ([100, 60, 0], "close start")):
    r = sim(start=start, label=label)
    gap = 200 - 8 - r.x
    powers = set(r.series("pl"))
    expect(r.crashes == 0, f"From the {label} the robot hit the wall.")
    expect(len(powers) >= 8, f"From the {label} the robot only used {len(powers)} different powers. Make the power proportional to the error!")
    expect(abs(gap - 20) <= 1.5, f"From the {label} the robot parked {gap:.1f} cm from the wall. Aim for 20 cm.")
SUCCESS = "Smooth as butter — fast far away, gentle up close 🅿️"
''',
        "xp": 20,
    },
    {
        "id": "p_thresholds_4", "concept": "thresholds", "title": "Auto-calibrate", "difficulty": 3,
        "task": "<p>This lab has a <b>blue floor</b> (it reads about 30). Make your robot <b>calibrate itself</b>: read the "
                "floor at the start, assume black tape is about 6, work out the halfway threshold, then drive and stop on the "
                "black line. The same program must also work in a white lab!</p>",
        "goals": ["Measure the floor first", "Threshold from the measurement", "Works on blue AND white floors"],
        "arena": BLUE_LAB, "starter": "threshold = 49\nrobot.drive(40, 40)\nwhile robot.floor() > threshold:\n    robot.wait(0.02)\nrobot.stop()\n",
        "solution": "floor_value = robot.floor()          # whatever this floor is\nthreshold = (floor_value + 6) / 2\n"
                    "robot.drive(40, 40)\nwhile robot.floor() > threshold:\n    robot.wait(0.02)\nrobot.stop()\n",
        "hints": ["Before driving, save robot.floor() in a variable.", "threshold = (floor_value + 6) / 2",
                  "floor_value = robot.floor()\nthreshold = (floor_value + 6) / 2"],
        "check": '''for zones, label in ((ARENA["zones"], "blue lab"), ([], "white lab")):
    r = sim(zones=zones, label=label)
    sensor = r.x + 6.5
    expect(r.x > 40, f"In the {label} the robot barely moved. On a blue floor (30) a threshold of 49 already looks like 'black'!")
    expect(abs(sensor - 160) <= 3, f"In the {label} the sensor stopped at {sensor:.0f} cm, but the line is at 160 cm.")
SUCCESS = "Self-calibrating robot — works on any floor 🧪"
''',
        "xp": 25,
    },
    {
        "id": "p_pid_2", "concept": "pid", "title": "Two-eyed P control", "difficulty": 3,
        "task": "<p>A different P controller: keep the tape <b>centred</b> between the side sensors. "
                "<code>error = robot.floor(\"left\") - robot.floor(\"right\")</code> is 0 when centred. "
                "Steer with <code>Kp * error</code> and finish a lap of the Speedway (both directions) in under 32 s.</p>",
        "goals": ["error = left − right", "Proportional steering", "Lap under 32 s both ways"],
        "arena": TWO_EYES, "starter": "Kp = 0.4\nbase = 60\n# TODO: error from the left and right sensors\n",
        "solution": P_PID2_SOL,
        "hints": ["If the left sensor is darker (smaller), the tape is to the left, so the error is negative.",
                  "A negative error must turn LEFT: robot.drive(base + turn, base - turn).",
                  "error = robot.floor(\"left\") - robot.floor(\"right\")\nturn = Kp * error\nrobot.drive(base + turn, base - turn)"],
        "check": _with_alt({**SPEEDWAY_FLIP, "time_limit": 40}, '''for a, label in ((ARENA, "Speedway"), (ALT, "clockwise Speedway")):
    r = sim(a, label=label)
    expect(len(set(r.series("pl"))) >= 8, f"On the {label} the motors only used a few powers — steer in proportion to the error.")
    expect(r.crashes == 0, f"On the {label} the robot crashed.")
    expect(r.laps >= 1 and r.lap_times[0] < 32, f"On the {label}: {r.laps} laps, lap times {r.lap_times}. Finish a lap in under 32 s.")
    expect(r.line_ratio >= 0.9, f"On the {label} the robot was on the tape only {r.line_ratio:.0%} of the time.")
SUCCESS = "Centred and smooth — two-eyed P control 👀"
'''),
        "xp": 25,
    },
]
