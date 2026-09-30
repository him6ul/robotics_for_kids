"""Static analysis of a learner's robot program: which robotics concepts it uses and how complex it is.

Shared by the check harness (inside the sandbox subprocess) and the server's analytics, so it must only
depend on the standard library.
"""
import ast

CONCEPTS = [
    "actuators", "sequencing", "kinematics", "sensors", "control_loop", "decisions", "thresholds",
    "feedback", "pid", "odometry", "state_machines", "manipulation", "navigation", "mapping",
    "behaviors", "design",
]

CONCEPT_LABELS = {
    "actuators": "Motors & Actuators", "sequencing": "Sequences & Timing", "kinematics": "Kinematics & Geometry",
    "sensors": "Sensors", "control_loop": "Sense-Think-Act Loop", "decisions": "Reactive Decisions",
    "thresholds": "Thresholds & Calibration", "feedback": "Feedback Control", "pid": "P / PID Control",
    "odometry": "Odometry & Gyro", "state_machines": "State Machines", "manipulation": "Grippers & Arms",
    "navigation": "Navigation", "mapping": "Maps & Path Planning", "behaviors": "Combining Behaviors",
    "design": "Engineering Design",
}

MOTION = {"drive", "forward", "backward", "turn", "turn_left", "turn_right", "stop", "move", "set"}
SENSORS = {"distance", "bumper", "floor", "floor_left", "floor_right", "color", "light", "light_left",
           "light_right", "camera", "heading", "encoders", "position", "hand", "angles", "holding"}
ODOMETRY = {"encoders", "reset_encoders", "heading", "position"}
MANIP = {"grab", "release", "holding", "shoulder", "elbow", "hand"}
TRIG = {"sin", "cos", "tan", "atan2", "atan", "acos", "asin", "hypot", "radians", "degrees", "sqrt"}
PID_NAMES = {"kp", "ki", "kd", "error", "err", "integral", "derivative", "last_error", "prev_error", "correction",
             "p_gain", "gain", "target", "setpoint"}
STATE_NAMES = {"state", "mode", "phase", "stage", "status"}
MAP_NAMES = {"grid", "maze", "map", "visited", "queue", "frontier", "path", "cells", "walls", "came_from", "dist"}


def parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _call_name(node):
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def _robot_calls(tree):
    """Names of methods called on `robot` / `arm`."""
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) \
                and n.func.value.id in ("robot", "arm"):
            out.append(n.func.attr)
    return out


def _names(tree):
    s = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            s.add(n.id.lower())
        elif isinstance(n, ast.arg):
            s.add(n.arg.lower())
        elif isinstance(n, ast.Attribute):
            s.add(n.attr.lower())
    return s


_SENSOR_VARS = set()


def _test_uses_sensor(test):
    for n in ast.walk(test):
        if isinstance(n, ast.Call) and _call_name(n) in SENSORS:
            return True
        if isinstance(n, ast.Name) and n.id in _SENSOR_VARS:
            return True
    return False


def _sensor_vars(tree):
    """Names that hold a sensor reading, e.g. `d = robot.distance()` or `left, right = robot.encoders()`."""
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and any(isinstance(c, ast.Call) and _call_name(c) in SENSORS for c in ast.walk(n.value)):
            for t in n.targets:
                for x in ast.walk(t):
                    if isinstance(x, ast.Name):
                        out.add(x.id)
    return out


def _body_calls(node, names):
    for n in ast.walk(node):
        if isinstance(n, ast.Call) and _call_name(n) in names:
            return True
    return False


