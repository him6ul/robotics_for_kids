"""Week 5 — Grab & build: robot arms, kinematics, grippers and warehouse robots."""

# ---------------------------------------------------------------------------
# arm arenas (side view)
# ---------------------------------------------------------------------------
ARM_LAB = {"type": "arm", "name": "Arm Lab", "size": [160, 100], "base": [40, 12], "links": [45, 35],
           "start": [90, -90], "time_limit": 30}

ARM_MARKS = {"type": "arm", "name": "Target Practice", "size": [160, 100], "base": [40, 12], "links": [45, 35],
             "start": [90, -90], "time_limit": 30,
             "marks": [[105, 50, "A"], [70, 75, "B"], [112, 18, "C"]]}

ARM_PICK = {"type": "arm", "name": "Pick & Place", "size": [160, 100], "base": [40, 12], "links": [45, 35],
            "start": [90, -90], "time_limit": 40,
            "blocks": [{"x": 70, "color": "red"}],
            "targets": [{"name": "goal", "x": 110, "w": 14, "color": "green"}]}

ARM_STACK = {"type": "arm", "name": "Tower Builder", "size": [160, 100], "base": [40, 12], "links": [45, 35],
             "start": [90, -90], "time_limit": 60,
             "blocks": [{"x": 60, "color": "red"}, {"x": 78, "color": "green"}, {"x": 96, "color": "blue"}],
             "targets": [{"name": "tower", "x": 114, "w": 14, "color": "yellow"}]}

ARM_REMIX = {"type": "arm", "name": "Arm Playground", "size": [180, 110], "base": [40, 12], "links": [50, 40],
             "start": [90, -90], "time_limit": 120,
             "blocks": [{"x": 58, "color": "red"}, {"x": 74, "color": "orange"}, {"x": 90, "color": "yellow"},
                        {"x": 106, "color": "green"}, {"x": 122, "color": "blue"}],
             "targets": [{"name": "left pad", "x": 20, "w": 14, "color": "purple"},
                         {"name": "right pad", "x": 145, "w": 14, "color": "yellow"}],
             "marks": [[120, 80, "⭐"], [60, 95, "☁️"]]}

# "Upgraded" arms used by the checks: same world, different robot. Good code reads arm.links() / arm.base().
ARM_BIG = {"links": [50, 40], "base": [30, 12]}
ARM_SMALL = {"links": [48, 36], "base": [36, 14]}

# helper code shared by the arm checks: rebuild the hand's path from the recorded joint angles
ARM_HELP = '''
def _hand_path(r, a):
    bx, by = a.get("base", [40, 12])
    L1, L2 = a.get("links", [45, 35])
    out = []
    for s, e in zip(r.frames["s"], r.frames["e"]):
        s1, s2 = math.radians(s), math.radians(s + e)
        out.append((bx + L1 * math.cos(s1) + L2 * math.cos(s2), by + L1 * math.sin(s1) + L2 * math.sin(s2)))
    return out

ARM_BIG = {"links": [50, 40], "base": [30, 12]}
ARM_SMALL = {"links": [48, 36], "base": [36, 14]}

def _variant(**kw):
    a = arena()
    a.update(kw)
    return a
'''

# ---------------------------------------------------------------------------
# Project 9 — Robot Arm
# ---------------------------------------------------------------------------
ARM_S1 = '''# 🦾 Wake up the robot arm
arm.move(90, 0)      # shoulder straight up, elbow straight
arm.say("Hello!")
# TODO: wave! Bend the elbow to 40, then to -40 ... three times
'''

ARM_S1_SOL = '''# 🦾 Wake up the robot arm
arm.move(90, 0)      # shoulder straight up, elbow straight
arm.say("Hello!")
for i in range(3):
    arm.move(90, 40)     # elbow bends left
    arm.move(90, -40)    # elbow bends right
arm.move(90, 0)
'''

ARM_S2 = '''import math

''' + ARM_S1_SOL + '''
# 📐 Where is the hand? Move to a new pose...
arm.move(60, -45)
# TODO: work out the hand's (x, y) with cos and sin, print it,
#       then print arm.hand() to compare
'''

ARM_S2_SOL = '''import math

''' + ARM_S1_SOL + '''
# 📐 Where is the hand? Move to a new pose...
arm.move(60, -45)
s, e = arm.angles()
L1, L2 = arm.links()
bx, by = arm.base()
elbow_x = bx + L1 * math.cos(math.radians(s))
elbow_y = by + L1 * math.sin(math.radians(s))
x = elbow_x + L2 * math.cos(math.radians(s + e))
y = elbow_y + L2 * math.sin(math.radians(s + e))
print("My maths says:", round(x, 1), round(y, 1))
print("arm.hand() says:", arm.hand())
'''

FK_FUNC = '''def hand_at(shoulder, elbow):
    """Forward kinematics: where would the hand be at these angles?"""
    bx, by = arm.base()
    L1, L2 = arm.links()
    s = math.radians(shoulder)
    se = math.radians(shoulder + elbow)
    x = bx + L1 * math.cos(s) + L2 * math.cos(se)
    y = by + L1 * math.sin(s) + L2 * math.sin(se)
    return x, y
'''

SEARCH_FUNC = '''def find_angles(tx, ty):
    """Try lots of angles and keep the ones that land closest to (tx, ty)."""
    best = (90, 0)
    best_err = 9999
    for s in range(0, 181, 2):
        for e in range(-160, 1, 2):          # elbow-up only: elbow 0 ... -160
            x, y = hand_at(s, e)
            err = math.hypot(x - tx, y - ty)
            if err < best_err:
                best_err = err
                best = (s, e)
    return best
'''

ARM_S3 = ARM_S2_SOL + '''
# 🎯 TODO: point at the marks A, B and C (in that order),
#          pausing half a second at each one
'''

ARM_S3_SOL = '''import math

''' + FK_FUNC + '''
''' + SEARCH_FUNC + '''
marks = [(105, 50, "A"), (70, 75, "B"), (112, 18, "C")]
for (x, y, name) in marks:
    s, e = find_angles(x, y)
    arm.move(s, e)
    arm.say(name)
    arm.beep()
    arm.wait(0.5)
'''

ARM_S4 = ARM_S3_SOL + '''
# 📦 TODO: pick up the red block at x = 70 and put it on the goal at x = 110
'''

ARM_S4_SOL = '''import math

''' + FK_FUNC + '''
''' + SEARCH_FUNC + '''
def go(x, y):
    s, e = find_angles(x, y)
    arm.move(s, e)

HIGH = 36      # safe travel height
TOP = 9        # just above the top of a block on the table (blocks are 8 cm tall)

go(70, HIGH)       # hover above the block
go(70, TOP)        # go down
arm.grab()
go(70, HIGH)       # lift
go(110, HIGH)      # carry it over the goal
go(110, TOP)       # lower it
arm.release()
go(110, HIGH)      # back off
arm.say("Delivered!")
'''

IK_FUNC = '''def ik(x, y):
    """Inverse kinematics: which angles put the hand at (x, y)? (elbow-up)"""
    bx, by = arm.base()
    L1, L2 = arm.links()
    dx, dy = x - bx, y - by
    d = math.hypot(dx, dy)
    # law of cosines gives the elbow bend
    c = (d * d - L1 * L1 - L2 * L2) / (2 * L1 * L2)
    c = max(-1, min(1, c))              # stay safe if the point is out of reach
    elbow = -math.acos(c)               # minus = elbow-up
    # aim at the point, then correct for the bent forearm
    shoulder = math.atan2(dy, dx) - math.atan2(L2 * math.sin(elbow), L1 + L2 * math.cos(elbow))
    return math.degrees(shoulder), math.degrees(elbow)
'''

ARM_S5 = ARM_S4_SOL + '''
# 🧠 TODO: write ik(x, y) with the law of cosines and use it in go()
#          instead of find_angles()
'''

ARM_S5_SOL = '''import math

''' + IK_FUNC + '''
def go(x, y):
    s, e = ik(x, y)
    arm.move(s, e)

HIGH = 36
TOP = 9

go(70, HIGH)
go(70, TOP)
arm.grab()
go(70, HIGH)
go(110, HIGH)
go(110, TOP)
arm.release()
go(110, HIGH)
arm.say("Delivered with IK!")
'''

ARM_BOSS_SOL = '''import math

''' + IK_FUNC + '''
def glide(x, y, steps=10):
    """Move the hand in a straight line to (x, y) in small IK steps."""
    hx, hy = arm.hand()
    for i in range(1, steps + 1):
        s, e = ik(hx + (x - hx) * i / steps, hy + (y - hy) * i / steps)
        arm.move(s, e)

HIGH = 36

def pick(x):
    glide(x, HIGH)
    glide(x, 9)
    arm.grab()
    glide(x, HIGH)

def place(x, level):
    glide(x, HIGH)
    glide(x, 8 * level + 9)     # level 0 = table, 1 = on one block, 2 = on two
    arm.release()
    glide(x, HIGH)

for level, x in enumerate([60, 78, 96]):
    pick(x)
    place(114, level)
arm.say("Tower complete!")
'''

