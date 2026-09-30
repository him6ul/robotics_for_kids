"""Week 2 — Robots that sense: distance sensors, bumpers, floor sensors and the sense → think → act loop."""


def _grid(x0, y0, w, h, nx, ny, margin):
    """Evenly spaced dust gems inside the rectangle (x0, y0, w, h)."""
    return [[x0 + round(margin + (w - 2 * margin) * i / (nx - 1)), y0 + round(margin + (h - 2 * margin) * j / (ny - 1))]
            for i in range(nx) for j in range(ny)]


def _mirror_y(arena, h):
    """Flip an arena upside down (y -> h - y), so a left turn becomes a right turn."""
    a = dict(arena)
    a["walls"] = [[x1, h - y1, x2, h - y2] for (x1, y1, x2, y2) in arena.get("walls", [])]
    a["boxes"] = [[x, h - y - bh, bw, bh] for (x, y, bw, bh) in arena.get("boxes", [])]
    a["zones"] = [dict(z, rect=[z["rect"][0], h - z["rect"][1] - z["rect"][3], z["rect"][2], z["rect"][3]])
                  for z in arena.get("zones", [])]
    a["gems"] = [[x, h - y] for (x, y) in arena.get("gems", [])]
    a["labels"] = [[x, h - y, t] for (x, y, t) in arena.get("labels", [])]
    sx, sy, sh = arena["start"]
    a["start"] = [sx, h - sy, -sh]
    return a


# ---------------------------------------------------------------------------
# arenas — Bat-Bot
# ---------------------------------------------------------------------------
ECHO_HALL = {"name": "Echo Hall", "size": [240, 140], "start": [40, 70, 0], "time_limit": 15,
             "labels": [[40, 50, "start"], [225, 70, "wall →"]]}

WALL_RUN = {"name": "Wall Run", "size": [260, 140], "start": [40, 70, 0], "time_limit": 20,
            "boxes": [[200, 20, 12, 100]],
            "labels": [[40, 50, "start"], [206, 12, "wall"]]}

BAT_ROOM = {"name": "Bat Room", "size": [220, 160], "start": [40, 85, 0], "time_limit": 30,
            "boxes": [[100, 70, 50, 30]],
            "labels": [[125, 85, "crate"]]}

FOLLOW = {"name": "Follow Me", "size": [260, 120], "start": [40, 60, 0], "time_limit": 15,
          "boxes": [[200, 40, 16, 40]],
          "zones": [{"name": "sweet_spot", "rect": [158, 40, 8, 40], "color": "yellow", "label": "30 cm"}],
          "labels": [[208, 90, "🐕 buddy"]]}

ZIGZAG = {"name": "Zig-Zag Corridor", "size": [320, 210], "start": [35, 40, 0], "time_limit": 45,
          "walls": [[0, 70, 95, 70], [95, 70, 95, 140], [95, 140, 175, 140], [175, 140, 175, 210],
                    [0, 10, 155, 10], [155, 10, 155, 80], [155, 80, 235, 80], [235, 80, 235, 150],
                    [235, 150, 320, 150]],
          "zones": [{"name": "exit", "rect": [280, 150, 40, 60], "color": "green", "label": "🏁"}],
          "labels": [[35, 20, "start"]]}

ZIGZAG_FLIP = dict(_mirror_y(ZIGZAG, 210), name="Zig-Zag Corridor (flipped)")

BAT_CAVE = {"name": "Bat Cave", "size": [320, 220], "start": [40, 40, 0], "time_limit": 90,
            "boxes": [[90, 90, 30, 60], [180, 30, 40, 40], [230, 140, 50, 30], [150, 170, 20, 30]],
            "gems": [[140, 120], [270, 60], [60, 180], [290, 195]],
            "labels": [[105, 80, "stalagmite"], [255, 130, "rock"]]}

# ---------------------------------------------------------------------------
# arenas — Robo-Vac
# ---------------------------------------------------------------------------
BUMP_LANE = {"name": "Hallway", "size": [240, 140], "start": [40, 70, 0], "time_limit": 15,
             "boxes": [[190, 20, 12, 100]],
             "labels": [[40, 50, "start"], [196, 12, "door"]]}

BEDROOM = {"name": "Bedroom", "size": [160, 120], "start": [45, 45, 30], "time_limit": 35,
           "gems": _grid(0, 0, 160, 120, 5, 4, 25),
           "labels": [[80, 6, "💎 = dust"]]}

BEDROOM_60 = dict(BEDROOM, time_limit=62)

STAIRS_ROOM = {"name": "Landing", "size": [200, 140], "start": [45, 45, 30], "time_limit": 62,
               "gems": _grid(0, 0, 160, 140, 5, 4, 25),
               "zones": [{"name": "stairs", "rect": [160, 0, 40, 140], "color": "black", "label": "🪜 stairs"}]}

_FLAT_BOXES = [[35, 145, 60, 30], [205, 50, 40, 30]]
_FLAT_STAIRS = [240, 150, 60, 50]


def _near(p, rect, m):
    return rect[0] - m <= p[0] <= rect[0] + rect[2] + m and rect[1] - m <= p[1] <= rect[1] + rect[3] + m


FLAT = {"name": "The Flat", "size": [300, 200], "start": [60, 60, 30], "time_limit": 180,
        "walls": [[150, 0, 150, 60], [150, 140, 150, 200]],
        "boxes": _FLAT_BOXES,
        "gems": [[x, y] for x in range(25, 300, 30) for y in range(25, 200, 30)
                 if not any(_near((x, y), b, 12) for b in _FLAT_BOXES)
                 and not _near((x, y), _FLAT_STAIRS, 14) and abs(x - 150) > 12],
        "zones": [{"name": "stairs", "rect": _FLAT_STAIRS, "color": "black", "label": "🪜 stairs"}],
        "labels": [[65, 160, "sofa"], [225, 65, "table"], [75, 8, "living room"], [225, 8, "kitchen"]]}

# ---------------------------------------------------------------------------
# Project 3 — Bat-Bot
# ---------------------------------------------------------------------------
BAT_S1 = '''# 🦇 Bat-Bot: switch on the bat ears
robot.say("Bat ears on!")
# TODO: read robot.distance(), print it, drive 50 cm, print it again
'''

BAT_S1_SOL = '''# 🦇 Bat-Bot: switch on the bat ears
robot.say("Bat ears on!")
d = robot.distance()
print("Wall ahead:", d, "cm")
robot.forward(50)
d = robot.distance()
print("Now it is:", d, "cm")
'''

BAT_S2 = BAT_S1_SOL + '''
# TODO: drive toward the wall and stop when the distance is under 30 cm
'''

BAT_S2_SOL = '''# 🦇 Bat-Bot: stop before the wall
robot.drive(50, 50)
while robot.distance() > 30:    # SENSE, then THINK: still far away?
    robot.wait(0.02)            # ACT: keep driving a moment longer
robot.stop()
robot.say("Wall ahead - stopped!")
'''

BAT_S3 = BAT_S2_SOL + '''
# TODO: go fast when far, slow when close, and stop at 20 cm
'''

BAT_S3_SOL = '''# 🦇 Bat-Bot: slow down like a parking car
d = robot.distance()
while d > 20:
    if d > 60:
        robot.drive(60, 60)     # far away: zoom
    elif d > 35:
        robot.drive(35, 35)     # getting closer: easy does it
    else:
        robot.drive(20, 20)     # very close: creep
    robot.wait(0.02)
    d = robot.distance()
robot.stop()
robot.say("Parked at 20 cm")
'''

BAT_S4 = BAT_S3_SOL + '''
# TODO: never stop! Drive forever, and turn away when a wall gets close
'''

BAT_S4_SOL = '''# 🦇 Bat-Bot: explore without crashing
while True:
    d = robot.distance()        # SENSE
    if d < 25:                  # THINK
        robot.stop()            # ACT
        robot.turn_left(90)
    else:
        robot.drive(50, 50)
    robot.wait(0.02)
'''

BAT_S5 = BAT_S4_SOL + '''
# TODO: follow-me mode! Keep 30 cm from your buddy: too far = forward, too close = back
'''

