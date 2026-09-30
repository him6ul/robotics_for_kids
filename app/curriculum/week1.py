"""Week 1 — Make it move: motors, sequences and turning geometry."""

# ---------------------------------------------------------------------------
# arenas
# ---------------------------------------------------------------------------
LAB = {"name": "Robot Lab", "size": [240, 160], "start": [40, 80, 0], "time_limit": 20,
       "labels": [[40, 60, "start"]]}

LANE = {"name": "Test Lane", "size": [240, 160], "start": [40, 80, 0], "time_limit": 15,
        "zones": [{"name": "target", "rect": [80, 60, 10, 40], "color": "yellow", "label": "45 cm"}],
        "lines": [{"pts": [[40, 50], [40, 110]], "width": 1.0}],
        "labels": [[40, 44, "start line"]]}

FLAG = {"name": "Flag Run", "size": [240, 160], "start": [40, 40, 0], "time_limit": 20,
        "zones": [{"name": "flag", "rect": [108, 68, 24, 24], "color": "green", "label": "🚩"}],
        "boxes": [[150, 90, 40, 40]]}

GARAGE = {"name": "Garage", "size": [240, 170], "start": [40, 40, 0], "time_limit": 30,
          "zones": [{"name": "garage", "rect": [172, 102, 36, 40], "color": "blue", "label": "🅿️"}],
          "walls": [[166, 100, 166, 150], [214, 100, 214, 150], [166, 150, 214, 150]],
          "boxes": [[40, 110, 50, 30]]}

GEMS = {"name": "Gem Path", "size": [240, 190], "start": [40, 40, 0], "time_limit": 30,
        "gems": [[110, 40], [170, 100], [170, 150]],
        "boxes": [[180, 20, 30, 40], [40, 120, 40, 40]]}

SLALOM = {"name": "Slalom", "size": [260, 160], "start": [30, 80, 0], "time_limit": 45,
          "boxes": [[76, 76, 8, 8], [126, 76, 8, 8], [176, 76, 8, 8]],
          "gems": [[80, 112], [130, 48], [180, 112]],
          "zones": [{"name": "finish", "rect": [220, 60, 40, 40], "color": "green", "label": "🏁"}]}

CANVAS = {"name": "Art Studio", "size": [280, 240], "start": [140, 120, 0], "time_limit": 90}

PLAYGROUND_W1 = {"name": "Big Lab", "size": [320, 220], "start": [40, 40, 0], "time_limit": 90,
                 "gems": [[100, 180], [260, 60], [280, 190], [160, 110]],
                 "boxes": [[120, 40, 30, 30], [200, 140, 40, 20]],
                 "zones": [{"name": "home", "rect": [20, 20, 40, 40], "color": "blue", "label": "🏠"}]}

# ---------------------------------------------------------------------------
# Project 1 — Hello, Robot!
# ---------------------------------------------------------------------------
HELLO_S1 = '''# 🤖 Wake up your robot!
robot.say("Hello, I am Bolt!")
# TODO: turn on the LED and make a beep
'''

HELLO_S1_SOL = '''# 🤖 Wake up your robot!
robot.say("Hello, I am Bolt!")
robot.led("green")
robot.beep(660)
robot.wait(0.5)
robot.beep(880)
'''

HELLO_S2 = HELLO_S1_SOL + '''
# 🚗 Drive forward 45 cm
robot.drive(50, 50)
# TODO: how long should the motors stay on?
'''

HELLO_S2_SOL = HELLO_S1_SOL + '''
# 🚗 Drive forward 45 cm
robot.drive(50, 50)     # 50% power = 15 cm per second
robot.wait(3)           # 15 cm/s x 3 s = 45 cm
robot.stop()
'''

HELLO_S3 = '''robot.say("Flag mission!")
robot.led("blue")
robot.forward(80)
# TODO: turn left and drive to the flag
'''

HELLO_S3_SOL = '''robot.say("Flag mission!")
robot.led("blue")
robot.forward(80)
robot.turn_left(90)
robot.forward(40)
robot.led("green")
robot.say("Got the flag!")
'''

HELLO_S4 = HELLO_S3_SOL

HELLO_S4_SOL = '''robot.say("Parking time")
robot.led("yellow")
robot.forward(150)
robot.turn_left(90)
robot.forward(82)
robot.led("green")
robot.say("Parked!")
'''

HELLO_S5 = HELLO_S4_SOL + '''
# TODO: new arena! Collect all 3 gems
'''

HELLO_S5_SOL = '''robot.say("Gem hunt!")
robot.forward(70)        # gem 1
robot.turn(45)
robot.forward(85)        # the diagonal: 60 x 1.414
robot.turn(45)
robot.forward(50)        # gem 3
robot.beep(1000)
robot.say("All gems!")
'''

BOSS1_SOL = '''import math

# where the robot is now, and where it points
x, y, heading = 30, 80, 0
points = [(80, 112), (130, 48), (180, 112), (235, 80)]

for (tx, ty) in points:
    angle = math.degrees(math.atan2(ty - y, tx - x))
    robot.turn(angle - heading)
    robot.forward(math.hypot(tx - x, ty - y))
    x, y, heading = tx, ty, angle
robot.say("Slalom champion!")
'''