ROBOT_ARM = {
    "id": "robot_arm", "week": 5, "order": 9, "title": "Robot Arm", "emoji": "🦾",
    "tagline": "Wave, point, pick & place and stack blocks with a two-joint robot arm",
    "story": "The lab just got a robot arm: a shoulder servo, an elbow servo and a gripper on the end. "
             "It can't see anything, so it has to be clever with angles. Teach it to wave, to know where its own "
             "hand is, to point at targets and finally to build a tower — using the same maths as real factory robots.",
    "concepts": ["manipulation", "kinematics"],
    "expected_minutes": 120,
    "real_world": "Car-factory arms weld and paint using exactly these ideas: forward kinematics tells them where the "
                  "tool is, inverse kinematics works out the joint angles to reach the next spot. The ISS's Canadarm2 "
                  "and da Vinci surgical robots solve the same equations, just with more joints.",
    "build_it": "Two SG90 hobby servos glued together (plus a third for a claw) on an Arduino or micro:bit make a "
                "real 2-link arm — the ik() function you write here works on it unchanged.",
    "steps": [
        {
            "id": "s1", "title": "Wave hello",
            "learn": "<p>This robot doesn't drive — it's an <b>arm</b>, seen from the side. It has two <b>joints</b>: "
                     "a <b>shoulder</b> at the base and an <b>elbow</b> in the middle. Each joint is turned by a "
                     "<b>servo</b>: a motor that you give an <i>angle</i> and it turns to that angle and holds it.</p>"
                     "<p>Two joints = two <b>degrees of freedom</b> (DOF). Your own arm has 7! A car-factory robot "
                     "usually has 6.</p>"
                     "<pre>arm.move(90, 0)     # shoulder 90° = straight up, elbow 0° = straight\n"
                     "arm.move(45, -30)   # shoulder tilted right, elbow bent 30° the other way\n"
                     "arm.say(\"Hi!\")</pre>"
                     "<p>The shoulder angle goes from 0 (pointing right) to 180 (pointing left). The elbow angle is "
                     "measured <i>from the upper arm</i>: 0 = straight, positive bends left (counter-clockwise), "
                     "negative bends right. <code>arm.move()</code> waits until both servos arrive (they turn 120° per second).</p>",
            "task": "<p>Raise the arm straight up, say hello, then <b>wave</b>: bend the elbow to 40 and back to -40, "
                    "<b>three times</b>. A <code>for</code> loop is perfect for this.</p>",
            "goals": ["Say hello", "Wave the elbow back and forth 3 times", "Don't crash into the table"],
            "arena": ARM_LAB, "starter": ARM_S1, "solution": ARM_S1_SOL,
            "hints": ["A wave is two moves: elbow one way, then the other way. Keep the shoulder at 90.",
                      "Put the two moves inside for i in range(3):",
                      "for i in range(3):\n    arm.move(90, 40)\n    arm.move(90, -40)"],
            "check": ARM_HELP + '''
def _waves(vals, th=20):
    turns, ref, up = 0, vals[0], None
    for v in vals:
        if up is None:
            if abs(v - ref) >= th:
                up, ref = v > ref, v
        elif up:
            if v > ref:
                ref = v
            elif ref - v >= th:
                turns, up, ref = turns + 1, False, v
        else:
            if v < ref:
                ref = v
            elif v - ref >= th:
                turns, up, ref = turns + 1, True, v
    return turns

r = sim()
expect(r.crashes == 0, f"The arm bumped into something {r.crashes} time(s). Keep the shoulder up at 90 while you wave.")
expect(r.said(), "Say hello with arm.say(\\"Hello!\\")")
w = _waves(r.frames["e"])
expect(w >= 4, f"I counted {w} change(s) of direction at the elbow. A 3-times wave needs the elbow to go 40 → -40 → 40 → -40 … (at least 4 turn-arounds).")
SUCCESS = "👋 Hello, world! Your arm just waved."
''',
            "concepts": ["manipulation", "actuators"], "xp": 15,
        },
        {
            "id": "s2", "title": "Where's my hand?",
            "learn": "<p>If you know the angles, can you work out where the hand is? That's called "
                     "<b>forward kinematics</b> (FK), and it's just triangles.</p>"
                     "<p>A stick of length <code>L</code> at angle <code>a</code> reaches "
                     "<code>L × cos(a)</code> to the right and <code>L × sin(a)</code> up. Python's maths toolbox "
                     "has cos and sin, but they want <b>radians</b> (another way to measure angles: 180° = π radians), "
                     "so convert first:</p>"
                     "<pre>import math\nmath.cos(math.radians(60))   # 0.5\nmath.sin(math.radians(90))   # 1.0</pre>"
                     "<p>Chain the two links: the elbow is <code>L1</code> away from the base at the shoulder angle. "
                     "The forearm points at angle <b>shoulder + elbow</b> (the elbow angle is relative!).</p>"
                     "<pre>elbow_x = bx + L1 * math.cos(math.radians(s))\n"
                     "x = elbow_x + L2 * math.cos(math.radians(s + e))</pre>"
                     "<p>Don't type in 45 and 35: read them with <code>arm.links()</code> and the base with "
                     "<code>arm.base()</code>. Then your code still works if the lab swaps in a bigger arm.</p>",
            "task": "<p>After your wave, move to <code>arm.move(60, -45)</code>. Get the angles with "
                    "<code>arm.angles()</code>, compute the hand's <b>x and y</b> with cos and sin, and "
                    "<code>print()</code> them. Then print <code>arm.hand()</code> — the arm's own answer — to compare.</p>",
            "goals": ["import math, use cos and sin", "Print your x and y", "They match arm.hand() (±1 cm)"],
            "arena": ARM_LAB, "starter": ARM_S2, "solution": ARM_S2_SOL,
            "hints": ["s, e = arm.angles() gives both angles; L1, L2 = arm.links() and bx, by = arm.base() give the sizes.",
                      "Do the elbow first: elbow_x = bx + L1 * cos(s), elbow_y = by + L1 * sin(s) — in radians!",
                      "x = elbow_x + L2 * math.cos(math.radians(s + e))\ny = elbow_y + L2 * math.sin(math.radians(s + e))\nprint(\"My maths says:\", round(x, 1), round(y, 1))"],
            "check": ARM_HELP + '''import re as _re
expect(imports("math"), "Start your program with import math so you can use math.cos and math.sin.")
expect(calls("cos") >= 1 and calls("sin") >= 1, "Forward kinematics needs math.cos(...) for x and math.sin(...) for y.")

def _matches(r):
    hx, hy = r.hand
    n = 0
    for line in r.lines:
        nums = [float(v) for v in _re.findall(r"-?\\d+(?:\\.\\d+)?", line)]
        if any(abs(a - hx) <= 1 and abs(b - hy) <= 1 for a, b in zip(nums, nums[1:])):
            n += 1
    return n

r = sim(label="the lab arm")
expect(r.crashes == 0, f"The arm crashed {r.crashes} time(s).")
n = _matches(r)
expect(n >= 1, f"The hand ended at ({r.hand[0]}, {r.hand[1]}) but I didn't see those two numbers printed. Print your x and y, e.g. print(\\"My maths says:\\", round(x, 1), round(y, 1)).")
expect(n >= 2, f"The hand is at ({r.hand[0]}, {r.hand[1]}). I need two matching lines: YOUR maths, and arm.hand() to compare. One of them is missing or doesn't match.")
r = sim(_variant(links=[50, 30], base=[30, 15]), label="a bigger arm (links 50 & 30, base at (30, 15))")
expect(_matches(r) >= 2, f"On a bigger arm (links 50 & 30, base (30, 15)) the hand is at ({r.hand[0]}, {r.hand[1]}), but your maths gives something else. Read the sizes with arm.links() and arm.base() instead of typing 45, 35, 40 and 12.")
SUCCESS = "Your maths matches the robot! That's forward kinematics 📐"
''',
            "concepts": ["kinematics", "manipulation"], "xp": 25,
        },
        {
            "id": "s3", "title": "Hit the marks",
            "learn": "<p>Now the other way round: the mark is at (105, 50) — which angles get the hand there? "
                     "That's <b>inverse kinematics</b> (IK) and it's harder. Here's a sneaky first solution: "
                     "<b>let the computer guess</b>. Try loads of angle pairs, use your FK to see where each one "
                     "lands, and keep the best.</p>"
                     "<pre>def hand_at(shoulder, elbow):\n    ...your FK maths...\n    return x, y\n\n"
                     "for s in range(0, 181, 2):          # every 2°\n    for e in range(-160, 1, 2):\n"
                     "        x, y = hand_at(s, e)\n        err = math.hypot(x - tx, y - ty)   # how far off?\n"
                     "        # remember s, e if err is the smallest so far</pre>"
                     "<p>That's a <b>loop inside a loop</b>: about 7 000 tries per mark, and a computer does them in a "
                     "blink. It's called a <b>brute-force search</b>. We only try elbows from 0 to -160 so the elbow "
                     "stays <i>up</i>, like your arm reaching down onto a desk.</p>"
                     "<p><code>def</code> with <code>return</code> makes a function that hands back an answer — "
                     "here a pair <code>(x, y)</code> that you unpack with <code>x, y = hand_at(s, e)</code>.</p>",
            "task": "<p>Turn your FK into a function <code>hand_at(shoulder, elbow)</code>, write "
                    "<code>find_angles(x, y)</code> that searches for the best angles, and point the hand at the marks "
                    "<b>A (105, 50)</b>, <b>B (70, 75)</b> and <b>C (112, 18)</b> in that order. Pause "
                    "<code>arm.wait(0.5)</code> at each one. Use <code>arm.links()</code> and <code>arm.base()</code> "
                    "inside <code>hand_at</code> — I'll test your program on a bigger arm too!</p>",
            "goals": ["Hand within 2.5 cm of A, then B, then C", "Pause at each mark", "Works on a bigger arm too"],
            "arena": ARM_MARKS, "starter": ARM_S3, "solution": ARM_S3_SOL,
            "hints": ["Copy your FK lines into def hand_at(shoulder, elbow): and end it with return x, y.",
                      "In find_angles keep two variables: best_err = 9999 and best = (90, 0). Inside the loops, if err < best_err, update both. Return best.",
                      "for (x, y, name) in [(105, 50, \"A\"), (70, 75, \"B\"), (112, 18, \"C\")]:\n    s, e = find_angles(x, y)\n    arm.move(s, e)\n    arm.wait(0.5)"],
            "check": ARM_HELP + '''
MARKS = [(105, 50, "A"), (70, 75, "B"), (112, 18, "C")]

def _visits(r, a):
    path = _hand_path(r, a)
    start, out = 0, []
    for (mx, my, name) in MARKS:
        hit = None
        for i in range(start, len(path)):
            if math.hypot(path[i][0] - mx, path[i][1] - my) <= 2.5:
                hit = i
                break
        if hit is None:
            best = min(math.hypot(p[0] - mx, p[1] - my) for p in path[start:] or path)
            return name, best
        start = hit
    return None, 0

for label, a in [("the lab arm", arena()), ("a bigger arm (links 50 & 40, base (30, 12))", _variant(**ARM_BIG))]:
    r = sim(a, label=label)
    expect(r.crashes == 0, f"The arm crashed {r.crashes} time(s) on {label}.")
    miss, best = _visits(r, a)
    expect(miss is None, f"On {label}: the hand never got within 2.5 cm of mark {miss} (closest: {best:.1f} cm). "
           + ("Visit A, then B, then C, and pause with arm.wait(0.5)." if label == "the lab arm" else
              "It works on the lab arm but not the bigger one — use arm.links() and arm.base() in hand_at()."))
SUCCESS = "🎯 Bullseye ×3! Your search found the angles all by itself."
''',
            "concepts": ["kinematics", "manipulation"], "xp": 30,
        },
        {
            "id": "s4", "title": "Pick & place",
            "learn": "<p>Pick & place is the most common job in the world for robot arms: grab a thing here, put it "
                     "there. Every real robot does it in the same careful steps:</p>"
                     "<ol><li><b>Hover</b> high above the block</li><li>Go <b>down</b> to just above its top</li>"
                     "<li><b>Grab</b></li><li><b>Lift</b> straight up</li><li><b>Carry</b> high over the goal</li>"
                     "<li>Go <b>down</b>, <b>release</b>, go back up</li></ol>"
                     "<p>Why hover? Because the arm moves by turning joints, the hand swings in a curve between "
                     "two poses. If you go straight from one low spot to another, it can scrape the table. "
                     "Moving high first keeps it safe.</p>"
                     "<p>Blocks are 8 cm cubes sitting on the table (y = 0), so the top of a block is y = 8. "
                     "<code>arm.grab()</code> only works when the hand is right at the top of a block — aim for y = 9. "
                     "Pushing the hand <i>into</i> the table or a block stalls the servo: that's a crash.</p>",
            "task": "<p>Make a <code>go(x, y)</code> function that uses <code>find_angles</code> and "
                    "<code>arm.move</code>. Then pick up the <b>red block at x = 70</b> and put it on the "
                    "<b>green goal at x = 110</b>. Travel at y = 36.</p>",
            "goals": ["Grab the red block", "Put it on the goal", "No crashes"],
            "arena": ARM_PICK, "starter": ARM_S4, "solution": ARM_S4_SOL,
            "hints": ["def go(x, y):\n    s, e = find_angles(x, y)\n    arm.move(s, e)",
                      "The order: go(70, 36), go(70, 9), grab, go(70, 36), go(110, 36), go(110, 9), release.",
                      "go(70, 36)\ngo(70, 9)\narm.grab()\ngo(70, 36)\ngo(110, 36)\ngo(110, 9)\narm.release()\ngo(110, 36)"],
            "check": '''r = sim()
grabs = [e for e in r.events if e["type"] == "grip" and e.get("got")]
expect(grabs, "The gripper never caught the block. Get the hand to (70, 9) — just above the block's top — then arm.grab().")
expect(r.crashes == 0, f"The arm crashed {r.crashes} time(s). Go up to y = 36 before moving sideways, and stop at y = 9 (not 8 or lower).")
expect(r.held is None, "You're still holding the block! Finish with arm.release() over the goal.")
b = r.blocks[0]
expect(r.blocks_in("goal") == 1, f"The block landed at x = {b['x']:.0f}, but the goal is at x = 110 (±7). Release it right above the goal.")
SUCCESS = "📦 Picked and placed like a factory pro!"
''',
            "concepts": ["manipulation", "kinematics"], "xp": 30,
        },
        {
            "id": "s5", "title": "Inverse kinematics",
            "learn": "<p>Brute force works, but it's slow and a bit wobbly (it only tries every 2°). Real robots solve "
                     "IK <b>exactly</b> with a triangle trick. The base, the elbow and the hand make a triangle with "
                     "sides <code>L1</code>, <code>L2</code> and <code>d</code> (the distance from base to target). "
                     "The <b>law of cosines</b> gives the angle in any triangle from its three sides:</p>"
                     "<pre>c = (d*d - L1*L1 - L2*L2) / (2*L1*L2)\nelbow = -math.acos(c)     # acos = 'which angle has this cos?'</pre>"
                     "<p>There are always <b>two</b> answers: <b>elbow-up</b> and <b>elbow-down</b> (try reaching for "
                     "a cup with your elbow high, then low). The minus sign picks elbow-up — elbow-down would drive the "
                     "elbow into the table.</p>"
                     "<p>Then aim the shoulder: <code>math.atan2(dy, dx)</code> is the angle from the base to the target, "
                     "and we tilt it back by how much the bent forearm pulls the hand away:</p>"
                     "<pre>shoulder = math.atan2(dy, dx) - math.atan2(L2*math.sin(elbow), L1 + L2*math.cos(elbow))</pre>"
                     "<p>Both come out in radians — use <code>math.degrees()</code> before calling <code>arm.move</code>. "
                     "If the target is out of reach, <code>c</code> is bigger than 1 and acos crashes, so clamp it with "
                     "<code>max(-1, min(1, c))</code>.</p>",
            "task": "<p>Write <code>ik(x, y)</code> using the law of cosines and return "
                    "<code>(shoulder, elbow)</code> in degrees. Use it inside <code>go()</code> instead of "
                    "<code>find_angles</code> and do the same pick & place. I'll try it on <b>three different arms</b>.</p>",
            "goals": ["ik() uses acos and atan2", "Pick & place works on 3 arms", "No crashes"],
            "arena": ARM_PICK, "starter": ARM_S5, "solution": ARM_S5_SOL,
            "hints": ["dx, dy = x - bx, y - by and d = math.hypot(dx, dy). Then c = (d*d - L1*L1 - L2*L2) / (2*L1*L2).",
                      "elbow = -math.acos(c) is in radians. Compute the shoulder in radians too, then convert both with math.degrees().",
                      "shoulder = math.atan2(dy, dx) - math.atan2(L2 * math.sin(elbow), L1 + L2 * math.cos(elbow))\nreturn math.degrees(shoulder), math.degrees(elbow)"],
            "check": ARM_HELP + '''expect(calls("acos") >= 1, "Use the law of cosines: math.acos(...) gives the elbow angle.")
expect(calls("atan2") >= 1, "Use math.atan2(dy, dx) to aim the shoulder at the target.")
for label, a in [("the lab arm", arena()), ("a bigger arm (links 50 & 40, base (30, 12))", _variant(**ARM_BIG)),
                 ("a different arm (links 48 & 36, base (36, 14))", _variant(**ARM_SMALL))]:
    r = sim(a, label=label)
    grabs = [e for e in r.events if e["type"] == "grip" and e.get("got")]
    expect(grabs, f"On {label} the gripper missed the block. Print ik(70, 9) and hand_at(...) of the answer to test your ik() — "
                  "and check the elbow is negative (elbow-up).")
    expect(r.crashes == 0, f"On {label} the arm crashed {r.crashes} time(s).")
    expect(r.blocks_in("goal") == 1, f"On {label} the block ended at x = {r.blocks[0]['x']:.0f}, not on the goal (x = 110).")
SUCCESS = "🧠 Exact inverse kinematics — the same maths inside every factory arm!"
''',
            "concepts": ["kinematics", "manipulation"], "xp": 40,
        },
    ],
    "boss": {
        "id": "boss", "title": "Tower of three",
        "learn": "<p>Stack all three blocks into a tower on the yellow pad. Each block goes one level higher: "
                 "the second one is released at y = 17, the third at y = 25.</p>"
                 "<p><b>Watch out:</b> the blocks are close together. When a joint move swings the hand in a curve, "
                 "the block you're carrying can clip its neighbour. Industrial arms have two kinds of moves: "
                 "<b>joint moves</b> (fast, curvy) and <b>linear moves</b> (the hand slides in a straight line). "
                 "Make your own linear move by walking the hand in small IK steps:</p>"
                 "<pre>def glide(x, y, steps=10):\n    hx, hy = arm.hand()\n    for i in range(1, steps + 1):\n"
                 "        s, e = ik(hx + (x - hx) * i / steps, hy + (y - hy) * i / steps)\n        arm.move(s, e)</pre>",
        "task": "<p>Stack the red (x = 60), green (x = 78) and blue (x = 96) blocks into a <b>3-block tower</b> "
                "on the yellow pad at x = 114. No crashes! It must work on a bigger arm too.</p>",
        "goals": ["Tower of 3 on the pad", "No crashes", "Works on a bigger arm"],
        "arena": ARM_STACK, "starter": ARM_S5_SOL, "solution": ARM_BOSS_SOL,
        "hints": ["Make pick(x) and place(x, level) functions. Level 0 = table, 1 = on top of one block…",
                  "Release height = 8 × level + 9. Travel at y = 36 so the carried block clears the tower.",
                  "for level, x in enumerate([60, 78, 96]):\n    pick(x)\n    place(114, level)"],
        "check": ARM_HELP + '''for label, a in [("the lab arm", arena()), ("a bigger arm (links 50 & 40, base (30, 12))", _variant(**ARM_BIG))]:
    r = sim(a, label=label)
    expect(r.crashes == 0, f"On {label} the arm crashed {r.crashes} time(s). Use glide() for straight-line moves near the other blocks.")
    n = r.blocks_in("tower")
    expect(n == 3 and r.tower >= 3, f"On {label}: {n} block(s) on the pad and the tallest stack is {r.tower}. Build all 3 into one tower at x = 114.")
SUCCESS = "🏗️ TOWER COMPLETE! You're a robot-arm engineer."
''',
        "concepts": ["manipulation", "kinematics"], "xp": 90,
    },
    "remix": {
        "prompt": "Make the arm yours! The playground has a longer arm, five blocks, two pads and two marks in the sky.",
        "ideas": ["Draw a square in the air with glide() — then a circle with sin and cos",
                  "Sort the blocks: warm colours on the left pad, cool colours on the right",
                  "Build the tallest tower you can (how high before the arm can't reach?)",
                  "Juggle: swap two towers using the empty space as a helper (the Towers of Hanoi puzzle!)"],
        "arena": ARM_REMIX,
    },
}