def detect_concepts(source, tree=None):
    """Return {concept: count} for the robotics concepts that appear in the code."""
    tree = tree or parse(source)
    found = {c: 0 for c in CONCEPTS}
    if tree is None:
        return found
    calls = _robot_calls(tree)
    names = _names(tree)
    _SENSOR_VARS.clear()
    _SENSOR_VARS.update(_sensor_vars(tree))
    motion = [c for c in calls if c in MOTION]
    sensed = [c for c in calls if c in SENSORS]
    found["actuators"] = len(motion) + calls.count("led") + calls.count("beep")
    found["sequencing"] = len(motion) if len(motion) >= 3 or calls.count("wait") >= 2 else 0
    found["sensors"] = len(sensed)
    found["odometry"] = sum(1 for c in calls if c in ODOMETRY)
    found["manipulation"] = sum(1 for c in calls if c in MANIP)
    # kinematics: trig / geometry, or differential steering (different wheel powers), or arm angles
    trig = sum(1 for n in ast.walk(tree) if isinstance(n, ast.Call) and _call_name(n) in TRIG)
    diff = 0
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and _call_name(n) == "drive" and len(n.args) == 2:
            a, b = (ast.dump(x) for x in n.args)
            if a != b:
                diff += 1
    found["kinematics"] = trig + diff + calls.count("move")
    for n in ast.walk(tree):
        if isinstance(n, ast.While):
            has_sense = _body_calls(n, SENSORS) or _test_uses_sensor(n.test)
            if has_sense and (_body_calls(n, MOTION) or _body_calls(n, {"wait"})):
                found["control_loop"] += 1
        elif isinstance(n, (ast.If, ast.IfExp)):
            if _test_uses_sensor(n.test):
                found["decisions"] += 1
        elif isinstance(n, ast.Compare):
            # comparing a sensor-looking value with a number: a threshold
            parts = [n.left] + list(n.comparators)
            if any(isinstance(p, ast.Constant) and isinstance(p.value, (int, float)) and not isinstance(p.value, bool)
                   for p in parts) and (any(_test_uses_sensor(p) for p in parts)
                                        or any(isinstance(p, ast.Name) and p.id.lower() in
                                               {"d", "dist", "distance", "v", "val", "value", "reading", "floor", "light",
                                                "left", "right", "front", "brightness", "threshold"} for p in parts)):
                found["thresholds"] += 1
        elif isinstance(n, ast.Name) and n.id.lower() in ("threshold", "black", "white", "gray", "grey", "midpoint"):
            found["thresholds"] += 1
    # feedback: a correction computed from a sensor reading feeds the motors
    pid_hits = len(names & PID_NAMES)
    if pid_hits and found["control_loop"]:
        found["feedback"] += pid_hits
    if {"kp", "p_gain", "gain"} & names or ({"error", "err"} & names and any(
            isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mult) for n in ast.walk(tree))):
        found["pid"] += 1 + len({"ki", "kd", "integral", "derivative", "last_error", "prev_error"} & names)
    if found["decisions"] and found["control_loop"]:
        found["feedback"] += 1
    # state machines: a state variable assigned strings and compared
    for n in ast.walk(tree):
        if isinstance(n, ast.Compare) and isinstance(n.left, ast.Name) and n.left.id.lower() in STATE_NAMES:
            found["state_machines"] += 1
    # navigation / mapping
    map_hits = len(names & MAP_NAMES)
    lists_of_lists = any(isinstance(n, ast.List) and n.elts and all(isinstance(e, ast.List) for e in n.elts)
                         for n in ast.walk(tree))
    if map_hits or lists_of_lists:
        found["mapping"] += map_hits + int(lists_of_lists)
    if {"distance"} <= set(calls) and ({"left", "right"} & _string_args(tree)) and found["control_loop"]:
        found["navigation"] += 1
    if found["mapping"] and found["odometry"]:
        found["navigation"] += 1
    if "position" in calls:
        found["navigation"] += 1
    # behaviours: several different sensors combined inside one control loop, or behaviour functions
    distinct = len(set(sensed))
    funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    if distinct >= 3 and found["control_loop"]:
        found["behaviors"] += distinct - 2
    if len(funcs) >= 3 and found["control_loop"]:
        found["behaviors"] += 1
    # design: planning comments + functions + a bigger program
    comments = sum(1 for l in source.splitlines() if l.strip().startswith("#"))
    code_lines = sum(1 for l in source.splitlines() if l.strip() and not l.strip().startswith("#"))
    if comments >= 4 and len(funcs) >= 2 and code_lines >= 30:
        found["design"] += 1
    return found


def _string_args(tree):
    s = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            for a in n.args:
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    s.add(a.value)
    return s


def uses(source, concept, tree=None):
    return detect_concepts(source, tree).get(concept, 0) > 0


def metrics(source):
    """Size and complexity numbers for a piece of code."""
    tree = parse(source)
    lines = [l for l in source.splitlines() if l.strip() and not l.strip().startswith("#")]
    comments = sum(1 for l in source.splitlines() if l.strip().startswith("#"))
    m = {"lines": len(lines), "comments": comments, "syntax_ok": tree is not None,
         "functions": 0, "classes": 0, "branches": 0, "loops": 0, "max_depth": 0,
         "cyclomatic": 1, "names": 0, "calls": 0, "robot_calls": 0, "sensor_kinds": 0}
    if tree is None:
        return m
    names = set()

    def depth(node, d=0):
        best = d
        for child in ast.iter_child_nodes(node):
            nd = d + 1 if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try,
                                              ast.FunctionDef, ast.ClassDef)) else d
            best = max(best, depth(child, nd))
        return best

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            m["functions"] += 1
        elif isinstance(node, ast.ClassDef):
            m["classes"] += 1
        elif isinstance(node, (ast.If, ast.IfExp)):
            m["branches"] += 1
            m["cyclomatic"] += 1
        elif isinstance(node, (ast.For, ast.While)):
            m["loops"] += 1
            m["cyclomatic"] += 1
        elif isinstance(node, ast.BoolOp):
            m["cyclomatic"] += len(node.values) - 1
        elif isinstance(node, ast.ExceptHandler):
            m["cyclomatic"] += 1
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, ast.Call):
            m["calls"] += 1
    calls = _robot_calls(tree)
    m["robot_calls"] = len(calls)
    m["sensor_kinds"] = len({c for c in calls if c in SENSORS})
    m["names"] = len(names)
    m["max_depth"] = depth(tree)
    return m


def complexity_score(source):
    """0-100 score combining size, structure, robot usage and concept breadth."""
    m = metrics(source)
    if not m["syntax_ok"]:
        return 0
    c = detect_concepts(source)
    breadth = sum(1 for v in c.values() if v)
    score = (min(m["lines"], 120) / 120) * 20 \
        + min(m["cyclomatic"], 25) / 25 * 25 \
        + min(breadth, 10) / 10 * 30 \
        + min(m["sensor_kinds"], 5) / 5 * 10 \
        + min(m["functions"] * 3 + m["classes"] * 6, 9) / 9 * 7 \
        + min(m["max_depth"], 5) / 5 * 8
    return round(score)
