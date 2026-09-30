"""RoboQuest server: a project-based robotics course for kids with a robot simulator, tracking & analytics."""
import asyncio
import copy
import csv
import datetime as dt
import hashlib
import io
import json
import os
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import time

from fastapi import Body, Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import analysis, analytics, db, digest, gamification, report, tutor
from . import observability as obs
from .curriculum import BY_ID, PRACTICE, PRACTICE_BY_ID, PROJECTS
from .curriculum import step as find_step
from .sandbox import kidast, robosim

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SANDBOX = os.path.join(ROOT, "app", "sandbox")
STATIC = os.path.join(ROOT, "static")
PY = sys.executable
RUN_TIMEOUT_SEC = 12
CHECK_TIMEOUT_SEC = 20
MAX_CODE = 60_000

app = FastAPI(title="RoboQuest")
db.init()
tutor.init()
digest.init()
obs.audit("system", "server.start", details={"python": sys.version.split()[0], "pid": os.getpid(),
                                               "projects": len(PROJECTS), "practice": len(PRACTICE)})

SANDBOX_ARENAS = {
    "open_lab": {"name": "Open Lab", "size": [320, 220], "start": [60, 110, 0], "time_limit": 120,
                 "gems": [[260, 60], [270, 170], [160, 190]], "boxes": [[150, 80, 40, 50]],
                 "zones": [{"name": "home", "rect": [20, 90, 40, 40], "color": "blue", "label": "🏠"}]},
    "sensor_park": {"name": "Sensor Park", "size": [320, 240], "start": [40, 40, 0], "time_limit": 120,
                    "boxes": [[110, 70, 30, 30], [220, 150, 50, 20]], "walls": [[200, 0, 200, 90]],
                    "lines": [{"pts": [[40, 200], [150, 200], [220, 120], [290, 120]], "width": 2.5}],
                    "zones": [{"name": "red", "rect": [250, 20, 50, 40], "color": "red"},
                              {"name": "green", "rect": [20, 150, 40, 40], "color": "green"}],
                    "lights": [[300, 220]], "gems": [[160, 40], [100, 150]],
                    "blocks": [{"pos": [170, 120], "color": "blue"}], "gripper": True},
    "race_oval": {"name": "Race Oval", "size": [300, 200], "start": [150, 30, 0], "time_limit": 120,
                  "lines": [{"pts": [[150 + 110 * __import__("math").cos(a / 36 * 6.2832 - 1.5708),
                                      100 + 70 * __import__("math").sin(a / 36 * 6.2832 - 1.5708)] for a in range(36)],
                             "closed": True, "width": 2.5}], "finish": [140, 20, 140, 40]},
    "arm_lab": {"type": "arm", "name": "Arm Lab", "blocks": [{"x": 90, "color": "red"}, {"x": 110, "color": "blue"},
                                                             {"x": 130, "color": "green"}],
                "targets": [{"name": "goal", "x": 60, "w": 16, "color": "yellow"}], "time_limit": 90},
}


# ---------------------------------------------------------------------------
# middleware: metrics + error capture
# ---------------------------------------------------------------------------
@app.middleware("http")
async def metrics_mw(request: Request, call_next):
    t0 = time.perf_counter()
    route = request.url.path
    try:
        response = await call_next(request)
    except Exception as e:  # noqa: BLE001
        obs.app_error(f"{request.method} {route}", e)
        obs.record("http.status_5xx")
        return JSONResponse({"detail": "Something went wrong on the server. It has been logged."}, status_code=500)
    ms = (time.perf_counter() - t0) * 1000
    if route.startswith("/static/"):
        # always revalidate (cheap, via ETag) so updates show up without a hard refresh
        response.headers["Cache-Control"] = "no-cache"
    if route.startswith("/api/"):
        parts = ["{id}" if p.isdigit() else p for p in route.split("/")]
        key = f"http.{request.method} {'/'.join(parts[:6])}"
        obs.record(key, ms)
        obs.record("http.all", ms)
        if response.status_code >= 500:
            obs.record("http.status_5xx")
        elif response.status_code >= 400:
            obs.record("http.status_4xx")
    return response


# ---------------------------------------------------------------------------
# parent auth (simple local PIN)
# ---------------------------------------------------------------------------
_parent_tokens = {}
_failed = {"n": 0, "until": 0.0}


def _hash_pin(pin, salt):
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), 200_000).hex()


def parent_required(request: Request):
    tok = request.cookies.get("rq_parent")
    exp = _parent_tokens.get(tok)
    if not exp or exp < time.time():
        raise HTTPException(401, "Parent PIN required")
    return True


@app.get("/api/parent/status")
def parent_status(request: Request):
    tok = request.cookies.get("rq_parent")
    return {"pin_set": bool(db.get_setting("parent_pin")), "logged_in": bool(_parent_tokens.get(tok, 0) > time.time())}


@app.post("/api/parent/login")
def parent_login(request: Request, body: dict = Body(...)):
    if _failed["until"] > time.time():
        raise HTTPException(429, f"Too many wrong PINs. Try again in {int(_failed['until'] - time.time())} s.")
    pin = str(body.get("pin", ""))
    stored = db.get_setting("parent_pin")
    if not stored:
        if len(pin) < 4:
            raise HTTPException(400, "Choose a PIN of at least 4 digits")
        salt = secrets.token_hex(16)
        db.set_setting("parent_pin", {"salt": salt, "hash": _hash_pin(pin, salt)})
        obs.audit("parent", "parent.pin_set", request=request)
    elif not secrets.compare_digest(_hash_pin(pin, stored["salt"]), stored["hash"]):
        _failed["n"] += 1
        if _failed["n"] >= 5:
            _failed["until"] = time.time() + 60
            _failed["n"] = 0
            obs.audit("system", "parent.lockout", details={"seconds": 60}, request=request)
        obs.audit("unknown", "parent.login_failed", request=request)
        raise HTTPException(403, "Wrong PIN")
    _failed["n"] = 0
    tok = secrets.token_urlsafe(24)
    _parent_tokens[tok] = time.time() + 12 * 3600
    obs.audit("parent", "parent.login", request=request)
    resp = JSONResponse({"ok": True})
    resp.set_cookie("rq_parent", tok, httponly=True, samesite="strict", max_age=12 * 3600)
    return resp


@app.post("/api/parent/logout")
def parent_logout(request: Request):
    _parent_tokens.pop(request.cookies.get("rq_parent"), None)
    obs.audit("parent", "parent.logout", request=request)
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("rq_parent")
    return resp


@app.post("/api/parent/pin")
def parent_change_pin(request: Request, body: dict = Body(...), _=Depends(parent_required)):
    pin = str(body.get("pin", ""))
    if len(pin) < 4:
        raise HTTPException(400, "PIN must be at least 4 digits")
    salt = secrets.token_hex(16)
    db.set_setting("parent_pin", {"salt": salt, "hash": _hash_pin(pin, salt)})
    obs.audit("parent", "parent.pin_changed", request=request)
    return {"ok": True}


# ---------------------------------------------------------------------------
# curriculum & learners
# ---------------------------------------------------------------------------
def _public_step(s):
    out = {k: v for k, v in s.items() if k not in ("solution", "check", "hints", "arena")}
    out["hint_count"] = len(s.get("hints", []))
    out["arena_kind"] = (s.get("arena") or {}).get("type", "drive")
    return out


@app.get("/api/curriculum")
def curriculum():
    projects = []
    for p in PROJECTS:
        q = {k: v for k, v in p.items() if k not in ("steps", "boss", "remix")}
        q["steps"] = [_public_step(s) for s in p["steps"]]
        q["boss"] = _public_step(p["boss"]) if p.get("boss") else None
        q["remix"] = {k: v for k, v in p.get("remix", {}).items() if k != "arena"}
        projects.append(q)
    practice = [_public_step(pr) for pr in PRACTICE]
    return {"projects": projects, "practice": practice, "concepts": kidast.CONCEPT_LABELS,
            "bestiary": {k: analysis.monster(k) for k in analysis.BESTIARY}, "badges": gamification.BADGES,
            "sandbox_arenas": {k: v["name"] for k, v in SANDBOX_ARENAS.items()}}