# ---------------------------------------------------------------------------
# warehouse arenas (top-down, gripper)
# ---------------------------------------------------------------------------
WH_BAY = {"name": "Loading Bay", "size": [240, 140], "start": [40, 70, 0], "time_limit": 25, "gripper": True,
          "blocks": [{"pos": [90, 70], "color": "red"}],
          "zones": [{"name": "dock", "rect": [180, 45, 40, 50], "color": "green", "label": "📦 dock"}],
          "labels": [[90, 58, "block"]]}

WH_EYES = {"name": "Robot Eyes", "size": [240, 180], "start": [60, 90, 0], "time_limit": 20, "gripper": True,
           "blocks": [{"pos": [150, 140], "color": "orange"}]}

WH_DOCKS = [{"name": "red dock", "rect": [10, 10, 44, 44], "color": "red", "label": "red"},
            {"name": "blue dock", "rect": [10, 126, 44, 44], "color": "blue", "label": "blue"}]
WH_GREEN = {"name": "green dock", "rect": [6, 70, 40, 40], "color": "green", "label": "green"}


def _floor(name, blocks, zones, time_limit=40, **extra):
    a = {"name": name, "size": [280, 180], "start": [70, 90, 0], "time_limit": time_limit, "gripper": True,
         "gps": True, "blocks": blocks, "zones": zones, "labels": [[70, 76, "🏠 home"]]}
    a.update(extra)
    return a


