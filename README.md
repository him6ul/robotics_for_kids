# RoboQuest: a 6-week, project-based robotics course

RoboQuest teaches robotics to a middle schooler (built for an 8th grader). He learns by **programming 12 robots** in a
browser simulator, writing real Python. Each robotics fundamental arrives exactly when a project needs it:

- motors and turning geometry
- sensors and the sense-think-act loop
- thresholds, feedback, and P/PID control
- odometry, gyros, and state machines
- grippers and arm kinematics
- maze navigation and path planning

Everything runs locally: a Python server plus a calm, modern browser UI with a code editor, an animated arena replay,
live telemetry graphs, a keyboard **Drive mode**, and an **Arena Builder**. It tracks progress, time and learning
patterns, and it gives a personalised guide for him and for you, with the usual audit, monitoring and data tools.

## Run it

```bash
./run.sh
```

Then open **http://127.0.0.1:8770**. On first run the script creates `.venv` and installs FastAPI and Uvicorn. All data
is kept in `data/roboquest.db` (SQLite). The Parent Zone (👪, top right) is protected by a PIN you choose the first time.

No robot kit is needed. Each project also has a short "build it for real" note (micro:bit, LEGO SPIKE, Arduino) if
you want to take it off-screen later.

## The 6-week program

Each week has two projects. The concepts listed are the ones that week introduces.

**Week 1: Make it move.** Concepts: actuators, sequences, differential steering, geometry.
- 🤖 **Hello, Robot!**: LEDs and sound, `drive`+`wait`, turns, parking in a garage, a gem hunt, and a slalom boss.
- 🎨 **Robo-Artist**: squares with loops, the 360° rule, circles from wheel speeds, flowers, spirals, and a star boss.

**Week 2: Robots that sense.** Concepts: sensors, the sense-think-act loop, reactive decisions, thresholds, behaviours.
- 🦇 **Bat-Bot**: ultrasonic distance, stopping before walls, soft parking, avoiding walls, and "follow me".
- 🧹 **Robo-Vac**: bumper, bump-and-turn, random turns, cleaning a room, and not falling down the stairs.

**Week 3: Follow the line.** Concepts: calibration, bang-bang vs proportional control, P and PD tuning, telemetry.
- 🛤️ **Line Tracker**: floor sensor, thresholds, zig-zag and two-sensor followers, and stopping at the finish.
- 🏎️ **Race Track Pro**: proportional steering, plotting the error, tuning Kp, derivative damping, and timed laps.

**Week 4: Know where you are.** Concepts: open vs closed loop, encoders, gyro, dead reckoning, state machines.
- 🧭 **Precision Pilot**: seeing motor drift, encoder distance, gyro turns, driving straight, and dead reckoning home.
- 🚚 **Delivery Bot**: states with LED colours, stopping at stations, deliveries, counting stops, and a WAIT state.

**Week 5: Grab & build.** Concepts: servos, joint angles, forward and inverse kinematics, pick-and-place, vision.
- 🦾 **Robot Arm**: servos, forward kinematics with sin/cos, reaching points, pick & place, IK, and a 3-block tower.
- 📦 **Warehouse Bot**: gripper, camera, approach & grab, colour sorting, and multi-block orders.

**Week 6: Smart robots.** Concepts: navigation, grid maps, BFS path planning, behaviour priorities, engineering design.
- 🌀 **Maze Master**: wall following with P control, the right-hand rule, escaping mazes, and BFS shortest paths.
- 🏆 **Rescue Mission (capstone)**: he plans it, explores, rescues, carries the kit, returns home, and combines everything.

Every project follows the same loop:

1. **Five missions.** Each has a short lesson with a real-robot analogy, a concrete task with a goal checklist, and 3
   hints of increasing detail. His code carries forward from mission to mission, so each project grows *one* program.
2. **▶ Run.** The whole run is simulated, then replayed. He can play, pause, scrub and change speed, and see:
   - sensor beams, pen trails, crash flashes and speech bubbles
   - a console where prints appear at the robot time they happened
   - a **Telemetry** tab graphing every sensor he read, plus his own `robot.plot()` values (great for PID tuning)
3. **✓ Test my robot.** Automated tests run his program in 2–5 different arenas or starting positions, so hard-coded
   moves don't pass. If a test fails, he gets a coaching message with numbers and can **watch the exact test run**
   that failed.