HELLO_ROBOT = {
    "id": "hello_robot", "week": 1, "order": 1, "title": "Hello, Robot!", "emoji": "🤖",
    "tagline": "Wake up your robot, make it drive, turn, park and hunt gems",
    "story": "Meet Bolt, your brand-new robot. Right now Bolt can't do anything on its own — every robot "
             "only does what its program tells it. Your first job as a robot engineer: bring Bolt to life, "
             "teach it to drive, and send it on its first missions around the lab.",
    "concepts": ["actuators", "sequencing"],
    "expected_minutes": 90,
    "real_world": "Factory robots and delivery robots all start with the same idea: a program is a list of "
                  "motor commands carried out in order. The Mars rovers get their daily 'drive list' sent from Earth!",
    "build_it": "With a LEGO SPIKE or a micro:bit car (e.g. a Cutebot), `drive()` is two motor-power blocks and `wait()` is a pause block.",
    "steps": [
        {
            "id": "s1", "title": "Wake up, Bolt!",
            "learn": "<p>A robot has three kinds of parts: <b>actuators</b> that <i>do</i> things (motors, lights, "
                     "speakers), <b>sensors</b> that <i>notice</i> things, and a <b>computer</b> that runs your program.</p>"
                     "<p>Today we start with actuators. Your robot is called <code>robot</code> and you give it "
                     "commands with a dot:</p><pre>robot.say(\"Hi!\")      # speech bubble\nrobot.led(\"purple\")    # light up the LED\n"
                     "robot.beep(440)        # play a note (440 Hz = the note A)\nrobot.wait(1)          # pause for 1 second</pre>"
                     "<p>Commands run <b>one after another</b>, top to bottom — that's called a <b>sequence</b>. "
                     "Press ▶ Run and watch the replay on the right.</p>",
            "task": "<p>Make Bolt say something, turn its LED on (any colour) and play <b>at least one beep</b>.</p>",
            "goals": ["Say something", "Turn the LED on", "Beep!"],
            "arena": LAB, "starter": HELLO_S1, "solution": HELLO_S1_SOL,
            "hints": ["The LED command is robot.led(...) with a colour name inside quotes.",
                      "The beep command is robot.beep(...). Try a number like 440 or 880 inside.",
                      "robot.led(\"green\")\nrobot.beep(880)"],
            "check": '''r = sim()
expect(r.said(), "Bolt didn't say anything. Use robot.say(\\"...\\")")
expect(r.led_colors() and any(c != "off" for c in r.led_colors()), "The LED never turned on. Try robot.led(\\"green\\").")
expect(r.count("beep") >= 1, "I didn't hear a beep! Add robot.beep(880).")
SUCCESS = "Bolt is awake! 🤖💡🔊"
''',
            "concepts": ["actuators", "sequencing"], "xp": 15,
        },
        {
            "id": "s2", "title": "First drive",
            "learn": "<p>Bolt has two wheels, each with its own motor. <code>robot.drive(left, right)</code> sets the "
                     "<b>power</b> of each motor from -100 (full reverse) to 100 (full forward). Same power on both = straight.</p>"
                     "<p>Here's the catch: <code>drive()</code> only <i>switches the motors on</i> and then your program "
                     "carries on instantly. If the program ends, the robot stops! You must <b>wait</b> while it drives:</p>"
                     "<pre>robot.drive(100, 100)   # full power = 30 cm per second\nrobot.wait(2)           # drive for 2 seconds → 60 cm\nrobot.stop()</pre>"
                     "<p>Robot engineers use this all the time: <b>distance = speed × time</b>. At power 50 the robot goes "
                     "15 cm every second.</p>",
            "task": "<p>Drive forward so the robot stops on the yellow <b>45 cm</b> mark. Use <code>drive()</code> "
                    "and <code>wait()</code> (no <code>forward()</code> yet!).</p>",
            "goals": ["Use drive() and wait()", "Stop on the 45 cm mark"],
            "arena": LANE, "starter": HELLO_S2, "solution": HELLO_S2_SOL,
            "hints": ["Run it first — what happens with only drive()? The program ends immediately, so the robot stops.",
                      "At power 50 the robot goes 15 cm each second. How many seconds make 45 cm?",
                      "robot.drive(50, 50)\nrobot.wait(3)\nrobot.stop()"],
            "check": '''expect(calls("drive") >= 1 and calls("wait") >= 1, "Use robot.drive(...) and robot.wait(...) for this mission.")
expect(calls("forward") == 0, "No robot.forward() yet — this mission is about drive() + wait().")
r = sim()
moved = r.x - 40
expect(moved > 2, "The robot didn't move. After robot.drive(...) you need robot.wait(...) so it has time to drive!")
expect(abs(r.heading) < 5, f"The robot turned (heading {r.heading}°). Give both motors the SAME power to go straight.")
expect(abs(moved - 45) <= 4, f"The robot drove {moved:.0f} cm but the mark is at 45 cm. Remember: distance = speed × time.")
SUCCESS = f"Bullseye! {moved:.0f} cm. distance = speed × time 🎯"
''',
            "concepts": ["actuators", "sequencing"], "xp": 20,
        },
        {
            "id": "s3", "title": "Move and turn",
            "learn": "<p>Doing the maths every time is tiring, so Bolt has shortcut commands:</p>"
                     "<pre>robot.forward(50)     # drive 50 cm, then stop\nrobot.backward(20)\nrobot.turn_left(90)   # spin on the spot\nrobot.turn_right(45)\nrobot.turn(-90)       # + is left, - is right</pre>"
                     "<p>To spin on the spot, the wheels turn in <b>opposite</b> directions. Try "
                     "<code>robot.drive(-40, 40)</code> in the playground to see it!</p>"
                     "<p>Directions in RoboQuest are like in maths: <b>0° points right</b> (east), 90° points up.</p>",
            "task": "<p>Drive to the green 🚩 flag: 80 cm forward, turn left, then 40 cm up. Stop on the flag.</p>",
            "goals": ["Use forward() and a turn", "Stop on the flag"],
            "arena": FLAG, "starter": HELLO_S3, "solution": HELLO_S3_SOL,
            "hints": ["After forward(80) the robot is right below the flag. Which way does it need to face?",
                      "Turning left 90° makes the robot face up (north).",
                      "robot.turn_left(90)\nrobot.forward(40)"],
            "check": '''r = sim()
expect(r.crashes == 0, f"Ouch — the robot hit something {r.crashes} time(s). Check your distances.")
expect(r.in_zone("flag"), f"The robot ended at ({r.x:.0f}, {r.y:.0f}) but the flag is at (120, 80). Two moves and a turn!")
SUCCESS = "Flag captured! 🚩"
''',
            "concepts": ["actuators", "sequencing"], "xp": 20,
        },
        {
            "id": "s4", "title": "Park in the garage",
            "learn": "<p>Real robots have to be <b>precise</b>: a delivery robot must stop at the right door, and a "
                     "car must park without scratching the walls. You plan the route as a <b>sequence of moves</b>, "
                     "then test and adjust. That's the engineering loop: <b>plan → try → fix</b>.</p>"
                     "<p>Tip: use the grid-less arena like graph paper. The start is at (40, 40); the garage centre is "
                     "around (190, 122). How far right is that? How far up?</p>",
            "task": "<p>New arena! Change your moves so Bolt parks <b>inside the blue garage 🅿️</b> without touching any "
                    "wall, then turns its LED green.</p>",
            "goals": ["Park inside the garage", "No crashes", "LED green at the end"],
            "arena": GARAGE, "starter": HELLO_S4, "solution": HELLO_S4_SOL,
            "hints": ["The garage opening faces down. Drive right until you're below it, then turn left and drive up.",
                      "From x = 40 to x = 190 is 150 cm. From y = 40 to about y = 122 is 82 cm.",
                      "robot.forward(150)\nrobot.turn_left(90)\nrobot.forward(82)\nrobot.led(\"green\")"],
            "check": '''r = sim()
expect(r.crashes == 0, f"Scratch! The robot bumped a wall {r.crashes} time(s). Line up with the garage door before driving in.")
expect(r.in_zone("garage"), f"The robot stopped at ({r.x:.0f}, {r.y:.0f}) — not inside the garage (around x 172–208, y 102–142).")
cols = r.led_colors()
expect(cols and cols[-1] == "green", "Parked! Now finish with robot.led(\\"green\\") so everyone knows.")
SUCCESS = "Perfect parking! 🅿️✨"
''',
            "concepts": ["sequencing", "actuators"], "xp": 25,
        },
        {
            "id": "s5", "title": "Gem hunt",
            "learn": "<p>Turns don't have to be 90°. A <b>45° turn</b> points the robot diagonally. And a diagonal is "
                     "longer than it looks: going 60 right and 60 up is about <b>85 cm</b> on the diagonal "
                     "(60 × 1.414 — that's Pythagoras!).</p><pre>robot.turn(45)      # half a right angle, to the left\nrobot.forward(85)</pre>"
                     "<p>Robots touching a gem collect it. Plan your route from gem to gem.</p>",
            "task": "<p>Collect all <b>3 gems</b> without crashing. Gem 1 is straight ahead, gem 2 is up the diagonal, "
                    "gem 3 is straight above gem 2.</p>",
            "goals": ["Collect 3 gems", "No crashes"],
            "arena": GEMS, "starter": HELLO_S5, "solution": HELLO_S5_SOL,
            "hints": ["Gem 1 is at x = 110, so drive 70 cm first.",
                      "Turn 45° left, then drive about 85 cm to gem 2 at (170, 100).",
                      "robot.forward(70)\nrobot.turn(45)\nrobot.forward(85)\nrobot.turn(45)\nrobot.forward(50)"],
            "check": '''r = sim()
expect(r.crashes == 0, f"The robot crashed {r.crashes} time(s) — check your distances and angles.")
expect(r.gems == 3, f"You collected {r.gems} of 3 gems. Watch the replay: where does the robot miss?")
SUCCESS = "All gems collected! 💎💎💎"
''',
            "concepts": ["sequencing", "actuators"], "xp": 30,
        },
    ],
    "boss": {
        "id": "boss", "title": "The Slalom",
        "learn": "<p>Slalom skiers weave between flags. Your robot must weave between the orange cones, "
                 "touching each gem, then finish in the 🏁 zone.</p>"
                 "<p><b>Pro move:</b> let Python do the geometry. <code>math.atan2(dy, dx)</code> gives the angle to a "
                 "point and <code>math.hypot(dx, dy)</code> gives the distance:</p>"
                 "<pre>import math\nangle = math.degrees(math.atan2(32, 50))   # about 33°\ndist = math.hypot(50, 32)                  # about 59 cm</pre>",
        "task": "<p>Start at (30, 80) facing right. Visit the gems at (80, 112), (130, 48) and (180, 112), then "
                "finish in the 🏁 zone around (235, 80). <b>No crashes!</b></p>",
        "goals": ["Collect all 3 gems", "Finish in the 🏁 zone", "No crashes"],
        "arena": SLALOM, "starter": "# 👾 BOSS: The Slalom\n# The robot starts at (30, 80) facing right (0°)\n\n",
        "solution": BOSS1_SOL,
        "hints": ["Work out each leg: from (30, 80) to (80, 112) is 50 right and 32 up.",
                  "turn() is relative: turn by (new angle - current angle) each time.",
                  "angle = math.degrees(math.atan2(ty - y, tx - x))\nrobot.turn(angle - heading)\nrobot.forward(math.hypot(tx - x, ty - y))"],
        "check": '''r = sim()
expect(r.crashes == 0, f"You hit a cone or wall {r.crashes} time(s)! Weave a little wider.")
expect(r.gems == 3, f"Collected {r.gems}/3 gems. Every gate counts in a slalom!")
expect(r.in_zone("finish"), f"You ended at ({r.x:.0f}, {r.y:.0f}). Finish inside the 🏁 zone.")
SUCCESS = "SLALOM CHAMPION! 🏆"
''',
        "concepts": ["sequencing", "kinematics"], "xp": 80,
    },
    "remix": {
        "prompt": "Make Bolt put on a show! Choreograph a robot dance, a light show, or a tour of the big lab.",
        "ideas": ["A dance with spins, beeps and LED colours on the beat",
                  "Play a tune with robot.beep() (C = 523, D = 587, E = 659…)",
                  "Visit all 4 gems in the big lab and return home",
                  "Draw your name's first letter while driving"],
        "arena": PLAYGROUND_W1,
    },
}