BAT_S5_SOL = '''# 🦇 Bat-Bot: follow-me (bang-bang control)
while True:
    d = robot.distance()
    if d > 33:
        robot.drive(50, 50)     # too far: catch up
        robot.led("blue")
    elif d < 27:
        robot.drive(-50, -50)   # too close: back off
        robot.led("red")
    else:
        robot.stop()            # just right
        robot.led("green")
    robot.wait(0.02)
'''

BAT_BOSS_SOL = '''# 👾 BOSS: the zig-zag corridor
while True:
    front = robot.distance("front")
    if front < 22:
        robot.stop()
        # which side has more room?
        if robot.distance("left") > robot.distance("right"):
            robot.turn_left(90)
        else:
            robot.turn_right(90)
    else:
        robot.drive(50, 50)
    robot.wait(0.02)
'''

BAT_S1_CHECK = '''import re
expect(calls("distance") >= 1, "Read the ultrasonic sensor with robot.distance() and store it: d = robot.distance()")
expect(calls("print") >= 1, "Use print(...) so we can see the number in the console.")
for sx, label in [(40, "start at x = 40"), (100, "start at x = 100")]:
    r = sim(start=[sx, 70, 0], label=label)
    nums = [float(n) for n in re.findall(r"-?\\d+(?:\\.\\d+)?", r.output)]
    first = 240 - sx - 8
    expect(nums, "I don't see any numbers in the console. print(d) after d = robot.distance().")
    expect(any(abs(n - first) <= 1.5 for n in nums),
           f"Test '{label}': the wall is {first} cm away at the start, but you printed {nums}. Print the value robot.distance() gives you.")
    expect(any(abs(n - (first - 50)) <= 1.5 for n in nums),
           f"Test '{label}': after driving 50 cm the sensor should read about {first - 50} cm. Read the distance AGAIN after robot.forward(50) and print it.")
SUCCESS = "Your robot can hear walls! 🦇 The number shrank by 50 — the sensor really measures."
'''

BAT_S2_CHECK = '''expect(calls("distance") >= 1, "Use robot.distance() to find out how far the wall is.")
expect(loops() >= 1, "Use a while loop that keeps checking the distance.")
tests = [(WALL_X, [40, 70, 0], "normal"), (140, [40, 70, 0], "wall moved closer"), (WALL_X, [80, 70, 0], "start further forward")]
for wall_x, start, label in tests:
    r = sim(arena(boxes=[[wall_x, 20, 12, 100]]), start=start, label=label)
    gap = wall_x - r.x - 8
    expect(r.crashes == 0, f"Test '{label}': CRUNCH! The robot hit the wall. Stop when robot.distance() drops below 30.")
    expect(gap <= 40, f"Test '{label}': the robot stopped {gap:.0f} cm from the wall — too early. Keep driving while the distance is more than 30.")
    expect(gap >= 18, f"Test '{label}': the robot stopped only {gap:.0f} cm from the wall. Stop a bit sooner (under 30 cm).")
SUCCESS = "Stopped safely every time — even when I moved the wall! That's a sensor at work. 🧱"
'''.replace("WALL_X", "200")

BAT_S3_CHECK = '''expect(calls("distance") >= 1, "Keep reading robot.distance() inside your loop.")
import ast as _ast
expect(any(isinstance(n, _ast.If) for n in _ast.walk(tree)), "Use if / elif / else on the distance to choose a speed.")
def near_speed(r, wall_x):
    xs, ts = r.series("x"), r.series("t")
    sp = [(xs[i] - xs[i - 1]) / (ts[i] - ts[i - 1]) for i in range(1, len(xs))
          if ts[i] > ts[i - 1] and 21 <= wall_x - xs[i] - 8 <= 28]
    return max(sp) if sp else 0.0
for wall_x, start, label in [(200, [40, 70, 0], "normal"), (130, [40, 70, 0], "wall moved closer")]:
    r = sim(arena(boxes=[[wall_x, 20, 12, 100]]), start=start, label=label)
    gap = wall_x - r.x - 8
    expect(r.crashes == 0, f"Test '{label}': the robot hit the wall! Stop when the distance reaches 20 cm.")
    expect(abs(gap - 20) <= 3, f"Test '{label}': the robot stopped {gap:.0f} cm from the wall. Aim for 20 cm (±3).")
    v = near_speed(r, wall_x)
    expect(v <= 9, f"Test '{label}': in the last few cm you were still going {v:.0f} cm/s. When it's close, slow down (power 30 or less = 9 cm/s).")
    expect(r.max_speed >= 13, f"Test '{label}': your top speed was only {r.max_speed:.0f} cm/s. Go FAST while the wall is far away (power 50+), then slow down.")
SUCCESS = "Smooth as a self-driving car! 🚗 Fast when far, gentle when close."
'''

BAT_S4_CHECK = '''expect(calls("distance") >= 1, "Read robot.distance() inside your loop.")
expect(uses("control_loop"), "You need a loop that keeps sensing and driving: while True: ...")
for start, label in [([40, 85, 0], "facing the crate"), ([60, 35, 0], "start bottom-left")]:
    r = sim(start=start, label=label)
    hs = r.series("h")
    turning = sum(abs(b - a) for a, b in zip(hs, hs[1:]))
    expect(r.crashes == 0, f"Test '{label}': the robot crashed {r.crashes} time(s). Turn away when the distance is under about 25 cm.")
    expect(r.distance >= 300, f"Test '{label}': the robot only drove {r.distance:.0f} cm in 30 s. Keep exploring the whole time — don't stop at the first wall!")
    expect(turning >= 250, f"Test '{label}': the robot only turned {turning:.0f}° in total. Each time a wall comes close, turn away and carry on.")
SUCCESS = "30 seconds of exploring, zero crashes. Your bat can fly! 🦇"
'''

BAT_S5_CHECK = '''expect(calls("distance") >= 1, "Read robot.distance() in your loop.")
tests = [(200, [40, 60, 0], "buddy far away"), (62, [40, 60, 0], "buddy walked right up close"), (160, [60, 60, 0], "buddy in the middle")]
for bx, start, label in tests:
    r = sim(arena(boxes=[[bx, 40, 16, 40]], zones=[]), start=start, label=label)
    gap = bx - r.x - 8
    expect(r.crashes == 0, f"Test '{label}': you bumped into your buddy! Back up when you're closer than 30 cm.")
    expect(abs(r.heading) <= 5, f"Test '{label}': the robot turned away (heading {r.heading:.0f}°). In follow-me mode, stay facing your buddy: forward or backward only.")
    expect(abs(gap - 30) <= 4, f"Test '{label}': you ended {gap:.0f} cm from your buddy. Keep about 30 cm: forward if too far, BACKWARD if too close.")
    if label.startswith("buddy walked"):
        expect(r.x < start[0] - 6, "When the buddy is too close, the robot must back away (drive with negative power).")
SUCCESS = "Good dog! 🐕 Your robot keeps a perfect 30 cm — that's bang-bang control."
'''

BAT_BOSS_CHECK = '''expect(calls("distance") >= 2, "Use the side sensors too: robot.distance(\\"left\\") and robot.distance(\\"right\\").")
for a, label in [(ZIGZAG, "zig-zag"), (ZIGZAG_FLIP, "flipped zig-zag")]:
    r = sim(a, label=label)
    expect(r.crashes == 0, f"'{label}': the robot scraped a wall {r.crashes} time(s). Turn when the front distance is about 22 cm, so you stay in the middle.")
    expect(r.visited("exit"), f"'{label}': the robot ended at ({r.x:.0f}, {r.y:.0f}) and never reached the 🏁 exit. At each dead end, look left and right and turn toward the side with more space.")
SUCCESS = "Through the zig-zag both ways, no hands! 🦇🏆"
'''