WH_GRAB = _floor("Pick-up Floor", [{"pos": [190, 120], "color": "green"}], [], 30)
WH_SORT = _floor("Sorting Floor", [{"pos": [190, 130], "color": "red"}], WH_DOCKS, 45)
WH_TWO = _floor("Two Orders", [{"pos": [170, 130], "color": "red"}, {"pos": [200, 60], "color": "blue"}], WH_DOCKS, 90)
WH_BOSS = _floor("Rush Hour", [{"pos": [170, 130], "color": "red"}, {"pos": [200, 60], "color": "blue"},
                               {"pos": [205, 105], "color": "green"}, {"pos": [150, 40], "color": "red"}],
                 WH_DOCKS + [WH_GREEN], 170)
WH_REMIX = {"name": "Mega Warehouse", "size": [320, 220], "start": [70, 110, 0], "time_limit": 180, "gripper": True,
            "gps": True,
            "blocks": [{"pos": [170, 170], "color": "red"}, {"pos": [220, 60], "color": "blue"},
                       {"pos": [200, 120], "color": "green"}, {"pos": [150, 50], "color": "yellow"},
                       {"pos": [250, 150], "color": "red"}, {"pos": [180, 30], "color": "blue"}],
            "zones": [{"name": "red dock", "rect": [10, 10, 44, 44], "color": "red", "label": "red"},
                      {"name": "blue dock", "rect": [10, 166, 44, 44], "color": "blue", "label": "blue"},
                      {"name": "green dock", "rect": [6, 90, 40, 40], "color": "green", "label": "green"}],
            "boxes": [[270, 90, 30, 40]],
            "labels": [[70, 96, "🏠 home"]]}

# ---------------------------------------------------------------------------
# Project 10 — Warehouse Bot
# ---------------------------------------------------------------------------
WH_S1 = '''# 📦 Warehouse Bot, reporting for duty!
robot.forward(39)
# TODO: close the gripper, carry the block to the dock and let go
'''

WH_S1_SOL = '''# 📦 Warehouse Bot, reporting for duty!
robot.forward(39)          # the block is now right in the gripper
if robot.grab():
    robot.say("Got it!")
robot.forward(110)         # carry it into the dock
robot.release()
robot.backward(20)         # back away so we don't bump it
'''

WH_S2 = '''# 👀 What can the camera see?
seen = robot.camera()
print(seen)
# TODO: if nothing is seen, turn a bit and look again.
#       Then turn by the block's angle to face it, and say its colour.
'''

WH_S2_SOL = '''# 👀 What can the camera see?
seen = robot.camera()
while not seen:            # an empty list means "nothing in view"
    robot.turn(15)
    seen = robot.camera()
block = seen[0]            # the nearest thing
print(block)
robot.turn(block["angle"])
robot.say("I see a " + block["color"] + " block!")
'''

WH_S3 = WH_S2_SOL + '''
# 🚗 TODO: drive toward the block, steering with the camera angle,
#          stop when it's close and grab it
'''

APPROACH = '''    # 🚗 approach: steer toward the block until it's in the gripper
    while True:
        seen = robot.camera()
        if not seen:
            break
        b = seen[0]
        if b["distance"] < 4:
            break
        steer = b["angle"] * 2
        robot.drive(40 - steer, 40 + steer)
        robot.wait(0.02)
    robot.stop()
'''

WH_S3_SOL = '''# 👀 look for a block
seen = robot.camera()
while not seen:
    robot.turn(15)
    seen = robot.camera()
robot.turn(seen[0]["angle"])

# 🚗 approach: steer toward the block until it's in the gripper
while True:
    seen = robot.camera()
    if not seen:
        break
    b = seen[0]
    if b["distance"] < 4:
        break
    steer = b["angle"] * 2          # block to the left → right wheel faster
    robot.drive(40 - steer, 40 + steer)
    robot.wait(0.02)
robot.stop()

if robot.grab():
    robot.say("Got a " + robot.holding() + " one!")
'''

NAV = '''import math

def wrap(angle):
    return (angle + 180) % 360 - 180

def turn_to(h):
    robot.turn(wrap(h - robot.heading()))

def go_to(tx, ty, stop_short=0):
    x, y = robot.position()
    turn_to(math.degrees(math.atan2(ty - y, tx - x)))
    robot.forward(math.hypot(tx - x, ty - y) - stop_short)
'''

WH_S4 = WH_S3_SOL + '''
# 🗺️ TODO: carry the block to the dock of its colour
#   red dock centre = (32, 32), blue dock centre = (32, 148)
'''

WH_S4_SOL = NAV + '''
''' + WH_S3_SOL + '''
# 🗺️ deliver to the dock of the same colour
color = robot.holding()
if color == "red":
    go_to(32, 32, 11)       # stop 11 cm short: the block sits 11 cm in front of the robot
elif color == "blue":
    go_to(32, 148, 11)
robot.release()
robot.backward(15)
'''

WH_S5 = WH_S4_SOL + '''
# 🔁 TODO: turn this into a state machine that keeps going:
#   SEARCH → APPROACH → DELIVER → HOME → SEARCH ... until no blocks are left
'''

