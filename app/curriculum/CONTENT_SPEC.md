# Curriculum content spec — RoboQuest

The learner is an 8th grader (~13 years old). He knows a little Python (variables, `if`, loops,
functions — he may have done a beginner Python course) but has never done robotics. The program
is 6 weeks, 2 projects per week. Each project is a robot he *programs in a simulator* and each
robotics fundamental is learned *because the project needs it*. Tone: warm, playful, curious,
never condescending, short sentences. Explain the *why* with real-robot analogies (Roombas, Mars
rovers, warehouse robots, self-driving cars, factory arms). Emoji welcome but sparingly. Assume
~45–60 minute sessions, 3–4 sessions per week.

When a project needs a Python idea he may not know yet (e.g. `while` loops, functions, lists,
`import math`), teach it briefly inside the lesson with a tiny example. Never assume classes.

Each week lives in `app/curriculum/weekN.py` and defines two module-level lists: `PROJECTS` and
`PRACTICE`. Plain Python data only (dicts/lists/strings). Arenas are dicts (see below). You may
define helper arena dicts / functions at module level to avoid repetition.

## Project

```python
{
    "id": "bat_bot",                  # snake_case, globally unique
    "week": 2,
    "order": 3,                       # 1..12 across the whole program
    "title": "Bat-Bot",
    "emoji": "🦇",
    "tagline": "Give your robot ultrasonic 'bat ears' so it never bumps into walls",
    "story": "…2–4 sentences setting up the mission…",
    "concepts": ["sensors", "control_loop", "decisions"],   # concepts this project TEACHES
    "expected_minutes": 100,          # realistic total for the core missions
    "real_world": "1–2 sentences: which real robots use this idea and how.",
    "build_it": "1–2 sentences: how you could build this with a real kit (micro:bit, LEGO SPIKE, Arduino) — optional fun.",
    "steps": [ STEP, ... ],           # exactly 5 core missions that build ONE program further each time
    "boss": STEP,                     # one harder optional stretch challenge (bigger xp), id "boss"
    "remix": {
        "prompt": "Make it yours! …",
        "ideas": ["idea 1", "idea 2", "idea 3", "idea 4"],   # easy → ambitious
        "arena": ARENA,               # the arena the remix runs in (often a bigger / trickier one)
    },
}
```

## Step (also used for `boss`)

```python
{
    "id": "s1",                       # s1..s5, "boss" for the boss
    "title": "Measure the wall",
    "learn": "HTML: the mini-lesson, 2–5 short paragraphs. Allowed tags: <p> <b> <i> <code> <pre> <ul> <li> <br>. "
             "Show a tiny example in <pre>. Explain WHY with an analogy / real robot.",
    "task": "HTML: exactly what to make the robot do in this mission. Concrete and short.",
    "goals": ["Stop before the wall", "Don't crash", "Stop within 5 cm of 20 cm"],   # 1–4 short checklist items shown to him
    "arena": ARENA,                   # the arena shown and used by ▶ Run (and by default in the check)
    "starter": "python code the editor starts with (the previous mission's program + a # TODO for the new part). MUST FAIL the check.",
    "hints": ["gentle nudge", "more specific", "nearly the answer (a code line)"],   # exactly 3
    "solution": "complete working program that PASSES the check",
    "check": "python snippet, see below",
    "concepts": ["sensors"],          # concepts exercised in this step (subset of the ids below)
    "xp": 20,                         # 10–40 for steps, 60–100 for boss
}
```

His code carries forward: when he passes mission N, mission N+1's editor opens with HIS code
(the `starter` is only used if he has no code yet), so each task must make sense as "add/modify
something in the program you already have". Keep starters consistent with the previous solution.
It's fine (and good) for later missions of a project to change the arena (harder layout, noise…).

## Concept ids (use only these)