BAT_BOT = {
    "id": "bat_bot", "week": 2, "order": 3, "title": "Bat-Bot", "emoji": "🦇",
    "tagline": "Give your robot ultrasonic 'bat ears' so it never bumps into walls",
    "story": "Bats fly through pitch-black caves without crashing. They shout, then listen for the echo. "
             "Bolt just got the same superpower: an ultrasonic distance sensor. Until now Bolt drove blind — "
             "today it learns to notice the world and react to it.",
    "concepts": ["sensors", "control_loop", "decisions", "thresholds"],
    "expected_minutes": 110,
    "real_world": "Car parking sensors beep faster as you back toward a wall — that's an ultrasonic sensor in a loop. "
                  "Warehouse robots and robot vacuums use the same sense → think → act loop hundreds of times a second.",
    "build_it": "An HC-SR04 ultrasonic sensor costs a couple of dollars and plugs into a micro:bit or Arduino; "
                "LEGO SPIKE has one that looks like two big eyes.",
    "steps": [
        {
            "id": "s1", "title": "Bat ears",
            "learn": "<p>Last week Bolt drove <b>blind</b>. It did exactly what you said, even if a wall was in the way. "
                     "Real robots need <b>sensors</b> to notice the world.</p>"
                     "<p>Bolt's ultrasonic sensor works like a bat 🦇: it sends out a squeak too high for humans to hear, "
                     "waits for the echo, and works out how far away the wall is. Sound travels about 343 m per second, "
                     "so a quick echo means the wall is close.</p>"
                     "<pre>d = robot.distance()        # a number in cm, measured from the robot's nose\n"
                     "print(\"Wall ahead:\", d)    # shows up in the console</pre>"
                     "<p><code>d</code> is a <b>variable</b>: a box that keeps the reading. Each time you call "
                     "<code>robot.distance()</code> you get a <i>fresh</i> reading. The sensor can see up to 200 cm.</p>",
            "task": "<p>Read the front distance and <b>print</b> it. Then drive <code>forward(50)</code>, read it "
                    "<b>again</b> and print the new value. Does it shrink by 50?</p>",
            "goals": ["Read robot.distance()", "Print it", "Drive 50 cm and print again"],
            "arena": ECHO_HALL, "starter": BAT_S1, "solution": BAT_S1_SOL,
            "hints": ["robot.distance() gives you a number. Save it in a variable, like d = robot.distance().",
                      "print(\"Wall ahead:\", d) shows the number in the console.",
                      "d = robot.distance()\nprint(\"Wall ahead:\", d)\nrobot.forward(50)\nd = robot.distance()\nprint(\"Now:\", d)"],
            "check": BAT_S1_CHECK,
            "concepts": ["sensors"], "xp": 15,
        },
        {
            "id": "s2", "title": "Stop before the wall",
            "learn": "<p>Here's the big idea of this week. Every smart robot runs the same little loop, over and over:</p>"
                     "<ul><li><b>SENSE</b>: read a sensor (how far is the wall?)</li>"
                     "<li><b>THINK</b>: decide (is it too close?)</li>"
                     "<li><b>ACT</b>: drive the motors (keep going, or stop)</li></ul>"
                     "<p>In Python, a <b>while loop</b> repeats as long as its question is <code>True</code>:</p>"
                     "<pre>robot.drive(50, 50)\nwhile robot.distance() > 30:   # sense + think\n    robot.wait(0.02)           # act: keep driving a moment\n"
                     "robot.stop()                   # the loop ended: the wall is close!</pre>"
                     "<p>The loop checks 50 times a second (<code>wait(0.02)</code>), so the robot never misses the moment. "
                     "A self-driving car's brain loops like this too — just much faster.</p>",
            "task": "<p>Drive toward the wall and <b>stop when the distance is under 30 cm</b>. "
                    "I'll test it with the wall in different places, so <code>forward(123)</code> won't work — use the sensor!</p>",
            "goals": ["Use a while loop", "Stop 20–40 cm from the wall", "Works wherever the wall is"],
            "arena": WALL_RUN, "starter": BAT_S2, "solution": BAT_S2_SOL,
            "hints": ["Start the motors with robot.drive(50, 50), then loop while the wall is still far away.",
                      "The loop question is robot.distance() > 30. Inside the loop, just wait a tiny bit.",
                      "robot.drive(50, 50)\nwhile robot.distance() > 30:\n    robot.wait(0.02)\nrobot.stop()"],
            "check": BAT_S2_CHECK,
            "concepts": ["sensors", "control_loop"], "xp": 20,
        },
        {
            "id": "s3", "title": "Slow down, park softly",
            "learn": "<p>A good driver doesn't slam the brakes at the last second. They slow down as they get close. "
                     "Let's teach Bolt: <b>far = fast, close = slow</b>.</p>"
                     "<p><code>if / elif / else</code> picks <b>one</b> of several choices. Python checks them top to bottom "
                     "and runs the first one that's true:</p>"
                     "<pre>d = robot.distance()\nif d > 60:\n    robot.drive(60, 60)    # far\nelif d > 35:\n    robot.drive(35, 35)    # medium\nelse:\n    robot.drive(20, 20)    # close</pre>"
                     "<p>Put that <i>inside</i> your while loop and read <code>d</code> again each time round — "
                     "otherwise the robot is looking at an old number! Numbers like 60 and 35 are called <b>thresholds</b>: "
                     "the cut-off points where the robot changes its mind.</p>",
            "task": "<p>Drive fast while the wall is far, slow down when it's close, and <b>stop exactly 20 cm</b> from the wall (±3 cm).</p>",
            "goals": ["Fast when far (power 50+)", "Slow when close (power 30 or less)", "Stop at 20 cm", "No crash"],
            "arena": WALL_RUN, "starter": BAT_S3, "solution": BAT_S3_SOL,
            "hints": ["Loop while d > 20. Inside the loop, choose a speed with if / elif / else, wait, then read d again.",
                      "Try 60 power when d > 60, 35 power when d > 35, and 20 power for the rest.",
                      "d = robot.distance()\nwhile d > 20:\n    if d > 60:\n        robot.drive(60, 60)\n    elif d > 35:\n        robot.drive(35, 35)\n    else:\n        robot.drive(20, 20)\n    robot.wait(0.02)\n    d = robot.distance()\nrobot.stop()"],
            "check": BAT_S3_CHECK,
            "concepts": ["decisions", "thresholds", "control_loop"], "xp": 25,
        },
        {
            "id": "s4", "title": "Turn away from walls",
            "learn": "<p>A bat doesn't stop at the first wall — it swerves and keeps flying. For a robot that runs "
                     "<b>forever</b>, use <code>while True:</code>. It never ends by itself (the arena's clock ends the run).</p>"
                     "<pre>while True:\n    d = robot.distance()      # SENSE\n    if d < 25:                # THINK\n        robot.stop()          # ACT\n        robot.turn_left(90)\n    else:\n        robot.drive(50, 50)\n    robot.wait(0.02)</pre>"
                     "<p>This is a <b>reflex</b>, like pulling your hand off a hot pan. Robot vacuums and toy drones "
                     "use this exact trick to wander around without crashing.</p>",
            "task": "<p>Explore the room for 30 seconds <b>without a single crash</b>: drive forward, and whenever "
                    "a wall is closer than about 25 cm, stop and turn away.</p>",
            "goals": ["Loop forever with while True", "Drive at least 300 cm", "Zero crashes"],
            "arena": BAT_ROOM, "starter": BAT_S4, "solution": BAT_S4_SOL,
            "hints": ["Replace your 'stop at 20 cm' loop with while True: so it never stops.",
                      "Inside: read d. If d < 25, stop and turn_left(90). Else drive forward.",
                      "while True:\n    d = robot.distance()\n    if d < 25:\n        robot.stop()\n        robot.turn_left(90)\n    else:\n        robot.drive(50, 50)\n    robot.wait(0.02)"],
            "check": BAT_S4_CHECK,
            "concepts": ["control_loop", "decisions", "sensors"], "xp": 25,
        },
        {
            "id": "s5", "title": "Follow me!",
            "learn": "<p>Some robots follow you around: shopping-cart robots, camera drones, even suitcases! "
                     "They try to keep a fixed distance from you. The simplest way is <b>bang-bang control</b>:</p>"
                     "<ul><li>too far → drive forward</li><li>too close → drive backward</li><li>just right → stop</li></ul>"
                     "<pre>if d > 33:\n    robot.drive(50, 50)\nelif d < 27:\n    robot.drive(-50, -50)   # negative power = reverse\nelse:\n    robot.stop()</pre>"
                     "<p>Why 27 and 33 instead of exactly 30? If you only stop at <i>exactly</i> 30.0, the robot would "
                     "wiggle back and forth forever. The gap in the middle is a <b>dead band</b> — a calm zone.</p>",
            "task": "<p>Your 🐕 buddy (the box) might be far away or right in your face. Keep about <b>30 cm</b> "
                    "from it: forward when too far, backward when too close. I'll test three different buddy positions.</p>",
            "goals": ["Forward if too far", "Backward if too close", "End 30 cm (±4) away", "Keep facing your buddy"],
            "arena": FOLLOW, "starter": BAT_S5, "solution": BAT_S5_SOL,
            "hints": ["Don't turn in this mission — only forward, backward or stop.",
                      "Use three cases: if d > 33 … elif d < 27 … else …",
                      "if d > 33:\n    robot.drive(50, 50)\nelif d < 27:\n    robot.drive(-50, -50)\nelse:\n    robot.stop()"],
            "check": BAT_S5_CHECK,
            "concepts": ["decisions", "thresholds", "control_loop"], "xp": 30,
        },
    ],
    "boss": {
        "id": "boss", "title": "The zig-zag corridor",
        "learn": "<p>Bolt has more than one ear! It can listen in six directions:</p>"
                 "<pre>robot.distance(\"front\")\nrobot.distance(\"left\")\nrobot.distance(\"right\")</pre>"
                 "<p>At a dead end, a smart robot <b>looks both ways</b> and turns toward the side with more room. "
                 "Comparing two sensors is a decision too:</p>"
                 "<pre>if robot.distance(\"left\") > robot.distance(\"right\"):\n    robot.turn_left(90)\nelse:\n    robot.turn_right(90)</pre>"
                 "<p>The corridor is 60 cm wide. If you turn when the front distance is about 22 cm, "
                 "your robot's centre is 30 cm from the wall — right in the middle of the next corridor.</p>",
        "task": "<p>Drive through the zig-zag corridor to the 🏁 exit with <b>no crashes</b>. "
                "I'll also run it in a <i>flipped</i> corridor, so your program has to decide left or right by itself.</p>",
        "goals": ["Reach the 🏁 exit", "Works in the flipped corridor too", "No crashes"],
        "arena": ZIGZAG, "starter": BAT_S5_SOL.replace("# 🦇 Bat-Bot: follow-me (bang-bang control)",
                                                       "# 👾 BOSS: get through the zig-zag (your follow-me code is below)"),
        "solution": BAT_BOSS_SOL,
        "hints": ["Start from your Turn-away program: drive, and do something when the front is close.",
                  "When front < 22: stop, then compare robot.distance(\"left\") with robot.distance(\"right\").",
                  "if robot.distance(\"left\") > robot.distance(\"right\"):\n    robot.turn_left(90)\nelse:\n    robot.turn_right(90)"],
        "check": BAT_BOSS_CHECK.replace("ZIGZAG_FLIP", repr(ZIGZAG_FLIP)).replace("(ZIGZAG,", "(" + repr(ZIGZAG) + ","),
        "concepts": ["sensors", "decisions", "control_loop"], "xp": 80,
    },
    "remix": {
        "prompt": "Make it yours! Turn Bolt into a cave explorer, a parking sensor, or a nervous pet.",
        "ideas": ["Parking beeper: beep faster and faster as the wall gets closer",
                  "Mood LED: green when the way is clear, yellow when careful, red when close",
                  "Explore the Bat Cave for 90 s without a crash — and grab the gems on the way",
                  "Turn toward whichever side (left or right) has more space, like the boss, but everywhere"],
        "arena": BAT_CAVE,
    },
}