MACHINE = '''
def search():
    """Sweep only the shelf area (heading -60 ... 60) so we never see the docks."""
    turn_to(-60)
    while robot.heading() < 60:
        seen = robot.camera()
        if seen:
            robot.turn(seen[0]["angle"])
            return True
        robot.turn(10)
    return False

def approach():
    while True:
        seen = robot.camera()
        if not seen:
            break
        b = seen[0]
        if b["distance"] < 4:
            break
        steer = b["angle"] * 2
        robot.drive(40 - steer, 40 + steer)
        robot.wait(0.02)
    robot.stop()
    return robot.grab()

HOME = (70, 90)
state = "SEARCH"
delivered = 0
while state != "DONE":
    if state == "SEARCH":
        robot.led("yellow")
        if search():
            state = "APPROACH"
        else:
            state = "DONE"
    elif state == "APPROACH":
        robot.led("blue")
        if approach():
            state = "DELIVER"
        else:
            state = "HOME"
    elif state == "DELIVER":
        robot.led("green")
        deliver(robot.holding())
        robot.release()
        robot.backward(15)
        delivered = delivered + 1
        state = "HOME"
    elif state == "HOME":
        robot.led("white")
        go_to(HOME[0], HOME[1])
        state = "SEARCH"
robot.say("All done: " + str(delivered) + " delivered!")
'''

WH_S5_SOL = NAV + '''
def deliver(color):
    if color == "red":
        go_to(32, 32, 11)
    elif color == "blue":
        go_to(32, 148, 11)
''' + MACHINE

WH_BOSS_SOL = NAV + '''
DOCKS = {"red": (32, 32), "blue": (32, 148), "green": (26, 90)}

def deliver(color):
    tx, ty = DOCKS[color]
    go_to(tx, ty, 11)
''' + MACHINE

WH_ARENA_CHECK = '''
def _grabbed(r):
    return [e for e in r.events if e["type"] == "grip" and e.get("got")]
'''