4. **Boss challenge**: the harder final test for each robot, worth big XP. It's required: the next robot unlocks only after the boss is beaten.
5. **Remix lab**: he writes an idea into the idea-o-meter, builds his own twist (in any arena, including ones he
   designed), and earns XP scaled by how much more complex it is than the original.
6. **Reflection**: he rates how fun and how hard it was, which feeds the guide.

Around the projects:
- **Side quests** (~40): small single-concept challenges the guide recommends when a skill is weak.
- **Playground**: free coding in any unlocked arena.
- **Drive mode**: keyboard teleop with live sensor readouts, so he can *feel* differential drive before programming it.
- **Arena Builder**: he draws walls, tape, zones, gems, blocks and lights, sets noise, GPS or a gripper, and then
  drives or programs in his own designs.
- **Robot Manual**: every command, unlocked week by week. The editor also autocompletes `robot.` and `arm.`.

## The simulator

`app/sandbox/robosim.py` is a small, deterministic 2-D simulator (standard library only).

**Wheeled robot**
- Radius 8 cm, wheels 14 cm apart, top speed 30 cm/s, physics at 50 Hz.
- Sensors:
  - ultrasonic distance in 5 directions (200 cm)
  - bumper
  - 3 floor reflectance sensors with a soft tape edge (so P-control works)
  - colour sensor and two light sensors
  - compass and gyro with drift
  - wheel encoders
  - a Pixy-style camera
  - optional GPS
- Actuators and extras: pen, LED, beeper, speech bubble, and a gripper for pushable/grabbable blocks.
- Optional **noise**: hidden per-wheel bias, jitter, sensor noise and gyro drift. Week 4 uses it to show why real
  robots need feedback.

**Arm**
- A 2-link arm (shoulder and elbow servos at 120°/s) in side view.
- Blocks that stack, and target zones on the table.

**Timing and safety**
- Every robot call costs 2 ms of robot time, so `while` loops that read sensors still move time forward.
- Programs run in a separate process with a wall-clock timeout, so a frozen loop is caught and explained.
- `print()` floods are capped.

## What gets tracked & analysed

- **Time on each project and step.** Counts active time only (the tab is visible and he did something in the last
  90 s), groups it into sessions, and compares it with each project's expected time.
- **Progress & pace.** Missions done vs. the 6-week plan, measured from the start date: ahead / on track / behind,
  with a projected finish date.
- **Concept mastery** (16 robotics concepts). Built from:
  - missions completed, and the quality of each pass (attempts, hints, time)
  - side quests
  - *independent use* found by static analysis of his Playground and remix code (e.g. a PID loop he wrote himself)
- **Learning style.** Seven traits:
  - Precision (first-try passes)
  - Independence (hints)
  - Persistence (recovering after a failed test)
  - Experimenting (runs per test)
  - Creativity (remixes, ideas, arenas)
  - **Tuning** (changing just numbers between runs, like a real engineer tuning Kp)
  - **Safety** (runs without crashes)

  These map to a persona: Tuner, Tinkerer, Planner, Inventor, Determined Climber, or All-Rounder.
- **How he experiments.** Every run's code is diffed against the previous version and classed as a tune (numbers
  only), a small edit, or a rewrite. Shows his most-tuned missions.
- **Robot behaviour.**
  - distance driven, robot time, gems
  - crash rate per week (is he getting safer?)
  - which sensors he reads, and when he first used each
  - Drive-mode time
  - arena designs and their design complexity
- **Idea complexity.** Each idea gets a 0–100 score from its features, concept breadth, sensing and advanced
  robotics (Spark → Mastermind). Remix complexity is measured against the original project.
- **Code growth.** A snapshot on every run and test: lines, complexity, concepts. You can scrub through every version
  next to the reference solution and **replay any old version in the simulator**.
- **How he investigates.** Replay scrubbing, opening telemetry, and opening the manual are logged as audit events.
- **Errors.** Python errors become a *Bug Bestiary* (e.g. the Wiring Gremlin 🔌 for robot misuse, the Math Mirage 🌵
  for unreachable arm targets), with friendly, specific explanations.
- **Enjoyment.** Fun and difficulty ratings per project. Low fun triggers coaching suggestions.

The **adaptive guide** turns all of this into next steps:
- **For him:**
  - continue
  - a side quest for a weak skill
  - the boss when he's cruising
  - a remix
  - focus mode when behind
  - a tip for a recurring bug
  - "slow down near walls" when many runs crash
  - try Drive mode
  - idea boosters