# ---------------------------------------------------------------------------
# Project 4 — Robo-Vac
# ---------------------------------------------------------------------------
VAC_HELP = '''import random as _random
import robosim as _rs
def run(seed, **kw):
    _random.seed(seed)          # same random numbers every time we test, so results are fair
    return sim(seed=seed, **kw)
def pinned(r):
    walls = r.world.walls
    xs, ys = r.series("x"), r.series("y")
    n = sum(1 for x, y in zip(xs, ys) if min(_rs.closest_on_seg(x, y, *w)[2] for w in walls) - 8 < 0.3)
    return n / max(1, len(xs))
def pct(r):
    return 100 * r.gems / max(1, r.gems_total)
'''

VAC_S1 = '''# 🧹 Robo-Vac v0.1
robot.drive(40, 40)
robot.wait(12)      # TODO: stop as soon as the bumper is pressed, not after 12 s
robot.stop()
'''

VAC_S1_SOL = '''# 🧹 Robo-Vac v0.1
robot.drive(40, 40)
while not robot.bumper():   # nothing touched yet?
    robot.wait(0.02)
robot.stop()
robot.say("Bump!")
'''

VAC_S2 = VAC_S1_SOL + '''
# TODO: keep cleaning for 30 s: after every bump, back up and turn
'''

VAC_S2_SOL = '''# 🧹 Robo-Vac v0.2
while robot.time() < 30:
    if robot.bumper():          # SENSE + THINK
        robot.stop()            # ACT: bump reflex
        robot.backward(10)
        robot.turn(120)
    else:
        robot.drive(50, 50)     # nothing in the way: vacuum on
    robot.wait(0.02)
robot.stop()
'''

VAC_S3 = VAC_S2_SOL + '''
# TODO: import random and turn a random amount after each bump
'''

VAC_S3_SOL = '''# 🧹 Robo-Vac v0.3
import random

while robot.time() < 30:
    if robot.bumper():
        robot.stop()
        robot.backward(10)
        robot.turn(random.randint(-160, 160))   # surprise me!
    else:
        robot.drive(50, 50)
    robot.wait(0.02)
robot.stop()
'''

VAC_S4 = VAC_S3_SOL + '''
# TODO: clean for 60 s and collect at least 70% of the dust
'''

VAC_S4_SOL = '''# 🧹 Robo-Vac v1.0
import random

while robot.time() < 60:
    if robot.bumper():
        robot.backward(8, 100)                        # quick reverse
        angle = random.choice([-1, 1]) * random.randint(60, 170)   # left or right, never tiny
        robot.turn(angle, 100)                        # quick random turn
    else:
        robot.drive(100, 100)                         # full power!
    robot.wait(0.02)
robot.stop()
robot.say("Room clean!")
'''

VAC_S5 = VAC_S4_SOL + '''
# TODO: the black floor is the stairs! Use robot.floor() to stay away from it
'''

VAC_S5_SOL = '''# 🧹 Robo-Vac v2.0 - now with cliff sensor
import random

while robot.time() < 60:
    if robot.floor() < 50:                            # 1st priority: don't fall!
        robot.backward(8, 100)
        robot.turn(random.choice([-1, 1]) * random.randint(60, 170), 100)
    elif robot.bumper():                              # 2nd: bumped something
        robot.backward(8, 100)
        robot.turn(random.choice([-1, 1]) * random.randint(60, 170), 100)
    else:                                             # 3rd: clean
        robot.drive(100, 100)
    robot.wait(0.02)
robot.stop()
robot.say("Room clean, still in one piece!")
'''

VAC_BOSS_SOL = '''# 👾 BOSS: clean the whole flat
import random

def escape():
    robot.backward(8, 100)
    robot.turn(random.choice([-1, 1]) * random.randint(60, 170), 100)

while robot.time() < 175:
    if robot.floor() < 50:          # stairs!
        robot.led("red")
        escape()
    elif robot.bumper():            # furniture or wall
        robot.led("yellow")
        escape()
    else:
        robot.led("green")
        robot.drive(100, 100)
    robot.wait(0.02)
robot.stop()
robot.say("Flat spotless!")
'''

VAC_S1_CHECK = '''expect(calls("bumper") >= 1, "Use robot.bumper() — it's True while something presses the front bumper.")
for wall_x, label in [(190, "door far away"), (120, "door moved closer")]:
    r = sim(arena(boxes=[[wall_x, 20, 12, 100]]), label=label)
    hits = [e["t"] for e in r.events if e["type"] == "crash"]
    expect(hits, f"Test '{label}': the robot never touched the door. Keep driving until the bumper is pressed.")
    ts, pl, pr = r.series("t"), r.series("pl"), r.series("pr")
    stop_t = next((t for t, a, b in zip(ts, pl, pr) if t >= hits[0] and a == 0 and b == 0), None)
    if stop_t is None and r.end_reason == "done":
        stop_t = r.time
    expect(stop_t is not None and stop_t - hits[0] <= 0.3,
           f"Test '{label}': the robot touched the door at {hits[0]:.1f} s but kept pushing" +
           (f" until {stop_t:.1f} s." if stop_t is not None else ".") + " Stop the moment robot.bumper() is True.")
    expect(r.crashes == 1, f"Test '{label}': the robot bumped {r.crashes} times. One gentle bump, then stop.")
SUCCESS = "Bump… stop! 🧹 Your vacuum can feel things now."
'''