| id | label | meaning |
|---|---|---|
| `actuators` | Motors & Actuators | motor power, differential drive, LEDs/sound as outputs |
| `sequencing` | Sequences & Timing | a program as a timed sequence of actions, open-loop moves |
| `kinematics` | Kinematics & Geometry | turning geometry, arcs, wheel base, speed × time, trig for arms |
| `sensors` | Sensors | reading distance / bumper / floor / colour / light / camera values |
| `control_loop` | Sense-Think-Act Loop | the repeating read-sensor → decide → drive loop, loop timing |
| `decisions` | Reactive Decisions | if/else on sensor values, reflexes |
| `thresholds` | Thresholds & Calibration | picking cut-off values, calibrating black/white, noise margins |
| `feedback` | Feedback Control | closed loop vs open loop, bang-bang control, correcting errors |
| `pid` | P / PID Control | error, proportional gain Kp, derivative, tuning, overshoot |
| `odometry` | Odometry & Gyro | encoders, heading, dead reckoning, drift |
| `state_machines` | State Machines | a `state` variable, transitions, modes |
| `manipulation` | Grippers & Arms | grippers, servos, joint angles, forward/inverse kinematics, pick & place |
| `navigation` | Navigation | wall following, maze strategies, going to a goal |
| `mapping` | Maps & Path Planning | grid maps, remembering where you've been, BFS shortest path |
| `behaviors` | Combining Behaviors | priorities between behaviours (avoid > seek > wander), multi-sensor |
| `design` | Engineering Design | plan → build → test → improve, decomposing into functions |

## The 6-week arc (follow this)

| Wk | # | id | Project | Concepts | Missions (5) → boss |
|---|---|---|---|---|---|
| 1 Make it move | 1 | `hello_robot` 🤖 Hello, Robot! | actuators, sequencing | say/LED/beep → drive()+wait() → forward()/turn() → park in the garage zone → collect gems along a path; boss: slalom through cones |
| | 2 | `robo_artist` 🎨 Robo-Artist | kinematics, sequencing | pen square with a `for` loop → any polygon (turn = 360/n) → circle with drive(l, r) (differential steering, radius) → flower / figure-8 → spiral; boss: 5-point star |
| 2 Robots that sense | 3 | `bat_bot` 🦇 Bat-Bot | sensors, control_loop, decisions, thresholds | print distance → stop before the wall (while loop) → slow down as it gets close (stop at 20 cm) → turn away from walls → follow-me: keep 30 cm from a moving… wall/box (bang-bang); boss: corridor zig-zag |
| | 4 | `robo_vac` 🧹 Robo-Vac | sensors, decisions, control_loop, behaviors | bumper stop → bump, back up, turn → random turns (`import random`) → clean for 60 s collecting ≥70 % dust gems → stay inside the room (black edge = stairs, floor sensor); boss: whole flat with furniture |
| 3 Follow the line | 5 | `line_tracker` 🛤️ Line Tracker | thresholds, sensors, feedback | read & print floor on white/black, pick a threshold → drive until the black line → one-sensor zig-zag edge follower (bang-bang) → two-sensor follower → stop on the red finish zone; boss: follow a line with sharp turns and a gap |
| | 6 | `race_track` 🏎️ Race Track Pro | pid, feedback | proportional steering on the edge (error = floor − target) → plot the error & tune Kp → go faster and finish 1 lap → add derivative (PD) for hairpins → 2 laps under a time; boss: 3 fast laps, no leaving the track |
| 4 Know where you are | 7 | `precision_pilot` 🧭 Precision Pilot | odometry, feedback, kinematics | see forward() drift in a noisy arena → drive exactly N cm with encoders → turn exactly 90° with the gyro → drive straight with heading correction → dead reckoning: go to a spot & come home; boss: 3 waypoints in the noisy arena |
| | 8 | `delivery_bot` 🚚 Delivery Bot | state_machines, behaviors, sensors | a `state` variable + LED colour per state → follow the road line and STOP at a coloured station → DELIVER (wait + beep) then continue → count stations, park at the 3rd → WAIT state when something blocks the road; boss: full delivery route |
| 5 Grab & build | 9 | `robot_arm` 🦾 Robot Arm | manipulation, kinematics | move the servos / wave → forward kinematics with sin/cos (compare with arm.hand()) → reach marked points → pick & place a block onto a target → inverse kinematics function (law of cosines) to reach (x, y); boss: stack a 3-block tower |
| | 10 | `warehouse_bot` 📦 Warehouse Bot | manipulation, state_machines, behaviors | grab the block in front, drive to the zone, release → use the camera to turn toward a block → approach & grab (distance) → deliver to the zone matching its colour → two blocks; boss: sort 4 blocks |
| 6 Smart robots | 11 | `maze_master` 🌀 Maze Master | navigation, mapping, feedback | wall-follow at 15 cm with P control on the side sensor → handle corners (right-hand rule) → escape a maze → represent a grid maze as a list of strings & find the shortest path with BFS → drive the planned path (gps arena); boss: shortest-path race |
| | 12 | `capstone` 🏆 Rescue Mission (capstone) | design, behaviors (+ everything) | plan: write the plan as comments + stub functions → explore & find survivors (gems) without crashing → carry the rescue kit (block) to the base zone → return home → combine into one mission-controller; boss: full rescue under time, no crashes |