# ---------------------------------------------------------------------------
# Project 2 — Robo-Artist
# ---------------------------------------------------------------------------
ART_S1 = '''robot.pen_down("blue")
robot.forward(50)
robot.turn(90)
# TODO: finish the square with a for loop
'''

ART_S1_SOL = '''robot.pen_down("blue")
for side in range(4):
    robot.forward(50)
    robot.turn(90)
robot.pen_up()
'''

ART_S2 = ART_S1_SOL + '''
# TODO: make a polygon(sides, size) function
'''

ART_S2_SOL = '''def polygon(sides, size):
    for i in range(sides):
        robot.forward(size)
        robot.turn(360 / sides)

robot.pen_down("purple")
polygon(3, 60)
polygon(6, 35)
robot.pen_up()
'''

ART_S3_SOL = '''def polygon(sides, size):
    for i in range(sides):
        robot.forward(size)
        robot.turn(360 / sides)

robot.pen_down("green")
# radius = 7 x (right + left) / (right - left) = 7 x 100 / 20 = 35 cm
robot.drive(40, 60)
robot.wait(15)
robot.stop()
robot.pen_up()
'''

ART_S4_SOL = '''def polygon(sides, size):
    for i in range(sides):
        robot.forward(size)
        robot.turn(360 / sides)

def circle(seconds):
    robot.drive(26, 54)     # radius about 20 cm
    robot.wait(seconds)
    robot.stop()

robot.pen_down("red")
for petal in range(6):
    circle(10.5)
    robot.turn(60)
robot.pen_up()
'''