WAREHOUSE_BOT = {
    "id": "warehouse_bot", "week": 5, "order": 10, "title": "Warehouse Bot", "emoji": "📦",
    "tagline": "Find blocks with a camera, grab them and sort them into the right docks",
    "story": "Bolt got a job at the RoboQuest warehouse! It has a gripper on the front and a little camera that "
             "recognises coloured blocks. Orders are piling up: find each block, pick it up gently and deliver it "
             "to the dock of the same colour — all by itself.",
    "concepts": ["manipulation", "state_machines", "behaviors"],
    "expected_minutes": 120,
    "real_world": "Amazon's Kiva (now Amazon Robotics) and Proteus robots carry whole shelves to human pickers, and "
                  "Ocado's grid robots fetch groceries from a giant 3-D grid. They find their way by reading QR stickers "
                  "on the floor — an indoor 'GPS' — and run state machines like the one you'll write.",
    "build_it": "A Pixy2 or HuskyLens camera recognises coloured objects and reports their angle and size — exactly "
                "like robot.camera(). Add a micro:bit or LEGO SPIKE car and a servo claw and you have a real Warehouse Bot.",
    "steps": [
        {
            "id": "s1", "title": "Grab & go",
            "learn": "<p>Bolt now has a <b>gripper</b> — two little jaws on the front. Robots that pick things up "
                     "are doing <b>manipulation</b>: changing the world, not just driving around in it.</p>"
                     "<pre>robot.grab()      # close the jaws: True if a block was caught\nrobot.holding()   # colour of the block you hold, or None\n"
                     "robot.release()   # open the jaws</pre>"
                     "<p>The jaws reach just in front of the robot: a block is caught when its centre is about "
                     "<b>11 cm ahead of the robot's centre</b> (the robot's radius is 8 cm and the block is 6 cm wide). "
                     "The block here is 50 cm ahead, so drive 50 − 11 = 39 cm.</p>"
                     "<p>Since <code>grab()</code> tells you whether it worked, you can use it in an <code>if</code>. "
                     "Real grippers do this too: a sensor in the jaws checks something is really there.</p>",
            "task": "<p>Drive up to the red block, <b>grab</b> it, carry it into the green <b>📦 dock</b> and "
                    "<b>release</b> it there. Then back away.</p>",
            "goals": ["Grab the block", "Release it inside the dock", "No crashes"],
            "arena": WH_BAY, "starter": WH_S1, "solution": WH_S1_SOL,
            "hints": ["After forward(39) the block is in the jaws. Call robot.grab().",
                      "The dock starts at x = 180. The block rides 11 cm ahead of the robot, so drive about 110 cm more.",
                      "robot.grab()\nrobot.forward(110)\nrobot.release()\nrobot.backward(20)"],
            "check": WH_ARENA_CHECK + '''r = sim()
expect(_grabbed(r), "The gripper never caught the block. Drive 39 cm so the block is in the jaws, then robot.grab().")
expect(r.crashes == 0, f"The robot bumped a wall {r.crashes} time(s).")
expect(r.held is None, "You're still holding the block — robot.release() to put it down.")
b = r.blocks[0]
expect(r.blocks_in("dock") == 1, f"The block ended at ({b['x']:.0f}, {b['y']:.0f}), outside the dock (x 180–220). Carry it further before releasing.")
SUCCESS = "📦 First delivery done!"
''',
            "concepts": ["manipulation", "actuators"], "xp": 15,
        },
        {
            "id": "s2", "title": "Robot eyes",
            "learn": "<p>In a real warehouse the blocks aren't always in the same place, so Bolt needs eyes. "
                     "<code>robot.camera()</code> returns a <b>list</b> of what it sees, nearest first. Each thing is a "
                     "<b>dictionary</b> — a little bundle of named values:</p>"
                     "<pre>seen = robot.camera()\n# [{'kind': 'block', 'color': 'orange', 'angle': 29.1, 'distance': 95.0}]\n"
                     "block = seen[0]          # the first (nearest) item\nprint(block[\"angle\"])    # read a value by its name</pre>"
                     "<p><code>angle</code> is how far the block is from straight ahead: + means left, − means right — "
                     "the same as <code>robot.turn()</code>! So <code>robot.turn(block[\"angle\"])</code> faces it.</p>"
                     "<p>The camera only sees 30° each side (like looking through a paper tube). If the list is empty "
                     "(<code>not seen</code> is True), turn a bit and look again. Vision sensors like the "
                     "<b>Pixy2</b> and <b>HuskyLens</b> work just like this.</p>",
            "task": "<p>Look with the camera. While nothing is seen, turn 15° and look again. Then <b>turn to face the "
                    "block</b> and say its colour. I'll move the block around to test you!</p>",
            "goals": ["Use robot.camera()", "Face the block (±5°)", "Say its colour"],
            "arena": WH_EYES, "starter": WH_S2, "solution": WH_S2_SOL,
            "hints": ["A while loop keeps looking: while not seen: turn a bit, then seen = robot.camera() again.",
                      "After the loop, seen[0] is the nearest block. Its angle is exactly how much to turn.",
                      "block = seen[0]\nrobot.turn(block[\"angle\"])\nrobot.say(\"I see a \" + block[\"color\"] + \" block!\")"],
            "check": '''expect(calls("camera") >= 1, "Use robot.camera() to look for the block.")
tests = [("block up to the right", None), ("block down to the right (out of view at first!)", [{"pos": [140, 25], "color": "purple"}]),
         ("block behind the robot", [{"pos": [25, 60], "color": "green"}])]
for label, blocks in tests:
    r = sim(label=label) if blocks is None else sim(label=label, blocks=blocks)
    b = r.blocks[0]
    want = math.degrees(math.atan2(b["y"] - r.y, b["x"] - r.x))
    off = (r.heading - want + 180) % 360 - 180
    expect(r.dist_to(60, 90) < 5, f"({label}) The robot drove away — this mission is just about turning to look.")
    expect(abs(off) <= 5, f"({label}) The robot faces {r.heading:.0f}° but the block is at {want:.0f}° ({abs(off):.0f}° off). "
                          "Keep turning until the camera sees it, then robot.turn(seen[0][\\"angle\\"]).")
    expect(r.said(b["color"]), f"({label}) Say the block's colour — this one is {b['color']}. Use seen[0][\\"color\\"].")
SUCCESS = "👀 Eagle eyes! Bolt can find blocks anywhere."
''',
            "concepts": ["sensors", "manipulation"], "xp": 20,
        },
        {
            "id": "s3", "title": "Approach & grab",
            "learn": "<p>Now drive to the block. You could turn once and drive straight, but a tiny angle error "
                     "grows over a long drive. Better: <b>keep looking while you drive</b> and steer toward the block — "
                     "a feedback loop, like the line followers from week 3.</p>"
                     "<pre>steer = b[\"angle\"] * 2\nrobot.drive(40 - steer, 40 + steer)   # block on the left → right wheel faster</pre>"
                     "<p>When do you stop? The camera's <code>distance</code> is measured from the robot's front edge "
                     "to the block's centre. The jaws are 3 cm ahead of the front edge, so stop when "
                     "<b>distance &lt; 4</b>. (The ultrasonic <code>robot.distance()</code> sees blocks too — it reads "
                     "about 0–1 when the block is in the jaws.)</p>"
                     "<p>Don't ram it! Pushing the block around is how warehouse robots knock over shelves. "
                     "A good grab is gentle: stop, then close the jaws.</p>",
            "task": "<p>After facing the block, drive toward it in a loop, steering with the camera angle. "
                    "Stop when it's close, <b>grab it</b>, and say its colour. Don't push it more than 4 cm.</p>",
            "goals": ["Steer toward the block with the camera", "Grab it without pushing it", "Works wherever the block is"],
            "arena": WH_GRAB, "starter": WH_S3, "solution": WH_S3_SOL,
            "hints": ["Use while True: … break. Inside, read the camera, and break when seen[0][\"distance\"] < 4.",
                      "Steer with robot.drive(40 - steer, 40 + steer) where steer = angle × 2, and robot.wait(0.02) each loop.",
                      "robot.stop()\nif robot.grab():\n    robot.say(\"Got a \" + robot.holding() + \" one!\")"],
            "check": WH_ARENA_CHECK + '''expect(calls("camera") >= 1, "Use robot.camera() to find and steer toward the block.")
tests = [("block up to the right", None), ("block down to the right", [{"pos": [175, 40], "color": "orange"}]),
         ("block far away, slightly up", [{"pos": [215, 110], "color": "purple"}])]
for label, blocks in tests:
    r = sim(label=label) if blocks is None else sim(label=label, blocks=blocks)
    start = (ARENA["blocks"] if blocks is None else blocks)[0]["pos"]
    g = _grabbed(r)
    expect(g, f"({label}) The gripper never caught the block. Stop when the camera distance is under 4, then robot.grab().")
    expect(r.crashes == 0, f"({label}) The robot crashed into a wall {r.crashes} time(s).")
    t_grab = g[0]["t"]
    pushed = 0
    for t, bl in zip(r.frames["t"], r.frames["blocks"]):
        if t <= t_grab:
            pushed = max(pushed, math.hypot(bl[0][0] - start[0], bl[0][1] - start[1]))
    expect(pushed <= 4, f"({label}) You pushed the block {pushed:.0f} cm before grabbing it. Stop a little earlier and grab gently.")
    expect(r.held, f"({label}) You caught the block but let go of it. Hold on to it this time!")
SUCCESS = "🤏 Smooth approach, gentle grab!"
''',
            "concepts": ["manipulation", "sensors", "feedback"], "xp": 30,
        },
        {
            "id": "s4", "title": "Sort by colour",
            "learn": "<p>This warehouse has an indoor <b>GPS</b>: <code>robot.position()</code> gives (x, y). Real Kiva "
                     "robots get the same thing by reading QR stickers on the floor. With GPS, going to a spot is the "
                     "trigonometry you already know:</p>"
                     "<pre>def go_to(tx, ty, stop_short=0):\n    x, y = robot.position()\n"
                     "    turn_to(math.degrees(math.atan2(ty - y, tx - x)))\n"
                     "    robot.forward(math.hypot(tx - x, ty - y) - stop_short)</pre>"
                     "<p><code>turn_to(h)</code> turns to a compass heading: <code>robot.turn(wrap(h - robot.heading()))</code>, "
                     "where <code>wrap</code> keeps the turn between -180 and 180 so the robot never spins the long way round:</p>"
                     "<pre>def wrap(angle):\n    return (angle + 180) % 360 - 180</pre>"
                     "<p>Why <code>stop_short=11</code>? You want the <i>block</i> to land on the dock, and it rides "
                     "11 cm in front of the robot's centre.</p>",
            "task": "<p>After grabbing, check <code>robot.holding()</code>. Carry red blocks to the <b>red dock</b> "
                    "(centre 32, 32) and blue blocks to the <b>blue dock</b> (centre 32, 148). Release and back off.</p>",
            "goals": ["Deliver to the dock of the block's colour", "No crashes", "Works for red and blue blocks"],
            "arena": WH_SORT, "starter": WH_S4, "solution": WH_S4_SOL,
            "hints": ["Put import math, wrap, turn_to and go_to at the top of your program.",
                      "color = robot.holding() then if color == \"red\": go_to(32, 32, 11) elif color == \"blue\": go_to(32, 148, 11).",
                      "robot.release()\nrobot.backward(15)"],
            "check": WH_ARENA_CHECK + '''tests = [("a red block", None), ("a blue block", [{"pos": [180, 45], "color": "blue"}]),
         ("a blue block far up", [{"pos": [215, 150], "color": "blue"}])]
for label, blocks in tests:
    r = sim(label=label) if blocks is None else sim(label=label, blocks=blocks)
    b = r.blocks[0]
    expect(_grabbed(r), f"({label}) The gripper never caught the block.")
    expect(r.crashes == 0, f"({label}) The robot crashed {r.crashes} time(s). Remember stop_short=11 so you stop before the wall.")
    expect(r.held is None, f"({label}) You're still holding the block — release it at the dock.")
    want = b["color"] + " dock"
    expect(r.blocks_in(want) == 1, f"({label}) The {b['color']} block ended at ({b['x']:.0f}, {b['y']:.0f}), not in the {want}. "
                                   "Use robot.holding() to pick the right dock.")
SUCCESS = "🎨 Sorted! Every block in its own dock."
''',
            "concepts": ["manipulation", "decisions", "navigation"], "xp": 30,
        },
        {
            "id": "s5", "title": "Two orders",
            "learn": "<p>Two blocks now. The robot has to repeat: search → approach → deliver → come home → search… "
                     "The cleanest way to write that is a <b>state machine</b>: a <code>state</code> variable says "
                     "what the robot is doing, and each state decides what comes next.</p>"
                     "<pre>state = \"SEARCH\"\nwhile state != \"DONE\":\n    if state == \"SEARCH\":\n"
                     "        if search():\n            state = \"APPROACH\"\n        else:\n            state = \"DONE\"\n"
                     "    elif state == \"APPROACH\":\n        ...</pre>"
                     "<p>A new problem: after the first delivery, the camera would happily spot the block sitting "
                     "in the dock and fetch it again! So <code>search()</code> only sweeps the shelf area: go home, "
                     "<code>turn_to(-60)</code>, then turn left 10° at a time until the camera sees something or the "
                     "heading passes 60. Nothing found = the job is done.</p>"
                     "<p>Pro tip: an LED colour per state makes a state machine easy to debug — "
                     "watch the replay!</p>",
            "task": "<p>Turn your program into a state machine with states <b>SEARCH</b>, <b>APPROACH</b>, "
                    "<b>DELIVER</b>, <b>HOME</b> and <b>DONE</b>. Deliver <b>both blocks</b> to their docks, then stop.</p>",
            "goals": ["Use a state variable", "Both blocks in their docks", "No crashes"],
            "arena": WH_TWO, "starter": WH_S5, "solution": WH_S5_SOL,
            "hints": ["Wrap your look / approach / deliver code into functions: search(), approach() and deliver(color).",
                      "In search(): turn_to(-60), then while robot.heading() < 60: look; if seen, turn to it and return True; else turn(10). After the loop return False.",
                      "elif state == \"HOME\":\n    go_to(70, 90)\n    state = \"SEARCH\""],
            "check": WH_ARENA_CHECK + '''expect(uses("state_machines"), "Use a state variable, e.g. state = \\"SEARCH\\" and if state == \\"SEARCH\\": …")
tests = [("red up, blue down", None), ("blue down-left, red far up",
         [{"pos": [160, 40], "color": "blue"}, {"pos": [205, 120], "color": "red"}])]
for label, blocks in tests:
    r = sim(label=label) if blocks is None else sim(label=label, blocks=blocks)
    expect(r.crashes == 0, f"({label}) The robot crashed {r.crashes} time(s).")
    for b in r.blocks:
        want = b["color"] + " dock"
        expect(want in b["zones"] and not b["held"],
               f"({label}) The {b['color']} block ended at ({b['x']:.0f}, {b['y']:.0f}), not in the {want}. "
               "After a delivery, go HOME and SEARCH again.")
SUCCESS = "🔁 Two orders shipped by a real state machine!"
''',
            "concepts": ["state_machines", "manipulation", "behaviors"], "xp": 40,
        },
    ],
    "boss": {
        "id": "boss", "title": "Rush hour",
        "learn": "<p>Four blocks, three colours, one robot. A green dock has opened behind the home spot "
                 "(centre 26, 90). Your state machine should handle it with just one more dock.</p>"
                 "<p><b>Pro move:</b> a dictionary can map each colour to its dock, so you don't need a long "
                 "if/elif chain:</p><pre>DOCKS = {\"red\": (32, 32), \"blue\": (32, 148), \"green\": (26, 90)}\n"
                 "tx, ty = DOCKS[color]</pre>",
        "task": "<p>Sort <b>all 4 blocks</b> (red, blue, green, red) into their matching docks within the time limit. "
                "No crashes. I'll shuffle the blocks for a second test.</p>",
        "goals": ["All 4 blocks in the right docks", "No crashes", "Works with shuffled blocks"],
        "arena": WH_BOSS, "starter": WH_S5_SOL, "solution": WH_BOSS_SOL,
        "hints": ["Your state machine already loops until no blocks are left — you mostly need the green dock.",
                  "Add a green case to deliver(), or switch to a DOCKS dictionary.",
                  "DOCKS = {\"red\": (32, 32), \"blue\": (32, 148), \"green\": (26, 90)}\ndef deliver(color):\n    tx, ty = DOCKS[color]\n    go_to(tx, ty, 11)"],
        "check": '''tests = [("rush hour", None), ("shuffled", [{"pos": [160, 40], "color": "blue"}, {"pos": [210, 120], "color": "red"},
                                           {"pos": [200, 30], "color": "green"}, {"pos": [180, 150], "color": "blue"}])]
for label, blocks in tests:
    r = sim(label=label) if blocks is None else sim(label=label, blocks=blocks)
    expect(r.crashes == 0, f"({label}) The robot crashed {r.crashes} time(s).")
    ok = sum(1 for b in r.blocks if (b["color"] + " dock") in b["zones"] and not b["held"])
    bad = [b for b in r.blocks if (b["color"] + " dock") not in b["zones"] or b["held"]]
    if bad:
        b = bad[0]
        raise CheckFail(f"({label}) {ok}/4 blocks sorted. The {b['color']} block ended at ({b['x']:.0f}, {b['y']:.0f}), "
                        f"not in the {b['color']} dock.")
SUCCESS = "🏆 RUSH HOUR CLEARED! The warehouse runs itself."
''',
        "concepts": ["state_machines", "behaviors", "manipulation"], "xp": 90,
    },
    "remix": {
        "prompt": "Run the Mega Warehouse! Six blocks, a yellow one with no dock, and a pillar in the way.",
        "ideas": ["Count deliveries per colour and say a report at the end",
                  "Invent a rule for the yellow block (a 'returns' pile?)",
                  "Add a CHARGE state: after every 3 deliveries, park at home and beep",
                  "Plan the order: fetch the nearest block first to beat your own time"],
        "arena": WH_REMIX,
    },
}