VAC_S2_CHECK = VAC_HELP + '''expect(calls("bumper") >= 1, "Keep checking robot.bumper() inside your loop.")
expect(calls("time") >= 1, "Use robot.time() to clean for 30 seconds: while robot.time() < 30:")
for start, label in [([45, 45, 30], "start bottom-left"), ([110, 80, 200], "start top-right")]:
    r = run(1, start=start, label=label)
    expect(r.last_move_t >= 25, f"Test '{label}': the robot stopped moving after {r.last_move_t:.1f} s. Keep cleaning for 30 seconds.")
    expect(r.crashes >= 2, f"Test '{label}': only {r.crashes} bump(s) in 30 s. After each bump, back up, turn and drive on.")
    p = pinned(r)
    expect(p <= 0.25, f"Test '{label}': the robot spent {100 * p:.0f}% of the time squashed against a wall. After a bump, BACK UP (robot.backward(10)) before turning. "
           "If it rubs along a wall, try a different turn angle — the bumper only feels things in front.")
    expect(r.distance >= 200, f"Test '{label}': the robot only drove {r.distance:.0f} cm. Keep driving between bumps.")
SUCCESS = "Bump, back up, turn, repeat — that's a real Roomba reflex! 🤖"
'''

VAC_S3_CHECK = VAC_HELP + '''expect(imports("random"), "Start your program with: import random")
expect(calls("randint") + calls("uniform") + calls("choice") + calls("random") >= 1,
       "Use random.randint(...) to pick a random turn angle.")
expect(calls("bumper") >= 1, "Keep your bumper reflex!")
r1 = run(1, label="random run 1")
expect(r1.crashes >= 2, f"Only {r1.crashes} bump(s) in 30 s. Keep driving, bumping and turning.")
expect(pinned(r1) <= 0.25, "The robot spends too long squashed against walls. Back up after each bump before turning.")
expect(r1.distance >= 200, f"The robot only drove {r1.distance:.0f} cm in 30 s. Keep moving between bumps.")
r2 = run(2, label="random run 2")
expect(r1.dist_to(r2.x, r2.y) > 5 or abs(r1.heading - r2.heading) > 5,
       "Two test runs with different random numbers ended in exactly the same place. Is your turn angle really random?")
SUCCESS = "Every run is different now! 🎲 Randomness helps a robot escape boring loops."
'''

VAC_S4_CHECK = VAC_HELP + '''expect(imports("random"), "Keep using random turns (import random).")
res = []
for seed in (1, 2, 3, 4, 5):
    r = run(seed, label=f"cleaning run {seed}")
    expect(r.time >= 55 and r.last_move_t >= 50, f"Run {seed}: the robot stopped cleaning after {r.last_move_t:.0f} s. Clean for 60 seconds: while robot.time() < 60:")
    res.append(pct(r))
avg = sum(res) / len(res)
expect(avg >= 70, "Dust collected in 5 test runs: " + ", ".join(f"{p:.0f}%" for p in res) +
       f" (average {avg:.0f}%). Aim for 70%! Try more speed (power 100), a short quick back-up, fast turns (robot.turn(angle, 100)) and no tiny turns.")
SUCCESS = f"Average {avg:.0f}% of the dust gone! ✨ Your Robo-Vac is ready for sale."
'''

VAC_S5_CHECK = VAC_HELP + '''expect(calls("floor") + calls("floor_left") + calls("floor_right") + calls("color") >= 1,
       "Use the floor sensor, robot.floor(), to see the dark stairs edge. White floor ≈ 92, black ≈ 6.")
res = []
tests = [(1, [45, 45, 30], "cleaning run 1"), (2, [45, 45, 30], "cleaning run 2"), (3, [110, 70, 0], "start facing the stairs")]
for seed, start, label in tests:
    r = run(seed, start=start, label=label)
    expect(not r.visited("stairs"), f"'{label}': AAAH! The robot rolled onto the stairs 🪜. Check robot.floor() FIRST in your loop — if it's dark (under 50), back up and turn.")
    res.append(pct(r))
avg = sum(res) / len(res)
expect(avg >= 60, "Dust collected: " + ", ".join(f"{p:.0f}%" for p in res) + f" (average {avg:.0f}%). Aim for 60%+ while staying safe.")
SUCCESS = f"No falls, {avg:.0f}% clean! 🧹 That's exactly how real robot vacuums use their cliff sensors."
'''

VAC_BOSS_CHECK = VAC_HELP + '''expect(calls("floor") + calls("floor_left") + calls("floor_right") + calls("color") >= 1, "Watch out for the stairs with robot.floor()!")
res = []
for seed in (1, 2, 3):
    r = run(seed, label=f"flat run {seed}")
    expect(not r.visited("stairs"), f"Run {seed}: the robot fell down the stairs 🪜! Floor check first, always.")
    got = [g for g in r.world.gems if g["got"] is not None]
    left, right = sum(1 for g in got if g["x"] < 150), sum(1 for g in got if g["x"] > 150)
    expect(left >= 3 and right >= 3, f"Run {seed}: you cleaned {left} dust in the living room and {right} in the kitchen. Clean BOTH rooms — go through the doorway!")
    res.append(pct(r))
avg = sum(res) / len(res)
expect(avg >= 55, "Dust collected: " + ", ".join(f"{p:.0f}%" for p in res) + f" (average {avg:.0f}%). Aim for 55%+ of the whole flat.")
SUCCESS = f"The whole flat is sparkling ({avg:.0f}%)! 🏆🧹"
'''

