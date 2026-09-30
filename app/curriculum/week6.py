"""Week 6 — Smart robots: wall following, maze solving with BFS, and a capstone rescue mission."""

# ---------------------------------------------------------------------------
# maze helpers: a maze is a list of strings, "#" = wall cell, "." = open cell.
# Row 0 is the TOP row. Every cell is 40 x 40 cm; the arena border is the outer wall.
# ---------------------------------------------------------------------------
CELL = 40


def maze_boxes(rows):
    """Merge the '#' cells into as few rectangles as possible (fewer walls = faster sensors)."""
    R, C = len(rows), len(rows[0])
    used = [[False] * C for _ in range(R)]
    boxes = []
    for r in range(R):
        for c in range(C):
            if rows[r][c] != "#" or used[r][c]:
                continue
            c2 = c
            while c2 + 1 < C and rows[r][c2 + 1] == "#" and not used[r][c2 + 1]:
                c2 += 1
            r2 = r
            while r2 + 1 < R and all(rows[r2 + 1][k] == "#" and not used[r2 + 1][k] for k in range(c, c2 + 1)):
                r2 += 1
            for rr in range(r, r2 + 1):
                for k in range(c, c2 + 1):
                    used[rr][k] = True
            boxes.append([c * CELL, (R - r2 - 1) * CELL, (c2 - c + 1) * CELL, (r2 - r + 1) * CELL])
    return boxes