PROJECTS = [ROBOT_ARM, WAREHOUSE_BOT]

# ---------------------------------------------------------------------------
# practice
# ---------------------------------------------------------------------------
P_STAR = {"type": "arm", "name": "Star Reach", "size": [160, 100], "start": [90, -90], "time_limit": 20,
          "marks": [[100, 60, "⭐"]]}

P_UNSTACK = {"type": "arm", "name": "Unstack", "size": [160, 100], "start": [90, -90], "time_limit": 40,
             "blocks": [{"x": 80, "color": "blue"}, {"x": 80, "y": 8, "color": "red"}],
             "targets": [{"name": "goal", "x": 115, "w": 14, "color": "green"}]}

P_LINE = {"type": "arm", "name": "Straight Line", "size": [160, 100], "start": [90, -90], "time_limit": 30,
          "marks": [[100, 20, "P"], [100, 60, "Q"]]}

P_GENTLE = {"name": "Gentle Grab", "size": [240, 120], "start": [40, 60, 0], "time_limit": 20, "gripper": True,
            "blocks": [{"pos": [110, 60], "color": "yellow"}]}

P_COURIER = {"name": "Courier", "size": [240, 120], "start": [60, 60, 0], "time_limit": 40, "gripper": True,
             "blocks": [{"pos": [160, 60], "color": "red"}],
             "zones": [{"name": "home", "rect": [10, 40, 50, 40], "color": "gray", "label": "🏠"}]}

P_PICKY = {"name": "Picky Picker", "size": [240, 160], "start": [40, 80, 0], "time_limit": 30, "gripper": True,
           "blocks": [{"pos": [100, 100], "color": "purple"}, {"pos": [170, 50], "color": "red"}]}