ART_S5_SOL = '''robot.pen_down("orange")
for i in range(20):
    robot.forward(5 + i * 5)
    robot.turn(90)
robot.pen_up()
'''

ART_BOSS_SOL = '''robot.pen_down("gold")
for point in range(5):
    robot.forward(80)
    robot.turn(144)
robot.pen_up()
robot.say("A star is born ⭐")
'''

SPIRAL_CHECK = '''import ast as _ast
r = sim()
expect(r.crashes == 0, f"The robot hit the wall {r.crashes} time(s). Make the spiral a little smaller.")
expect(r.pen_length > 0, "Put the pen down so we can see the spiral!")
grows = False
for loop in [n for n in _ast.walk(tree) if isinstance(n, (_ast.For, _ast.While))]:
    for c in _ast.walk(loop):
        if isinstance(c, _ast.Call) and getattr(c.func, "attr", "") in ("forward", "wait", "drive") and c.args:
            if any(not isinstance(a, _ast.Constant) for a in c.args):
                grows = True
expect(grows, "Inside your loop, the distance should change each time — use the loop variable, like robot.forward(5 + i * 5).")
expect(r.corners() >= 12 or r.pen_length >= 900, f"I only see {r.corners()} corners. A spiral needs lots of turns — try range(20).")
expect(not r.closed, "Your drawing ends where it started — that's a loop, not a spiral! Each side should be longer than the last.")
w, h = r.trail_bbox
expect(w >= 90 and h >= 90, f"The spiral is only {w:.0f} × {h:.0f} cm. Let it grow bigger (about 100 cm or more).")
SUCCESS = "Hypnotic! 🌀"
'''