def _learner(learner_id):
    row = db.one("SELECT * FROM learners WHERE id=?", (learner_id,))
    if not row:
        raise HTTPException(404, "No such learner")
    return row


@app.get("/api/learners")
def list_learners():
    rows = db.q("SELECT * FROM learners ORDER BY id")
    for r in rows:
        r["level"] = gamification.level_for(gamification.total_xp(r["id"]))
        r["badges_earned"] = db.scalar("SELECT COUNT(*) FROM badges WHERE learner_id=? AND badge_id IN (%s)"
                                       % ",".join("?" * len(gamification.BADGES)), (r["id"], *gamification.BADGES))
        r["badges_total"] = len(gamification.BADGES)
    return rows


LEARNER_FIELDS = ("name", "avatar", "theme", "sound", "start_date", "robot_color", "robot_name")


@app.post("/api/learners")
def create_learner(request: Request, body: dict = Body(...)):
    name = str(body.get("name", "")).strip()[:40]
    if not name:
        raise HTTPException(400, "Name required")
    start = body.get("start_date") or dt.date.today().isoformat()
    lid = db.ex("""INSERT INTO learners(name, avatar, theme, robot_color, robot_name, start_date, created_at)
                   VALUES(?,?,?,?,?,?,?)""",
                (name, str(body.get("avatar", "🤖"))[:8], str(body.get("theme", "slate"))[:20],
                 str(body.get("robot_color", "#5b8def"))[:20], str(body.get("robot_name", "Bolt")).strip()[:20] or "Bolt",
                 start, db.now()))
    obs.audit(f"learner:{lid}", "learner.create", "learner", lid, {"name": name, "start_date": start}, request)
    return _learner(lid)


@app.patch("/api/learners/{lid}")
def update_learner(lid: int, request: Request, body: dict = Body(...)):
    _learner(lid)
    allowed = {k: body[k] for k in LEARNER_FIELDS if k in body}
    if "start_date" in allowed:
        try:
            dt.date.fromisoformat(str(allowed["start_date"]))
        except ValueError:
            raise HTTPException(400, "start_date must be YYYY-MM-DD")
    for k, v in allowed.items():
        db.ex(f"UPDATE learners SET {k}=? WHERE id=?", (v, lid))
    obs.audit(f"learner:{lid}", "learner.update", "learner", lid, allowed, request)
    return _learner(lid)


@app.get("/api/learners/{lid}")
def get_learner(lid: int):
    return _learner(lid)


@app.get("/api/learners/{lid}/state")
def learner_state(lid: int):
    learner = _learner(lid)
    xp = gamification.total_xp(lid)
    prog = db.q("SELECT project_id, step_id, status, attempts, hints_used, seconds, xp FROM step_progress WHERE learner_id=?", (lid,))
    g = analytics.guide(lid)
    return {
        "learner": learner,
        "level": gamification.level_for(xp),
        "streak": gamification.streak(lid),
        "progress": prog,
        "projects": analytics.project_status(lid),
        "open": _open_map(lid),
        "week_quests": analytics.week_quests(lid),
        "badges": gamification.badge_list(lid),
        "guide": {"kid": g["kid"], "path": g["path"], "position": g["position"], "schedule": g["schedule"]},
        "today_minutes": round(db.scalar("SELECT SUM(seconds) FROM time_log WHERE learner_id=? AND day=?",
                                         (lid, dt.date.today().isoformat())) / 60),
    }


def _open_map(lid):
    unlocked = _unlocked_projects(lid)
    out = {}
    for p in PROJECTS:
        if p["id"] not in unlocked:
            continue
        done = _done_steps(lid, p["id"])
        ids = [x["id"] for x in p["steps"]]
        opened = []
        for i in ids:
            opened.append(i)
            if i not in done:
                break
        if all(i in done for i in ids):
            opened += ["boss", "remix"]
        out[p["id"]] = opened
    return out


@app.get("/api/learners/{lid}/journey")
def journey(lid: int):
    """Kid-friendly slice of the analytics."""
    _learner(lid)
    return {
        "mastery": analytics.concept_mastery(lid),
        "style": analytics.learning_style(lid),
        "activity": analytics.activity(lid, 28),
        "errors": analytics.errors(lid),
        "ideas": analytics.ideas(lid),
        "code_growth": analytics.code_growth(lid),
        "robot": analytics.robot_stats(lid),
    }


# ---------------------------------------------------------------------------
# arenas: mission arenas, sandbox arenas and his own designs
# ---------------------------------------------------------------------------
def _item(project_id, step_id):
    if project_id == "_practice":
        return PRACTICE_BY_ID.get(step_id)
    if project_id in BY_ID and step_id != "remix":
        try:
            return find_step(project_id, step_id)
        except KeyError:
            return None
    return None


def _unlocked_projects(lid):
    return {p["id"] for p in analytics.project_status(lid) if p["unlocked"]}


def _done_steps(lid, project):
    return {r["step_id"] for r in db.q("SELECT step_id FROM step_progress WHERE learner_id=? AND project_id=? AND status='done'",
                                       (lid, project))}


def _unlocked_week(lid):
    return max([p["week"] for p in analytics.project_status(lid) if p["unlocked"]] or [1])


def step_lock(lid, project, step):
    """Why this learner can't open project/step yet, or None if it's open. Missions go strictly in order:
    a project opens when the previous one is finished, mission N when missions 1..N-1 are passed,
    and the boss / remix when all five missions are done. Side quests open with the week that teaches them."""
    if project in ("_playground",):
        return None
    if project == "_practice":
        pr = PRACTICE_BY_ID.get(step)
        if not pr:
            return None
        return None if pr["week"] <= _unlocked_week(lid) else f"This side quest unlocks in week {pr['week']}."
    if project not in BY_ID:
        return None
    if project not in _unlocked_projects(lid):
        wk = BY_ID[project]["week"]
        earlier = [p for p in PROJECTS if p["week"] == wk - 1]
        if earlier and BY_ID[project] is next(p for p in PROJECTS if p["week"] == wk):
            q = analytics.week_quests(lid)[wk - 1]
            if q["next"] and all(p["id"] in _unlocked_projects(lid) for p in earlier):
                return f"Finish all week {wk - 1} side quests first ({q['done']}/{q['total']} done)."
        return "Finish the previous robot (all missions, its boss and a remix) first — then this one unlocks."
    ids = [x["id"] for x in BY_ID[project]["steps"]]
    done = _done_steps(lid, project)
    if step in ("boss", "remix"):
        return None if all(i in done for i in ids) else "Finish all five missions first."
    if step in ids:
        missing = [i for i in ids[:ids.index(step)] if i not in done]
        if missing:
            return f"Finish mission {ids.index(missing[0]) + 1} first."
    return None


def require_open(lid, project, step):
    why = step_lock(lid, project, step)
    if why:
        raise HTTPException(403, why)


def resolve_arena(lid, ref):
    """ref: 'step:<project>/<step>', 'practice:<id>', 'remix:<project>', 'sandbox:<key>', 'custom:<id>'."""
    kind, _, key = str(ref or "sandbox:open_lab").partition(":")
    if kind == "step":
        pid, _, sid = key.partition("/")
        it = _item(pid, sid)
        if it and step_lock(lid, pid, sid) is None:
            return copy.deepcopy(it["arena"])
    elif kind == "practice" and key in PRACTICE_BY_ID and step_lock(lid, "_practice", key) is None:
        return copy.deepcopy(PRACTICE_BY_ID[key]["arena"])
    elif kind == "remix" and key in BY_ID and step_lock(lid, key, "remix") is None:
        return copy.deepcopy(BY_ID[key]["remix"]["arena"])
    elif kind == "sandbox" and key in SANDBOX_ARENAS:
        return copy.deepcopy(SANDBOX_ARENAS[key])
    elif kind == "custom" and key.isdigit():
        row = db.one("SELECT spec FROM arenas WHERE id=? AND learner_id=?", (int(key), lid))
        if row:
            return json.loads(row["spec"])
    raise HTTPException(404, "Unknown arena")