- **For you:** coaching notes, for example:
  - a concept needs reinforcement
  - heavy hint use
  - lots of crashes, or "getting safer" 👍
  - tuning by pure trial and error
  - a project he didn't enjoy
  - ideas running ahead of his skills
  - inactivity

  It also gives conversation starters.

## Auditing, monitoring & data (Parent Zone)

- **Audit log.** Append-only and **hash-chained**: each row stores SHA-256(previous hash + row), and **Verify
  integrity** proves nothing was edited or deleted. It covers every meaningful action:
  - runs, tests, hints, answer peeks
  - ideas, remixes, reflections, arenas, drive sessions, UI investigation events
  - sessions
  - parent logins (including failed attempts and lockouts), report views, exports, backups, deletions, retention
  - server start/stop

  Each row has the actor, timestamp, IP and browser. The log is filterable and exportable, and each learner has an
  **Activity timeline**.
- **Monitoring.**
  - uptime and health (`/api/health`)
  - request volume and per-endpoint latency (avg / p95 / max)
  - simulator latency, robot-seconds simulated, frames and payload size
  - test latency and pass rate
  - Drive-mode tick latency
  - frozen loops and print floods stopped
  - server exceptions with stack traces
  - DB size, memory and disk
  - AI tutor latency, tokens and errors

  Metrics are rolled up per minute into SQLite for history charts.
- **Data.**
  - a catalog of every table (what it holds, row counts, first and last timestamps)
  - a table browser, CSV/JSON export, and a full `.db` backup
  - a data-collected-per-day chart
  - data-quality checks (orphans, negative durations, audit id gaps)
  - a retention pruner for bulky telemetry
  - per-learner deletion, itself audited with row counts

## 🔧 Sprocket, the AI tutor (optional)

Sprocket is a Socratic "robot mechanic" tutor built on the Claude API (`claude-opus-5-5`).

**What it sees.** The lesson, his code, the last run's summary (position, crashes, sensors used, errors, simulator
notes), and the last failed test.

**What it does.** Gives clues, never full solutions. It reviews code with line-pinned tips, and it flags anything a
parent should know about.

**Guardrails.** The same as PyQuest: it stays on topic, never asks for personal information, and ignores "give me
the answer" tricks in code.

**Cost and privacy.**
- It is **off by default**.
- A daily question limit is set in Parent Zone → AI tutor.
- When it's on, his questions, code and run summaries go to Anthropic's API. His name is not sent.

Setup: start the app with a key, then turn Sprocket on in Parent Zone → AI tutor.

```bash
ANTHROPIC_API_KEY=sk-ant-... ./run.sh
```

To try the UI with canned replies (no key, no cost), use demo mode:

```bash
ROBOQUEST_TUTOR_FAKE=1 ./run.sh
```

## How it works

```
app/
  main.py            FastAPI: REST API, simulation runs & tests, drive-mode WebSocket, parent/admin endpoints, metrics middleware
  db.py              SQLite schema & helpers
  analytics.py       mastery, learning style, experiment patterns, robot stats, activity, errors, ideas, adaptive guide
  analysis.py        friendly errors, Bug Bestiary, idea scoring, arena design score
  gamification.py    XP, levels (Spare Part → Chief Roboticist), streaks, badges
  observability.py   hash-chained audit log, metrics, error capture, monitoring & data catalog
  tutor.py           Sprocket, the AI tutor (Claude API)
  curriculum/        week1.py … week6.py + CONTENT_SPEC.md (format, robot API, arena & test API)
  sandbox/
    robosim.py       the simulator (drive world + arm world) and the Robot / Arm APIs
    robolive.py      runs one program → frames/events/prints JSON for the replay
    robocheck.py     test harness: sim() in several arenas, Result helpers, friendly failures
    kidast.py        static analysis: robotics concept detection & complexity
static/  index.html, css/style.css, js/ (app, core, kid, workspace, arena, telemetry, drive, builder, manual, tutor, parent)
tools/validate_curriculum.py   proves every solution passes and every starter fails
```

This is a family-computer tool, not a hardened multi-user sandbox, so the server only listens on `127.0.0.1`.

### Editing the curriculum

Missions live in `app/curriculum/weekN.py`; the format is in `CONTENT_SPEC.md`. After editing, run:

```bash
.venv/bin/python tools/validate_curriculum.py
```

It checks every mission and side quest:
- the reference solution passes
- the starter fails
- the solution runs in the arena
- the remix arena works
- ids are unique
- only allowed HTML is used
