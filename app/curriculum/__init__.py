"""Loads the 6-week curriculum from week1.py … week6.py."""
import importlib

PROJECTS = []
PRACTICE = []
for _w in range(1, 7):
    try:
        _m = importlib.import_module(f"{__name__}.week{_w}")
    except ModuleNotFoundError as _e:
        if _e.name != f"{__name__}.week{_w}":
            raise
        continue
    PROJECTS.extend(getattr(_m, "PROJECTS", []))
    for _pr in getattr(_m, "PRACTICE", []):
        _pr.setdefault("week", _w)          # side quests belong to the week file they're in
        PRACTICE.append(_pr)
PROJECTS.sort(key=lambda p: p["order"])
BY_ID = {p["id"]: p for p in PROJECTS}
PRACTICE_BY_ID = {p["id"]: p for p in PRACTICE}


def week_practice(week):
    return [pr for pr in PRACTICE if pr["week"] == week]


def step(project_id, step_id):
    p = BY_ID[project_id]
    for s in p["steps"] + ([p["boss"]] if p.get("boss") else []):
        if s["id"] == step_id:
            return s
    raise KeyError(step_id)