@app.get("/api/learners/{lid}/arenas")
def list_arenas(lid: int):
    _learner(lid)
    unlocked = _unlocked_projects(lid)
    built_in = [{"ref": f"sandbox:{k}", "name": v["name"], "group": "Sandbox", "kind": v.get("type", "drive")}
                for k, v in SANDBOX_ARENAS.items()]
    for p in PROJECTS:
        if p["id"] not in unlocked:
            continue
        for s in p["steps"] + [p["boss"]]:
            if step_lock(lid, p["id"], s["id"]):
                continue
            built_in.append({"ref": f"step:{p['id']}/{s['id']}", "name": f"{p['emoji']} {s['arena'].get('name', s['title'])}",
                             "group": p["title"], "kind": s["arena"].get("type", "drive")})
        if step_lock(lid, p["id"], "remix"):
            continue
        built_in.append({"ref": f"remix:{p['id']}", "name": f"{p['emoji']} {p['remix']['arena'].get('name', 'Remix arena')}",
                         "group": p["title"], "kind": p["remix"]["arena"].get("type", "drive")})
    mine = db.q("SELECT id, name, complexity, created_at, updated_at FROM arenas WHERE learner_id=? ORDER BY updated_at DESC", (lid,))
    for m in mine:
        m["ref"] = f"custom:{m['id']}"
    # de-duplicate arenas that several missions share
    seen, uniq = set(), []
    for a in built_in:
        k = (a["group"], a["name"])
        if k not in seen:
            seen.add(k)
            uniq.append(a)
    return {"built_in": uniq, "mine": mine}


@app.get("/api/learners/{lid}/arena")
def get_arena(lid: int, ref: str):
    a = resolve_arena(lid, ref)
    return robosim.public(robosim.normalize(a))


def _nums(item, n):
    """First n values of item as finite floats, or None if any is missing / not a number."""
    try:
        vals = [float(v) for v in list(item)[:n]]
    except (TypeError, ValueError):
        return None
    return vals if len(vals) == n and all(v == v and abs(v) != float("inf") for v in vals) else None


def _clean_arena(spec):
    """Keep only known keys with sane sizes (arenas come from the builder UI); drop malformed entries."""
    if not isinstance(spec, dict):
        raise HTTPException(400, "Arena must be an object")
    out = {"name": str(spec.get("name", "My arena"))[:40]}
    w, h = spec.get("size", [300, 200])
    out["size"] = [max(80, min(600, float(w))), max(80, min(400, float(h)))]
    st = list(spec.get("start") or []) + [0, 0, 0]
    out["start"] = _nums(st[:2], 2) and _nums(st, 3) or [40.0, 40.0, 0.0]
    lists = {"walls": 4, "boxes": 4, "gems": 2, "lights": 2}
    for k, n in lists.items():
        out[k] = [v for v in (_nums(item, n) for item in (spec.get(k) or [])[:150]) if v is not None]
    out["lines"] = []
    for ln in (spec.get("lines") or [])[:20]:
        pts = [v for v in (_nums(p, 2) for p in (ln.get("pts") or [])[:300]) if v is not None]
        if len(pts) >= 2:
            w = _nums([ln.get("width", 2.5)], 1)
            out["lines"].append({"pts": pts, "closed": bool(ln.get("closed")), "width": max(1.0, min(6.0, w[0] if w else 2.5))})
    out["zones"] = [{"name": str(z.get("name", f"zone{i}"))[:20], "rect": r, "color": str(z.get("color", "green"))[:12],
                     "label": str(z.get("label", ""))[:12]}
                    for i, z in enumerate((spec.get("zones") or [])[:30]) for r in [_nums(z.get("rect") or [], 4)] if r]
    out["blocks"] = [{"pos": pos, "color": str(b.get("color", "red"))[:12]}
                     for b in (spec.get("blocks") or [])[:20] for pos in [_nums(b.get("pos") or [], 2)] if pos]
    fin = _nums(spec.get("finish") or [], 4)
    if fin:
        out["finish"] = fin
    out["noise"] = max(0.0, min(1.0, float(spec.get("noise", 0))))
    out["gps"] = bool(spec.get("gps"))
    out["gripper"] = bool(spec.get("gripper"))
    out["time_limit"] = max(5.0, min(180.0, float(spec.get("time_limit", 60))))
    return out