def cell_xy(rows, cell):
    r, c = cell
    return [c * CELL + CELL // 2, (len(rows) - r) * CELL - CELL // 2]


def maze_arena(name, rows, start, heading, goal, time_limit, **extra):
    gx, gy = cell_xy(rows, goal)
    sx, sy = cell_xy(rows, start)
    a = {"name": name, "size": [len(rows[0]) * CELL, len(rows) * CELL], "start": [sx, sy, heading],
         "time_limit": time_limit, "boxes": maze_boxes(rows), "grid": {"cell": CELL},
         "zones": [{"name": "exit", "rect": [gx - 18, gy - 18, 36, 36], "color": "green", "label": "EXIT"}]}
    a.update(extra)
    return a


# the mazes (row 0 = top)
SNAKE = ["####...",
         "######.",
         "##...#.",
         "##.#.#.",
         "...#..."]
SNAKE_FLIP = SNAKE[::-1]

MAZE_A = ["...#...",
          ".#.#.#.",
          ".#...#.",
          ".###.##",
          "...#..."]

MAZE_B = ["..#....",
          ".##.##.",
          "....#..",
          ".##.#.#",
          "...#..."]

RACE = ["........",
        ".##.##.#",
        ".#...#..",
        ".#.#.##.",
        "...#...."]

BIG = [".........",
       ".###.##.#",
       ".#...#...",
       ".#.#.#.#.",
       "...#...#.",
       ".#.###..."]

# ---------------------------------------------------------------------------
# arenas
# ---------------------------------------------------------------------------
HALL_UP = {"name": "Sloping Hallway", "size": [320, 140], "start": [30, 46, 0], "time_limit": 25,
           "walls": [[0, 20, 320, 50]], "labels": [[160, 12, "the wall slopes — keep 15 cm!"]]}
HALL_DOWN = {"name": "Sloping Hallway 2", "size": [320, 140], "start": [30, 70, 0], "time_limit": 25,
             "walls": [[0, 50, 320, 20]]}

SNAKE_ARENA = maze_arena("Snake Corridor", SNAKE, (4, 0), 0, (0, 4), 60)
SNAKE_FLIP_ARENA = maze_arena("Flipped Snake", SNAKE_FLIP, (0, 0), 0, (4, 4), 60)

MAZE_A_ARENA = maze_arena("The Labyrinth", MAZE_A, (4, 0), 0, (0, 6), 90, noise=0.3)
MAZE_B_ARENA = maze_arena("The Other Labyrinth", MAZE_B, (4, 6), 90, (0, 0), 90, noise=0.3)

PLAN_ARENA = maze_arena("The Labyrinth (map)", MAZE_A, (4, 0), 0, (0, 6), 10,
                        labels=[[20, 20, "S"], [260, 180, "G"]])
GPS_ARENA = maze_arena("The Labyrinth + GPS", MAZE_A, (4, 0), 0, (0, 6), 60, gps=True, noise=0.2)
RACE_ARENA = maze_arena("Race Maze", RACE, (4, 7), 180, (2, 3), 11, gps=True, noise=0.2)
BIG_ARENA = maze_arena("Mega Maze", BIG, (5, 0), 0, (0, 8), 180, gps=True, noise=0.2)

# ---------------------------------------------------------------------------
# helpers used inside checks
# ---------------------------------------------------------------------------
# Runs ONLY the learner's function definitions (plus imports and simple constants that don't touch
# the robot) so a check can call a pure function like shortest_path() on mazes it has never seen.
# A 1-second alarm protects against searches that never end.
KID_FUNCS = '''
import ast as _ast, io as _io, contextlib as _cl, signal as _sig

class _TooSlow(BaseException):
    pass

def _alarm(*_a):
    raise _TooSlow()

def _mentions_robot(node):
    return any(isinstance(n, _ast.Name) and n.id == "robot" for n in _ast.walk(node))

def kid_functions():
    ns = {"__name__": "kid_functions"}
    _sig.signal(_sig.SIGALRM, _alarm)
    for node in tree.body:
        keep = isinstance(node, (_ast.FunctionDef, _ast.Import, _ast.ImportFrom)) or (
            isinstance(node, (_ast.Assign, _ast.AnnAssign)) and not _mentions_robot(node)
            and not any(isinstance(n, _ast.Call) for n in _ast.walk(node)))
        if not keep:
            continue
        _sig.setitimer(_sig.ITIMER_REAL, 1.0)
        try:
            with _cl.redirect_stdout(_io.StringIO()):
                exec(compile(_ast.Module(body=[node], type_ignores=[]), "main.py", "exec"), ns)
        except (Exception, _TooSlow):
            pass
        finally:
            _sig.setitimer(_sig.ITIMER_REAL, 0)
    return ns

def call_kid(fn, *args):
    _sig.signal(_sig.SIGALRM, _alarm)
    _sig.setitimer(_sig.ITIMER_REAL, 1.0)
    try:
        with _cl.redirect_stdout(_io.StringIO()):
            return fn(*args)
    except _TooSlow:
        raise CheckFail(f"Your {fn.__name__}() is still searching after a whole second — it may be going round in "
                        "circles. Make sure every cell is only added to the queue ONCE (mark it as visited / put it in came_from).")
    except Exception as e:
        raise CheckFail(f"Your {fn.__name__}() crashed on one of my test mazes with {type(e).__name__}: {e}")
    finally:
        _sig.setitimer(_sig.ITIMER_REAL, 0)

def bfs_steps(maze, start, goal):
    """The checker's own BFS: number of steps on the shortest path (None if there is no path)."""
    dist = {start: 0}
    queue = [start]
    while queue:
        r, c = queue.pop(0)
        if (r, c) == goal:
            return dist[(r, c)]
        for n in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= n[0] < len(maze) and 0 <= n[1] < len(maze[0]) and maze[n[0]][n[1]] != "#" and n not in dist:
                dist[n] = dist[(r, c)] + 1
                queue.append(n)
    return None
'''


def _consts(**kw):
    """Put Python values into a check snippet as code."""
    return "".join(f"{k} = {v!r}\n" for k, v in kw.items())


# ---------------------------------------------------------------------------
# Project 11 — Maze Master
# ---------------------------------------------------------------------------
MAZE_S1 = '''# 🧱 Hug the wall: keep your right side 15 cm from the wall
while robot.distance("front") > 20:
    right = robot.distance("right")
    # TODO: work out the error and steer with it (P control)
    robot.drive(50, 50)
    robot.wait(0.02)
robot.stop()
'''

MAZE_S1_SOL = '''# 🧱 Hug the wall: keep your right side 15 cm from the wall
TARGET = 15      # cm from the wall
KP = 2           # how hard to steer for every cm of error

while robot.distance("front") > 20:
    right = robot.distance("right")
    error = TARGET - right          # + means too close, - means too far
    robot.drive(50 - KP * error, 50 + KP * error)
    robot.plot("right", right)
    robot.wait(0.02)
robot.stop()
'''

MAZE_TOOLS = '''TARGET = 12      # the middle of a 40 cm corridor is 12 cm from the wall
KP = 2           # how hard to steer for every cm of error
LIMIT = 5        # never steer harder than this

def turn_on_grid(degrees):
    # turn, then snap to the nearest grid direction (0, 90, 180 or -90) with the compass
    goal = round((robot.heading() + degrees) / 90) * 90
    robot.turn((goal - robot.heading() + 180) % 360 - 180)

def drive_one_cell():
    turn_on_grid(0)                  # line up with the grid first
    robot.reset_encoders()
    while sum(robot.encoders()) / 2 < 40:
        if robot.distance("front") < 12:
            break
        right = robot.distance("right")
        steer = 0
        if right < 20:               # only steer when there IS a wall next to us
            error = TARGET - right
            steer = max(-LIMIT, min(LIMIT, KP * error))
        robot.drive(60 - steer, 60 + steer)
        robot.wait(0.02)
    robot.stop()
'''

MAZE_S2 = MAZE_S1_SOL + '''
# TODO: corners! Think in 40 cm cells and use the right-hand rule:
#   gap on the right -> turn right,  wall in front -> turn left,  otherwise go straight
'''

MAZE_S2_SOL = MAZE_TOOLS + '''
# 🖐️ the right-hand rule, one cell at a time
while robot.color() != "green":
    if robot.distance("right") > 30:       # gap on the right -> turn right
        turn_on_grid(-90)
        drive_one_cell()
    elif robot.distance("front") > 30:     # the way ahead is open -> go
        drive_one_cell()
    else:                                  # wall in front -> turn left
        turn_on_grid(90)
robot.say("Made it!")
'''

MAZE_S3 = MAZE_S2_SOL + '''
# TODO: count the cells you drive and print the total when you escape
'''

MAZE_S3_SOL = MAZE_TOOLS + '''
# 🖐️ the right-hand rule, one cell at a time
cells = 0
while robot.color() != "green":
    if robot.distance("right") > 30:       # gap on the right -> turn right
        turn_on_grid(-90)
        drive_one_cell()
        cells = cells + 1
    elif robot.distance("front") > 30:     # the way ahead is open -> go
        drive_one_cell()
        cells = cells + 1
    else:                                  # wall in front -> turn left
        turn_on_grid(90)
print("Escaped in", cells, "cells")
robot.say("Escaped!")
'''

MAZE_MAP = '''# 🗺️ The map of the Labyrinth: "#" = wall cell, "." = open cell. Row 0 is the TOP row.
MAZE = ["...#...",
        ".#.#.#.",
        ".#...#.",
        ".###.##",
        "...#..."]
START = (4, 0)     # (row, column): bottom-left
GOAL = (0, 6)      # top-right
'''

BFS_FUNC = '''
def shortest_path(maze, start, goal):
    queue = [start]                  # cells waiting to be explored (first in, first out)
    came_from = {start: None}        # every cell we've seen -> the cell we came from
    while queue:
        cell = queue.pop(0)
        if cell == goal:
            break
        r, c = cell
        for nr, nc in [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]:    # up, down, left, right
            if 0 <= nr < len(maze) and 0 <= nc < len(maze[0]):
                if maze[nr][nc] != "#" and (nr, nc) not in came_from:
                    came_from[(nr, nc)] = cell
                    queue.append((nr, nc))
    if goal not in came_from:
        return []                    # no way through!
    # follow the notes back from the goal to the start
    path = []
    cell = goal
    while cell is not None:
        path.append(cell)
        cell = came_from[cell]
    path.reverse()
    return path
'''

MAZE_S4 = MAZE_MAP + '''
def shortest_path(maze, start, goal):
    # TODO: breadth-first search! Use a queue and a came_from dictionary.
    return []

path = shortest_path(MAZE, START, GOAL)
print("Path:", path)
print(len(path) - 1, "steps")
'''

MAZE_S4_SOL = MAZE_MAP + BFS_FUNC + '''
path = shortest_path(MAZE, START, GOAL)
print("Path:", path)
print(len(path) - 1, "steps")
'''

GPS_TOOLS = '''
def cell_center(cell):
    # (row, col) -> (x, y) in cm. Row 0 is at the TOP of the arena.
    r, c = cell
    return c * 40 + 20, len(MAZE) * 40 - (r * 40 + 20)

def cell_of(x, y):
    # (x, y) in cm -> (row, col)
    return int((len(MAZE) * 40 - y) // 40), int(x // 40)

def go_to(tx, ty):
    # drive to the point (tx, ty) with GPS + compass feedback
    while True:
        x, y = robot.position()
        if math.hypot(tx - x, ty - y) < 3:
            break
        target = math.degrees(math.atan2(ty - y, tx - x))
        error = (target - robot.heading() + 180) % 360 - 180
        if abs(error) > 20:
            robot.turn(error, TURN_POWER)    # facing the wrong way: turn on the spot first
        else:
            robot.drive(POWER - 2 * error, POWER + 2 * error)
        robot.wait(0.02)
    robot.stop()
'''

MAZE_S5 = MAZE_S4_SOL + '''
# TODO: find your START cell from robot.position(), then drive the path cell by cell
'''

MAZE_S5_SOL = "import math\n" + MAZE_MAP.replace("START = (4, 0)     # (row, column): bottom-left\n", "") + BFS_FUNC \
    + "\nPOWER = 50\nTURN_POWER = 40\n" + GPS_TOOLS + '''
start = cell_of(*robot.position())       # where am I? ask the GPS
path = shortest_path(MAZE, start, GOAL)
print("Plan:", len(path) - 1, "steps from", start)
for cell in path[1:]:
    go_to(*cell_center(cell))
robot.say("Treasure room reached!")
'''

RACE_MAP = '''# 🏁 The Race Maze (row 0 is the TOP row). The treasure is in the middle.
MAZE = ["........",
        ".##.##.#",
        ".#...#..",
        ".#.#.##.",
        "...#...."]
GOAL = (2, 3)
'''

MAZE_BOSS = "import math\n" + RACE_MAP + BFS_FUNC + "\nPOWER = 50\nTURN_POWER = 40\n" + GPS_TOOLS + '''
start = cell_of(*robot.position())
path = shortest_path(MAZE, start, GOAL)
# 👾 BOSS: this is too slow! Go faster, and only stop at the corners of the path.
for cell in path[1:]:
    go_to(*cell_center(cell))
'''

MAZE_BOSS_SOL = "import math\n" + RACE_MAP + BFS_FUNC + "\nPOWER = 90\nTURN_POWER = 80\n" + GPS_TOOLS + '''
def corners(path):
    # keep only the cells where the path changes direction (and the last one)
    keep = []
    for i in range(1, len(path)):
        if i == len(path) - 1:
            keep.append(path[i])
        else:
            before = (path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1])
            after = (path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1])
            if before != after:
                keep.append(path[i])
    return keep

start = cell_of(*robot.position())
path = shortest_path(MAZE, start, GOAL)
for cell in corners(path):
    go_to(*cell_center(cell))
robot.say("Fastest in the maze!")
'''

BFS_TESTS = [
    ([".....", ".#.#.", ".....", ".#.#.", "....."], (4, 0), (0, 4), "lots of loops"),
    (["..#...", "#.#.#.", "..#.#.", ".##.#.", "....#."], (0, 0), (0, 5), "winding"),
    (["........", "######.#", "........", ".#######", "........"], (0, 0), (4, 7), "the long way round"),
    (["......", ".####.", ".#..#.", ".#.##.", "......"], (2, 2), (4, 5), "two routes"),
]

MAZE_S1_CHECK = _consts(HALL2=HALL_DOWN) + r'''
expect(calls("distance") >= 1, "Read the side sensor with robot.distance(\"right\").")
for lab, arn in (("wall sloping up", ARENA), ("wall sloping down", HALL2)):
    r = sim(arn, label=lab)
    expect(r.used("distance_right"), "Your robot never looked right! Use right = robot.distance(\"right\") inside the loop.")
    expect(r.crashes == 0, f"({lab}) The robot bumped the wall {r.crashes} time(s). Check the sign: when it's too close (error > 0) it must steer LEFT, so the RIGHT wheel goes faster.")
    expect(r.x > 250, f"({lab}) The robot stopped at x = {r.x:.0f}. Keep following the wall to the end of the hallway.")
    d = [v for v, t in zip(r.series("distance_right"), r.series("t")) if v is not None and t > 3]
    expect(len(d) > 20, f"({lab}) The robot didn't drive along the wall for long enough.")
    avg = sum(d) / len(d)
    worst = max(abs(v - 15) for v in d)
    expect(abs(avg - 15) <= 2.5, f"({lab}) On average your robot stayed {avg:.1f} cm from the wall — the target is 15 cm. Is error = 15 - right, and does the error change the motor powers?")
    expect(worst <= 6, f"({lab}) Your robot wobbled up to {worst:.1f} cm away from the 15 cm line. Try a different KP (like 1, 2 or 3).")
SUCCESS = f"Wall-hugger! Average {avg:.1f} cm from the wall. That's P control keeping you on track 🧱"
'''

MAZE_S2_CHECK = _consts(FLIP=SNAKE_FLIP_ARENA) + r'''
expect(calls("distance") >= 2, "Use the distance sensors (front AND right) to decide what to do at each cell.")
for lab, arn in (("snake corridor", ARENA), ("flipped snake", FLIP)):
    r = sim(arn, label=lab)
    bumps = [e for e in r.events if e["type"] == "crash"]
    if bumps:
        raise CheckFail(f"({lab}) Bump! The robot touched a wall {len(bumps)} time(s), first near ({bumps[0]['x']:.0f}, {bumps[0]['y']:.0f}). Snap to the grid before each cell, and limit your steering.")
    expect(r.visited("exit"), f"({lab}) The robot didn't reach the green EXIT — it ended at ({r.x:.0f}, {r.y:.0f}) after {r.time:.0f} s. Watch the replay: which corner confused it? Right gap → turn right, wall ahead → turn left.")
SUCCESS = "Left turns, right turns, no problem — you've got the right-hand rule! 🖐️"
'''

MAZE_S3_CHECK = _consts(OTHER=MAZE_B_ARENA) + r'''
import re as _re
for lab, arn in (("the Labyrinth", ARENA), ("the other labyrinth", OTHER)):
    r = sim(arn, label=lab)
    bumps = [e for e in r.events if e["type"] == "crash"]
    if bumps:
        raise CheckFail(f"({lab}) Bump near ({bumps[0]['x']:.0f}, {bumps[0]['y']:.0f})! This maze has noisy motors, so your P steering (and snapping to the grid) really matters.")
    expect(r.visited("exit"), f"({lab}) Still lost after {r.time:.0f} s — the robot ended at ({r.x:.0f}, {r.y:.0f}). Keep one hand on the wall and you WILL find the exit.")
    cells = round(r.distance / 40)
    nums = [int(n) for n in _re.findall(r"\d+", r.output)]
    expect(nums, f"({lab}) You escaped! Now count: print(\"Escaped in\", cells, \"cells\") at the end.")
    expect(any(abs(n - cells) <= 1 for n in nums), f"({lab}) You printed {nums[-1]}, but the robot drove about {cells} cells ({r.distance:.0f} cm ÷ 40). Add 1 to your counter every time you drive a cell.")
SUCCESS = f"Escaped both labyrinths! The last one took {cells} cells… but was that the SHORTEST way? 🤔"
'''

MAZE_S4_CHECK = KID_FUNCS + _consts(TESTS=BFS_TESTS, MAZE_A=MAZE_A) + r'''
expect(defines("shortest_path"), "Make a function: def shortest_path(maze, start, goal):")
sp = kid_functions().get("shortest_path")
expect(callable(sp), "I couldn't find a working shortest_path function. Define it at the top level of your program (not inside a loop).")
for maze, start, goal, lab in TESTS:
    want = bfs_steps(maze, start, goal)
    p = call_kid(sp, maze, start, goal)
    expect(isinstance(p, (list, tuple)) and len(p) > 0, f"On my test maze '{lab}' your shortest_path() returned {p!r}. It should return the list of cells from start to goal, like [(4, 0), (3, 0), ...].")
    try:
        p = [(int(c[0]), int(c[1])) for c in p]
    except Exception:
        raise CheckFail(f"({lab}) Each cell in the path should be a (row, col) pair, but I got {p[:3]!r}…")
    expect(p[0] == start, f"({lab}) The path should begin at the start cell {start}, but it begins at {p[0]}.")
    expect(p[-1] == goal, f"({lab}) The path should end at the goal {goal}, but it ends at {p[-1]}.")
    for a, b in zip(p, p[1:]):
        expect(abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1, f"({lab}) Your path jumps from {a} to {b} — every step must go to a neighbour (up, down, left or right).")
        expect(0 <= b[0] < len(maze) and 0 <= b[1] < len(maze[0]) and maze[b[0]][b[1]] != "#", f"({lab}) Your path walks through {b}, which is a wall or outside the maze! Use the maze you're GIVEN (the maze parameter) and skip '#' cells.")
    expect(len(p) - 1 == want, f"({lab}) Your path takes {len(p) - 1} steps, but the shortest way is {want}. BFS explores in waves: take the OLDEST cell from the queue with queue.pop(0).")
r = sim()
steps = bfs_steps(MAZE_A, (4, 0), (0, 6))
expect(r.has(str(steps)), f"Your BFS works on all my secret mazes! 🎉 Last thing: print the number of steps for the Labyrinth, print(len(path) - 1, \"steps\") — it should say {steps}.")
SUCCESS = f"BFS found the {steps}-step path. Your wall-follower needed 26 cells for the same trip! 🗺️"
'''

MAZE_S5_CHECK = KID_FUNCS + _consts(MAZE_A=MAZE_A) + r'''
expect(calls("position") >= 1, "Use the GPS: x, y = robot.position() tells you where you are.")
expect(calls("shortest_path") >= 1, "Plan first! Call shortest_path(...) to get the list of cells to drive.")
for start, lab in (((4, 0), "start bottom-left"), ((0, 0), "start top-left"), ((2, 4), "start in the middle")):
    sx, sy = start[1] * 40 + 20, 200 - (start[0] * 40 + 20)
    steps = bfs_steps(MAZE_A, start, (0, 6))
    r = sim(start=[sx, sy, 0], label=lab)
    bumps = [e for e in r.events if e["type"] == "crash"]
    if bumps:
        raise CheckFail(f"({lab}) Bump near ({bumps[0]['x']:.0f}, {bumps[0]['y']:.0f})! Drive to the CENTRE of each cell on the path.")
    expect(r.visited("exit"), f"({lab}) The robot never reached the EXIT — it ended at ({r.x:.0f}, {r.y:.0f}). Did you work out the start cell from robot.position() (not a fixed START)?")
    expect(r.distance <= steps * 40 + 30, f"({lab}) You drove {r.distance:.0f} cm, but the shortest path is only {steps} cells = {steps * 40} cm. Follow the planned path cell by cell.")
SUCCESS = "Plan → drive → arrive. That's exactly how warehouse robots and self-driving cars navigate! 🤖🗺️"
'''

MAZE_BOSS_CHECK = r'''
for st, lab in (([300, 20, 180], "start bottom-right"), ([300, 180, -90], "start top-right")):
    r = sim(start=st, label=lab)
    bumps = [e for e in r.events if e["type"] == "crash"]
    if bumps:
        raise CheckFail(f"({lab}) Bump near ({bumps[0]['x']:.0f}, {bumps[0]['y']:.0f})! Fast is good, crashing is not — the corridors are only 40 cm wide.")
    expect(r.visited("exit"), f"({lab}) ⏱ 11 seconds are up and the robot is at ({r.x:.0f}, {r.y:.0f}), not in the treasure room. Go faster: more POWER, faster turns, and only stop at the corners of the path.")
SUCCESS = "🏆 MAZE MASTER! Planned, raced and never touched a wall."
'''

MAZE_MASTER = {
    "id": "maze_master", "week": 6, "order": 11, "title": "Maze Master", "emoji": "🌀",
    "tagline": "Follow walls, escape labyrinths, then plan the shortest path with BFS",
    "story": "A robot is trapped in an underground labyrinth. First it has to feel its way out with one "
             "'hand' on the wall. Then you'll give it something much smarter: a map and a planning brain "
             "that finds the shortest way to the treasure before it even moves.",
    "concepts": ["navigation", "mapping", "feedback"],
    "expected_minutes": 150,
    "real_world": "Micromouse robots race through mazes exactly like this: explore first, then run the shortest path "
                  "at top speed. Warehouse robots and game characters plan routes on grid maps with BFS and its cousin A*.",
    "build_it": "With a LEGO SPIKE or an Arduino car and a side-facing ultrasonic sensor you can wall-follow a cardboard "
                "maze on the floor — make the corridors a bit wider than the robot.",
    "steps": [
        {
            "id": "s1", "title": "Hug the wall",
            "learn": "<p>Imagine walking through a dark hallway with your right hand touching the wall. If the wall "
                     "gets too close you step left; if it slips away you step right. That's <b>wall following</b>, "
                     "and it's a <b>feedback loop</b>: measure, compare with what you want, correct.</p>"
                     "<p>Your robot has a <b>side distance sensor</b>: <code>robot.distance(\"right\")</code>. The "
                     "<b>error</b> is how far you are from where you want to be:</p>"
                     "<pre>error = 15 - right        # + = too close, - = too far\n"
                     "robot.drive(50 - KP * error, 50 + KP * error)</pre>"
                     "<p>Too close (error positive) → the right wheel speeds up → the robot steers left, away from "
                     "the wall. The bigger the error, the harder it steers. That's <b>P control</b> (P for "
                     "<i>proportional</i>) — the same idea you used on the race track, now with a sonar instead of a floor sensor.</p>",
            "task": "<p>The hallway wall is <b>slanted</b>, so driving straight won't work. Keep the robot's right side "
                    "<b>15 cm</b> from the wall all the way to the end, using P control.</p>",
            "goals": ["Use robot.distance(\"right\")", "Stay about 15 cm from the wall", "No bumps"],
            "arena": HALL_UP, "starter": MAZE_S1, "solution": MAZE_S1_SOL,
            "hints": ["Inside the loop, work out error = 15 - right.",
                      "Change the wheel powers by KP × error: one wheel gets more, the other less. Start with KP = 2.",
                      "error = 15 - right\nrobot.drive(50 - 2 * error, 50 + 2 * error)"],
            "check": MAZE_S1_CHECK, "concepts": ["feedback", "navigation", "sensors"], "xp": 25,
        },
        {
            "id": "s2", "title": "Corners and the right-hand rule",
            "learn": "<p>Corners break a simple wall-follower. Maze robots (like <b>micromouse</b> racers) solve this by "
                     "thinking in <b>cells</b>: this maze is a grid of 40 cm squares. At the centre of every cell the robot "
                     "looks around and follows the <b>right-hand rule</b>:</p>"
                     "<ol><li>Gap on the right? → turn right and drive one cell.</li>"
                     "<li>Else, open ahead? → drive one cell.</li>"
                     "<li>Else (wall in front) → turn left and look again.</li></ol>"
                     "<p>Two tools make it reliable. <code>turn_on_grid()</code> uses the compass to snap to an exact "
                     "grid direction, so small errors never add up. <code>drive_one_cell()</code> drives 40 cm with the "
                     "encoders while your P controller keeps it in the middle (12 cm from the wall in a 40 cm corridor):</p>"
                     "<pre>def turn_on_grid(degrees):\n    goal = round((robot.heading() + degrees) / 90) * 90\n"
                     "    robot.turn((goal - robot.heading() + 180) % 360 - 180)\n\n"
                     "def drive_one_cell():\n    turn_on_grid(0)\n    robot.reset_encoders()\n"
                     "    while sum(robot.encoders()) / 2 &lt; 40:\n        right = robot.distance(\"right\")\n"
                     "        steer = 0\n        if right &lt; 20:                     # only if there IS a wall\n"
                     "            steer = max(-5, min(5, KP * (12 - right)))   # limit the steering\n"
                     "        robot.drive(60 - steer, 60 + steer)\n        robot.wait(0.02)\n    robot.stop()</pre>"
                     "<p>Why limit the steering? When a wall ends, the sensor suddenly reads a huge error — without a "
                     "limit the robot would swerve into the corner. Real robots clamp their motors too.</p>",
            "task": "<p>Drive through the snake corridor to the green <b>EXIT</b> using the right-hand rule, cell by cell. "
                    "It must work in the flipped snake too!</p>",
            "goals": ["Right-hand rule at every cell", "Reach the EXIT", "No bumps", "Works in the flipped snake too"],
            "arena": SNAKE_ARENA, "starter": MAZE_S2, "solution": MAZE_S2_SOL,
            "hints": ["Copy turn_on_grid() and drive_one_cell() from the lesson first, and test one cell.",
                      "Your main loop runs while robot.color() != \"green\". Inside: check the right side first, then the front.",
                      "if robot.distance(\"right\") > 30:\n    turn_on_grid(-90)\n    drive_one_cell()\nelif robot.distance(\"front\") > 30:\n    drive_one_cell()\nelse:\n    turn_on_grid(90)"],
            "check": MAZE_S2_CHECK, "concepts": ["navigation", "feedback", "odometry"], "xp": 30,
        },
        {
            "id": "s3", "title": "Escape the labyrinth",
            "learn": "<p>Here's an amazing fact: if all the walls of a maze are connected to the outside wall, keeping one "
                     "hand on the wall <b>always</b> gets you out. Dead ends are no problem — the robot just turns left twice "
                     "and comes back. (That's why the rule is famous: it's thousands of years old, from the stories "
                     "about the labyrinth of the Minotaur!)</p>"
                     "<p>But this labyrinth has <b>noisy motors</b>, like a real robot. Without feedback the robot "
                     "slowly drifts into walls. Your P steering and grid snapping fix that.</p>"
                     "<p>Let's also measure how good the route is. A counter is just a variable you add to:</p>"
                     "<pre>cells = 0\n...\ncells = cells + 1     # after every drive_one_cell()\n...\nprint(\"Escaped in\", cells, \"cells\")</pre>",
            "task": "<p>Escape the labyrinth (and a second one!) to the green <b>EXIT</b> without bumping, then "
                    "<b>print how many cells</b> the robot drove.</p>",
            "goals": ["Reach the EXIT in both labyrinths", "No bumps (noisy motors!)", "Print the number of cells driven"],
            "arena": MAZE_A_ARENA, "starter": MAZE_S3, "solution": MAZE_S3_SOL,
            "hints": ["Make cells = 0 before the loop.",
                      "Add 1 right after each drive_one_cell() call, then print after the loop ends.",
                      "cells = cells + 1\n...\nprint(\"Escaped in\", cells, \"cells\")"],
            "check": MAZE_S3_CHECK, "concepts": ["navigation", "feedback"], "xp": 30,
        },
        {
            "id": "s4", "title": "Plan with BFS",
            "learn": "<p>The wall-follower got out, but it wandered into every dead end. If the robot has a <b>map</b>, it "
                     "can plan the <b>shortest</b> path before moving. A grid map can be a list of strings:</p>"
                     "<pre>MAZE = [\"...#...\",     # row 0 = top\n        \".#.#.#.\",\n        ...]\n"
                     "MAZE[row][col]   # \"#\" = wall, \".\" = open</pre>"
                     "<p>Now a treasure hunt 🏴‍☠️. You and your friends start in one room. Every minute, each group "
                     "splits up and steps into every <i>neighbouring</i> room nobody has explored yet, leaving a "
                     "note on the door: <i>\"I came from room X\"</i>. The first group to reach the treasure took the "
                     "shortest route — and by following the notes backwards you can trace it! That's "
                     "<b>BFS (breadth-first search)</b>:</p>"
                     "<ul><li><b>queue</b> — the rooms waiting to be explored, oldest first: "
                     "<code>queue.append(cell)</code> adds at the back, <code>queue.pop(0)</code> takes from the front.</li>"
                     "<li><b>came_from</b> — a dictionary of notes: <code>came_from[(2, 3)] = (2, 2)</code>. "
                     "It's also our <b>visited</b> list: if a cell is already in it, don't add it again.</li></ul>"
                     "<pre>queue = [start]\ncame_from = {start: None}\nwhile queue:\n    cell = queue.pop(0)\n"
                     "    for each neighbour (up/down/left/right) that is open and not in came_from:\n"
                     "        came_from[neighbour] = cell\n        queue.append(neighbour)</pre>"
                     "<p>Then walk backwards from the goal: goal → came_from[goal] → … → start, and reverse the list.</p>",
            "task": "<p>Write <code>shortest_path(maze, start, goal)</code>. It returns the list of <code>(row, col)</code> "
                    "cells from start to goal (both included), along the shortest route. Print the path and the number "
                    "of steps (<code>len(path) - 1</code>). I'll also test it on some secret mazes!</p>",
            "goals": ["Define shortest_path(maze, start, goal)", "Return the shortest list of cells", "Works on secret mazes", "Print the steps for the Labyrinth"],
            "arena": PLAN_ARENA, "starter": MAZE_S4, "solution": MAZE_S4_SOL,
            "hints": ["Neighbours of (r, c) are (r-1, c), (r+1, c), (r, c-1) and (r, c+1). Skip ones outside the maze or with \"#\".",
                      "After the search, start at the goal and keep doing cell = came_from[cell] until you reach None. Then path.reverse().",
                      "if maze[nr][nc] != \"#\" and (nr, nc) not in came_from:\n    came_from[(nr, nc)] = cell\n    queue.append((nr, nc))"],
            "check": MAZE_S4_CHECK, "concepts": ["mapping"], "xp": 40,
        },
        {
            "id": "s5", "title": "Drive the plan",
            "learn": "<p>A plan is only useful if the robot can follow it. This labyrinth has <b>GPS</b>: "
                     "<code>robot.position()</code> gives <code>(x, y)</code> in cm. Two little converters link the map "
                     "to the real world (remember: row 0 is at the TOP):</p>"
                     "<pre>def cell_center(cell):\n    r, c = cell\n    return c * 40 + 20, len(MAZE) * 40 - (r * 40 + 20)\n\n"
                     "def cell_of(x, y):\n    return int((len(MAZE) * 40 - y) // 40), int(x // 40)</pre>"
                     "<p>Then a <b>go-to-point</b> controller: aim at the target with <code>math.atan2</code>, compare with "
                     "the compass, and steer by the heading error — feedback again!</p>"
                     "<pre>target = math.degrees(math.atan2(ty - y, tx - x))\nerror = (target - robot.heading() + 180) % 360 - 180\n"
                     "robot.drive(50 - 2 * error, 50 + 2 * error)</pre>"
                     "<p>Sense → <b>plan</b> → act: that's how self-driving cars work. They plan a route on a map, "
                     "then use feedback to follow it.</p>",
            "task": "<p>Find the start cell from <code>robot.position()</code>, plan with <code>shortest_path</code>, then "
                    "drive to the centre of every cell on the path until you reach the EXIT. I'll start you in different places!</p>",
            "goals": ["Start cell from the GPS", "Follow the planned path", "Reach the EXIT from any start", "No bumps"],
            "arena": GPS_ARENA, "starter": MAZE_S5, "solution": MAZE_S5_SOL,
            "hints": ["start = cell_of(*robot.position()) — the * unpacks (x, y) into two arguments.",
                      "Write go_to(tx, ty): loop until you're within 3 cm; if the heading error is big, robot.turn(error) first.",
                      "for cell in path[1:]:\n    go_to(*cell_center(cell))"],
            "check": MAZE_S5_CHECK, "concepts": ["navigation", "mapping", "feedback"], "xp": 40,
        },
    ],
    "boss": {
        "id": "boss", "title": "Shortest-path race",
        "learn": "<p>Micromouse robots explore slowly, then do a <b>speed run</b> on the shortest path. Stopping at every "
                 "cell wastes time — you only need to stop where the path <b>turns</b>. A cell is a corner if the step "
                 "into it and the step out of it go in different directions:</p>"
                 "<pre>before = (path[i][0] - path[i-1][0], path[i][1] - path[i-1][1])\n"
                 "after  = (path[i+1][0] - path[i][0], path[i+1][1] - path[i][1])\nif before != after:   # it's a corner!</pre>"
                 "<p>Also try more <code>POWER</code> and faster turns: <code>robot.turn(error, 80)</code>.</p>",
        "task": "<p>Race to the treasure room in the middle of the Race Maze in under <b>11 seconds</b>, from two different "
                "starts, without touching a wall.</p>",
        "goals": ["Plan with BFS", "Reach the treasure in under 11 s", "Works from both starts", "No bumps"],
        "arena": RACE_ARENA, "starter": MAZE_BOSS, "solution": MAZE_BOSS_SOL,
        "hints": ["First try more POWER (like 80–90) and TURN_POWER (80). Is it fast enough?",
                  "Write corners(path) that keeps only the cells where the direction changes, plus the last cell.",
                  "for cell in corners(path):\n    go_to(*cell_center(cell))"],
        "check": MAZE_BOSS_CHECK, "concepts": ["mapping", "navigation", "feedback"], "xp": 90,
    },
    "remix": {
        "prompt": "Make it yours! Build your own maze solver for the Mega Maze — or design a maze that tricks wall-followers.",
        "ideas": ["Change MAZE to match the Mega Maze and plan a path across it",
                  "Draw the planned path with robot.pen_down() before driving it",
                  "Use the LEFT-hand rule instead — is it faster here?",
                  "Explore with the wall-follower, build the map yourself from the sensors, then speed-run with BFS"],
        "arena": BIG_ARENA,
    },
}


# ---------------------------------------------------------------------------
# Project 12 — Rescue Mission (capstone)
# ---------------------------------------------------------------------------
def _zone(name, x, y, w, h, color, label):
    return {"name": name, "rect": [x, y, w, h], "color": color, "label": label}


RESCUE_ZONES = [_zone("home", 10, 10, 50, 50, "blue", "🏠 home"), _zone("base", 255, 155, 55, 55, "green", "⛺ base")]
RESCUE_RUBBLE = [[150, 20, 30, 25], [20, 110, 30, 25], [270, 20, 30, 30], [180, 195, 30, 25]]
RESCUE_LABELS = [[100, 40, "L1"], [250, 80, "L2"], [110, 160, "L3"]]

PLAN_ROOM = {"name": "Mission Control", "size": [320, 220], "start": [35, 35, 0], "time_limit": 20, "gps": True,
             "gripper": True, "boxes": RESCUE_RUBBLE, "zones": RESCUE_ZONES, "labels": RESCUE_LABELS}
RESCUE_A = {"name": "Disaster Zone", "size": [320, 220], "start": [35, 35, 0], "time_limit": 120, "gps": True,
            "gripper": True, "boxes": RESCUE_RUBBLE, "zones": RESCUE_ZONES, "labels": RESCUE_LABELS,
            "gems": [[60, 160], [210, 90], [290, 130]], "blocks": [{"pos": [160, 180], "color": "orange"}]}
RESCUE_B = {**RESCUE_A, "name": "Disaster Zone (day 2)", "gems": [[150, 120], [40, 200], [240, 30]],
            "blocks": [{"pos": [230, 150], "color": "orange"}]}
KIT_A = {**RESCUE_A, "time_limit": 150}
KIT_B = {**RESCUE_B, "time_limit": 150}
HOME_A = {**RESCUE_A, "time_limit": 170}
HOME_B = {**RESCUE_B, "time_limit": 170}
AFTERSHOCK_A = {**RESCUE_A, "name": "Aftershock", "time_limit": 170, "noise": 0.3,
                "gems": [[70, 90], [180, 130], [280, 60]], "blocks": [{"pos": [130, 110], "color": "orange"}]}
AFTERSHOCK_B = {**AFTERSHOCK_A, "name": "Aftershock (night)", "gems": [[240, 150], [130, 90], [60, 195]],
                "blocks": [{"pos": [200, 80], "color": "orange"}]}

CAP_PLAN = """# 🏆 RESCUE MISSION — the plan
# 1. Search the disaster zone from 3 lookout spots and rescue all 3 survivors (gems)
# 2. Find the rescue kit (the orange block) with the camera and grab it
# 3. Carry the kit to the base camp ⛺
# 4. Drive back home 🏠 and report "Mission complete!"
# Rule number 1: NEVER crash into the rubble.
"""

CAP_S1 = """# 🏆 RESCUE MISSION — the plan
# 1. ...

def find_survivors():
    pass

# TODO: finish the plan (at least 4 comment lines) and add a stub function for every part
find_survivors()
"""

CAP_STUB_SURVIVORS = """
def find_survivors():
    robot.say("TODO: find the survivors")
"""

CAP_STUB_KIT = """
def fetch_kit():
    robot.say("TODO: find and grab the kit")
    return False

def deliver_kit():
    robot.say("TODO: carry the kit to base")
"""

CAP_STUB_HOME = """
def go_home():
    robot.say("TODO: drive home")
"""

CAP_MAIN = """
# ---- the mission ----
find_survivors()
if fetch_kit():
    deliver_kit()
go_home()
"""

CAP_S1_SOL = CAP_PLAN + CAP_STUB_SURVIVORS + CAP_STUB_KIT + CAP_STUB_HOME + CAP_MAIN

CAP_TOOLS = """import math

HOME = (35, 35)
BASE = (282, 182)
LOOKOUTS = [(100, 50), (250, 90), (110, 170)]    # L1, L2, L3: safe spots with a good view
SURVIVORS = 3

# ---- toolbox ----
def blocked():
    # AVOID: is there rubble right in front of me?
    return robot.distance("front") < 10 or robot.distance("front_left") < 8 or robot.distance("front_right") < 8

def go_to(tx, ty):
    # drive to (tx, ty) with GPS + compass feedback
    while True:
        x, y = robot.position()
        if math.hypot(tx - x, ty - y) < 4:
            break
        target = math.degrees(math.atan2(ty - y, tx - x))
        error = (target - robot.heading() + 180) % 360 - 180
        if abs(error) > 20:
            robot.turn(error)
        else:
            robot.drive(60 - 2 * error, 60 + 2 * error)
        robot.wait(0.02)
    robot.stop()

def scan(kind):
    # spin in 30 degree steps until the camera sees a "gem" or a "block"
    for step in range(12):
        for thing in robot.camera():
            if thing["kind"] == kind:
                return thing
        robot.turn(30)
    return None

def chase_gem():
    # SEEK: steer at the nearest survivor until the camera can't see it any more
    last = 999
    while True:
        gems = [t for t in robot.camera() if t["kind"] == "gem"]
        if not gems or gems[0]["distance"] > last + 10:
            robot.stop()
            return last < 8              # it vanished right in front of us: rescued!
        if blocked():                    # AVOID beats SEEK
            robot.stop()
            robot.backward(10)
            return False
        last = gems[0]["distance"]
        steer = gems[0]["angle"]
        robot.drive(40 - steer, 40 + steer)
        robot.wait(0.02)
"""

CAP_SURVIVORS = """
def find_survivors():
    found = 0
    for spot in LOOKOUTS:
        for attempt in range(3):
            go_to(*spot)
            if found == SURVIVORS or not scan("gem"):
                break                    # nothing (more) to see from here: next lookout
            if chase_gem():
                found = found + 1
                robot.beep(1200)
                robot.say("Survivor " + str(found) + " rescued!")
    return found
"""

CAP_KIT = """
def fetch_kit():
    for spot in LOOKOUTS:
        go_to(*spot)
        kit = scan("block")
        if kit:
            while kit and kit["distance"] > 4:        # creep up until it's right in the gripper
                if kit["distance"] > 25 and blocked():  # AVOID still wins (but the kit itself is fine to touch)
                    robot.backward(10)
                    break
                robot.drive(30 - kit["angle"], 30 + kit["angle"])
                robot.wait(0.02)
                kits = [t for t in robot.camera() if t["kind"] == "block"]
                kit = kits[0] if kits else None
            robot.stop()
            if robot.grab():
                return True
    return False

def deliver_kit():
    go_to(*BASE)
    robot.release()
    robot.backward(15)
    robot.say("Kit delivered!")
"""

CAP_HOME = """
def go_home():
    go_to(*HOME)
    robot.led("green")
    robot.say("Mission complete!")
"""

CAP_S2 = CAP_S1_SOL
CAP_S2_SOL = CAP_PLAN + "\n" + CAP_TOOLS + CAP_SURVIVORS + CAP_STUB_KIT + CAP_STUB_HOME + CAP_MAIN
CAP_S3 = CAP_S2_SOL
CAP_S3_SOL = CAP_PLAN + "\n" + CAP_TOOLS + CAP_SURVIVORS + CAP_KIT + CAP_STUB_HOME + CAP_MAIN
CAP_S4 = CAP_S3_SOL
CAP_S4_SOL = CAP_PLAN + "\n" + CAP_TOOLS + CAP_SURVIVORS + CAP_KIT + CAP_HOME + CAP_MAIN

CAP_CONTROLLER = """
# ---- the mission controller: one state at a time ----
state = "search"
while state != "done":
    if state == "search":
        robot.led("yellow")
        find_survivors()
        state = "fetch"
    elif state == "fetch":
        robot.led("blue")
        if fetch_kit():
            state = "deliver"
        else:
            state = "home"               # no kit? still get everyone home safely
    elif state == "deliver":
        robot.led("purple")
        deliver_kit()
        state = "home"
    elif state == "home":
        go_home()
        state = "done"
"""

CAP_S5 = CAP_S4_SOL
CAP_S5_SOL = CAP_PLAN + "\n" + CAP_TOOLS + CAP_SURVIVORS + CAP_KIT + CAP_HOME + CAP_CONTROLLER

QUAKE_A = {**RESCUE_A, "name": "Earthquake City", "time_limit": 120, "noise": 0.3,
           "gems": [[60, 160], [210, 90], [290, 130], [140, 140]], "blocks": [{"pos": [250, 40], "color": "orange"}]}
QUAKE_B = {**QUAKE_A, "name": "Earthquake City (storm)", "gems": [[150, 120], [40, 200], [240, 30], [300, 100]],
           "blocks": [{"pos": [60, 80], "color": "orange"}]}

CAP_BOSS = CAP_S5_SOL.replace("SURVIVORS = 3", "SURVIVORS = 4   # 👾 BOSS: 4 survivors and only 120 seconds!")
CAP_BOSS_SOL = (CAP_PLAN.replace("3 survivors", "4 survivors") + "\n" + CAP_TOOLS + CAP_SURVIVORS + CAP_KIT + CAP_HOME
                + CAP_CONTROLLER).replace("SURVIVORS = 3", "SURVIVORS = 4") \
    .replace("            robot.turn(error)\n", "            robot.turn(error, 80)\n") \
    .replace("robot.drive(60 - 2 * error, 60 + 2 * error)", "robot.drive(85 - 2 * error, 85 + 2 * error)") \
    .replace("        robot.turn(30)\n", "        robot.turn(30, 80)\n") \
    .replace("robot.drive(40 - steer, 40 + steer)", "robot.drive(60 - steer, 60 + steer)")

RESCUE_RESULT = r"""
def rescue_report(r, lab, survivors):
    bumps = [e for e in r.events if e["type"] == "crash"]
    if bumps:
        raise CheckFail(f"({lab}) CRASH into the rubble near ({bumps[0]['x']:.0f}, {bumps[0]['y']:.0f}) at {bumps[0]['t']:.0f} s! "
                        "Rule number 1 of rescue robots: don't make things worse. Check blocked() before you drive on.")
    expect(r.gems == survivors, f"({lab}) You rescued {r.gems} of {survivors} survivors in {r.time:.0f} s. Watch the replay: "
                                "which one did the camera never spot? Scan from each lookout, and try again after every rescue.")

def kit_report(r, lab):
    b = r.blocks[0]
    expect(not b["held"], f"({lab}) The robot is still holding the kit at ({b['x']:.0f}, {b['y']:.0f}). robot.release() it in the base camp!")
    expect(r.blocks_in("base") >= 1, f"({lab}) The rescue kit ended at ({b['x']:.0f}, {b['y']:.0f}), not in the ⛺ base camp. "
                                     "Find it with scan(\"block\"), creep up until it's about 4 cm away, grab(), then go_to(*BASE).")

def home_report(r, lab):
    expect(r.in_zone("home") or r.end_reason != "time_limit", f"({lab}) ⏱ Time's up! After {r.time:.0f} s the robot was at ({r.x:.0f}, {r.y:.0f}), "
                                                               "still out in the disaster zone. Find where your robot wastes time and speed that part up.")
    expect(r.in_zone("home"), f"({lab}) The robot finished at ({r.x:.0f}, {r.y:.0f}) after {r.time:.0f} s — not in the 🏠 home zone. "
                              "Every mission ends with the robot back home safely.")
"""

CAP_S1_CHECK = r"""
import ast as _ast
comments = [l for l in source.splitlines() if l.strip().startswith("#")]
expect(len(comments) >= 4, f"Your plan has {len(comments)} comment line(s). Write at least 4 steps of the plan as # comments first.")
funcs = [n.name for n in _ast.walk(tree) if isinstance(n, _ast.FunctionDef)]
expect(len(funcs) >= 3, f"You have {len(funcs)} function(s). Break the mission into at least 3 functions (one per part of the plan) — for now they can just say what they WILL do.")
missing = [f for f in funcs if calls(f) == 0]
expect(not missing, f"You defined {missing[0] if missing else ''}() but never call it. Call every part of the plan at the bottom of your program.")
r = sim()
expect(r.crashes == 0, "Your stubs should be safe — the robot crashed!")
SUCCESS = f"A plan with {len(comments)} comment lines and {len(funcs)} functions that already runs. That's how engineers start! 📋"
"""

CAP_S2_CHECK = RESCUE_RESULT + _consts(DAY2=RESCUE_B) + r"""
expect(calls("camera") >= 1, "Survivors could be anywhere — use robot.camera() to look for them.")
for lab, arn in (("day 1", ARENA), ("day 2: survivors moved", DAY2)):
    r = sim(arn, label=lab)
    rescue_report(r, lab, 3)
SUCCESS = "3 survivors rescued, twice, with zero crashes. 🚁 Search-and-rescue pros!"
"""

CAP_S3_CHECK = RESCUE_RESULT + _consts(DAY2=KIT_B) + r"""
expect(calls("grab") >= 1, "Pick up the kit with robot.grab().")
for lab, arn in (("day 1", ARENA), ("day 2: everything moved", DAY2)):
    r = sim(arn, label=lab)
    rescue_report(r, lab, 3)
    kit_report(r, lab)
SUCCESS = "The rescue kit made it to base camp! 📦⛺"
"""

CAP_S4_CHECK = RESCUE_RESULT + _consts(DAY2=HOME_B) + r"""
for lab, arn in (("day 1", ARENA), ("day 2: everything moved", DAY2)):
    r = sim(arn, label=lab)
    rescue_report(r, lab, 3)
    kit_report(r, lab)
    home_report(r, lab)
SUCCESS = "Survivors ✓ Kit ✓ Home ✓ — the whole mission works! 🏠"
"""

CAP_S5_CHECK = RESCUE_RESULT + _consts(NIGHT=AFTERSHOCK_B) + r"""
expect(uses("state_machines"), "Build a mission controller: a state variable (like state = \"search\") and a loop with if state == \"search\": … elif state == \"fetch\": …")
expect(loops() >= 1 and ("while" in source), "The controller should be a while loop that keeps running until the mission is done.")
for lab, arn in (("aftershock", ARENA), ("aftershock at night", NIGHT)):
    r = sim(arn, label=lab)
    rescue_report(r, lab, 3)
    kit_report(r, lab)
    home_report(r, lab)
    colors = set(r.led_colors()) - {"off"}
    expect(len(colors) >= 3, f"({lab}) Show the state on the LED so the rescue team can see what the robot is doing — I saw {len(colors)} colour(s), use at least 3 (one per state).")
SUCCESS = "Mission controller online! Different ground, noisy motors, same perfect rescue. 🧠"
"""

CAP_BOSS_CHECK = RESCUE_RESULT + _consts(STORM=QUAKE_B) + r"""
for lab, arn in (("earthquake city", ARENA), ("earthquake city in a storm", STORM)):
    r = sim(arn, label=lab)
    rescue_report(r, lab, 4)
    kit_report(r, lab)
    home_report(r, lab)
SUCCESS = "🏆 FULL RESCUE in under 2 minutes, twice, no crashes. You're a robotics engineer now!"
"""

CAPSTONE = {
    "id": "capstone", "week": 6, "order": 12, "title": "Rescue Mission", "emoji": "🏆",
    "tagline": "Capstone: plan, build and test a robot that rescues survivors and gets home safe",
    "story": "An earthquake has hit the city. Your robot is the first one in: it must find the survivors, "
             "bring them the rescue kit and make it home — without making anything worse. This is your final "
             "project, and you'll build it the way real engineers do: plan it, build it in pieces, test, improve.",
    "concepts": ["design", "behaviors", "state_machines", "navigation"],
    "expected_minutes": 180,
    "real_world": "Search-and-rescue robots crawled through the rubble after earthquakes and the 9/11 attacks. NASA's "
                  "Ingenuity helicopter on Mars flew 72 missions, each one planned, tested and improved step by step. "
                  "In RoboCup Rescue, student teams build robots for exactly this kind of arena.",
    "build_it": "A micro:bit or LEGO SPIKE car with an ultrasonic sensor, a simple claw and a phone camera can do a "
                "cardboard-box version: lookouts marked with tape, a ball as the rescue kit.",
    "steps": [
        {
            "id": "s1", "title": "Make a plan",
            "learn": "<p>Big robots aren't built in one go. Engineers use the <b>engineering design process</b>:</p>"
                     "<ol><li><b>Plan</b> — what exactly must the robot do? Break it into parts.</li>"
                     "<li><b>Build</b> — one part at a time.</li><li><b>Test</b> — does that part work? In every situation?</li>"
                     "<li><b>Improve</b> — fix what the test showed, then test again.</li></ol>"
                     "<p>NASA planned every one of Ingenuity's flights on Mars like this. Start by writing the plan as "
                     "<b>comments</b>, then make a <b>stub</b> function for each part — a function that doesn't do the "
                     "real job yet, but lets the whole program run:</p>"
                     "<pre>def fetch_kit():\n    robot.say(\"TODO: find and grab the kit\")\n    return False</pre>"
                     "<p>This is called <b>decomposition</b>: a scary big problem becomes several small friendly ones.</p>",
            "task": "<p>Write the mission plan as <b>at least 4 comment lines</b>, and at least <b>3 stub functions</b> "
                    "(e.g. <code>find_survivors</code>, <code>fetch_kit</code>, <code>deliver_kit</code>, "
                    "<code>go_home</code>). Call them all at the bottom so the program runs from start to end.</p>",
            "goals": ["4+ comment lines of plan", "3+ functions", "Every function is called", "The program runs"],
            "arena": PLAN_ROOM, "starter": CAP_S1, "solution": CAP_S1_SOL,
            "hints": ["The mission has 4 parts: survivors, kit, deliver, home. One comment line each!",
                      "A stub can just use robot.say(\"TODO …\") — or pass — inside.",
                      "def fetch_kit():\n    robot.say(\"TODO: grab the kit\")\n    return False\n\ndef go_home():\n    robot.say(\"TODO: drive home\")"],
            "check": CAP_S1_CHECK, "concepts": ["design"], "xp": 20,
        },
        {
            "id": "s2", "title": "Find the survivors",
            "learn": "<p>The survivors (💎) could be anywhere, so the robot needs a <b>search pattern</b>. Rescue drones "
                     "fly to lookout points and scan around. Our lookouts L1, L2 and L3 are safe spots with a good view:</p>"
                     "<pre>LOOKOUTS = [(100, 50), (250, 90), (110, 170)]</pre>"
                     "<p>Build it from small tools (functions), testing each one:</p>"
                     "<ul><li><code>go_to(x, y)</code> — your GPS driver from Maze Master.</li>"
                     "<li><code>scan(\"gem\")</code> — turn 30° at a time until <code>robot.camera()</code> sees one.</li>"
                     "<li><code>chase_gem()</code> — steer at <code>angle</code> until the gem disappears (rescued!).</li>"
                     "<li><code>blocked()</code> — rubble right in front? Check <code>front</code>, <code>front_left</code> "
                     "and <code>front_right</code>.</li></ul>"
                     "<p>Inside <code>chase_gem()</code>, check <code>blocked()</code> <b>first</b>. This is a "
                     "<b>behaviour priority</b>: AVOID beats SEEK. A rescue robot that crashes into a wall is no help to anyone.</p>"
                     "<pre>if blocked():          # 1. AVOID (most important)\n    robot.backward(10)\n    return False\n"
                     "steer = gems[0][\"angle\"]  # 2. SEEK\nrobot.drive(40 - steer, 40 + steer)</pre>",
            "task": "<p>Fill in <code>find_survivors()</code>: visit each lookout, scan, chase any survivor you see, go back "
                    "to the lookout and scan again. Rescue <b>all 3 survivors</b> without crashing. (Day 2 moves them!)</p>",
            "goals": ["Search from the lookouts", "Rescue 3 survivors", "Works on day 2 too", "No crashes"],
            "arena": RESCUE_A, "starter": CAP_S2, "solution": CAP_S2_SOL,
            "hints": ["Build and test one tool at a time: first go_to() to the 3 lookouts, then scan(), then chase_gem().",
                      "robot.camera() gives a list; keep only gems: [t for t in robot.camera() if t[\"kind\"] == \"gem\"]. A gem that disappears when it was very close has been rescued.",
                      "for spot in LOOKOUTS:\n    for attempt in range(3):\n        go_to(*spot)\n        if found == SURVIVORS or not scan(\"gem\"):\n            break\n        if chase_gem():\n            found = found + 1"],
            "check": CAP_S2_CHECK, "concepts": ["behaviors", "sensors", "navigation", "design"], "xp": 35,
        },
        {
            "id": "s3", "title": "Carry the rescue kit",
            "learn": "<p>Now the orange <b>rescue kit</b> (a block). The camera sees it as <code>\"kind\": \"block\"</code>. "
                     "Grabbing needs care: the gripper only closes on a block that is right in front of the robot "
                     "(camera distance about 4 cm).</p>"
                     "<pre>kit = scan(\"block\")\nwhile kit and kit[\"distance\"] &gt; 4:\n"
                     "    robot.drive(30 - kit[\"angle\"], 30 + kit[\"angle\"])   # creep up slowly\n"
                     "    robot.wait(0.02)\n    kits = [t for t in robot.camera() if t[\"kind\"] == \"block\"]\n"
                     "    kit = kits[0] if kits else None\nrobot.stop()\nrobot.grab()</pre>"
                     "<p>Careful: the distance sensor ALSO sees the kit as an obstacle, so only check "
                     "<code>blocked()</code> while the kit is still far away. Then <b>carry</b> it to base with "
                     "<code>go_to(*BASE)</code> and <code>robot.release()</code>.</p>",
            "task": "<p>Replace the kit stubs: find the kit, grab it, carry it into the green ⛺ base camp and release it. "
                    "Keep rescuing the survivors first!</p>",
            "goals": ["Rescue 3 survivors", "Grab the kit", "Kit released in the base camp", "No crashes"],
            "arena": KIT_A, "starter": CAP_S3, "solution": CAP_S3_SOL,
            "hints": ["Reuse your tools! Loop over the LOOKOUTS, go_to each one and scan(\"block\") until you see the kit.",
                      "Creep up at low power and stop when kit[\"distance\"] is 4 or less, then robot.grab() returns True.",
                      "def deliver_kit():\n    go_to(*BASE)\n    robot.release()\n    robot.backward(15)"],
            "check": CAP_S3_CHECK, "concepts": ["manipulation", "behaviors", "design"], "xp": 35,
        },
        {
            "id": "s4", "title": "Return home",
            "learn": "<p>A mission isn't finished until the robot is back. Mars rovers and rescue robots must always keep "
                     "a way home — a robot stuck in the rubble becomes something ELSE that needs rescuing!</p>"
                     "<p>Your home is at <code>HOME = (35, 35)</code>. Because your <code>go_to()</code> is a reusable "
                     "function, this part is short. That's the magic of decomposition: every new part gets easier.</p>"
                     "<p><b>Test</b> the whole mission on both days now. If something fails, watch the replay, find the "
                     "part that went wrong, and <b>improve</b> just that function.</p>",
            "task": "<p>Replace the <code>go_home()</code> stub: drive back into the 🏠 home zone, then turn the LED green "
                    "and say that the mission is complete.</p>",
            "goals": ["Survivors + kit still work", "End in the home zone", "Report \"Mission complete!\"", "No crashes"],
            "arena": HOME_A, "starter": CAP_S4, "solution": CAP_S4_SOL,
            "hints": ["go_to(*HOME) takes you home.", "Add robot.led(\"green\") and robot.say(...) at the end.",
                      "def go_home():\n    go_to(*HOME)\n    robot.led(\"green\")\n    robot.say(\"Mission complete!\")"],
            "check": CAP_S4_CHECK, "concepts": ["navigation", "design"], "xp": 25,
        },
        {
            "id": "s5", "title": "The mission controller",
            "learn": "<p>Real robots have a <b>mission controller</b>: the brain that decides what to do next. You met "
                     "<b>state machines</b> with the Delivery Bot — one <code>state</code> variable, and rules for when to "
                     "switch:</p>"
                     "<pre>state = \"search\"\nwhile state != \"done\":\n    if state == \"search\":\n        find_survivors()\n"
                     "        state = \"fetch\"\n    elif state == \"fetch\":\n        if fetch_kit():\n            state = \"deliver\"\n"
                     "        else:\n            state = \"home\"    # no kit? still get home!\n    ...</pre>"
                     "<p>Inside every state, <b>behaviour priorities</b> keep the robot safe (this is called "
                     "<i>subsumption</i> — a higher behaviour takes over a lower one):</p>"
                     "<ol><li><b>AVOID</b> — rubble ahead? back off (always wins)</li><li><b>CARRY</b> — holding the kit? head for base</li>"
                     "<li><b>SEEK</b> — see a survivor? go to it</li><li><b>WANDER</b> — nothing seen? move to the next lookout</li></ol>"
                     "<p>Roombas, RoboCup soccer robots and Mars rovers all combine behaviours like this.</p>",
            "task": "<p>Replace the list of calls at the bottom with a <b>state machine</b> mission controller, and show each "
                    "state with a different <b>LED colour</b> (at least 3). Then test it in the Aftershock arena: rubble "
                    "moved and the motors are noisy!</p>",
            "goals": ["A state variable + while loop", "3+ LED colours (one per state)", "Full rescue in the Aftershock", "No crashes"],
            "arena": AFTERSHOCK_A, "starter": CAP_S5, "solution": CAP_S5_SOL,
            "hints": ["Start with state = \"search\" and a while state != \"done\": loop.",
                      "Each if/elif branch does one job, sets an LED colour, and then changes state.",
                      "elif state == \"deliver\":\n    robot.led(\"purple\")\n    deliver_kit()\n    state = \"home\""],
            "check": CAP_S5_CHECK, "concepts": ["state_machines", "behaviors", "design"], "xp": 40,
        },
    ],
    "boss": {
        "id": "boss", "title": "Full rescue",
        "learn": "<p>The final test: <b>Earthquake City</b>. Four survivors, noisy motors and only <b>120 seconds</b>. "
                 "Time to <b>improve</b> your design:</p>"
                 "<ul><li>Where does your robot waste time? Watch the replay and the clock.</li>"
                 "<li>Faster turns: <code>robot.turn(30, 80)</code>. Faster driving in <code>go_to()</code>.</li>"
                 "<li>Is the search order of your lookouts smart?</li></ul>"
                 "<p>Change one thing at a time and test again — that's how you know what actually helped.</p>",
        "task": "<p>Rescue all <b>4 survivors</b>, deliver the kit to base and get home in under <b>120 s</b>, "
                "with no crashes, in both Earthquake City layouts.</p>",
        "goals": ["4 survivors", "Kit in base", "Home in under 120 s", "No crashes, both layouts"],
        "arena": QUAKE_A, "starter": CAP_BOSS, "solution": CAP_BOSS_SOL,
        "hints": ["Set SURVIVORS = 4 first and run it. Where does the time go?",
                  "Scanning takes lots of small turns: turn faster with robot.turn(30, 80).",
                  "In go_to(), use robot.turn(error, 80) and drive at 85 instead of 60; chase gems at 60."],
        "check": CAP_BOSS_CHECK, "concepts": ["design", "behaviors", "state_machines"], "xp": 100,
    },
    "remix": {
        "prompt": "Make it yours! Your rescue robot is ready for any disaster. Design your own mission.",
        "ideas": ["Beep a different tune for every survivor you rescue",
                  "Draw a map of where you found each survivor with robot.pen_down()",
                  "Remember where you saw the kit during the search so you don't need to look again",
                  "Build a 'battery': if robot.time() > 100, switch to the \"home\" state no matter what"],
        "arena": {**QUAKE_B, "name": "Rescue Playground", "time_limit": 180},
    },
}

PROJECTS = [MAZE_MASTER, CAPSTONE]

# ---------------------------------------------------------------------------
# Practice side quests
# ---------------------------------------------------------------------------
LEFT_HALL = {"name": "Left-Wall Hallway", "size": [320, 140], "start": [30, 94, 0], "time_limit": 25,
             "walls": [[0, 120, 320, 90]], "labels": [[160, 130, "wall on the LEFT"]]}
LEFT_HALL_2 = {**LEFT_HALL, "start": [30, 70, 0], "walls": [[0, 90, 320, 120]]}

FLAGS = {"name": "Flag Tour", "size": [300, 200], "start": [40, 40, 0], "time_limit": 60, "gps": True, "noise": 0.3,
         "boxes": [[130, 80, 40, 40]],
         "zones": [_zone("A", 235, 25, 30, 30, "red", "A"), _zone("B", 235, 145, 30, 30, "yellow", "B"),
                   _zone("C", 45, 145, 30, 30, "purple", "C")]}

WANDER_ROOM = {"name": "Rubble Room", "size": [280, 200], "start": [40, 100, 0], "time_limit": 40,
               "boxes": [[110, 40, 30, 40], [180, 120, 40, 30], [90, 150, 25, 25]]}
WANDER_ROOM_2 = {**WANDER_ROOM, "boxes": [[120, 80, 40, 40], [210, 30, 30, 30], [200, 150, 30, 30]]}

PATROL = {"name": "Night Patrol", "size": [260, 200], "start": [40, 40, 0], "time_limit": 60,
          "boxes": [[90, 80, 80, 40]], "gems": [[210, 40], [210, 160], [40, 160]],
          "zones": [_zone("start", 25, 25, 30, 30, "blue", "🏠")]}

PATROL_STARTER = """# 🔦 Night patrol — this works, but it's long and repetitive!
robot.forward(170)
robot.beep(880)
robot.say("All clear!")
robot.turn_left(90)
robot.forward(120)
robot.beep(880)
robot.say("All clear!")
robot.turn_left(90)
robot.forward(170)
robot.beep(880)
robot.say("All clear!")
robot.turn_left(90)
robot.forward(120)
robot.beep(880)
robot.say("All clear!")
robot.turn_left(90)
"""

PATROL_SOL = """# 🔦 Night patrol — one function, used four times
def patrol_leg(cm):
    robot.forward(cm)
    robot.beep(880)
    robot.say("All clear!")
    robot.turn_left(90)

for leg in range(2):
    patrol_leg(170)
    patrol_leg(120)
"""

PRACTICE = [
    {
        "id": "p_feedback_6", "concept": "feedback", "title": "Left-wall hugger", "difficulty": 2,
        "task": "<p>This time the wall is on the robot's <b>LEFT</b>. Keep 15 cm from it with P control, all the way "
                "down the slanted hallway. Careful: which way should you steer when you're too close now?</p>",
        "goals": ["Use robot.distance(\"left\")", "Stay about 15 cm from the wall", "No bumps"],
        "arena": LEFT_HALL,
        "starter": "while robot.distance(\"front\") > 20:\n    left = robot.distance(\"left\")\n    error = 15 - left\n"
                   "    robot.drive(50, 50)   # TODO: steer with the error\n    robot.wait(0.02)\nrobot.stop()\n",
        "solution": "KP = 2\nwhile robot.distance(\"front\") > 20:\n    left = robot.distance(\"left\")\n    error = 15 - left      # + = too close\n"
                    "    robot.drive(50 + KP * error, 50 - KP * error)   # too close -> steer RIGHT\n    robot.wait(0.02)\nrobot.stop()\n",
        "hints": ["Too close to a LEFT wall means you must turn right — so the LEFT wheel goes faster.",
                  "It's the same as the right-wall version, but with the + and - swapped.",
                  "robot.drive(50 + 2 * error, 50 - 2 * error)"],
        "check": _consts(HALL2=LEFT_HALL_2) + r"""
for lab, arn in (("wall sloping down", ARENA), ("wall sloping up", HALL2)):
    r = sim(arn, label=lab)
    expect(r.used("distance_left"), "Use the left sensor: robot.distance(\"left\").")
    expect(r.crashes == 0, f"({lab}) Bump! When you're too close to a LEFT wall, the LEFT wheel must go faster to steer away.")
    d = [v for v, t in zip(r.series("distance_left"), r.series("t")) if v is not None and t > 3]
    expect(r.x > 250 and len(d) > 20, f"({lab}) The robot stopped at x = {r.x:.0f}. Follow the wall to the end.")
    avg = sum(d) / len(d)
    expect(abs(avg - 15) <= 2.5 and max(abs(v - 15) for v in d) <= 6, f"({lab}) Your robot stayed {avg:.1f} cm from the wall on average (target 15). Steer with KP × error.")
SUCCESS = "Left or right, you can hug any wall! 🧱"
""",
        "xp": 20,
    },
    {
        "id": "p_navigation_6", "concept": "navigation", "title": "Flag tour", "difficulty": 2,
        "task": "<p>This field has GPS but noisy motors. Write <code>go_to(x, y)</code> with feedback and visit the flags "
                "<b>A (250, 40)</b>, <b>B (250, 160)</b> and <b>C (60, 160)</b> in that order. Don't hit the crate!</p>",
        "goals": ["Use robot.position()", "Visit A, then B, then C", "No bumps"],
        "arena": FLAGS,
        "starter": "import math\n\ndef go_to(tx, ty):\n    # TODO: loop: read robot.position(), aim at the target, drive\n    pass\n\n"
                   "go_to(250, 40)\ngo_to(250, 160)\ngo_to(60, 160)\n",
        "solution": "import math\n\ndef go_to(tx, ty):\n    while True:\n        x, y = robot.position()\n"
                    "        if math.hypot(tx - x, ty - y) < 4:\n            break\n"
                    "        target = math.degrees(math.atan2(ty - y, tx - x))\n"
                    "        error = (target - robot.heading() + 180) % 360 - 180\n"
                    "        if abs(error) > 20:\n            robot.turn(error)\n        else:\n"
                    "            robot.drive(60 - 2 * error, 60 + 2 * error)\n        robot.wait(0.02)\n    robot.stop()\n\n"
                    "go_to(250, 40)\ngo_to(250, 160)\ngo_to(60, 160)\n",
        "hints": ["The angle to the target is math.degrees(math.atan2(ty - y, tx - x)).",
                  "error = (target - robot.heading() + 180) % 360 - 180 keeps the error between -180 and 180.",
                  "robot.drive(60 - 2 * error, 60 + 2 * error)"],
        "check": r"""
expect(calls("position") >= 1, "Use the GPS: x, y = robot.position().")
r = sim()
expect(r.crashes == 0, f"You bumped something {r.crashes} time(s). The crate is in the middle — the straight lines between the flags miss it.")
order = [z for z in r.s["visited"] if z in ("A", "B", "C")]
expect(order[:3] == ["A", "B", "C"], f"You visited {order or 'no flags'} — the tour is A, then B, then C.")
SUCCESS = "Flag tour complete! 🚩🚩🚩"
""",
        "xp": 20,
    },
    {
        "id": "p_mapping_1", "concept": "mapping", "title": "Count the open cells", "difficulty": 1,
        "task": "<p>A map is a list of strings. Write <code>count_open(maze)</code> that returns how many cells are open "
                "(<code>\".\"</code>). Print the answer for the Labyrinth. I'll test it on other maps too!</p>",
        "goals": ["Define count_open(maze)", "Correct on every map", "Print the Labyrinth's count"],
        "arena": PLAN_ARENA,
        "starter": MAZE_MAP + "\ndef count_open(maze):\n    # TODO: loop over the rows, and over the characters in each row\n    return 0\n\nprint(count_open(MAZE), \"open cells\")\n",
        "solution": MAZE_MAP + "\ndef count_open(maze):\n    total = 0\n    for row in maze:\n        for ch in row:\n"
                    "            if ch == \".\":\n                total = total + 1\n    return total\n\nprint(count_open(MAZE), \"open cells\")\n",
        "hints": ["for row in maze: gives each string; for ch in row: gives each character.",
                  "Start a counter at 0 and add 1 for every \".\".",
                  "for row in maze:\n    for ch in row:\n        if ch == \".\":\n            total = total + 1"],
        "check": KID_FUNCS + _consts(TESTS=[b[0] for b in BFS_TESTS]) + r"""
expect(defines("count_open"), "Make a function: def count_open(maze):")
fn = kid_functions().get("count_open")
expect(callable(fn), "I couldn't find a working count_open function at the top level of your program.")
for maze in TESTS:
    want = sum(row.count(".") for row in maze)
    got = call_kid(fn, maze)
    expect(got == want, f"On one of my test maps count_open() said {got!r}, but it has {want} open cells. Count the maze you're GIVEN.")
r = sim()
expect(r.has("23"), "Now print the count for the Labyrinth: print(count_open(MAZE)) — it has 23 open cells.")
SUCCESS = "23 open cells. Now you can read a map like a robot! 🗺️"
""",
        "xp": 15,
    },
    {
        "id": "p_mapping_2", "concept": "mapping", "title": "Who are my neighbours?", "difficulty": 2,
        "task": "<p>The heart of every maze search: write <code>neighbours(maze, cell)</code> that returns a list of the "
                "<b>open</b> cells directly up, down, left and right of <code>cell = (row, col)</code>. Don't fall off the "
                "edge of the map!</p>",
        "goals": ["Define neighbours(maze, cell)", "Only open cells", "Nothing outside the map"],
        "arena": PLAN_ARENA,
        "starter": MAZE_MAP + "\ndef neighbours(maze, cell):\n    r, c = cell\n    result = []\n    # TODO: check (r-1, c), (r+1, c), (r, c-1), (r, c+1)\n    return result\n\nprint(neighbours(MAZE, (2, 2)))\n",
        "solution": MAZE_MAP + "\ndef neighbours(maze, cell):\n    r, c = cell\n    result = []\n"
                    "    for nr, nc in [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]:\n"
                    "        if 0 <= nr < len(maze) and 0 <= nc < len(maze[0]) and maze[nr][nc] == \".\":\n"
                    "            result.append((nr, nc))\n    return result\n\nprint(neighbours(MAZE, (2, 2)))\n",
        "hints": ["Make a list of the 4 candidate cells and check each one.",
                  "A cell is inside the map if 0 <= nr < len(maze) and 0 <= nc < len(maze[0]).",
                  "if 0 <= nr < len(maze) and 0 <= nc < len(maze[0]) and maze[nr][nc] == \".\":\n    result.append((nr, nc))"],
        "check": KID_FUNCS + _consts(MAZE_A=MAZE_A, T2=BFS_TESTS[0][0]) + r"""
expect(defines("neighbours"), "Make a function: def neighbours(maze, cell):")
fn = kid_functions().get("neighbours")
expect(callable(fn), "I couldn't find a working neighbours function at the top level of your program.")
def truth(maze, cell):
    r, c = cell
    return {(nr, nc) for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
            if 0 <= nr < len(maze) and 0 <= nc < len(maze[0]) and maze[nr][nc] == "."}
for maze, cell, what in ((MAZE_A, (2, 2), "a cell in the middle"), (MAZE_A, (0, 0), "the top-left corner"),
                         (MAZE_A, (4, 6), "the bottom-right corner"), (T2, (2, 2), "a crossroads"), (T2, (1, 0), "the left edge")):
    got = call_kid(fn, maze, cell)
    try:
        got_set = {(int(a), int(b)) for a, b in got}
    except Exception:
        raise CheckFail(f"neighbours() should return a list of (row, col) pairs, but for {what} I got {got!r}.")
    want = truth(maze, cell)
    expect(got_set == want, f"For {what} {cell} you said {sorted(got_set)}, but the open neighbours are {sorted(want)}.")
SUCCESS = "Perfect neighbours! That's the first half of BFS. 🏘️"
""",
        "xp": 20,
    },
    {
        "id": "p_mapping_3", "concept": "mapping", "title": "Is there a way?", "difficulty": 3,
        "task": "<p>Write <code>steps(maze, start, goal)</code> that returns the <b>number of steps</b> on the shortest "
                "path — or <code>-1</code> if the goal can't be reached at all. Hint: BFS can store the distance to every "
                "cell instead of came_from.</p>",
        "goals": ["Define steps(maze, start, goal)", "Shortest number of steps", "-1 when there's no way"],
        "arena": PLAN_ARENA,
        "starter": MAZE_MAP + "\ndef steps(maze, start, goal):\n    # TODO: BFS with a dist dictionary: dist[start] = 0\n    return -1\n\nprint(steps(MAZE, START, GOAL))\n",
        "solution": MAZE_MAP + "\ndef steps(maze, start, goal):\n    dist = {start: 0}\n    queue = [start]\n    while queue:\n"
                    "        cell = queue.pop(0)\n        if cell == goal:\n            return dist[cell]\n        r, c = cell\n"
                    "        for nr, nc in [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]:\n"
                    "            if 0 <= nr < len(maze) and 0 <= nc < len(maze[0]) and maze[nr][nc] != \"#\" and (nr, nc) not in dist:\n"
                    "                dist[(nr, nc)] = dist[cell] + 1\n                queue.append((nr, nc))\n    return -1\n\n"
                    "print(steps(MAZE, START, GOAL))\n",
        "hints": ["dist is a dictionary: dist[start] = 0, and every new neighbour gets dist[cell] + 1.",
                  "If the queue runs empty and you never reached the goal, there's no way: return -1.",
                  "if cell == goal:\n    return dist[cell]"],
        "check": KID_FUNCS + _consts(TESTS=BFS_TESTS, WALLED=(["..#..", "..#..", "###..", "....."], (0, 0), (3, 4))) + r"""
expect(defines("steps"), "Make a function: def steps(maze, start, goal):")
fn = kid_functions().get("steps")
expect(callable(fn), "I couldn't find a working steps function at the top level of your program.")
for maze, start, goal, lab in TESTS:
    want = bfs_steps(maze, start, goal)
    got = call_kid(fn, maze, start, goal)
    expect(got == want, f"On my test maze '{lab}' you said {got!r} steps, but the shortest path is {want}.")
maze, start, goal = WALLED
got = call_kid(fn, maze, start, goal)
expect(got == -1, f"On a maze where the start is walled in, steps() said {got!r}. When there's no way to the goal, return -1.")
SUCCESS = "You can measure any maze — and spot impossible ones! 🧭"
""",
        "xp": 25,
    },
    {
        "id": "p_behaviors_6", "concept": "behaviors", "title": "Safe wanderer", "difficulty": 2,
        "task": "<p>Wander around the rubble room for 40 seconds and cover at least <b>3 metres</b> without a single "
                "crash. Two behaviours: <b>AVOID</b> (something close? turn away) beats <b>WANDER</b> (drive on).</p>",
        "goals": ["Keep moving (3 m or more)", "No crashes", "Works in a second room too"],
        "arena": WANDER_ROOM,
        "starter": "while True:\n    # TODO: AVOID first, then WANDER\n    robot.drive(50, 50)\n    robot.wait(0.02)\n",
        "solution": "while True:\n    front = robot.distance(\"front\")\n"
                    "    if front < 20 or robot.distance(\"front_left\") < 12 or robot.distance(\"front_right\") < 12:\n"
                    "        robot.stop()                          # AVOID wins: turn toward the more open side\n"
                    "        if robot.distance(\"left\") > robot.distance(\"right\"):\n"
                    "            robot.turn(100)\n        else:\n            robot.turn(-100)\n    else:\n"
                    "        robot.drive(50, 50)                   # WANDER\n    robot.wait(0.02)\n",
        "hints": ["Check the distance sensors at the start of every loop.",
                  "Use front, front_left and front_right so you also notice corners of boxes.",
                  "if robot.distance(\"front\") < 20:\n    robot.stop()\n    robot.turn(100)\nelse:\n    robot.drive(50, 50)"],
        "check": _consts(ROOM2=WANDER_ROOM_2) + r"""
expect(calls("distance") >= 1, "Use the distance sensor to notice rubble before you hit it.")
for lab, arn in (("rubble room", ARENA), ("another rubble room", ROOM2)):
    r = sim(arn, label=lab)
    expect(r.crashes == 0, f"({lab}) Crash! {r.crashes} bump(s). AVOID must be checked first, every loop — try the front_left and front_right sensors too.")
    expect(r.distance >= 300, f"({lab}) The robot only travelled {r.distance:.0f} cm. Keep wandering — at least 300 cm in 40 s.")
SUCCESS = "Wandered far and never touched a thing. Roomba would be proud! 🧹"
""",
        "xp": 20,
    },
    {
        "id": "p_design_6", "concept": "design", "title": "Tidy up with a function", "difficulty": 1,
        "task": "<p>This patrol program works, but it repeats the same 4 lines again and again. Engineers "
                "<b>decompose</b>: put the repeated part in a function like <code>patrol_leg(cm)</code> and call it. "
                "Same patrol, much tidier code!</p>",
        "goals": ["Define a function with a parameter", "Call it at least 3 times (or in a loop)", "Still collect all 3 gems"],
        "arena": PATROL, "starter": PATROL_STARTER, "solution": PATROL_SOL,
        "hints": ["Which 4 lines are repeated? Only the distance changes.",
                  "def patrol_leg(cm): … then use cm inside instead of the number.",
                  "for leg in range(2):\n    patrol_leg(170)\n    patrol_leg(120)"],
        "check": r"""
import ast as _ast
funcs = [n for n in _ast.walk(tree) if isinstance(n, _ast.FunctionDef)]
expect(funcs, "Make a function for one patrol leg: def patrol_leg(cm):")
expect(any(f.args.args for f in funcs), "Give your function a parameter (like cm) so each leg can be a different length.")
expect(calls("forward") <= 2, f"There are still {calls('forward')} robot.forward(...) lines. Put forward inside your function and call the function instead.")
r = sim()
expect(r.crashes == 0, "The patrol bumped into something — check the distances.")
expect(r.gems == 3, f"The patrol only reached {r.gems} of 3 gems. It should still do the same route.")
SUCCESS = "Same patrol, half the code. That's decomposition! ✂️"
""",
        "xp": 15,
    },
]