ROBO_VAC = {
    "id": "robo_vac", "week": 2, "order": 4, "title": "Robo-Vac", "emoji": "🧹",
    "tagline": "Build a robot vacuum that bumps, turns, cleans the room and never falls down the stairs",
    "story": "Your family's floor is covered in dust (the 💎 gems). You're going to build a robot vacuum "
             "like a Roomba. It has no map and no camera — just a bumper, a floor sensor and a clever loop. "
             "Can such a simple robot clean a whole flat?",
    "concepts": ["sensors", "decisions", "control_loop", "behaviors"],
    "expected_minutes": 110,
    "real_world": "The first Roombas (2002) had no map at all: they bounced off furniture with a bumper and picked "
                  "random new directions. Underneath they have 'cliff sensors' — floor sensors that stop them "
                  "falling down stairs. Today's robot vacuums still use both as safety reflexes.",
    "build_it": "A micro:bit car with a push-button (or a LEGO touch sensor) on the front makes a bumper; "
                "a line-following sensor pointing down works as a cliff sensor.",
    "steps": [
        {
            "id": "s1", "title": "Bumper stop",
            "learn": "<p>The simplest sensor of all is a <b>bumper</b>: a button on the front that gets pushed "
                     "when the robot touches something. <code>robot.bumper()</code> gives <code>True</code> "
                     "(pressed) or <code>False</code> (not pressed).</p>"
                     "<p>Remember the while loop from Bat-Bot? <code>not</code> flips True and False, so "
                     "<code>while not robot.bumper():</code> means <i>\"while nothing is touching me\"</i>:</p>"
                     "<pre>robot.drive(40, 40)\nwhile not robot.bumper():\n    robot.wait(0.02)\nrobot.stop()</pre>"
                     "<p>Same loop as before: <b>sense</b> (bumper?) → <b>think</b> (still free?) → <b>act</b> (keep driving).</p>",
            "task": "<p>Drive toward the door and <b>stop the moment the bumper is pressed</b>. "
                    "I'll move the door, so a timed wait won't work.</p>",
            "goals": ["Use robot.bumper()", "Stop right after the bump", "Only one bump"],
            "arena": BUMP_LANE, "starter": VAC_S1, "solution": VAC_S1_SOL,
            "hints": ["Replace the long wait with a loop that checks the bumper.",
                      "while not robot.bumper(): keeps looping until something is touched.",
                      "robot.drive(40, 40)\nwhile not robot.bumper():\n    robot.wait(0.02)\nrobot.stop()"],
            "check": VAC_S1_CHECK,
            "concepts": ["sensors", "control_loop"], "xp": 15,
        },
        {
            "id": "s2", "title": "Bump, back up, turn",
            "learn": "<p>A vacuum that stops at the first wall isn't much use. After a bump it should "
                     "<b>back up, turn, and carry on</b>. And it should clean for a while, not forever.</p>"
                     "<p><code>robot.time()</code> tells you how many seconds have passed. So this loop runs for 30 seconds:</p>"
                     "<pre>while robot.time() < 30:\n    if robot.bumper():\n        robot.backward(10)\n        robot.turn(120)\n    else:\n        robot.drive(50, 50)\n    robot.wait(0.02)</pre>"
                     "<p>Why back up first? If you turn while squashed against the wall, you rub along it. "
                     "Real robots always leave a little space before turning.</p>",
            "task": "<p>Clean the bedroom for <b>30 seconds</b>: drive, and after every bump back up about 10 cm and turn. "
                    "Don't get stuck against a wall!</p>",
            "goals": ["Loop for 30 seconds", "Back up and turn after each bump", "Keep moving — never stuck on a wall"],
            "arena": BEDROOM, "starter": VAC_S2, "solution": VAC_S2_SOL,
            "hints": ["Use while robot.time() < 30: as your loop.",
                      "Inside: if robot.bumper(): back up and turn. else: drive forward.",
                      "while robot.time() < 30:\n    if robot.bumper():\n        robot.backward(10)\n        robot.turn(120)\n    else:\n        robot.drive(50, 50)\n    robot.wait(0.02)"],
            "check": VAC_S2_CHECK,
            "concepts": ["decisions", "control_loop", "sensors"], "xp": 20,
        },
        {
            "id": "s3", "title": "Random turns",
            "learn": "<p>Watch the replay from last time: always turning 120° makes the robot drive the <b>same path "
                     "again and again</b>, missing whole parts of the room. The fix sounds silly but works: "
                     "<b>be random!</b></p>"
                     "<pre>import random                      # put this at the top\n\nangle = random.randint(-160, 160)   # a random whole number from -160 to 160\nrobot.turn(angle)</pre>"
                     "<p><code>import</code> loads a Python toolbox. <code>random.randint(a, b)</code> picks a surprise "
                     "number between a and b. Negative angles turn right, positive turn left.</p>"
                     "<p>The first Roombas cleaned this way: bump, random turn, go. No map needed!</p>",
            "task": "<p>Add <code>import random</code> and turn a <b>random</b> angle after each bump. "
                    "I'll run it twice with different random numbers — the two runs should end up in different places.</p>",
            "goals": ["import random", "Random turn after each bump", "Still bumps, backs up and keeps going"],
            "arena": BEDROOM, "starter": VAC_S3, "solution": VAC_S3_SOL,
            "hints": ["The very first line should be: import random",
                      "Replace robot.turn(120) with a random angle.",
                      "robot.turn(random.randint(-160, 160))"],
            "check": VAC_S3_CHECK,
            "concepts": ["decisions", "control_loop", "behaviors"], "xp": 25,
        },
        {
            "id": "s4", "title": "Clean the room",
            "learn": "<p>Time for a real job: clean for <b>60 seconds</b> and pick up at least <b>70%</b> of the dust. "
                     "This is where robot engineers start <b>tuning</b>: change one number, test, compare.</p>"
                     "<ul><li><b>Speed</b>: more power covers more floor (power 100 = 30 cm/s).</li>"
                     "<li><b>Turn speed</b>: <code>robot.turn(angle, 100)</code> turns with full power — less time spinning.</li>"
                     "<li><b>Back-up distance</b>: <code>robot.backward(8, 100)</code> is quick and still safe.</li>"
                     "<li><b>No tiny turns</b>: turning 5° just bumps the same wall again. Pick a size from 60 to 170 "
                     "and a random side: <code>random.choice([-1, 1]) * random.randint(60, 170)</code> "
                     "(<code>random.choice</code> picks one item from a list).</li></ul>"
                     "<p>Random robots are a bit different every run, so I test <b>5 runs</b> and use the <b>average</b>. "
                     "Scientists do the same when results are noisy.</p>",
            "task": "<p>Clean for <b>60 s</b> and collect on average <b>≥ 70%</b> of the dust gems over 5 test runs.</p>",
            "goals": ["Clean for 60 seconds", "Average ≥ 70% dust collected", "Keep the random bump reflex"],
            "arena": BEDROOM_60, "starter": VAC_S4, "solution": VAC_S4_SOL,
            "hints": ["First change the loop to while robot.time() < 60:",
                      "Then tune: drive(100, 100), power 100 for backward() and turn(), and no tiny turns.",
                      "robot.backward(8, 100)\nangle = random.choice([-1, 1]) * random.randint(60, 170)\nrobot.turn(angle, 100)\n...\nrobot.drive(100, 100)"],
            "check": VAC_S4_CHECK,
            "concepts": ["behaviors", "control_loop", "sensors"], "xp": 30,
        },
        {
            "id": "s5", "title": "Don't fall down the stairs",
            "learn": "<p>New house, new danger: the black area is the <b>stairs</b> 🪜. There's no wall, so the bumper "
                     "won't help. Real robot vacuums have <b>cliff sensors</b> underneath that notice when the floor disappears.</p>"
                     "<p>Bolt's floor sensor looks down just in front of the wheels: <code>robot.floor()</code> gives "
                     "about <b>92</b> on white floor and about <b>6</b> on black. Anything under 50 means \"danger!\"</p>"
                     "<p>Now your robot has several <b>behaviours</b>, so you need <b>priorities</b>. Check the most "
                     "important one first — <code>if / elif / else</code> runs only the first match:</p>"
                     "<pre>if robot.floor() < 50:      # 1. don't fall\n    ...\nelif robot.bumper():        # 2. bumped something\n    ...\nelse:                       # 3. clean\n    robot.drive(100, 100)</pre>",
            "task": "<p>Clean the landing for 60 s <b>without ever rolling onto the stairs</b>, and still collect on average 60% of the dust. "
                    "One test starts facing the stairs!</p>",
            "goals": ["Use robot.floor()", "Never on the stairs", "Average ≥ 60% dust"],
            "arena": STAIRS_ROOM, "starter": VAC_S5, "solution": VAC_S5_SOL,
            "hints": ["The stairs have no wall, so you need a floor check as well as the bumper.",
                      "Put the floor check FIRST: if robot.floor() < 50: back up and turn. Then elif robot.bumper(): …",
                      "if robot.floor() < 50:\n    robot.backward(8, 100)\n    robot.turn(random.choice([-1, 1]) * random.randint(60, 170), 100)\nelif robot.bumper():\n    ..."],
            "check": VAC_S5_CHECK,
            "concepts": ["behaviors", "sensors", "decisions", "thresholds"], "xp": 35,
        },
    ],
    "boss": {
        "id": "boss", "title": "Clean the whole flat",
        "learn": "<p>The final test: a whole flat with two rooms, a doorway, a sofa, a table and the stairs. "
                 "You have 3 minutes (<code>while robot.time() < 175:</code>).</p>"
                 "<p>Your program is getting long, so tidy it with a <b>function</b>: the same escape move is used "
                 "for the stairs and for bumps.</p>"
                 "<pre>def escape():\n    robot.backward(8, 100)\n    robot.turn(random.choice([-1, 1]) * random.randint(60, 170), 100)</pre>"
                 "<p>Bonus idea: show which behaviour is in charge with the LED — red for stairs, yellow for a bump, "
                 "green for cleaning. Engineers call this <b>debugging with lights</b>.</p>",
        "task": "<p>Clean <b>both rooms</b> of the flat in 3 minutes, collect on average ≥ 55% of the dust over "
                "3 runs, and <b>never</b> fall down the stairs.</p>",
        "goals": ["Clean both rooms", "Average ≥ 55% dust", "Never on the stairs"],
        "arena": FLAT, "starter": VAC_S5_SOL.replace("while robot.time() < 60:", "while robot.time() < 60:   # TODO: 3 minutes!"),
        "solution": VAC_BOSS_SOL,
        "hints": ["Change the loop to while robot.time() < 175: so it has time to reach the kitchen.",
                  "Keep the floor check first, then the bumper, then drive at full power.",
                  "def escape():\n    robot.backward(8, 100)\n    robot.turn(random.choice([-1, 1]) * random.randint(60, 170), 100)"],
        "check": VAC_BOSS_CHECK,
        "concepts": ["behaviors", "sensors", "control_loop"], "xp": 90,
    },
    "remix": {
        "prompt": "Make it yours! Invent Robo-Vac 3000 with new cleaning moves.",
        "ideas": ["Play a happy tune when the 3 minutes are up",
                  "Spot-clean mode: start with a growing spiral using drive(100, x) with x slowly increasing",
                  "Use the ultrasonic sensor to slow down before furniture — gentle bumps only",
                  "Wall-follow mode for a few seconds after each bump, like real Roombas do along skirting boards"],
        "arena": FLAT,
    },
}