ROBO_ARTIST = {
    "id": "robo_artist", "week": 1, "order": 2, "title": "Robo-Artist", "emoji": "🎨",
    "tagline": "Put a pen on your robot and draw shapes, circles, flowers and spirals",
    "story": "Bolt has a new tool: a pen it can lower onto the floor. Wherever it drives, it draws. "
             "Turn the lab floor into an art gallery — and discover the geometry every robot uses to steer.",
    "concepts": ["kinematics", "sequencing"],
    "expected_minutes": 100,
    "real_world": "Robot vacuum cleaners, lawn-mower robots and CNC drawing machines all plan paths out of lines and "
                  "arcs. Changing the speed of each wheel is exactly how a Roomba curves around your sofa.",
    "build_it": "Tape a marker to the back of a micro:bit or LEGO robot, put it on big paper, and run the same programs!",
    "steps": [
        {
            "id": "s1", "title": "Square with a loop",
            "learn": "<p><code>robot.pen_down(\"blue\")</code> lowers the pen, <code>robot.pen_up()</code> lifts it.</p>"
                     "<p>A square is <i>forward, turn, forward, turn…</i> four times. Instead of copying lines, "
                     "a <b>for loop</b> repeats them:</p><pre>for i in range(4):\n    robot.forward(50)   # indented = inside the loop\n    robot.turn(90)</pre>"
                     "<p>Robots love loops: a warehouse robot repeats its route hundreds of times a day.</p>",
            "task": "<p>Draw a <b>square with 50 cm sides</b> using a <code>for</code> loop.</p>",
            "goals": ["Use a for loop", "Draw a closed square, 50 cm sides"],
            "arena": CANVAS, "starter": ART_S1, "solution": ART_S1_SOL,
            "hints": ["Put the forward and the turn inside a for loop.", "range(4) repeats 4 times.",
                      "for side in range(4):\n    robot.forward(50)\n    robot.turn(90)"],
            "check": '''expect(loops() >= 1, "Use a for loop to repeat the sides.")
r = sim()
expect(r.pen_length > 0, "No drawing! Use robot.pen_down(...) before driving.")
w, h = r.trail_bbox
expect(abs(w - 50) <= 4 and abs(h - 50) <= 4, f"Your drawing is {w:.0f} × {h:.0f} cm. A square with 50 cm sides should be 50 × 50.")
expect(r.closed, "The square isn't closed — the pen should end where it started. 4 sides, 4 turns of 90°!")
expect(r.corners() >= 3, "I don't see square corners. Turn 90° after each side.")
SUCCESS = "A perfect square! ⬛"
''',
            "concepts": ["sequencing", "kinematics"], "xp": 20,
        },
        {
            "id": "s2", "title": "Any polygon",
            "learn": "<p>How much does the robot turn in total when it drives all the way round a shape and faces "
                     "the same way again? Always <b>360°</b>. So for a shape with <code>n</code> sides, each turn is "
                     "<b>360 / n</b>: triangle 120°, pentagon 72°, hexagon 60°.</p>"
                     "<p>Let's package that into a <b>function</b> — a named mini-program you can reuse:</p>"
                     "<pre>def polygon(sides, size):\n    for i in range(sides):\n        robot.forward(size)\n        robot.turn(360 / sides)\n\npolygon(5, 40)   # a pentagon!</pre>",
            "task": "<p>Write <code>polygon(sides, size)</code> and use it to draw a <b>triangle with 60 cm sides</b> and then a "
                    "<b>hexagon with 35 cm sides</b>, both from the same starting point.</p>",
            "goals": ["Define polygon(sides, size)", "Draw a triangle (60) and a hexagon (35)"],
            "arena": CANVAS, "starter": ART_S2, "solution": ART_S2_SOL,
            "hints": ["The turn inside the function is 360 / sides.",
                      "Call your function twice: once with 3 sides, once with 6.",
                      "polygon(3, 60)\npolygon(6, 35)"],
            "check": '''expect(defines("polygon"), "Make a function called polygon: def polygon(sides, size):")
expect(calls("polygon") >= 2, "Call polygon(...) twice — a triangle and a hexagon.")
expect("360" in source, "Work out the turn from 360 degrees: 360 / sides.")
r = sim()
expect(abs(r.pen_length - 390) <= 12, f"Your pen drew {r.pen_length:.0f} cm. A 60 cm triangle + a 35 cm hexagon is 180 + 210 = 390 cm.")
expect(r.closed, "The shapes don't close up — check your turn is 360 / sides.")
SUCCESS = "Triangle ✓ Hexagon ✓ — you just used the 360° rule! 🔺⬡"
''',
            "concepts": ["kinematics", "sequencing"], "xp": 25,
        },
        {
            "id": "s3", "title": "Robot circles",
            "learn": "<p>What happens if the wheels have <b>different</b> speeds? The faster wheel travels further, so the "
                     "robot curves toward the slower side and drives in a <b>circle</b>. This is called "
                     "<b>differential steering</b> — it's how tanks, Roombas and wheelchairs turn.</p>"
                     "<p>Robot engineers have a formula. With wheels 14 cm apart, the circle's radius is:</p>"
                     "<pre>radius = 7 × (right + left) / (right - left)\n\nrobot.drive(40, 60)   # 7 × 100 / 20 = 35 cm radius</pre>"
                     "<p>The robot's speed is the average of the wheels: (40 + 60) / 2 = 50 power = 15 cm/s. "
                     "A circle of radius 35 is 2 × π × 35 ≈ 220 cm long — so how many seconds for one full lap?</p>",
            "task": "<p>Keep your <code>polygon</code> function but remove the triangle/hexagon calls. Draw <b>one full circle with a radius "
                    "of about 35 cm</b> (70 cm wide) using <code>drive(left, right)</code> and <code>wait()</code>.</p>",
            "goals": ["Different wheel powers", "Circle about 70 cm wide", "Go all the way round (once)"],
            "arena": CANVAS, "starter": ART_S2_SOL.replace("polygon(3, 60)\npolygon(6, 35)\n", "# TODO: draw a circle with drive() and wait()\n"),
            "solution": ART_S3_SOL,
            "hints": ["Try robot.drive(40, 60) — the formula says that's a 35 cm radius.",
                      "The circle is about 220 cm long and the robot goes 15 cm/s. 220 / 15 ≈ 15 seconds.",
                      "robot.drive(40, 60)\nrobot.wait(15)\nrobot.stop()"],
            "check": '''expect(calls("drive") >= 1, "Use robot.drive(left, right) with different powers.")
r = sim()
expect(r.pen_length > 0, "Put the pen down to draw your circle!")
w, h = r.trail_bbox
expect(r.pen_length >= 200, f"Your line is {r.pen_length:.0f} cm long — a full circle of radius 35 is about 220 cm. Wait a bit longer!")
expect(r.pen_length <= 260, f"Your line is {r.pen_length:.0f} cm — that's more than one lap (about 220 cm). Wait a little less.")
expect(abs(w - 70) <= 9 and abs(h - 70) <= 9, f"Your circle is {w:.0f} × {h:.0f} cm. A radius of 35 makes it about 70 × 70. Check the formula!")
SUCCESS = "Round and round! ⭕ That's differential steering."
''',
            "concepts": ["kinematics", "actuators"], "xp": 25,
        },
        {
            "id": "s4", "title": "Flower power",
            "learn": "<p>Combine what you know: a loop that draws a circle, then turns a bit, then draws another circle. "
                     "If you turn <b>60°</b> between circles, six circles make a flower 🌸.</p>"
                     "<p>A function makes it neat:</p><pre>def circle(seconds):\n    robot.drive(26, 54)   # radius ≈ 20 cm\n    robot.wait(seconds)\n    robot.stop()</pre>"
                     "<p>With <code>drive(26, 54)</code> the robot goes 12 cm/s and a full circle takes about 10.5 s.</p>",
            "task": "<p>Draw a <b>flower with 6 circular petals</b>: repeat <i>circle, turn 60°</i> six times.</p>",
            "goals": ["Use a loop", "6 petals (circles)", "Turn between petals"],
            "arena": CANVAS, "starter": ART_S3_SOL.replace("robot.drive(40, 60)\nrobot.wait(15)\nrobot.stop()\n", "# TODO: loop 6 times: a circle, then turn 60\n"),
            "solution": ART_S4_SOL,
            "hints": ["Make a circle(...) function with drive + wait + stop inside.",
                      "for petal in range(6): then call circle and turn(60) inside the loop.",
                      "for petal in range(6):\n    circle(10.5)\n    robot.turn(60)"],
            "check": '''expect(loops() >= 1, "Use a loop to draw the petals.")
expect(calls("turn") >= 1, "Turn between petals with robot.turn(60).")
r = sim()
expect(r.crashes == 0, "The robot hit a wall — make the petals smaller.")
w, h = r.trail_bbox
expect(r.pen_length >= 450, f"Your flower's line is only {r.pen_length:.0f} cm. Six full circles should be much longer — are they full circles?")
expect(w >= 55 and h >= 55, f"The flower is {w:.0f} × {h:.0f} cm — the petals should spread out all around (turn 60° each time).")
SUCCESS = "Beautiful flower! 🌸"
''',
            "concepts": ["kinematics", "sequencing"], "xp": 30,
        },
        {
            "id": "s5", "title": "Spiral",
            "learn": "<p>In a loop, the loop variable <code>i</code> counts 0, 1, 2, 3… You can use it to make each side "
                     "<b>longer</b> than the last:</p><pre>for i in range(20):\n    robot.forward(5 + i * 5)   # 5, 10, 15, 20…\n    robot.turn(90)</pre>"
                     "<p>That's a square spiral! Lawn-mower robots use spirals to cover a whole garden.</p>",
            "task": "<p>Start fresh (you can delete the flower): draw a <b>spiral</b> that grows to about 100 cm wide, "
                    "using a loop where the distance grows each time.</p>",
            "goals": ["Distance grows each time round", "About 100 cm wide", "No crashes"],
            "arena": CANVAS, "starter": "robot.pen_down(\"orange\")\nfor i in range(20):\n    robot.forward(20)   # TODO: make this grow\n    robot.turn(90)\n",
            "solution": ART_S5_SOL,
            "hints": ["The forward distance must change — use i inside it.", "5 + i * 5 grows by 5 cm every side.",
                      "robot.forward(5 + i * 5)"],
            "check": SPIRAL_CHECK,
            "concepts": ["kinematics", "sequencing"], "xp": 30,
        },
    ],
    "boss": {
        "id": "boss", "title": "Draw a star",
        "learn": "<p>A 5-point star is a polygon with a twist: the robot turns so much that it crosses its own lines. "
                 "It still turns all the way round — but <b>twice</b> (720°) before facing the start direction. "
                 "So each turn is 720 / 5 = ?</p>",
        "task": "<p>Draw a <b>5-point star with 80 cm lines</b> that closes perfectly.</p>",
        "goals": ["5 lines of 80 cm", "Star closes perfectly", "5 sharp points"],
        "arena": CANVAS, "starter": "robot.pen_down(\"gold\")\n# 👾 BOSS: draw a 5-point star\n",
        "solution": ART_BOSS_SOL,
        "hints": ["It's a loop of 5 lines.", "The total turning is 720°, split over 5 turns.",
                  "for point in range(5):\n    robot.forward(80)\n    robot.turn(144)"],
        "check": '''r = sim()
expect(r.crashes == 0, "The robot hit the wall.")
expect(abs(r.pen_length - 400) <= 15, f"Your star's lines add up to {r.pen_length:.0f} cm — 5 lines × 80 cm = 400.")
expect(r.closed, "The star doesn't close. Try turning 720 / 5 degrees each time.")
expect(4 <= r.corners(90) <= 6, f"I count {r.corners(90)} sharp points — a star has 5.")
SUCCESS = "⭐ A STAR IS BORN ⭐"
''',
        "concepts": ["kinematics", "sequencing"], "xp": 70,
    },
    "remix": {
        "prompt": "Make your own robot masterpiece! Combine shapes, colours and loops into art nobody has seen before.",
        "ideas": ["A rainbow: circles of different colours and sizes",
                  "A spirograph: a polygon, turn 10°, repeat 36 times",
                  "Draw a house with a door and a window",
                  "A galaxy: spirals with growing arcs using drive(left, right) with changing speeds"],
        "arena": {**CANVAS, "name": "Giant Canvas", "size": [340, 280], "start": [170, 140, 0], "time_limit": 180},
    },
}