PRACTICE = [
    {
        "id": "p_manipulation_star", "concept": "manipulation", "title": "Reach for the star", "difficulty": 1,
        "task": "<p>Move the arm so the hand touches the ⭐ at <b>(100, 60)</b> (within 3 cm). Experiment: change the "
                "two angles in <code>arm.move(shoulder, elbow)</code> and print <code>arm.hand()</code> to see where "
                "you ended up.</p>",
        "goals": ["Hand within 3 cm of the star"],
        "arena": P_STAR, "starter": "arm.move(45, 0)\nprint(arm.hand())\n",
        "solution": "arm.move(53, -33)\nprint(arm.hand())\n",
        "hints": ["With the shoulder at 45 and the elbow straight, the hand is too high. Bend the elbow down (negative).",
                  "Try a shoulder a bit higher (50–55) and an elbow around -30.",
                  "arm.move(53, -33)"],
        "check": '''r = sim()
hx, hy = r.hand
d = math.hypot(hx - 100, hy - 60)
expect(r.crashes == 0, "The arm crashed into something.")
expect(d <= 3, f"The hand is at ({hx}, {hy}), {d:.1f} cm from the star at (100, 60). Keep adjusting the angles!")
SUCCESS = "⭐ Star caught!"
''',
        "xp": 15,
    },
    {
        "id": "p_kinematics_elbow", "concept": "kinematics", "title": "Elbow finder", "difficulty": 2,
        "task": "<p>Where is the <b>elbow joint</b>? It's the end of the upper arm: <code>L1</code> away from the base "
                "at the shoulder angle. After <code>arm.move(30, 0)</code>, compute the elbow's x and y with "
                "<code>math.cos</code> and <code>math.sin</code> and print them. Read the sizes with "
                "<code>arm.links()</code> and <code>arm.base()</code> — I'll test on a second arm.</p>",
        "goals": ["Use cos and sin", "Print the elbow's x and y (±1 cm)", "Works on a different arm"],
        "arena": ARM_LAB, "starter": "import math\narm.move(30, 0)\n# TODO: print the elbow's x and y\n",
        "solution": "import math\narm.move(30, 0)\ns, e = arm.angles()\nL1, L2 = arm.links()\nbx, by = arm.base()\n"
                    "ex = bx + L1 * math.cos(math.radians(s))\ney = by + L1 * math.sin(math.radians(s))\n"
                    "print(\"elbow:\", round(ex, 1), round(ey, 1))\n",
        "hints": ["The elbow only depends on the shoulder angle and L1.",
                  "Remember math.cos wants radians: math.cos(math.radians(s)).",
                  "ex = bx + L1 * math.cos(math.radians(s))\ney = by + L1 * math.sin(math.radians(s))\nprint(ex, ey)"],
        "check": '''import re as _re
expect(calls("cos") >= 1 and calls("sin") >= 1, "Use math.cos for x and math.sin for y.")

def _ok(r, a):
    bx, by = a.get("base", [40, 12])
    L1 = a.get("links", [45, 35])[0]
    ex, ey = bx + L1 * math.cos(math.radians(r.shoulder)), by + L1 * math.sin(math.radians(r.shoulder))
    for line in r.lines:
        nums = [float(n) for n in _re.findall(r"-?\\d+(?:\\.\\d+)?", line)]
        for p, q in zip(nums, nums[1:]):
            if abs(p - ex) <= 1 and abs(q - ey) <= 1:
                return True, ex, ey
    return False, ex, ey

for label, a in [("the lab arm", arena()), ("an arm with a 55 cm upper arm, base (30, 15)", arena(links=[55, 30], base=[30, 15]))]:
    r = sim(a, label=label)
    good, ex, ey = _ok(r, a)
    expect(good, f"On {label} the elbow is at ({ex:.1f}, {ey:.1f}), but I didn't see those numbers printed. "
                 "Use arm.links() and arm.base() instead of typing the sizes.")
SUCCESS = "💪 Elbow located!"
''',
        "xp": 20,
    },
    {
        "id": "p_manipulation_unstack", "concept": "manipulation", "title": "Unstack", "difficulty": 2,
        "task": "<p>A red block sits on top of a blue one at x = 80. Move <b>only the red block</b> onto the green goal "
                "at x = 115, leaving the blue block where it is. The top of the red block is at y = 16, so grab at y = 17. "
                "An <code>ik()</code> and <code>go()</code> are ready for you.</p>",
        "goals": ["Red block on the goal", "Blue block still at x = 80", "No crashes"],
        "arena": P_UNSTACK,
        "starter": "import math\n\n" + IK_FUNC + "\ndef go(x, y):\n    s, e = ik(x, y)\n    arm.move(s, e)\n\n# TODO: unstack!\n",
        "solution": "import math\n\n" + IK_FUNC + "\ndef go(x, y):\n    s, e = ik(x, y)\n    arm.move(s, e)\n\n"
                    "go(80, 40)\ngo(80, 17)\narm.grab()\ngo(80, 40)\ngo(115, 40)\ngo(115, 9)\narm.release()\ngo(115, 40)\n",
        "hints": ["Hover first: go(80, 40). Then go down to the top of the red block: go(80, 17).",
                  "Grab, lift back up to 40, move over x = 115, go down to 9 (it lands on the table) and release.",
                  "go(80, 40)\ngo(80, 17)\narm.grab()\ngo(80, 40)\ngo(115, 40)\ngo(115, 9)\narm.release()"],
        "check": '''r = sim()
expect(r.crashes == 0, f"The arm crashed {r.crashes} time(s). Stop at y = 17 above the stack, not lower.")
red = [b for b in r.blocks if b["color"] == "red"][0]
blue = [b for b in r.blocks if b["color"] == "blue"][0]
expect(r.blocks_in("goal", "red") == 1, f"The red block is at x = {red['x']:.0f}, not on the goal at x = 115.")
expect(abs(blue["x"] - 80) < 1 and blue["level"] == 0, "Leave the blue block where it was!")
SUCCESS = "🧱 Unstacked!"
''',
        "xp": 25,
    },
    {
        "id": "p_kinematics_line", "concept": "kinematics", "title": "Ruler-straight", "difficulty": 3,
        "task": "<p>Slide the hand from <b>P (100, 20)</b> straight up to <b>Q (100, 60)</b>, staying within 1.5 cm of "
                "the line x = 100 the whole way. A single <code>arm.move</code> swings in a curve — instead, walk the hand "
                "through lots of in-between points with <code>ik()</code> (that's a <b>linear move</b>).</p>",
        "goals": ["Start at P", "Reach Q", "Stay on the line x = 100 (±1.5 cm)"],
        "arena": P_LINE,
        "starter": "import math\n\n" + IK_FUNC + "\ns, e = ik(100, 20)\narm.move(s, e)\ns, e = ik(100, 60)\narm.move(s, e)\n",
        "solution": "import math\n\n" + IK_FUNC + "\ns, e = ik(100, 20)\narm.move(s, e)\nfor i in range(1, 41):\n"
                    "    s, e = ik(100, 20 + i)\n    arm.move(s, e)\n",
        "hints": ["Replace the second move with a loop that moves y from 20 to 60 a little at a time.",
                  "for i in range(1, 41): then y = 20 + i. Each step is only 1 cm, so the curve can't wander far.",
                  "for i in range(1, 41):\n    s, e = ik(100, 20 + i)\n    arm.move(s, e)"],
        "check": '''bx, by = ARENA.get("base", [40, 12])
L1, L2 = ARENA.get("links", [45, 35])
r = sim()
path = []
for s, e in zip(r.frames["s"], r.frames["e"]):
    a1, a2 = math.radians(s), math.radians(s + e)
    path.append((bx + L1 * math.cos(a1) + L2 * math.cos(a2), by + L1 * math.sin(a1) + L2 * math.sin(a2)))
i0 = next((i for i, p in enumerate(path) if math.hypot(p[0] - 100, p[1] - 20) <= 1.5), None)
expect(i0 is not None, "Start by moving the hand to P (100, 20).")
i1 = next((i for i in range(i0, len(path)) if math.hypot(path[i][0] - 100, path[i][1] - 60) <= 1.5), None)
expect(i1 is not None, "After P, get the hand up to Q (100, 60).")
worst = max(abs(p[0] - 100) for p in path[i0:i1 + 1])
expect(worst <= 1.5, f"On the way from P to Q the hand wandered {worst:.1f} cm off the line. Use many small ik() steps.")
SUCCESS = "📏 Ruler-straight! That's a linear move."
''',
        "xp": 30,
    },
    {
        "id": "p_manipulation_gentle", "concept": "manipulation", "title": "Gentle grab", "difficulty": 1,
        "task": "<p>There's a block somewhere straight ahead. Drive forward until the <b>distance sensor</b> reads "
                "less than 1 cm (the block is in the jaws), stop, and grab it. Don't bulldoze it!</p>",
        "goals": ["Stop using robot.distance()", "Grab the block", "Push it less than 3 cm"],
        "arena": P_GENTLE, "starter": "robot.drive(40, 40)\n# TODO: stop when the block is close, then grab\n",
        "solution": "robot.drive(40, 40)\nwhile robot.distance() > 1:\n    robot.wait(0.02)\nrobot.stop()\nrobot.grab()\n",
        "hints": ["A while loop can wait while robot.distance() is still more than 1.",
                  "After the loop, robot.stop() and then robot.grab().",
                  "while robot.distance() > 1:\n    robot.wait(0.02)\nrobot.stop()\nrobot.grab()"],
        "check": '''expect(calls("distance") >= 1, "Use robot.distance() to know when the block is close.")
for label, pos in [("block 70 cm away", [110, 60]), ("block 120 cm away", [160, 60])]:
    r = sim(label=label, blocks=[{"pos": pos, "color": "yellow"}])
    g = [e for e in r.events if e["type"] == "grip" and e.get("got")]
    expect(g, f"({label}) The gripper didn't catch the block. Stop when the distance is under 1, then robot.grab().")
    pushed = max(math.hypot(bl[0][0] - pos[0], bl[0][1] - pos[1]) for t, bl in zip(r.frames["t"], r.frames["blocks"]) if t <= g[0]["t"])
    expect(pushed <= 3, f"({label}) You pushed the block {pushed:.0f} cm before grabbing. Stop sooner!")
    expect(r.held == "yellow", f"({label}) You should be holding the block at the end.")
SUCCESS = "🤲 Gentle as a surgeon robot."
''',
        "xp": 15,
    },
    {
        "id": "p_state_machines_courier", "concept": "state_machines", "title": "Mood-light courier", "difficulty": 2,
        "task": "<p>Write a state machine with a <code>state</code> variable and an LED colour per state: "
                "<b>SEEK</b> (yellow) drive to the block, <b>CARRY</b> (green) grab it and back up until "
                "<code>robot.distance(\"back\")</code> &lt; 25, then release it in the 🏠 zone, <b>DONE</b> (blue).</p>",
        "goals": ["Use a state variable", "LEDs: yellow → green → blue", "Block ends in the home zone"],
        "arena": P_COURIER, "starter": "state = \"SEEK\"\nrobot.led(\"yellow\")\n# TODO: the rest of the state machine\n",
        "solution": "state = \"SEEK\"\nwhile state != \"DONE\":\n    if state == \"SEEK\":\n        robot.led(\"yellow\")\n"
                    "        robot.drive(40, 40)\n        if robot.distance() < 1:\n            robot.stop()\n            robot.grab()\n"
                    "            state = \"CARRY\"\n    elif state == \"CARRY\":\n        robot.led(\"green\")\n"
                    "        robot.drive(-40, -40)\n        if robot.distance(\"back\") < 25:\n            robot.stop()\n"
                    "            robot.release()\n            state = \"DONE\"\n    robot.wait(0.02)\nrobot.led(\"blue\")\n",
        "hints": ["Loop with while state != \"DONE\": and use if / elif for each state.",
                  "In SEEK: drive forward; when robot.distance() < 1, stop, grab and switch state to \"CARRY\".",
                  "elif state == \"CARRY\":\n    robot.led(\"green\")\n    robot.drive(-40, -40)\n    if robot.distance(\"back\") < 25:\n        robot.stop()\n        robot.release()\n        state = \"DONE\""],
        "check": '''expect(uses("state_machines"), "Use a state variable: state = \\"SEEK\\" and if state == \\"SEEK\\": …")
for label, pos in [("block 100 cm away", [160, 60]), ("block 150 cm away", [210, 60])]:
    r = sim(label=label, blocks=[{"pos": pos, "color": "red"}])
    cols = [c for i, c in enumerate(r.led_colors()) if i == 0 or c != r.led_colors()[i - 1]]
    order = [c for c in cols if c in ("yellow", "green", "blue")]
    expect(order[:3] == ["yellow", "green", "blue"] or (len(order) >= 3 and order[0] == "yellow" and "green" in order and order[-1] == "blue"),
           f"({label}) The LEDs went {order}. Use yellow for SEEK, green for CARRY and blue when DONE.")
    expect(r.crashes == 0, f"({label}) The robot crashed {r.crashes} time(s).")
    expect(r.held is None and r.blocks_in("home") == 1, f"({label}) The block should end (released) in the 🏠 zone.")
SUCCESS = "🚦 A tidy state machine!"
''',
        "xp": 25,
    },
    {
        "id": "p_behaviors_picky", "concept": "behaviors", "title": "Picky picker", "difficulty": 3,
        "task": "<p>Two blocks: a purple one and a red one. The customer ordered <b>red</b>! Turn until the camera sees a "
                "<b>red</b> block (ignore other colours), then drive to it steering with its angle, and grab it.</p>",
        "goals": ["Look for the red block only", "Grab it", "Leave the purple one alone"],
        "arena": P_PICKY,
        "starter": "seen = robot.camera()\nwhile not seen:\n    robot.turn(15)\n    seen = robot.camera()\n"
                   "robot.turn(seen[0][\"angle\"])\nrobot.forward(50)\nrobot.grab()\n",
        "solution": "def find_red():\n    for thing in robot.camera():\n        if thing[\"color\"] == \"red\":\n            return thing\n"
                    "    return None\n\nred = find_red()\nwhile red is None:\n    robot.turn(15)\n    red = find_red()\n"
                    "robot.turn(red[\"angle\"])\nwhile red is not None and red[\"distance\"] >= 4:\n"
                    "    steer = red[\"angle\"] * 2\n    robot.drive(40 - steer, 40 + steer)\n    robot.wait(0.02)\n    red = find_red()\n"
                    "robot.stop()\nrobot.grab()\n",
        "hints": ["Loop over robot.camera() with for thing in robot.camera(): and check thing[\"color\"] == \"red\".",
                  "Make a find_red() function that returns the red thing or None, and use it both to search and to steer.",
                  "while red is not None and red[\"distance\"] >= 4:\n    steer = red[\"angle\"] * 2\n    robot.drive(40 - steer, 40 + steer)\n    robot.wait(0.02)\n    red = find_red()"],
        "check": '''for label, blocks in [("purple near, red to the right", None),
                      ("red up, purple down", [{"pos": [110, 55], "color": "purple"}, {"pos": [180, 120], "color": "red"}])]:
    r = sim(label=label) if blocks is None else sim(label=label, blocks=blocks)
    expect(r.held == "red", f"({label}) You're holding {r.held or 'nothing'} — the order was for the RED block.")
    expect(r.crashes == 0, f"({label}) The robot crashed {r.crashes} time(s).")
SUCCESS = "🍒 Picked exactly the right one."
''',
        "xp": 30,
    },
]