## Simulator facts (use these numbers)

* Units: cm, seconds, degrees. y points **up**; heading 0 = east →, 90 = north ↑; positive turns are **left**.
* Robot: circle, radius **8 cm**, wheels 14 cm apart. Power 100 = **30 cm/s**. `forward()` defaults to power 50 (15 cm/s),
  `turn()` defaults to power 40 (a 90° turn takes ~0.9 s).
* Physics runs at 50 Hz (0.02 s). Every robot call costs 2 ms of robot time, so a loop that keeps reading a sensor
  still moves time forward; `robot.wait(0.02)` in a loop is still good practice.
* The program's end = the robot stops. The arena's `time_limit` (default 60 s) ends the run gracefully (not an error);
  `while True:` loops are normal and simply end at the time limit.
* Ultrasonic range 200 cm, measured from the robot's front edge. Floor sensors sit 6.5 cm ahead of the centre,
  at 2.4 cm left / centre / 2.4 cm right. White floor ≈ 92, black tape ≈ 6, with a smooth ~1.6 cm edge
  (so reading ≈ 50 means "half on the edge"). Default tape width 2.5 cm, so on a straight line both side sensors
  read white when centred. Coloured zones: red 46, green 40, blue 30, yellow 76, orange 58, purple 26, gray 64.
* Noise (arena `"noise": 0..1`) gives each wheel a hidden bias (up to ±7 % × noise) plus jitter, noisy sensors and
  gyro drift. Use it in week 4+ to motivate feedback; keep weeks 1–3 noise-free unless a mission is about noise.
* Crashes: touching a wall counts one crash each time contact starts. Pushing a block is not a crash.

## Robot API (global `robot`, no import needed)

Movement: `robot.drive(left, right)` (power -100…100, keeps going), `robot.stop()`, `robot.wait(seconds)`,
`robot.forward(cm, power=50)`, `robot.backward(cm, power=50)`, `robot.turn(degrees, power=40)` (+ = left),
`robot.turn_left(deg=90)`, `robot.turn_right(deg=90)`.

Sensors: `robot.distance(direction="front")` — "front", "left", "right", "front_left", "front_right", "back";
`robot.bumper()` → bool; `robot.floor(which="center")` 0–100 — "left"/"center"/"right", also `floor_left()`,
`floor_right()`; `robot.color()` → "white"/"black"/"red"/…; `robot.light("left"|"right")`, `light_left()`, `light_right()`
0–100; `robot.heading()` compass degrees (-180, 180]; `robot.encoders()` → (left_cm, right_cm);
`robot.reset_encoders()`; `robot.camera()` → list of `{"kind": "block"|"gem", "color", "angle", "distance"}` nearest
first (±30° field of view, 160 cm); `robot.position()` → (x, y) only if the arena has `"gps": True`;
`robot.time()` seconds since start.