@app.post("/api/learners/{lid}/arenas")
def save_arena(lid: int, request: Request, body: dict = Body(...)):
    _learner(lid)
    spec = _clean_arena(body.get("spec", {}))
    cx = analysis.arena_complexity(spec)
    now = db.now()
    aid = body.get("id")
    if aid:
        if not db.one("SELECT id FROM arenas WHERE id=? AND learner_id=?", (aid, lid)):
            raise HTTPException(404, "No such arena")
        db.ex("UPDATE arenas SET name=?, spec=?, complexity=?, updated_at=? WHERE id=?", (spec["name"], json.dumps(spec), cx, now, aid))
        action = "arena.update"
    else:
        if db.scalar("SELECT COUNT(*) FROM arenas WHERE learner_id=?", (lid,)) >= 50:
            raise HTTPException(400, "You have 50 arenas already — delete one first!")
        aid = db.ex("INSERT INTO arenas(learner_id, name, spec, complexity, created_at, updated_at) VALUES(?,?,?,?,?,?)",
                    (lid, spec["name"], json.dumps(spec), cx, now, now))
        action = "arena.create"
    obs.audit(f"learner:{lid}", action, "arena", aid, {"name": spec["name"], "complexity": cx,
                                                       "elements": {k: len(spec.get(k, [])) for k in ("walls", "boxes", "lines", "zones", "gems", "blocks", "lights")}},
              request)
    xp = 0
    if action == "arena.create" and db.scalar("SELECT COUNT(*) FROM arenas WHERE learner_id=?", (lid,)) <= 5:
        xp = gamification.award_xp(lid, 10 + cx // 10, f"arena:{aid}")
    badges = gamification.evaluate_badges(lid, PROJECTS)
    return {"id": aid, "ref": f"custom:{aid}", "complexity": cx, "xp": xp, "badges": badges, "spec": spec}


@app.get("/api/learners/{lid}/arenas/{aid}")
def load_arena(lid: int, aid: int):
    row = db.one("SELECT * FROM arenas WHERE id=? AND learner_id=?", (aid, lid))
    if not row:
        raise HTTPException(404)
    row["spec"] = json.loads(row["spec"])
    return row


@app.delete("/api/learners/{lid}/arenas/{aid}")
def delete_arena(lid: int, aid: int, request: Request):
    row = db.one("SELECT name FROM arenas WHERE id=? AND learner_id=?", (aid, lid))
    if not row:
        raise HTTPException(404)
    db.ex("DELETE FROM arenas WHERE id=?", (aid,))
    obs.audit(f"learner:{lid}", "arena.delete", "arena", aid, {"name": row["name"]}, request)
    return {"ok": True}


# ---------------------------------------------------------------------------
# code: load / autosave
# ---------------------------------------------------------------------------
PLAYGROUND_CODE = '''# 🧪 Playground — try anything here!
robot.say("Hello!")
robot.led("green")
robot.forward(40)
robot.turn(90)
print("distance ahead:", robot.distance())
'''


@app.get("/api/learners/{lid}/code")
def get_code(lid: int, project: str, step: str):
    require_open(lid, project, step)
    row = db.one("SELECT code FROM code_saves WHERE learner_id=? AND project_id=? AND step_id=?", (lid, project, step))
    if row:
        return {"code": row["code"], "source": "saved"}
    if project in BY_ID:
        p = BY_ID[project]
        ids = [s["id"] for s in p["steps"]]
        if step in ("remix", "boss"):
            prev = ids[-1]
        elif step in ids and ids.index(step) > 0:
            prev = ids[ids.index(step) - 1]
        else:
            prev = None
        if prev and step != "boss":
            r = db.one("""SELECT c.code FROM code_saves c JOIN step_progress s ON s.learner_id=c.learner_id
                          AND s.project_id=c.project_id AND s.step_id=c.step_id
                          WHERE c.learner_id=? AND c.project_id=? AND c.step_id=? AND s.status='done'""", (lid, project, prev))
            if r:
                title = "Remix it your way!" if step == "remix" else find_step(project, step)["title"]
                return {"code": r["code"].rstrip() + f"\n\n# 👉 New mission: {title} (see the mission card)\n", "source": "carried"}
        if step == "remix":
            return {"code": find_step(project, ids[-1])["solution"], "source": "starter"}
    if project == "_playground":
        return {"code": PLAYGROUND_CODE, "source": "starter"}
    it = _item(project, step)
    return {"code": it["starter"] if it else "", "source": "starter"}


@app.put("/api/learners/{lid}/code")
def save_code(lid: int, body: dict = Body(...)):
    code = str(body.get("code", ""))[:MAX_CODE]
    db.ex("""INSERT INTO code_saves(learner_id, project_id, step_id, code, updated_at) VALUES(?,?,?,?,?)
             ON CONFLICT(learner_id, project_id, step_id) DO UPDATE SET code=excluded.code, updated_at=excluded.updated_at""",
          (lid, str(body["project"])[:60], str(body["step"])[:60], code, db.now()))
    return {"ok": True}


@app.post("/api/learners/{lid}/code/reset")
def reset_code(lid: int, request: Request, body: dict = Body(...)):
    db.ex("DELETE FROM code_saves WHERE learner_id=? AND project_id=? AND step_id=?", (lid, body["project"], body["step"]))
    obs.audit(f"learner:{lid}", "code.reset", "step", f"{body['project']}/{body['step']}", request=request)
    it = _item(body["project"], body["step"])
    if body["project"] == "_playground":
        return {"code": PLAYGROUND_CODE}
    return {"code": it["starter"] if it else ""}


def _ensure_progress(lid, project, step):
    db.ex("""INSERT OR IGNORE INTO step_progress(learner_id, project_id, step_id, status, started_at)
             VALUES(?,?,?,'started',?)""", (lid, project, step, db.now()))


def _snapshot(lid, project, step, kind, code):
    info = analysis.analyze_code(code)
    db.ex("""INSERT INTO snapshots(learner_id, project_id, step_id, ts, kind, code, lines, complexity, concepts)
             VALUES(?,?,?,?,?,?,?,?,?)""",
          (lid, project, step, db.now(), kind, code, info["metrics"]["lines"], info["complexity"], json.dumps(info["concepts"])))
    return info


# ---------------------------------------------------------------------------
# simulation runs
# ---------------------------------------------------------------------------
def _sandbox_env():
    return {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1",
            "HOME": tempfile.gettempdir()}


_active = {"runs": 0, "checks": 0}


def run_sim(source, arena, seed=12345):
    t0 = time.perf_counter()
    _active["runs"] += 1
    obs.gauge("runner.active", _active["runs"])
    try:
        p = subprocess.run([PY, os.path.join(SANDBOX, "robolive.py")],
                           input=json.dumps({"source": source, "arena": arena, "seed": seed}), capture_output=True,
                           text=True, timeout=RUN_TIMEOUT_SEC, cwd=tempfile.gettempdir(), env=_sandbox_env())
        res = json.loads(p.stdout)
        obs.record("runner.payload_kb", len(p.stdout) / 1024)
    except subprocess.TimeoutExpired:
        obs.record("runner.killed")
        world = robosim.make_world(arena)
        res = robosim.result_payload(world, {"end_reason": "error", "output": "", "prints": [], "hints": [],
                                             "error": {"type": "Timeout", "line": None, "code_line": "", "text": "Timeout",
                                                       "msg": "your program ran for too long without the robot's clock moving. "
                                                              "Does a loop forget to call the robot or robot.wait()?"}})
    except json.JSONDecodeError:
        obs.record("runner.internal_error")
        world = robosim.make_world(arena)
        res = robosim.result_payload(world, {"end_reason": "error", "output": "", "prints": [], "hints": [],
                                             "error": {"type": "SimulatorError", "line": None, "code_line": "", "text": "",
                                                       "msg": "the simulator had a problem. Try running again."}})
    finally:
        _active["runs"] -= 1
        obs.gauge("runner.active", _active["runs"])
    ms = (time.perf_counter() - t0) * 1000
    obs.record("runner.duration_ms", ms)
    obs.record("runner.sim_seconds", res.get("summary", {}).get("time", 0))
    obs.record("runner.frames", len((res.get("frames") or {}).get("t", [])))
    obs.record("runner.robot_crashes", res.get("summary", {}).get("crashes", 0))
    if res.get("end_reason") == "output_limit":
        obs.record("runner.output_limit")
    res["duration_ms"] = int(ms)
    return res


def _decorate_error(res):
    err = res.get("error")
    if err:
        if err["type"] == "ValueError" and "math domain" in (err.get("msg") or ""):
            err["type"] = "MathDomainError"
        err["friendly"] = analysis.explain(err["type"], err.get("msg", ""), err.get("text", ""))
        err["monster"] = analysis.monster(err["type"])
    return res


@app.post("/api/learners/{lid}/run")
async def run(lid: int, request: Request, body: dict = Body(...)):
    _learner(lid)
    project, step, mode = str(body.get("project", "_playground")), str(body.get("step", "main")), str(body.get("mode", "step"))
    code = str(body.get("code", ""))[:MAX_CODE]
    require_open(lid, project, step)
    if project == "_playground" or step == "remix":
        ref = body.get("arena") or (f"remix:{project}" if step == "remix" else "sandbox:open_lab")
    elif project == "_practice":
        ref = f"practice:{step}"
    else:
        ref = f"step:{project}/{step}"
    arena = resolve_arena(lid, ref)
    seed = int(body.get("seed", 12345)) % 1_000_000
    res = _decorate_error(await asyncio.to_thread(run_sim, code, arena, seed))
    summ = res.get("summary", {})
    err = res.get("error")
    ok = not err
    if err:
        obs.record("runner.kid_error")
    db.ex("""INSERT INTO runs(learner_id, project_id, step_id, mode, ts, duration_ms, ok, error_type, error_line, error_msg,
             output_chars, sim_time, distance, crashes, gems, sensors, end_reason, arena) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (lid, project, step, mode, db.now(), res["duration_ms"], int(ok), err["type"] if err else None,
           err.get("line") if err else None, (err.get("msg") or "")[:300] if err else None, len(res.get("output", "")),
           summ.get("time"), summ.get("distance", summ.get("path")), summ.get("crashes", 0), summ.get("gems", 0),
           json.dumps(summ.get("sensors_used", [])), res.get("end_reason"), ref))
    if project not in ("_playground",):
        _ensure_progress(lid, project, step)
        db.ex("UPDATE step_progress SET runs=runs+1, errors=errors+?, crashes=crashes+? WHERE learner_id=? AND project_id=? AND step_id=?",
              (1 if err else 0, summ.get("crashes", 0), lid, project, step))
    _snapshot(lid, project, step, mode if mode in ("playground", "remix") else "run", code)
    obs.audit(f"learner:{lid}", "code.run", "step", f"{project}/{step}",
              {"mode": mode, "ok": ok, "error": err["type"] if err else None, "ms": res["duration_ms"], "arena": ref,
               "robot_time": summ.get("time"), "crashes": summ.get("crashes"), "gems": summ.get("gems"),
               "end": res.get("end_reason")}, request)
    res["badges"] = gamification.evaluate_badges(lid, PROJECTS)
    res["badge_count"] = {"earned": db.scalar("SELECT COUNT(*) FROM badges WHERE learner_id=?", (lid,)),
                          "total": len(gamification.BADGES)}
    if mode == "playground":
        res["playground_runs"] = db.scalar("SELECT COUNT(*) FROM runs WHERE learner_id=? AND mode='playground'", (lid,))
    return res


# ---------------------------------------------------------------------------
# checks, hints
# ---------------------------------------------------------------------------
def run_check(source, check, arena):
    t0 = time.perf_counter()
    _active["checks"] += 1
    try:
        p = subprocess.run([PY, os.path.join(SANDBOX, "robocheck.py")],
                           input=json.dumps({"source": source, "check": check, "arena": arena}), capture_output=True, text=True,
                           timeout=CHECK_TIMEOUT_SEC, cwd=tempfile.gettempdir(), env=_sandbox_env())
        res = json.loads(p.stdout)
    except subprocess.TimeoutExpired:
        obs.record("checker.timeout")
        res = {"passed": False, "message": "The test took too long — maybe a loop that never lets robot time move? "
                                           "Make sure every loop calls the robot or robot.wait()."}
    except json.JSONDecodeError:
        obs.record("checker.internal_error")
        res = {"passed": False, "message": "The tester got confused. Try running your robot first.", "checker_error": True}
    finally:
        _active["checks"] -= 1
    ms = (time.perf_counter() - t0) * 1000
    obs.record("checker.duration_ms", ms)
    if res.get("passed"):
        obs.record("checker.passed")
    if res.get("checker_error"):
        obs.record("checker.internal_error")
    res["duration_ms"] = int(ms)
    if res.get("replay"):
        _decorate_error(res["replay"])
    return res


@app.post("/api/learners/{lid}/check")
async def check(lid: int, request: Request, body: dict = Body(...)):
    _learner(lid)
    project, step, code = body["project"], body["step"], str(body.get("code", ""))[:MAX_CODE]
    require_open(lid, project, step)
    item = _item(project, step)
    if not item:
        raise HTTPException(404, "Unknown step")
    res = await asyncio.to_thread(run_check, code, item["check"], item["arena"])
    _ensure_progress(lid, project, step)
    prog = db.one("SELECT * FROM step_progress WHERE learner_id=? AND project_id=? AND step_id=?", (lid, project, step))
    was_done = prog["status"] == "done"
    attempts = prog["attempts"] + 1
    db.ex("UPDATE step_progress SET attempts=? WHERE learner_id=? AND project_id=? AND step_id=?", (attempts, lid, project, step))
    db.ex("""INSERT INTO checks(learner_id, project_id, step_id, ts, passed, message, duration_ms, scenarios, scenario)
             VALUES(?,?,?,?,?,?,?,?,?)""",
          (lid, project, step, db.now(), int(res["passed"]), res.get("message", "")[:500], res["duration_ms"],
           res.get("runs", 0), res.get("scenario")))
    code_info = _snapshot(lid, project, step, "check", code)
    level_before = gamification.level_for(gamification.total_xp(lid))["level"]
    rewards = {"xp": 0, "bonuses": [], "badges": [], "level_up": None}
    if res["passed"] and not was_done:
        base = item.get("xp", 20)
        xp = base
        first_try = attempts == 1
        if first_try:
            xp += 5
            rewards["bonuses"].append("First try! +5")
        if prog["hints_used"] == 0:
            xp += 5
            rewards["bonuses"].append("No hints! +5")
        if prog["crashes"] == 0 and prog["runs"] > 0:
            xp += 5
            rewards["bonuses"].append("Zero crashes! +5")
        if prog["hints_used"] >= 4:
            xp = max(5, base // 3)
            rewards["bonuses"] = ["Peeked at the answer — partial XP"]
        gamification.award_xp(lid, xp, f"step:{project}/{step}")
        db.ex("""UPDATE step_progress SET status='done', completed_at=?, first_try=?, xp=?
                 WHERE learner_id=? AND project_id=? AND step_id=?""", (db.now(), int(first_try), xp, lid, project, step))
        rewards["xp"] = xp
        rewards["badges"] = gamification.evaluate_badges(lid, PROJECTS)
        lvl = gamification.level_for(gamification.total_xp(lid))
        if lvl["level"] > level_before:
            rewards["level_up"] = lvl
    nxt, project_complete = None, False
    if res["passed"] and project in BY_ID:
        p = BY_ID[project]
        ids = [s["id"] for s in p["steps"]]
        if step in ids and ids.index(step) + 1 < len(ids):
            nxt = {"project": project, "step": ids[ids.index(step) + 1]}
        done = {r["step_id"] for r in db.q("SELECT step_id FROM step_progress WHERE learner_id=? AND project_id=? AND status='done'",
                                           (lid, project))}
        project_complete = all(i in done for i in ids) and step in ids and not was_done
    obs.audit(f"learner:{lid}", "check.pass" if res["passed"] else "check.fail", "step", f"{project}/{step}",
              {"attempt": attempts, "xp": rewards["xp"], "ms": res["duration_ms"], "complexity": code_info["complexity"],
               "tests": res.get("runs"), "scenario": res.get("scenario"), "message": res.get("message", "")[:120]}, request)
    return {**res, "attempts": attempts, "rewards": rewards, "next": nxt, "project_complete": project_complete,
            "code": code_info, "level": gamification.level_for(gamification.total_xp(lid)),
            "badge_count": {"earned": db.scalar("SELECT COUNT(*) FROM badges WHERE learner_id=?", (lid,)),
                            "total": len(gamification.BADGES)}}


@app.post("/api/learners/{lid}/hint")
def hint(lid: int, request: Request, body: dict = Body(...)):
    project, step, level = body["project"], body["step"], int(body.get("level", 1))
    require_open(lid, project, step)
    item = _item(project, step)
    if not item:
        raise HTTPException(404, "Unknown step")
    _ensure_progress(lid, project, step)
    prog = db.one("SELECT * FROM step_progress WHERE learner_id=? AND project_id=? AND step_id=?", (lid, project, step))
    hints = item.get("hints", [])
    if level == 4:
        if prog["hints_used"] < 3 or prog["attempts"] < 3:
            raise HTTPException(400, "Try all 3 hints and at least 3 checks first — you've got this!")
        text = item["solution"]
    elif 1 <= level <= len(hints):
        text = hints[level - 1]
    else:
        raise HTTPException(400, "No such hint")
    if level > prog["hints_used"]:
        db.ex("UPDATE step_progress SET hints_used=? WHERE learner_id=? AND project_id=? AND step_id=?", (level, lid, project, step))
        db.ex("INSERT INTO hints(learner_id, project_id, step_id, ts, level) VALUES(?,?,?,?,?)", (lid, project, step, db.now(), level))
        obs.audit(f"learner:{lid}", "hint.open" if level < 4 else "solution.peek", "step", f"{project}/{step}", {"level": level}, request)
    return {"level": level, "text": text, "is_solution": level == 4}


@app.get("/api/learners/{lid}/hints")
def hints_opened(lid: int, project: str, step: str):
    prog = db.one("SELECT hints_used, attempts FROM step_progress WHERE learner_id=? AND project_id=? AND step_id=?", (lid, project, step))
    item = _item(project, step)
    n = prog["hints_used"] if prog else 0
    hints = item.get("hints", []) if item else []
    return {"opened": [hints[i] for i in range(min(n, 3, len(hints)))], "used": n,
            "attempts": prog["attempts"] if prog else 0,
            "solution": item["solution"] if item and n >= 4 else None}


# ---------------------------------------------------------------------------
# time tracking & client telemetry
# ---------------------------------------------------------------------------
@app.post("/api/learners/{lid}/heartbeat")
def heartbeat(lid: int, body: dict = Body(...)):
    secs = max(0, min(int(body.get("seconds", 0)), 30))
    project, step = str(body.get("project") or "_home")[:60], str(body.get("step") or "-")[:60]
    now = db.now()
    last = db.one("SELECT * FROM learning_sessions WHERE learner_id=? ORDER BY last_seen DESC LIMIT 1", (lid,))
    if last and now - last["last_seen"] < 300:
        db.ex("UPDATE learning_sessions SET last_seen=?, active_seconds=active_seconds+? WHERE id=?", (now, secs, last["id"]))
    else:
        sid = db.ex("INSERT INTO learning_sessions(learner_id, started_at, last_seen, active_seconds) VALUES(?,?,?,?)",
                    (lid, now, now, secs))
        obs.audit(f"learner:{lid}", "session.start", "session", sid)
    if secs:
        db.ex("""INSERT INTO time_log(learner_id, project_id, step_id, day, seconds) VALUES(?,?,?,?,?)
                 ON CONFLICT(learner_id, project_id, step_id, day) DO UPDATE SET seconds=seconds+excluded.seconds""",
              (lid, project, step, dt.date.today().isoformat(), secs))
        if project in BY_ID or project == "_practice":
            _ensure_progress(lid, project, step)
            db.ex("UPDATE step_progress SET seconds=seconds+? WHERE learner_id=? AND project_id=? AND step_id=?",
                  (secs, lid, project, step))
    obs.record("heartbeat")
    return {"ok": True}


CLIENT_EVENTS = {"replay.scrub", "replay.speed", "telemetry.open", "manual.open", "builder.test", "lesson.read"}


@app.post("/api/learners/{lid}/event")
def client_event(lid: int, request: Request, body: dict = Body(...)):
    """Small UI signals worth auditing (how he investigates: scrubbing replays, reading telemetry, opening the manual)."""
    kind = str(body.get("type", ""))
    if kind not in CLIENT_EVENTS:
        raise HTTPException(400, "Unknown event")
    obs.record(f"ui.{kind}")
    obs.audit(f"learner:{lid}", f"ui.{kind}", "step", str(body.get("where", ""))[:80],
              {k: v for k, v in (body.get("details") or {}).items()} if isinstance(body.get("details"), dict) else None, request)
    return {"ok": True}


# ---------------------------------------------------------------------------
# ideas, remixes, reflections
# ---------------------------------------------------------------------------
def _learned(lid):
    return [m["concept"] for m in analytics.concept_mastery(lid) if m["started"]]


@app.post("/api/learners/{lid}/ideas/analyze")
def idea_preview(lid: int, body: dict = Body(...)):
    return analysis.analyze_idea(str(body.get("text", ""))[:2000], _learned(lid))


@app.post("/api/learners/{lid}/ideas")
def add_idea(lid: int, request: Request, body: dict = Body(...)):
    text = str(body.get("text", "")).strip()[:2000]
    if len(text) < 5:
        raise HTTPException(400, "Tell me a bit more about your idea!")
    a = analysis.analyze_idea(text, _learned(lid))
    iid = db.ex("INSERT INTO ideas(learner_id, project_id, ts, text, score, level, analysis) VALUES(?,?,?,?,?,?,?)",
                (lid, body.get("project"), db.now(), text, a["score"], a["level"], json.dumps(a)))
    xp = gamification.award_xp(lid, 5 + a["level"] * 3, f"idea:{iid}")
    obs.audit(f"learner:{lid}", "idea.add", "idea", iid, {"score": a["score"], "level": a["level"], "project": body.get("project")}, request)
    badges = gamification.evaluate_badges(lid, PROJECTS)
    return {"id": iid, "analysis": a, "xp": xp, "badges": badges}


@app.get("/api/learners/{lid}/ideas")
def list_ideas(lid: int):
    return analytics.ideas(lid)


@app.post("/api/learners/{lid}/remix")
async def submit_remix(lid: int, request: Request, body: dict = Body(...)):
    project, code = body["project"], str(body.get("code", ""))[:MAX_CODE]
    if project not in BY_ID:
        raise HTTPException(404, "Unknown project")
    require_open(lid, project, "remix")
    p = BY_ID[project]
    ref = body.get("arena") or f"remix:{project}"
    arena = resolve_arena(lid, ref)
    base = p["steps"][-1]["solution"]
    res = await asyncio.to_thread(run_check, code, """
r = sim()
expect(r.error is None, f"Your remix crashed with {r.error}: {r.error_msg} — fix it and submit again!")
""", arena)
    info = _snapshot(lid, project, "remix", "remix", code)
    base_c = kidast.complexity_score(base)
    if not res["passed"]:
        return {"accepted": False, "message": res["message"], "code": info, "replay": res.get("replay")}
    if code.strip() == base.strip() or info["complexity"] < 5:
        return {"accepted": False, "message": "Add your own twist first — change or add something!", "code": info}
    growth = info["complexity"] - base_c
    xp = max(15, min(80, 20 + growth * 2 + len(info["concepts"]) * 2 + (10 if ref.startswith("custom:") else 0)))
    prev = db.one("SELECT MAX(xp) m FROM remixes WHERE learner_id=? AND project_id=?", (lid, project))
    award = max(0, xp - (prev["m"] or 0))
    rid = db.ex("""INSERT INTO remixes(learner_id, project_id, idea_id, ts, code, complexity, base_complexity, concepts, xp, arena)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (lid, project, body.get("idea_id"), db.now(), code, info["complexity"], base_c, json.dumps(info["concepts"]), award, ref))
    if body.get("idea_id"):
        db.ex("UPDATE ideas SET status='built', built_complexity=? WHERE id=? AND learner_id=?", (info["complexity"], body["idea_id"], lid))
    gamification.award_xp(lid, award, f"remix:{project}")
    obs.audit(f"learner:{lid}", "remix.submit", "project", project,
              {"complexity": info["complexity"], "base": base_c, "xp": award, "arena": ref}, request)
    badges = gamification.evaluate_badges(lid, PROJECTS)
    return {"accepted": True, "id": rid, "xp": award, "complexity": info["complexity"], "base_complexity": base_c,
            "concepts": info["concepts"], "badges": badges,
            "message": "Remix saved! " + ("It's more complex than the original — nice!" if growth > 0 else "Nice twist!")}


@app.post("/api/learners/{lid}/reflection")
def reflection(lid: int, request: Request, body: dict = Body(...)):
    fun, diff = int(body.get("fun", 3)), int(body.get("difficulty", 3))
    db.ex("INSERT INTO reflections(learner_id, project_id, ts, fun, difficulty, note) VALUES(?,?,?,?,?,?)",
          (lid, body.get("project"), db.now(), max(1, min(5, fun)), max(1, min(5, diff)), str(body.get("note", ""))[:500]))
    xp = 0
    if not db.scalar("SELECT COUNT(*) FROM xp_log WHERE learner_id=? AND reason=?", (lid, f"reflect:{body.get('project')}")):
        xp = gamification.award_xp(lid, 10, f"reflect:{body.get('project')}")
    obs.audit(f"learner:{lid}", "reflection.add", "project", body.get("project"), {"fun": fun, "difficulty": diff}, request)
    return {"ok": True, "xp": xp}


# ---------------------------------------------------------------------------
# Drive mode (keyboard teleop): the simulator runs in-process, live
# ---------------------------------------------------------------------------
@app.websocket("/ws/drive")
async def ws_drive(ws: WebSocket):
    await ws.accept()
    lid, sid, world, started = None, None, None, time.time()
    cmd = {"l": 0.0, "r": 0.0, "end": False}

    def finish():
        """Save the session once and award XP/badges. Returns the summary (or None if nothing to save)."""
        nonlocal sid
        if not sid or world is None:
            return None
        this, sid = sid, None
        secs = round(time.time() - started, 1)
        gems = sum(1 for g in world.gems if g["got"] is not None)
        db.ex("UPDATE drive_sessions SET seconds=?, distance=?, crashes=?, gems=? WHERE id=?",
              (secs, round(world.st["distance"], 1), world.st["crashes"], gems, this))
        obs.audit(f"learner:{lid}", "drive.end", "drive_session", this,
                  {"seconds": secs, "distance": round(world.st["distance"], 1), "crashes": world.st["crashes"], "gems": gems})
        xp = 0
        if secs >= 60 and not db.scalar("SELECT COUNT(*) FROM xp_log WHERE learner_id=? AND reason=?",
                                        (lid, f"drive:{dt.date.today()}")):
            xp = gamification.award_xp(lid, 10, f"drive:{dt.date.today()}")
        new = gamification.evaluate_badges(lid, PROJECTS)
        total_secs = db.scalar("SELECT SUM(seconds) FROM drive_sessions WHERE learner_id=?", (lid,))
        return {"seconds": secs, "distance": round(world.st["distance"], 1), "crashes": world.st["crashes"], "gems": gems,
                "gems_total": len(world.gems), "laps": world.st["laps"], "xp": xp, "new_badges": new,
                "badges_earned": db.scalar("SELECT COUNT(*) FROM badges WHERE learner_id=?", (lid,)),
                "badges_total": len(gamification.BADGES), "drive_minutes_total": round(total_secs / 60, 1)}
    try:
        msg = await ws.receive_json()
        lid = int(msg["learner"])
        _learner(lid)
        ref = str(msg.get("arena") or "sandbox:open_lab")
        spec = resolve_arena(lid, ref)
        if spec.get("type") == "arm":
            await ws.send_json({"t": "error", "msg": "Drive mode is for wheeled robots. Pick a driving arena!"})
            return
        spec["time_limit"] = 600
        spec["gripper"] = True
        world = robosim.World(spec, seed=int(time.time()) % 100000)
        for ch in ("distance_front", "distance_left", "distance_right", "floor_left", "floor_center", "floor_right",
                   "light_left", "light_right", "heading", "encoder_left", "encoder_right", "bumper"):
            world.use(ch)
        sid = db.ex("INSERT INTO drive_sessions(learner_id, arena, started_at, seconds, distance, crashes, gems, gems_total) VALUES(?,?,?,?,?,?,?,?)",
                    (lid, ref, started, 0, 0, 0, 0, len(world.gems)))
        obs.record("teleop.session")
        obs.audit(f"learner:{lid}", "drive.start", "arena", ref)
        await ws.send_json({"t": "arena", "arena": robosim.public(world.a)})

        async def reader():
            while True:
                m = await ws.receive_json()
                if m.get("type") == "cmd":
                    cmd["l"] = max(-100.0, min(100.0, float(m.get("l", 0))))
                    cmd["r"] = max(-100.0, min(100.0, float(m.get("r", 0))))
                elif m.get("type") == "end":
                    cmd["end"] = True
                    return
                elif m.get("type") == "action":
                    a = m.get("a")
                    rb = robosim.Robot(world)
                    if a == "grab":
                        rb.grab() if world.held is None else rb.release()
                    elif a == "pen":
                        rb.pen_up() if world.pen else rb.pen_down(str(m.get("color", "black")))
                    elif a == "beep":
                        rb.beep(880)
                    elif a == "reset":
                        world.x, world.y = float(world.a["start"][0]), float(world.a["start"][1])
                        world.th = robosim.math.radians(world.a["start"][2])

        rtask = asyncio.create_task(reader())
        sent_events = 0
        try:
            while not rtask.done() and not cmd["end"]:
                t0 = time.perf_counter()
                world.pl, world.pr = cmd["l"], cmd["r"]
                try:
                    world.tick()
                    world.tick()
                except robosim.TimeUp:
                    break
                ms = (time.perf_counter() - t0) * 1000
                obs.record("teleop.tick_ms", ms)
                ev = world.events[sent_events:]
                sent_events = len(world.events)
                await ws.send_json({"t": "state", "time": round(world.t, 2), "x": round(world.x, 2), "y": round(world.y, 2),
                                    "h": round(robosim.math.degrees(world.th), 1), "pl": world.pl, "pr": world.pr,
                                    "pen": world.pen, "held": world.held,
                                    "sensors": {ch: world.CHANNELS[ch](world) for ch in world.used},
                                    "color": world.color_at(), "camera": world.camera(),
                                    "blocks": [[round(b["x"], 1), round(b["y"], 1)] for b in world.blocks],
                                    "events": ev, "summary": {"crashes": world.st["crashes"], "distance": round(world.st["distance"], 1),
                                                              "gems": sum(1 for g in world.gems if g["got"] is not None),
                                                              "gems_total": len(world.gems), "laps": world.st["laps"]}})
                await asyncio.sleep(max(0.0, 0.04 - (time.perf_counter() - t0)))
        finally:
            rtask.cancel()
        if cmd["end"]:
            summary = finish()
            if summary:
                await ws.send_json({"t": "summary", **summary})
    except WebSocketDisconnect:
        pass
    except HTTPException as e:
        try:
            await ws.send_json({"t": "error", "msg": e.detail})
        except Exception:  # noqa: BLE001
            pass
    except Exception as e:  # noqa: BLE001
        obs.app_error("ws_drive", e)
    finally:
        finish()                       # leaving the page without "End drive" still saves the session
        try:
            await ws.close()
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# parent: analytics, audit, monitoring, data
# ---------------------------------------------------------------------------
@app.get("/api/parent/report/{lid}")
def parent_report(lid: int, request: Request, _=Depends(parent_required)):
    _learner(lid)
    obs.audit("parent", "report.view", "learner", lid, request=request)
    return analytics.full_report(lid)


@app.get("/api/parent/report/{lid}/export.{fmt}")
def parent_report_export(lid: int, fmt: str, request: Request, _=Depends(parent_required)):
    """Downloadable report: a printable HTML page, or the full analytics as JSON (both include badge progress)."""
    if fmt not in ("html", "json"):
        raise HTTPException(404)
    learner = _learner(lid)
    r = analytics.full_report(lid)
    r["badge_progress"] = report.badge_progress(r["badges"])
    obs.audit("parent", "report.export", "learner", lid, {"format": fmt}, request)
    name = f"roboquest-report-{learner['name'].lower().replace(' ', '-')}-{dt.date.today()}.{fmt}"
    if fmt == "json":
        return Response(json.dumps(r, default=str, indent=1), media_type="application/json",
                        headers={"Content-Disposition": f"attachment; filename={name}"})
    return Response(report.render(r), media_type="text/html",
                    headers={"Content-Disposition": f"inline; filename={name}"})


# ---------------------------------------------------------------------------
# weekly email
# ---------------------------------------------------------------------------
@app.get("/api/parent/email")
def parent_email_settings(_=Depends(parent_required)):
    return digest.public_settings()


@app.post("/api/parent/email")
def parent_email_save(request: Request, body: dict = Body(...), _=Depends(parent_required)):
    before = digest.redacted(digest.settings())
    after = digest.redacted(digest.save_settings(body))
    obs.audit("parent", "email.settings", details={"before": before, "after": after}, request=request)
    return digest.public_settings()


@app.get("/api/parent/email/preview/{lid}")
def parent_email_preview(lid: int, _=Depends(parent_required)):
    _learner(lid)
    d = digest.build(lid)
    return Response(d["html"], media_type="text/html")


@app.post("/api/parent/email/test/{lid}")
async def parent_email_test(lid: int, request: Request, _=Depends(parent_required)):
    _learner(lid)
    try:
        return await asyncio.to_thread(digest.send_digest, lid, "test", "parent", request)
    except digest.EmailError as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/parent/timeline/{lid}")
def parent_timeline(lid: int, limit: int = 300, _=Depends(parent_required)):
    return obs.audit_query(actor=f"learner:{lid}", limit=min(limit, 1000))


@app.get("/api/parent/code/{lid}")
def parent_code_history(lid: int, project: str, step: str, _=Depends(parent_required)):
    rows = db.q("""SELECT id, ts, kind, lines, complexity, concepts, code FROM snapshots
                   WHERE learner_id=? AND project_id=? AND step_id=? ORDER BY ts""", (lid, project, step))
    item = _item(project, step)
    return {"snapshots": rows, "reference": item["solution"] if item else None}


@app.post("/api/parent/replay/{lid}")
async def parent_replay(lid: int, request: Request, body: dict = Body(...), _=Depends(parent_required)):
    """Re-run one of his saved code versions so the parent can watch it."""
    snap = db.one("SELECT * FROM snapshots WHERE id=? AND learner_id=?", (int(body["snapshot"]), lid))
    if not snap:
        raise HTTPException(404)
    ref = (f"practice:{snap['step_id']}" if snap["project_id"] == "_practice" else
           f"remix:{snap['project_id']}" if snap["step_id"] == "remix" else
           "sandbox:open_lab" if snap["project_id"] == "_playground" else f"step:{snap['project_id']}/{snap['step_id']}")
    res = _decorate_error(await asyncio.to_thread(run_sim, snap["code"], resolve_arena(lid, ref)))
    obs.audit("parent", "replay.view", "snapshot", snap["id"], request=request)
    return res


@app.get("/api/parent/solution/{project}/{step}")
def parent_solution(project: str, step: str, request: Request, _=Depends(parent_required)):
    item = _item(project, step)
    if not item:
        raise HTTPException(404)
    obs.audit("parent", "solution.view", "step", f"{project}/{step}", request=request)
    return {"solution": item["solution"], "hints": item.get("hints", [])}


@app.get("/api/parent/audit")
def parent_audit(request: Request, actor: str = None, action: str = None, entity: str = None, since: float = None,
                 until: float = None, text: str = None, limit: int = 200, offset: int = 0, _=Depends(parent_required)):
    return obs.audit_query(actor, action, entity, since, until, text, min(limit, 1000), offset)


@app.get("/api/parent/audit/verify")
def parent_audit_verify(request: Request, _=Depends(parent_required)):
    r = obs.verify_audit_chain()
    obs.audit("parent", "audit.verify", details=r, request=request)
    return r


@app.get("/api/parent/monitoring")
def parent_monitoring(hours: int = 24, _=Depends(parent_required)):
    snap = obs.snapshot(max(1, min(hours, 24 * 30)))
    snap["active_now"] = dict(_active)
    return snap


@app.get("/api/parent/errors/{eid}")
def parent_error_detail(eid: int, _=Depends(parent_required)):
    return db.one("SELECT * FROM app_errors WHERE id=?", (eid,))


@app.get("/api/parent/data")
def parent_data(_=Depends(parent_required)):
    return obs.data_overview()


@app.get("/api/parent/data/{table}")
def parent_table(table: str, request: Request, limit: int = 50, offset: int = 0, learner: int = None, _=Depends(parent_required)):
    if table not in db.TABLES:
        raise HTTPException(404)
    cols = [r["name"] for r in db.q(f"PRAGMA table_info({table})")]
    where, args = "", []
    if learner is not None and "learner_id" in cols:
        where, args = "WHERE learner_id=?", [learner]
    order = "ts DESC" if "ts" in cols else "rowid DESC"
    rows = db.q(f"SELECT * FROM {table} {where} ORDER BY {order} LIMIT ? OFFSET ?", (*args, min(limit, 500), offset))
    if table == "settings":
        rows = [{"key": r["key"], "value": "•••" if r["key"] == "parent_pin"
                 else json.dumps(digest.redacted(json.loads(r["value"]))) if r["key"] == "email" else r["value"]} for r in rows]
    return {"columns": cols, "rows": rows, "total": db.scalar(f"SELECT COUNT(*) FROM {table} {where}", args)}


@app.get("/api/parent/export/{table}.{fmt}")
def parent_export(table: str, fmt: str, request: Request, _=Depends(parent_required)):
    if table not in db.TABLES or table == "settings" or fmt not in ("csv", "json"):
        raise HTTPException(404)
    rows = db.q(f"SELECT * FROM {table}")
    obs.audit("parent", "data.export", "table", table, {"format": fmt, "rows": len(rows)}, request)
    if fmt == "json":
        return Response(json.dumps(rows, default=str, indent=1), media_type="application/json",
                        headers={"Content-Disposition": f"attachment; filename={table}.json"})
    buf = io.StringIO()
    if rows:
        w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={table}.csv"})


@app.get("/api/parent/backup")
def parent_backup(request: Request, _=Depends(parent_required)):
    path = os.path.join(tempfile.gettempdir(), f"roboquest-backup-{int(time.time())}.db")
    dst = sqlite3.connect(path)
    db.conn().backup(dst)
    dst.close()
    obs.audit("parent", "data.backup", details={"bytes": os.path.getsize(path)}, request=request)
    return FileResponse(path, filename=f"roboquest-backup-{dt.date.today()}.db", media_type="application/octet-stream")


@app.delete("/api/parent/learners/{lid}")
def parent_delete_learner(lid: int, request: Request, _=Depends(parent_required)):
    learner = _learner(lid)
    counts = {}
    with db.tx() as c:
        for t in db.LEARNER_TABLES + ["tutor_messages"]:
            counts[t] = c.execute(f"DELETE FROM {t} WHERE learner_id=?", (lid,)).rowcount
        c.execute("DELETE FROM learners WHERE id=?", (lid,))
    obs.audit("parent", "learner.delete", "learner", lid, {"name": learner["name"], "rows_deleted": counts}, request)
    return {"ok": True, "rows_deleted": counts}


@app.post("/api/parent/retention")
def parent_retention(request: Request, body: dict = Body(...), _=Depends(parent_required)):
    """Prune bulky telemetry older than N days (run snapshots, metrics). Learning records and the audit log are kept."""
    days = max(7, int(body.get("days", 90)))
    cutoff = time.time() - days * 86400
    with db.tx() as c:
        s = c.execute("DELETE FROM snapshots WHERE ts < ? AND kind IN ('run','playground')", (cutoff,)).rowcount
        m = c.execute("DELETE FROM metrics_minute WHERE minute < ?", (int(cutoff // 60),)).rowcount
    obs.audit("parent", "data.retention", details={"days": days, "snapshots_deleted": s, "metrics_deleted": m}, request=request)
    return {"snapshots_deleted": s, "metrics_deleted": m}


# ---------------------------------------------------------------------------
# AI tutor (Sprocket)
# ---------------------------------------------------------------------------
def _tutor_target(project, step):
    item = _item(project, step)
    title = BY_ID[project]["title"] if project in BY_ID else {"_practice": "Side quest", "_playground": "Playground"}.get(project, project)
    return item, title


def _tutor_reply(fn):
    try:
        return {"ok": True, **fn()}
    except tutor.TutorError as e:
        return {"ok": False, "error": str(e), "status": e.status}


@app.get("/api/tutor/status")
def tutor_status(learner: int = None):
    return tutor.status(learner)


@app.get("/api/learners/{lid}/tutor/history")
def tutor_history(lid: int, project: str, step: str):
    return tutor.history(lid, project, step)


@app.post("/api/learners/{lid}/tutor/chat")
async def tutor_chat(lid: int, body: dict = Body(...)):
    _learner(lid)
    project, step = body["project"], body["step"]
    require_open(lid, project, step)
    item, title = _tutor_target(project, step)
    kind = "error" if body.get("kind") == "error" else "chat"
    return await asyncio.to_thread(_tutor_reply, lambda: tutor.chat(
        lid, project, step, body.get("question", ""), str(body.get("code", ""))[:20000], body.get("run"), item, title, kind))


@app.post("/api/learners/{lid}/tutor/review")
async def tutor_review(lid: int, body: dict = Body(...)):
    _learner(lid)
    project, step = body["project"], body["step"]
    item, title = _tutor_target(project, step)
    return await asyncio.to_thread(_tutor_reply, lambda: tutor.review(
        lid, project, step, str(body.get("code", ""))[:20000], body.get("run"), item, title))


@app.get("/api/parent/tutor/{lid}")
def parent_tutor(lid: int, _=Depends(parent_required)):
    return {"status": tutor.status(lid), "stats": tutor.stats(lid), "transcripts": tutor.transcripts(lid)}


@app.post("/api/parent/tutor/settings")
def parent_tutor_settings(request: Request, body: dict = Body(...), _=Depends(parent_required)):
    before = tutor.settings()
    after = tutor.save_settings(body)
    obs.audit("parent", "tutor.settings", details={"before": before, "after": after}, request=request)
    return tutor.status()


@app.post("/api/parent/tutor/test")
async def parent_tutor_test(request: Request, _=Depends(parent_required)):
    if not tutor.status()["configured"]:
        return {"ok": False, "error": "No Anthropic credentials found. Set ANTHROPIC_API_KEY before starting RoboQuest."}
    res = await asyncio.to_thread(_tutor_reply, tutor.test_connection)
    obs.audit("parent", "tutor.test", details={"ok": res.get("ok"), "error": res.get("error")}, request=request)
    return res


@app.get("/api/health")
def health():
    try:
        db.scalar("SELECT 1")
        ok = True
    except Exception:  # noqa: BLE001
        ok = False
    return {"status": "ok" if ok else "degraded", "uptime_sec": round(time.time() - obs.STARTED),
            "projects": len(PROJECTS), "practice": len(PRACTICE), "active": dict(_active)}


@app.on_event("startup")
async def _startup():
    app.state.email_task = asyncio.create_task(digest.scheduler_loop())


@app.on_event("shutdown")
def _shutdown():
    obs.flush()
    obs.audit("system", "server.stop")


# ---------------------------------------------------------------------------
# static front-end
# ---------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"), headers={"Cache-Control": "no-cache"})