PROJECTS = [BAT_BOT, ROBO_VAC]

# ---------------------------------------------------------------------------
# Practice side quests
# ---------------------------------------------------------------------------
RADAR = {"name": "Radar Room", "size": [240, 160], "start": [70, 60, 0], "time_limit": 10}

PING_PONG = {"name": "Ping-Pong Hall", "size": [200, 100], "start": [60, 50, 0], "time_limit": 45}

PARKING = {"name": "Parking Space", "size": [240, 120], "start": [40, 60, 0], "time_limit": 30,
           "boxes": [[200, 20, 12, 80]], "labels": [[206, 12, "wall"]]}

T_JUNCTION = {"name": "Dead End", "size": [240, 160], "start": [120, 40, 90], "time_limit": 25,
              "boxes": [[20, 100, 60, 60]],
              "zones": [{"name": "goal", "rect": [190, 110, 50, 50], "color": "green", "label": "🏁"}]}

T_JUNCTION_FLIP = {**T_JUNCTION, "boxes": [[160, 100, 60, 60]],
                   "zones": [{"name": "goal", "rect": [0, 110, 50, 50], "color": "green", "label": "🏁"}]}

EDGE = {"name": "Table Edge", "size": [240, 120], "start": [40, 60, 0], "time_limit": 20,
        "lines": [{"pts": [[150, 20], [150, 100]], "width": 2.5}], "labels": [[150, 12, "edge"]]}

POND = {"name": "Duck Pond", "size": [240, 180], "start": [40, 40, 0], "time_limit": 25,
        "zones": [{"name": "pond", "rect": [95, 65, 50, 50], "color": "black", "label": "🦆 pond"}]}