Fun: `robot.led(color)`, `robot.say(text)` (speech bubble), `robot.beep(pitch=880, seconds=0.15)`,
`robot.pen_down(color="black")`, `robot.pen_up()`, `robot.plot(name, value)` (his own telemetry line).

Gripper (arena `"gripper": True`): `robot.grab()` → True if a block was right in front (within ~4.5 cm of the
gripper point just ahead of the robot), `robot.release()`, `robot.holding()` → colour or None.

`print()` works and is shown in the console, time-stamped.

### Arm API (global `arm`, in arenas with `"type": "arm"`)

Side view. Table top is y = 0. Base at `arena["base"]` (default (40, 12)). Links default 45 cm and 35 cm.
Shoulder angle 0 = pointing right, 90 = straight up (0…180). Elbow is relative to the upper arm, 0 = straight,
positive bends counter-clockwise (-160…160). Servos move at 120°/s.

`arm.move(shoulder, elbow)` (waits until there), `arm.set(shoulder, elbow)` (doesn't wait), `arm.shoulder(a)`,
`arm.elbow(a)`, `arm.wait(s)`, `arm.angles()`, `arm.hand()` → (x, y) of the gripper tip, `arm.links()`, `arm.base()`,
`arm.is_moving()`, `arm.grab()` (gripper tip within ~4.5 cm horizontally and 3.5 cm vertically of the TOP centre of a
block with nothing on it), `arm.release()` (the block drops onto what's below), `arm.holding()`, `arm.say()`,
`arm.beep()`, `arm.plot()`, `arm.time()`. Blocks are 8 cm cubes; a block's `x` is its centre, `y` its bottom.
Moving the hand or a held block into the table / another block stalls the servo and counts as a crash.

## Arena dict

```python
{
    "name": "Garage",
    "size": [240, 160],               # width, height in cm (border walls added automatically)
    "start": [30, 80, 0],             # x, y, heading
    "time_limit": 30,                 # seconds (max 180)
    "walls": [[x1, y1, x2, y2], ...], # thin wall segments
    "boxes": [[x, y, w, h], ...],     # solid rectangles (x, y = bottom-left corner)
    "lines": [{"pts": [[x, y], ...], "closed": False, "width": 2.5}],   # black tape
    "zones": [{"name": "garage", "rect": [x, y, w, h], "color": "green", "label": "🅿️"}],
    "gems": [[x, y], ...],            # collected when the robot's body touches them
    "blocks": [{"pos": [x, y], "color": "red"}],   # 6 cm pushable / grabbable cubes
    "lights": [[x, y]],               # light bulbs for light sensors
    "finish": [x1, y1, x2, y2],       # lap line; laps count when crossing it with the segment's LEFT side as forward
                                      # (from (x1,y1) looking toward (x2,y2), forward = to the left). Start the robot
                                      # just past the line.
    "noise": 0.0, "gps": False, "gripper": False,
    "grid": {"cell": 40},             # optional: draw faint grid lines (mazes)
    "labels": [[x, y, "text"]],       # optional floor labels
}
```
Arm arena: `{"type": "arm", "name", "size": [160, 100], "base": [40, 12], "links": [45, 35], "start": [90, -90],
"blocks": [{"x": 95, "color": "red"}], "targets": [{"name": "goal", "x": 120, "w": 14, "color": "green"}],
"marks": [[x, y, "A"]], "time_limit": 60}`.

Keep arenas small and readable (≈ 200–320 × 140–220 cm). Keep walls ≥ 20 cm from the start pose. Draw the
path he needs with zones/gems/labels so the goal is obvious from the picture.

## Check snippets

A check is Python code run in a sandbox. It passes if it finishes without raising. Fail with
`expect(cond, "friendly message")`. The FIRST failing message is shown to the kid and the failing
simulation is replayed for him, so write it as a helpful coach: say what you expected and what you saw
(use numbers!), never just "wrong". Optionally set `SUCCESS = "…"` to a celebration line.

Available names:

* `source`, `tree` (ast), `ARENA` (this step's arena dict), `math`
* `sim(arena_dict=None, seed=None, label=None, allow_error=False, **overrides) -> Result` — runs his whole program
  fresh in ARENA (or the dict you pass **positionally**), with keyword overrides replacing top-level arena keys,
  e.g. `sim(start=[40, 60, 0], label="closer wall")`, `sim(noise=0.6, seed=3)`. Crashes (Python errors) fail the
  check kindly unless `allow_error=True`.
* `arena(**overrides)` → a modified copy of ARENA (e.g. to move a wall: `sim(arena(boxes=[[150, 40, 20, 80]]))`).
* `expect(cond, msg)`, `raise CheckFail(msg)`, `uses(concept)`, `calls(name)` (e.g. `calls("distance")`,
  `calls("wait")`), `defines(name)`, `imports(module)`, `loops()` (number of for/while loops), `norm(text)`.

`Result` (drive world): `.x .y .heading .time .crashes .distance .gems .gems_total .line_ratio` (fraction of moving
time the robot centre was within ~5 cm of a tape line) `.laps .lap_times .min_gap` (closest the robot body got to a
wall, cm) `.max_speed .moving_time .last_move_t .blocks` (list of `{"x","y","color","held","zones"}`) `.held
.output .lines .has(text) .said(text=None) .count(event_type)` ("crash", "gem", "beep", "say", "led", "lap", "grip")
`.led_colors() .in_zone(name)` (robot centre at the end) `.visited(name) .zone_time(name) .dist_to(x, y) .stopped
.used(channel)` (e.g. "distance_front", "floor_left", "heading") `.blocks_in(zone, color=None) .min_front_distance()
.series(name)` (telemetry list: "x", "y", "h", "pl", "pr", a sensor channel, or his plot name) `.trail` (pen points)
`.strokes .pen_length .trail_bbox` (w, h) `.closed` (pen ended near where it started) `.corners(min_turn=35)`
`.end_reason` ("done" / "time_limit" / "error") `.error .error_msg`.

`Result` (arm world): `.shoulder .elbow .hand .crashes .blocks` (`{"x","y","color","held","targets","level"}`)
`.held .tower` (height of the tallest stack) `.path .blocks_in(target_name, color=None)` + the text/event helpers.

Rules for good checks:

* Test with **2+ different arenas/starts** whenever the behaviour should depend on sensors, so hard-coded
  `forward(83)` programs don't pass sensor missions. Label them (`label="wall further away"`).
* Be lenient about style, strict about the robotics idea. Use tolerances (± a few cm / degrees).
* Use static checks for the idea when behaviour alone can't prove it (e.g. `expect(calls("distance") >= 1, …)`,
  `expect(uses("control_loop"), …)`, `expect(calls("encoders") or calls("heading"), …)`).
* The starter must FAIL the check and the solution must PASS it (`tools/validate_curriculum.py` proves it).
* Never require things the task didn't ask for.
* Keep each check fast (under ~2 s total); a handful of sims is fine.

## PRACTICE (per week, 5–8 items)

Small standalone warm-up challenges the adaptive guide recommends when a concept is weak. Same step format
plus `concept` and `difficulty` (1 easy, 2 medium, 3 tricky):

```python
{"id": "p_sensors_1", "concept": "sensors", "title": "Wall Radar", "difficulty": 1,
 "task": "HTML", "goals": ["…"], "arena": ARENA, "starter": "…", "hints": ["…", "…", "…"],
 "solution": "…", "check": "…", "xp": 15}
```

## Validate

`python tools/validate_curriculum.py N` runs every solution (must pass) and every starter (must fail)
through the real checker and checks the structure. Keep going until it reports zero problems.