PROJECTS = [HELLO_ROBOT, ROBO_ARTIST]

# ---------------------------------------------------------------------------
# Practice side quests
# ---------------------------------------------------------------------------
DOCK = {"name": "Loading Dock", "size": [200, 160], "start": [60, 80, 0], "time_limit": 15,
        "zones": [{"name": "dock", "rect": [10, 60, 30, 40], "color": "blue", "label": "dock"}],
        "walls": [[5, 58, 45, 58], [5, 102, 45, 102]]}

CRATE = {"name": "Crate Loop", "size": [240, 160], "start": [40, 40, 0], "time_limit": 40,
         "boxes": [[90, 60, 50, 40]],
         "gems": [[115, 40], [190, 80], [115, 120], [40, 80]],
         "zones": [{"name": "start", "rect": [25, 25, 30, 30], "color": "green"}]}

PRACTICE = [
    {
        "id": "p_actuators_1", "concept": "actuators", "title": "Reverse into the dock", "difficulty": 1,
        "task": "<p>Trucks back into loading docks. Drive <b>backwards</b> into the blue dock behind you — keep facing right!</p>",
        "goals": ["Drive backwards", "Stop inside the dock", "Still facing right"],
        "arena": DOCK, "starter": "robot.forward(35)\n", "solution": "robot.backward(35)\nrobot.beep()\n",
        "hints": ["Which command moves backwards?", "The dock is about 35 cm behind you.", "robot.backward(35)"],
        "check": '''r = sim()
expect(abs(r.heading) < 10, f"The robot turned around (heading {r.heading}°). Back in without turning!")
expect(r.in_zone("dock"), f"The robot ended at x = {r.x:.0f}. The dock is between x = 10 and 40.")
expect(r.crashes == 0, "Careful — you bumped the dock walls.")
SUCCESS = "Beep beep beep… docked! 🚚"
''',
        "xp": 15,
    },
    {
        "id": "p_actuators_2", "concept": "actuators", "title": "Spin & shine", "difficulty": 1,
        "task": "<p>Do a full <b>360° spin left</b> with the LED green, then a full <b>360° spin right</b> with the LED blue.</p>",
        "goals": ["Spin 360° left (green)", "Spin 360° right (blue)", "End facing the start direction"],
        "arena": LAB, "starter": "robot.led(\"green\")\n", "solution": "robot.led(\"green\")\nrobot.turn(360)\nrobot.led(\"blue\")\nrobot.turn(-360)\n",
        "hints": ["robot.turn(360) is one whole spin to the left.", "Negative angles turn right.",
                  "robot.turn(360)\nrobot.led(\"blue\")\nrobot.turn(-360)"],
        "check": '''r = sim()
h = r.series("h")
expect(max(h) >= 350, f"The robot only spun {max(h):.0f}° to the left. A full spin is 360°.")
expect(abs(h[-1]) <= 5, f"You should end facing the start direction, but you're {h[-1]:.0f}° off.")
cols = r.led_colors()
expect("green" in cols and "blue" in cols, "Use a green LED for the left spin and blue for the right spin.")
SUCCESS = "Dizzy but dazzling! 💫"
''',
        "xp": 15,
    },
    {
        "id": "p_sequencing_1", "concept": "sequencing", "title": "Around the crate", "difficulty": 2,
        "task": "<p>Drive all the way round the crate, touching the 4 gems, and finish back in the green start square.</p>",
        "goals": ["4 gems", "Back in the start square", "No crashes"],
        "arena": CRATE, "starter": "robot.forward(150)\nrobot.turn_left()\n",
        "solution": "for side in range(2):\n    robot.forward(150)\n    robot.turn_left()\n    robot.forward(80)\n    robot.turn_left()\n",
        "hints": ["It's a rectangle: 150 cm, turn, 80 cm, turn, and again.", "A loop that runs twice can do it.",
                  "for side in range(2):\n    robot.forward(150)\n    robot.turn_left()\n    robot.forward(80)\n    robot.turn_left()"],
        "check": '''r = sim()
expect(r.crashes == 0, "You bumped the crate or a wall.")
expect(r.gems == 4, f"{r.gems}/4 gems. Go all the way round!")
expect(r.in_zone("start"), "Finish back in the green square where you started.")
SUCCESS = "Lap complete! 📦"
''',
        "xp": 20,
    },
    {
        "id": "p_sequencing_2", "concept": "sequencing", "title": "Traffic light", "difficulty": 2,
        "task": "<p>Be a polite robot: LED <b>red</b>, wait 2 s, <b>yellow</b>, wait 1 s, <b>green</b> — and only THEN drive 30 cm.</p>",
        "goals": ["Red → yellow → green", "Wait at red for 2 s", "Drive only on green"],
        "arena": LAB, "starter": "robot.led(\"red\")\nrobot.forward(30)\n",
        "solution": "robot.led(\"red\")\nrobot.wait(2)\nrobot.led(\"yellow\")\nrobot.wait(1)\nrobot.led(\"green\")\nrobot.forward(30)\n",
        "hints": ["Use robot.wait() between colours.", "The order is red, yellow, green, then forward.",
                  "robot.led(\"red\")\nrobot.wait(2)\nrobot.led(\"yellow\")\nrobot.wait(1)\nrobot.led(\"green\")"],
        "check": '''r = sim()
leds = [e for e in r.events if e["type"] == "led"]
names = [e["color"] for e in leds]
expect("red" in names and "yellow" in names and "green" in names, "Use all three colours: red, yellow and green.")
t_red = next(e["t"] for e in leds if e["color"] == "red")
t_yel = next(e["t"] for e in leds if e["color"] == "yellow")
t_grn = next(e["t"] for e in leds if e["color"] == "green")
expect(t_red < t_yel < t_grn, "The order should be red → yellow → green.")
expect(t_grn - t_red >= 2.8, f"The light went from red to green in {t_grn - t_red:.1f} s. Wait 2 s on red and 1 s on yellow.")
xs = r.series("x"); ts = r.series("t")
before = [x for x, t in zip(xs, ts) if t < t_grn - 0.05]
expect(all(abs(x - 40) < 0.5 for x in before), "The robot moved before the light was green! 🚨")
expect(r.x - 40 >= 25, "After green, drive forward 30 cm.")
SUCCESS = "Model citizen robot! 🚦"
''',
        "xp": 20,
    },
    {
        "id": "p_kinematics_1", "concept": "kinematics", "title": "Pivot turn", "difficulty": 2,
        "task": "<p>Turn <b>90° left</b> by keeping the LEFT wheel still and driving only the right wheel "
                "(<code>robot.drive(0, 50)</code>). How long does it take? Right wheel speed 15 cm/s, and it travels "
                "a quarter circle of radius 14 cm.</p>",
        "goals": ["Only the right wheel moves", "Turn 90° (±6°)"],
        "arena": LAB, "starter": "robot.drive(0, 50)\n", "solution": "robot.drive(0, 50)\nrobot.wait(1.47)\nrobot.stop()\n",
        "hints": ["A quarter circle of radius 14 is 2 × π × 14 / 4 ≈ 22 cm.", "22 cm at 15 cm/s is about 1.5 seconds.",
                  "robot.drive(0, 50)\nrobot.wait(1.47)\nrobot.stop()"],
        "check": '''expect(calls("turn") + calls("turn_left") + calls("turn_right") == 0, "No turn() here — use drive(0, 50) for a pivot.")
r = sim()
expect(abs(r.heading - 90) <= 6, f"You turned {r.heading:.0f}°. Aim for 90°.")
expect(r.dist_to(40, 80) > 4, "The robot should pivot around its left wheel, so its centre moves a little.")
SUCCESS = "Pivot pro! ↪️"
''',
        "xp": 20,
    },
    {
        "id": "p_kinematics_2", "concept": "kinematics", "title": "U-turn", "difficulty": 3,
        "task": "<p>Make a smooth <b>U-turn</b>: half a circle with radius 30 cm, so you end 60 cm above the start, "
                "facing the other way. Use <code>drive(left, right)</code> and the radius formula "
                "<code>7 × (right + left) / (right - left)</code>.</p>",
        "goals": ["Half circle, radius 30", "End at (40, 140) facing left"],
        "arena": {"name": "U-turn", "size": [200, 180], "start": [40, 80, 0], "time_limit": 20,
                  "zones": [{"name": "end", "rect": [30, 130, 20, 20], "color": "yellow"}]},
        "starter": "robot.drive(50, 50)\nrobot.wait(2)\n",
        "solution": "robot.drive(46, 74)   # radius = 7 x 120 / 28 = 30\nrobot.wait(5.24)      # half circle = 3.14 x 30 = 94 cm at 18 cm/s\nrobot.stop()\n",
        "hints": ["For radius 30, right/left must be about 37/23 (try 46 and 74).",
                  "Half a circle of radius 30 is π × 30 ≈ 94 cm. At (46+74)/2 = 60 power = 18 cm/s that's ≈ 5.2 s.",
                  "robot.drive(46, 74)\nrobot.wait(5.24)\nrobot.stop()"],
        "check": '''r = sim()
expect(r.crashes == 0, "Bumped a wall — check your radius.")
expect(abs(abs(r.heading) - 180) <= 10, f"You're facing {r.heading:.0f}°. After a U-turn you should face 180° (left).")
expect(r.dist_to(40, 140) <= 8, f"You ended at ({r.x:.0f}, {r.y:.0f}); a radius-30 U-turn ends at (40, 140).")
SUCCESS = "Smooth U-turn! ↩️"
''',
        "xp": 25,
    },
]