PRACTICE = [
    {
        "id": "p_sensors_1", "concept": "sensors", "title": "Wall radar", "difficulty": 1,
        "task": "<p>Be a radar! Print the distance in <b>four directions</b>: <code>\"front\"</code>, "
                "<code>\"left\"</code>, <code>\"right\"</code> and <code>\"back\"</code>. Don't move — just measure.</p>",
        "goals": ["Print front, left, right and back distances"],
        "arena": RADAR, "starter": "print(\"front:\", robot.distance(\"front\"))\n# TODO: left, right and back\n",
        "solution": "for side in [\"front\", \"left\", \"right\", \"back\"]:\n    print(side, robot.distance(side))\n",
        "hints": ["robot.distance(\"left\") measures to the left.", "You need four prints (or a for loop over a list).",
                  "for side in [\"front\", \"left\", \"right\", \"back\"]:\n    print(side, robot.distance(side))"],
        "check": '''import re
for (sx, sy), label in [((70, 60), "start A"), ((150, 100), "start B")]:
    r = sim(start=[sx, sy, 0], label=label)
    nums = [float(n) for n in re.findall(r"-?\\d+(?:\\.\\d+)?", r.output)]
    want = {"front": 240 - sx - 8, "left": 160 - sy - 8, "right": sy - 8, "back": sx - 8}
    for name, v in want.items():
        expect(any(abs(n - v) <= 1.5 for n in nums), f"Test '{label}': I expected the {name} distance ({v} cm) in your output but saw {nums}.")
SUCCESS = "Radar sweep complete! 📡"
''',
        "xp": 15,
    },
    {
        "id": "p_sensors_2", "concept": "sensors", "title": "Ping-pong counter", "difficulty": 2,
        "task": "<p>Bounce between the two end walls like a ping-pong ball: drive until the <b>bumper</b> is pressed, "
                "back up a little, turn around, and go again. <b>Count the bumps</b>, and after the 3rd bump stop and "
                "<code>say</code> the count.</p>",
        "goals": ["Exactly 3 bumps", "Stop after the 3rd", "Say the number 3"],
        "arena": PING_PONG,
        "starter": "robot.drive(50, 50)\nwhile not robot.bumper():\n    robot.wait(0.02)\nrobot.stop()\n# TODO: count bumps, turn around, repeat until 3\n",
        "solution": "bumps = 0\nwhile bumps < 3:\n    robot.drive(60, 60)\n    while not robot.bumper():\n        robot.wait(0.02)\n"
                    "    robot.stop()\n    bumps = bumps + 1\n    robot.backward(5)\n    robot.turn(180)\nrobot.stop()\nrobot.say(\"Bumps: \" + str(bumps))\n",
        "hints": ["Make a variable bumps = 0 and add 1 after every bump.", "Wrap the drive-until-bump part in while bumps < 3:",
                  "bumps = bumps + 1\nrobot.backward(5)\nrobot.turn(180)"],
        "check": '''expect(calls("bumper") >= 1, "Use robot.bumper() to feel the wall.")
for w, label in [(200, "long hall"), (150, "short hall")]:
    r = sim(size=[w, 100], label=label)
    expect(r.crashes == 3, f"Test '{label}': I counted {r.crashes} bump(s). Stop after exactly 3.")
    expect(r.said("3"), "Say the count at the end, e.g. robot.say(\\"Bumps: \\" + str(bumps)).")
    expect(r.end_reason == "done", f"Test '{label}': the program was still running when time ran out. Stop after the 3rd bump.")
SUCCESS = "Ping… pong… ping! 🏓 3 bumps counted."
''',
        "xp": 20,
    },
    {
        "id": "p_control_loop_1", "concept": "control_loop", "title": "Parking beeper", "difficulty": 2,
        "task": "<p>Be a car parking sensor: creep toward the wall (power 30), <b>beep</b> every time round the loop "
                "once the wall is closer than <b>50 cm</b> (stay quiet before that), and stop <b>10 cm</b> from the wall.</p>",
        "goals": ["Beep only when closer than 50 cm", "Stop 10 cm (±3) from the wall", "No crash"],
        "arena": PARKING, "starter": "robot.drive(30, 30)\nwhile robot.distance() > 10:\n    robot.wait(0.1)\nrobot.stop()\n# TODO: beep inside the loop when the wall is close\n",
        "solution": "robot.drive(30, 30)\nwhile robot.distance() > 10:\n    if robot.distance() < 50:\n        robot.beep(1000, 0.05)\n    robot.wait(0.1)\nrobot.stop()\n",
        "hints": ["The beep goes INSIDE the while loop, so it repeats.", "Only beep if robot.distance() < 50.",
                  "if robot.distance() < 50:\n    robot.beep(1000, 0.05)"],
        "check": '''expect(calls("beep") >= 1, "Use robot.beep() inside your loop.")
for wx, label in [(200, "wall far"), (130, "wall closer")]:
    r = sim(arena(boxes=[[wx, 20, 12, 80]]), label=label)
    gap = wx - r.x - 8
    expect(r.crashes == 0, f"Test '{label}': bumped the wall!")
    expect(abs(gap - 10) <= 3, f"Test '{label}': you stopped {gap:.0f} cm from the wall. Stop at 10 cm.")
    beeps = [e["t"] for e in r.events if e["type"] == "beep"]
    expect(len(beeps) >= 5, f"Test '{label}': only {len(beeps)} beep(s). Beep every time round the loop once you're close.")
    ts, xs = r.series("t"), r.series("x")
    def gap_at(t):
        i = min(range(len(ts)), key=lambda k: abs(ts[k] - t))
        return wx - xs[i] - 8
    early = [round(gap_at(t)) for t in beeps if gap_at(t) > 53]
    expect(not early, f"Test '{label}': you beeped when the wall was still {max(early) if early else 0} cm away. Stay quiet until it's under 50 cm.")
SUCCESS = "Beep… beep.. beep.beep! 🚗 Just like a real car."
''',
        "xp": 20,
    },
    {
        "id": "p_decisions_1", "concept": "decisions", "title": "Traffic-light LED", "difficulty": 1,
        "task": "<p>Drive toward the wall and show how close it is with the LED: <b>green</b> when more than 60 cm, "
                "<b>yellow</b> between 30 and 60, <b>red</b> under 30. Stop at 15 cm.</p>",
        "goals": ["Green → yellow → red", "Stop at 15 cm (±3)"],
        "arena": PARKING, "starter": "robot.drive(40, 40)\nwhile robot.distance() > 15:\n    # TODO: choose the LED colour\n    robot.wait(0.02)\nrobot.stop()\n",
        "solution": "robot.drive(40, 40)\nwhile robot.distance() > 15:\n    d = robot.distance()\n    if d > 60:\n        robot.led(\"green\")\n"
                    "    elif d > 30:\n        robot.led(\"yellow\")\n    else:\n        robot.led(\"red\")\n    robot.wait(0.02)\nrobot.stop()\n",
        "hints": ["Read d = robot.distance() inside the loop.", "Use if / elif / else with 60 and 30.",
                  "if d > 60:\n    robot.led(\"green\")\nelif d > 30:\n    robot.led(\"yellow\")\nelse:\n    robot.led(\"red\")"],
        "check": '''import ast as _ast
expect(any(isinstance(n, _ast.If) for n in _ast.walk(tree)), "Use if / elif / else on the distance.")
for wx, label in [(200, "wall far"), (150, "wall closer")]:
    r = sim(arena(boxes=[[wx, 20, 12, 80]]), label=label)
    gap = wx - r.x - 8
    expect(r.crashes == 0, f"Test '{label}': bumped the wall!")
    expect(abs(gap - 15) <= 3, f"Test '{label}': you stopped {gap:.0f} cm away. Stop at 15 cm.")
    order = []
    for c in r.led_colors():
        if not order or order[-1] != c:
            order.append(c)
    expect(order == ["green", "yellow", "red"], f"Test '{label}': the LED went {' → '.join(order) or 'nowhere'}. It should go green → yellow → red.")
SUCCESS = "🟢🟡🔴 Your robot shows what it senses!"
''',
        "xp": 15,
    },
    {
        "id": "p_decisions_2", "concept": "decisions", "title": "Which way is open?", "difficulty": 2,
        "task": "<p>Drive up until the wall is 20 cm away. Then <b>look left and right</b>, turn toward the side "
                "with more space, and drive until you're 20 cm from the next wall — into the 🏁 zone. "
                "The blocked side changes between tests!</p>",
        "goals": ["Compare left and right distances", "End in the 🏁 zone", "No crash"],
        "arena": T_JUNCTION,
        "starter": "robot.drive(50, 50)\nwhile robot.distance() > 20:\n    robot.wait(0.02)\nrobot.stop()\n# TODO: turn toward the open side and drive on\n",
        "solution": "def drive_to_wall():\n    robot.drive(50, 50)\n    while robot.distance() > 20:\n        robot.wait(0.02)\n    robot.stop()\n\n"
                    "drive_to_wall()\nif robot.distance(\"left\") > robot.distance(\"right\"):\n    robot.turn_left(90)\nelse:\n    robot.turn_right(90)\ndrive_to_wall()\n",
        "hints": ["robot.distance(\"left\") and robot.distance(\"right\") measure the sides.",
                  "if left is bigger, turn_left(90), else turn_right(90). Then drive to the wall again.",
                  "if robot.distance(\"left\") > robot.distance(\"right\"):\n    robot.turn_left(90)\nelse:\n    robot.turn_right(90)"],
        "check": '''for a, label in [(ARENA, "open on the right"), (FLIP, "open on the left")]:
    r = sim(a, label=label)
    expect(r.crashes == 0, f"Test '{label}': crashed!")
    expect(r.in_zone("goal"), f"Test '{label}': you ended at ({r.x:.0f}, {r.y:.0f}), not in the 🏁 zone. Turn toward the side with the bigger distance.")
SUCCESS = "You picked the open road every time! 🛣️"
'''.replace("FLIP", repr(T_JUNCTION_FLIP)),
        "xp": 20,
    },
    {
        "id": "p_thresholds_1", "concept": "thresholds", "title": "Stop at the edge", "difficulty": 2,
        "task": "<p>A black line marks the edge of the table. Drive forward and <b>stop as soon as the floor sensor "
                "sees the dark line</b> — don't cross it! White ≈ 92 and black ≈ 6, so pick a <b>threshold</b> in between.</p>",
        "goals": ["Use robot.floor()", "Stop just before the line", "Works wherever the line is"],
        "arena": EDGE, "starter": "robot.forward(100)\n",
        "solution": "robot.drive(40, 40)\nwhile robot.floor() > 50:\n    robot.wait(0.02)\nrobot.stop()\n",
        "hints": ["robot.floor() is about 92 on white and 6 on black.", "Drive while the floor is brighter than 50.",
                  "robot.drive(40, 40)\nwhile robot.floor() > 50:\n    robot.wait(0.02)\nrobot.stop()"],
        "check": '''expect(calls("floor") + calls("floor_left") + calls("floor_right") >= 1, "Use robot.floor() to look at the floor.")
for lx, label in [(150, "edge at 150"), (100, "edge at 100")]:
    r = sim(lines=[{"pts": [[lx, 20], [lx, 100]], "width": 2.5}], label=label)
    expect(r.x <= lx - 3, f"Test '{label}': the robot's centre ended at x = {r.x:.0f}, over the edge at {lx}! Stop when the floor reading drops.")
    expect(r.x >= lx - 14, f"Test '{label}': the robot stopped at x = {r.x:.0f}, far from the edge at {lx}. Is your threshold too high?")
SUCCESS = "Right at the edge, not a cm over! 📏"
''',
        "xp": 20,
    },
    {
        "id": "p_behaviors_1", "concept": "behaviors", "title": "Don't feed the ducks", "difficulty": 3,
        "task": "<p>Explore the park for 25 s with <b>two reflexes</b>: if the floor is dark (the pond) back up and turn; "
                "else if a wall is closer than 25 cm, turn away; else drive. No splashes, no crashes!</p>",
        "goals": ["Never drive into the pond", "No crashes", "Drive at least 250 cm"],
        "arena": POND,
        "starter": "while True:\n    if robot.distance() < 25:\n        robot.turn_left(90)\n    else:\n        robot.drive(50, 50)\n    robot.wait(0.02)\n",
        "solution": "while True:\n    if robot.floor() < 50:\n        robot.backward(10)\n        robot.turn_left(120)\n    elif robot.distance() < 25:\n"
                    "        robot.stop()\n        robot.turn_left(90)\n    else:\n        robot.drive(50, 50)\n    robot.wait(0.02)\n",
        "hints": ["Put the floor check first — it's the most important.", "if robot.floor() < 50: back up and turn. elif robot.distance() < 25: turn.",
                  "if robot.floor() < 50:\n    robot.backward(10)\n    robot.turn_left(120)\nelif robot.distance() < 25:\n    robot.turn_left(90)"],
        "check": '''expect(calls("floor") >= 1, "Use robot.floor() to spot the dark pond.")
for start, label in [([40, 40, 0], "start by the gate"), ([40, 90, 0], "start facing the pond")]:
    r = sim(start=start, label=label)
    expect(not r.visited("pond"), f"Test '{label}': SPLASH! 🦆 The robot drove into the pond. Check robot.floor() first.")
    expect(r.crashes == 0, f"Test '{label}': the robot hit a wall {r.crashes} time(s).")
    expect(r.distance >= 250, f"Test '{label}': only {r.distance:.0f} cm explored. Keep going for the whole 25 s.")
SUCCESS = "Dry wheels and happy ducks! 🦆"
''',
        "xp": 25,
    },
]
