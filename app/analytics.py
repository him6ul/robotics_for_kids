"""Learning analytics: progress, time, concept mastery, learning style, trends and the adaptive guide path."""
import datetime as dt
import json
from collections import Counter, defaultdict

from . import db, gamification
from .analysis import GENERIC, monster
from .curriculum import PRACTICE, PROJECTS
from .sandbox import kidast

DAY = 86400


def _progress(learner_id):
    return {(r["project_id"], r["step_id"]): r
            for r in db.q("SELECT * FROM step_progress WHERE learner_id=?", (learner_id,))}


def project_status(learner_id, prog=None):
    """Per-project progress, unlock state and time vs. expectation."""
    prog = prog or _progress(learner_id)
    out, unlocked = [], True
    for p in PROJECTS:
        core = p["steps"]
        rows = [prog.get((p["id"], s["id"])) for s in core]
        done = [r for r in rows if r and r["status"] == "done"]
        boss = prog.get((p["id"], "boss"))
        secs = sum(r["seconds"] for r in prog.values() if r and r["project_id"] == p["id"])
        complete = len(done) == len(core)
        reflection = db.one("SELECT fun, difficulty FROM reflections WHERE learner_id=? AND project_id=? ORDER BY ts DESC LIMIT 1",
                            (learner_id, p["id"]))
        out.append({
            "id": p["id"], "week": p["week"], "order": p["order"], "title": p["title"], "emoji": p["emoji"],
            "steps_total": len(core), "steps_done": len(done), "complete": complete, "unlocked": unlocked,
            "boss_done": bool(boss and boss["status"] == "done"),
            "remixed": bool(db.scalar("SELECT COUNT(*) FROM remixes WHERE learner_id=? AND project_id=?",
                                      (learner_id, p["id"]))),
            "seconds": secs, "expected_seconds": p["expected_minutes"] * 60,
            "attempts": sum(r["attempts"] for r in done), "hints": sum(r["hints_used"] for r in rows if r),
            "runs": sum(r["runs"] for r in rows if r), "errors": sum(r["errors"] for r in rows if r),
            "crashes": sum(r["crashes"] for r in rows if r),
            "first_try": sum(r["first_try"] for r in done),
            "started_at": min((r["started_at"] for r in rows if r and r["started_at"]), default=None),
            "completed_at": max((r["completed_at"] for r in done), default=None) if complete else None,
            "fun": reflection["fun"] if reflection else None,
            "difficulty": reflection["difficulty"] if reflection else None,
        })
        unlocked = unlocked and complete
    return out


def current_position(learner_id, statuses=None, prog=None):
    prog = prog or _progress(learner_id)
    statuses = statuses or project_status(learner_id, prog)
    for ps in statuses:
        if not ps["complete"]:
            p = next(x for x in PROJECTS if x["id"] == ps["id"])
            for s in p["steps"]:
                r = prog.get((p["id"], s["id"]))
                if not r or r["status"] != "done":
                    return {"project": p["id"], "step": s["id"], "project_title": p["title"], "step_title": s["title"],
                            "week": p["week"]}
    return None


def schedule(learner_id, statuses=None):
    learner = db.one("SELECT * FROM learners WHERE id=?", (learner_id,))
    start = dt.date.fromisoformat(learner["start_date"])
    days_in = (dt.date.today() - start).days
    cal_week = max(1, min(6, days_in // 7 + 1))
    statuses = statuses or project_status(learner_id)
    done_steps = sum(p["steps_done"] for p in statuses)
    total_steps = sum(p["steps_total"] for p in statuses)
    expected_frac = min(1.0, max(0.0, (days_in + 1) / 42))
    actual_frac = done_steps / total_steps if total_steps else 0
    active_days = max(1, len(gamification.active_days(learner_id)))
    finish = None
    if done_steps and days_in > 0:
        rate = done_steps / (days_in + 1)
        finish = (dt.date.today() + dt.timedelta(days=round((total_steps - done_steps) / rate))).isoformat()
    delta = actual_frac - expected_frac
    status = "ahead" if delta > 0.08 else "behind" if delta < -0.12 else "on track"
    return {"start_date": learner["start_date"], "days_in": days_in, "calendar_week": cal_week,
            "expected_pct": round(expected_frac * 100), "actual_pct": round(actual_frac * 100),
            "status": status, "projected_finish": finish, "active_days": active_days,
            "planned_finish": (start + dt.timedelta(days=41)).isoformat()}


# ---------------------------------------------------------------------------
# Concept mastery
# ---------------------------------------------------------------------------
def concept_mastery(learner_id, prog=None):
    prog = prog or _progress(learner_id)
    evidence = defaultdict(lambda: {"steps": 0, "done": 0, "quality": [], "independent": 0, "practice": 0,
                                    "practice_total": 0, "errors": 0})
    for p in PROJECTS:
        per_step = p["expected_minutes"] * 60 / max(1, len(p["steps"]))
        for s in p["steps"] + ([p["boss"]] if p.get("boss") else []):
            for c in s.get("concepts", []):
                e = evidence[c]
                if s["id"] != "boss":
                    e["steps"] += 1
                r = prog.get((p["id"], s["id"]))
                if r:
                    e["errors"] += r["errors"]
                if r and r["status"] == "done":
                    if s["id"] != "boss":
                        e["done"] += 1
                    qual = 1.0 - 0.15 * min(r["hints_used"], 3) - 0.06 * min(max(r["attempts"] - 1, 0), 5)
                    if r["seconds"] > per_step * 2.5:
                        qual -= 0.1
                    if s["id"] == "boss":
                        qual += 0.2
                    e["quality"].append(max(0.2, min(1.2, qual)))
    for pr in PRACTICE:
        e = evidence[pr["concept"]]
        e["practice_total"] += 1
        r = prog.get(("_practice", pr["id"]))
        if r and r["status"] == "done":
            e["practice"] += 1
    # independent use: concepts appearing in playground / remix / capstone code
    for row in db.q("""SELECT concepts FROM snapshots WHERE learner_id=? AND kind IN ('playground','remix')""",
                    (learner_id,)):
        for c in json.loads(row["concepts"] or "[]"):
            evidence[c]["independent"] += 1
    from . import tutor
    asked = tutor.concept_questions(learner_id)
    out = []
    for c in kidast.CONCEPTS:
        e = evidence[c]
        base = e["done"] / e["steps"] if e["steps"] else 0
        quality = sum(e["quality"]) / len(e["quality"]) if e["quality"] else 0
        indep = min(e["independent"] / 3, 1)
        practice = min(e["practice"] / 2, 1)
        score = min(1.0, 0.65 * base * min(quality, 1.0) + 0.2 * indep + 0.15 * practice
                    + (0.1 if quality > 1 else 0))
        started = e["done"] > 0 or e["independent"] > 0 or e["practice"] > 0
        label = ("not started" if not started else "learning" if score < 0.35 else
                 "getting it" if score < 0.6 else "strong" if score < 0.85 else "mastered")
        out.append({"concept": c, "label": kidast.CONCEPT_LABELS[c], "score": round(score, 2),
                    "status": label, "started": started, "steps_done": e["done"], "steps_total": e["steps"],
                    "independent_uses": e["independent"], "practice_done": e["practice"],
                    "avg_quality": round(quality, 2), "errors": e["errors"], "tutor_questions": asked.get(c, 0)})
    return out


# ---------------------------------------------------------------------------
# Learning style
# ---------------------------------------------------------------------------
def learning_style(learner_id, prog=None):
    prog = prog or _progress(learner_id)
    L = (learner_id,)
    done = [r for r in prog.values() if r["status"] == "done"]
    n_checks = db.scalar("SELECT COUNT(*) FROM checks WHERE learner_id=?", L)
    n_runs = db.scalar("SELECT COUNT(*) FROM runs WHERE learner_id=? AND mode IN ('step','practice')", L)
    first_try = sum(r["first_try"] for r in done) / len(done) if done else 0
    hints_per_step = sum(r["hints_used"] for r in done) / len(done) if done else 0
    tutor_q = db.scalar("SELECT COUNT(*) FROM tutor_messages WHERE learner_id=? AND role='kid' AND kind IN ('chat','error')", L)
    tutor_per_step = tutor_q / len(done) if done else 0
    runs_per_check = n_runs / n_checks if n_checks else 0

    # persistence: steps with a failed check that were eventually passed
    failed_steps = db.q("SELECT DISTINCT project_id, step_id FROM checks WHERE learner_id=? AND passed=0", L)
    recovered = sum(1 for f in failed_steps if (prog.get((f["project_id"], f["step_id"])) or {}).get("status") == "done")
    persistence = recovered / len(failed_steps) if failed_steps else (1.0 if done else 0)

    # error recovery time: from a crash to the next clean run on the same step
    runs = db.q("SELECT project_id, step_id, ts, ok FROM runs WHERE learner_id=? ORDER BY ts", L)
    pending, recov = {}, []
    for r in runs:
        k = (r["project_id"], r["step_id"])
        if not r["ok"]:
            pending.setdefault(k, r["ts"])
        elif k in pending:
            recov.append(r["ts"] - pending.pop(k))
    recov = [x for x in recov if x < 1800]
    avg_recovery = sum(recov) / len(recov) if recov else None

    # pace vs expected on finished projects
    statuses = project_status(learner_id, prog)
    fin = [p for p in statuses if p["complete"] and p["seconds"]]
    pace = sum(p["seconds"] for p in fin) / sum(p["expected_seconds"] for p in fin) if fin else None

    # creativity: remixes, ideas, playground, going beyond the reference solution
    remixes = db.scalar("SELECT COUNT(*) FROM remixes WHERE learner_id=?", L)
    ideas = db.q("SELECT score FROM ideas WHERE learner_id=?", L)
    playground = db.scalar("SELECT COUNT(*) FROM runs WHERE learner_id=? AND mode='playground'", L)
    beyond = []
    by_id = {p["id"]: p for p in PROJECTS}
    for (pid, sid), r in prog.items():
        if r["status"] != "done" or pid not in by_id:
            continue
        snap = db.one("""SELECT complexity FROM snapshots WHERE learner_id=? AND project_id=? AND step_id=? AND kind='check'
                         ORDER BY ts DESC LIMIT 1""", (learner_id, pid, sid))
        try:
            ref = kidast.complexity_score(next(s for s in by_id[pid]["steps"] + [by_id[pid]["boss"]] if s["id"] == sid)["solution"])
        except StopIteration:
            continue
        if snap and ref:
            beyond.append(snap["complexity"] / ref)
    beyond_ratio = sum(beyond) / len(beyond) if beyond else None
    creativity = min(1.0, remixes * 0.15 + len(ideas) * 0.08 + min(playground, 20) * 0.02
                     + (max(0, beyond_ratio - 1) * 0.6 if beyond_ratio else 0)
                     + (sum(i["score"] for i in ideas) / len(ideas) / 200 if ideas else 0))

    exp = experiment_patterns(learner_id)
    traits = {
        "Precision": round(first_try, 2),
        "Independence": round(max(0.0, 1 - (hints_per_step + 0.5 * tutor_per_step) / 3), 2) if done else 0,
        "Persistence": round(persistence, 2),
        "Experimenting": round(min(runs_per_check / 6, 1), 2),
        "Creativity": round(creativity, 2),
        "Speed": round(max(0.0, min(1.0, 1.5 - pace)), 2) if pace else 0,
        "Tuning": round(min(1.0, exp["tune_ratio"] * 2), 2) if exp["edits"] else 0,
        "Safety": round(robot_stats(learner_id)["safety"], 2),
    }
    if not done:
        persona = ("New Explorer", "🌱", "Just getting started — the robot adventure begins!")
    elif traits["Tuning"] >= 0.6 and traits["Experimenting"] >= 0.4:
        persona = ("Tuner", "🎚️", "Loves tweaking numbers and watching what changes — exactly how real engineers tune robots. Encourage predicting the result before each run.")
    elif traits["Experimenting"] > 0.6 and traits["Precision"] < 0.5:
        persona = ("Tinkerer", "🔧", "Learns by trying things and running the robot a lot. Great instinct — watching the replay closely will make it even faster.")
    elif traits["Precision"] >= 0.6 and traits["Experimenting"] < 0.4:
        persona = ("Planner", "📐", "Thinks first and often gets it right the first time. Encourage more experimenting — breaking things is how you discover things.")
    elif traits["Creativity"] >= 0.6:
        persona = ("Inventor", "💡", "Loves adding own twists and ideas. Keep feeding that with remix challenges.")
    elif traits["Persistence"] >= 0.8 and traits["Independence"] < 0.5:
        persona = ("Determined Climber", "🧗", "Doesn't give up, and uses hints as a ladder. Try waiting a minute before opening a hint.")
    else:
        persona = ("All-Rounder", "⭐", "A balanced learner — steady progress across the board.")
    return {
        "traits": traits,
        "persona": {"name": persona[0], "emoji": persona[1], "desc": persona[2]},
        "raw": {"first_try_rate": round(first_try, 2), "hints_per_step": round(hints_per_step, 2),
                "runs_per_check": round(runs_per_check, 2), "persistence": round(persistence, 2),
                "avg_error_recovery_sec": round(avg_recovery) if avg_recovery else None,
                "pace_ratio": round(pace, 2) if pace else None,
                "beyond_reference_ratio": round(beyond_ratio, 2) if beyond_ratio else None,
                "remixes": remixes, "ideas": len(ideas), "playground_runs": playground,
                "tutor_questions": tutor_q, "tutor_per_step": round(tutor_per_step, 2),
                "tune_edits": exp["tune"], "small_edits": exp["small"], "rewrites": exp["rewrite"],
                "tune_ratio": exp["tune_ratio"]},
        "experiments": exp,
    }


# ---------------------------------------------------------------------------
# Time, activity, errors, ideas, code growth
# ---------------------------------------------------------------------------
def experiment_patterns(learner_id):
    """How he changes code between runs: tweaking numbers (tuning), small edits, or big rewrites."""
    import difflib
    import re
    rows = db.q("""SELECT project_id, step_id, code FROM snapshots WHERE learner_id=? AND kind IN ('run','check','playground','remix')
                   ORDER BY project_id, step_id, ts""", (learner_id,))
    tune = small = rewrite = same = 0
    per_step = defaultdict(lambda: [0, 0, 0])
    num = re.compile(r"-?\d+(?:\.\d+)?")
    prev = {}
    for r in rows:
        k = (r["project_id"], r["step_id"])
        code = r["code"] or ""
        if k in prev:
            a = prev[k]
            if a == code:
                same += 1
            elif num.sub("#", a) == num.sub("#", code):
                tune += 1
                per_step[k][0] += 1
            else:
                ratio = difflib.SequenceMatcher(None, a.splitlines(), code.splitlines()).ratio()
                if ratio >= 0.6:
                    small += 1
                    per_step[k][1] += 1
                else:
                    rewrite += 1
                    per_step[k][2] += 1
        prev[k] = code
    edits = tune + small + rewrite
    top = sorted(per_step.items(), key=lambda kv: -kv[1][0])[:5]
    return {"tune": tune, "small": small, "rewrite": rewrite, "reruns_unchanged": same, "edits": edits,
            "tune_ratio": round(tune / edits, 2) if edits else 0.0,
            "most_tuned": [{"project_id": k[0], "step_id": k[1], "tunes": v[0]} for k, v in top if v[0]]}


def robot_stats(learner_id):
    """Robot-specific signals: distance, crashes, sensors used, drive mode, and whether he's getting safer."""
    L = (learner_id,)
    runs = db.q("SELECT ts, distance, crashes, gems, sim_time, sensors, mode FROM runs WHERE learner_id=? ORDER BY ts", L)
    drives = db.one("""SELECT COUNT(*) n, COALESCE(SUM(seconds),0) s, COALESCE(SUM(distance),0) d,
                       COALESCE(SUM(crashes),0) c, COALESCE(SUM(gems),0) g FROM drive_sessions WHERE learner_id=?""", L)
    sensors = Counter()
    first_seen = {}
    for r in runs:
        for ch in json.loads(r["sensors"] or "[]"):
            kind = ch.split("_")[0]
            sensors[kind] += 1
            first_seen.setdefault(kind, r["ts"])
    n = len(runs)
    half = n // 2
    def rate(rs):
        return round(sum(1 for r in rs if (r["crashes"] or 0) > 0) / len(rs), 2) if rs else None
    early, late = rate(runs[:half]) if half >= 5 else None, rate(runs[half:]) if half >= 5 else None
    crash_rate = rate(runs) or 0.0
    weekly = defaultdict(lambda: {"runs": 0, "crash_runs": 0, "distance": 0.0})
    learner = db.one("SELECT start_date FROM learners WHERE id=?", L)
    start = dt.datetime.fromisoformat(learner["start_date"]).timestamp() if learner else 0
    for r in runs:
        w = max(1, int((r["ts"] - start) // (7 * DAY)) + 1)
        weekly[w]["runs"] += 1
        weekly[w]["crash_runs"] += 1 if (r["crashes"] or 0) > 0 else 0
        weekly[w]["distance"] += r["distance"] or 0
    return {
        "runs": n, "distance_m": round(sum(r["distance"] or 0 for r in runs) / 100, 1),
        "robot_seconds": round(sum(r["sim_time"] or 0 for r in runs)),
        "gems": sum(r["gems"] or 0 for r in runs), "crashes": sum(r["crashes"] or 0 for r in runs),
        "crash_run_rate": crash_rate, "crash_rate_early": early, "crash_rate_late": late,
        "safety": 1 - crash_rate if n else 0.0,
        "sensors": dict(sensors.most_common()), "sensor_kinds": len(sensors),
        "sensor_timeline": sorted([{"sensor": k, "first": v} for k, v in first_seen.items()], key=lambda x: x["first"]),
        "drive": {"sessions": drives["n"], "minutes": round(drives["s"] / 60, 1), "distance_m": round(drives["d"] / 100, 1),
                  "crashes": drives["c"], "gems": drives["g"]},
        "arenas_built": db.scalar("SELECT COUNT(*) FROM arenas WHERE learner_id=?", L),
        "arena_complexity": [r["complexity"] for r in db.q("SELECT complexity FROM arenas WHERE learner_id=? ORDER BY created_at", L)],
        "weekly": [{"week": w, **v, "distance": round(v["distance"] / 100, 1)} for w, v in sorted(weekly.items())],
    }


def activity(learner_id, days=42):
    L = (learner_id,)
    since = (dt.date.today() - dt.timedelta(days=days - 1)).isoformat()
    per_day = {r["day"]: r["s"] for r in db.q(
        "SELECT day, SUM(seconds) s FROM time_log WHERE learner_id=? AND day>=? GROUP BY day", (learner_id, since))}
    daily = []
    for i in range(days):
        d = (dt.date.today() - dt.timedelta(days=days - 1 - i)).isoformat()
        daily.append({"day": d, "minutes": round(per_day.get(d, 0) / 60, 1)})
    sessions = db.q("SELECT * FROM learning_sessions WHERE learner_id=? ORDER BY started_at", L)
    hours = Counter()
    for s in sessions:
        hours[dt.datetime.fromtimestamp(s["started_at"]).hour] += round(s["active_seconds"] / 60)
    by_mode = db.q("""SELECT CASE WHEN project_id LIKE '\\_%' ESCAPE '\\' THEN project_id ELSE 'projects' END m,
                      SUM(seconds) s FROM time_log WHERE learner_id=? GROUP BY m""", L)
    total = db.scalar("SELECT SUM(seconds) FROM time_log WHERE learner_id=?", L)
    return {
        "daily": daily,
        "total_minutes": round(total / 60),
        "sessions": len(sessions),
        "avg_session_minutes": round(sum(s["active_seconds"] for s in sessions) / len(sessions) / 60, 1) if sessions else 0,
        "longest_session_minutes": round(max((s["active_seconds"] for s in sessions), default=0) / 60, 1),
        "by_hour": [{"hour": h, "minutes": hours.get(h, 0)} for h in range(24)],
        "by_mode": {r["m"]: round(r["s"] / 60) for r in by_mode},
        "streak": gamification.streak(learner_id),
    }


def errors(learner_id):
    L = (learner_id,)
    rows = db.q("SELECT error_type, ts, project_id, step_id FROM runs WHERE learner_id=? AND ok=0 AND error_type IS NOT NULL", L)
    by_type = Counter(r["error_type"] for r in rows)
    week_ago = db.now() - 7 * DAY
    recent = Counter(r["error_type"] for r in rows if r["ts"] >= week_ago)
    defeated = {r["error_type"] for r in db.q(
        """SELECT DISTINCT r.error_type FROM runs r WHERE r.learner_id=? AND r.ok=0 AND r.error_type IS NOT NULL
           AND EXISTS (SELECT 1 FROM runs r2 WHERE r2.learner_id=r.learner_id AND r2.project_id=r.project_id
           AND r2.step_id=r.step_id AND r2.ts>r.ts AND r2.ok=1)""", L)}
    learner = db.one("SELECT start_date FROM learners WHERE id=?", L)
    start = dt.datetime.fromisoformat(learner["start_date"]).timestamp()
    weekly = defaultdict(Counter)
    for r in rows:
        weekly[max(1, int((r["ts"] - start) // (7 * DAY)) + 1)][r["error_type"]] += 1
    runs_total = db.scalar("SELECT COUNT(*) FROM runs WHERE learner_id=?", L)
    return {
        "total": len(rows), "runs": runs_total,
        "crash_rate": round(len(rows) / runs_total, 2) if runs_total else 0,
        "by_type": [{**monster(t), "count": n, "recent": recent.get(t, 0), "defeated": t in defeated,
                     "tip": GENERIC.get(t, "")} for t, n in by_type.most_common()],
        "weekly": [{"week": w, **dict(c)} for w, c in sorted(weekly.items())],
        "recent_messages": db.q("""SELECT ts, project_id, step_id, error_type, error_msg, error_line FROM runs
                                   WHERE learner_id=? AND ok=0 ORDER BY ts DESC LIMIT 15""", L),
    }


def ideas(learner_id):
    rows = db.q("SELECT * FROM ideas WHERE learner_id=? ORDER BY ts", (learner_id,))
    for r in rows:
        r["analysis"] = json.loads(r["analysis"] or "{}")
    remixes = db.q("SELECT id, project_id, ts, complexity, base_complexity, concepts, xp FROM remixes WHERE learner_id=? ORDER BY ts",
                   (learner_id,))
    for r in remixes:
        r["concepts"] = json.loads(r["concepts"] or "[]")
    return {"ideas": rows, "remixes": remixes,
            "avg_score": round(sum(r["score"] for r in rows) / len(rows)) if rows else None,
            "trend": [{"ts": r["ts"], "score": r["score"], "level": r["level"]} for r in rows]}


def code_growth(learner_id):
    rows = db.q("""SELECT project_id, step_id, ts, lines, complexity, concepts FROM snapshots
                   WHERE learner_id=? AND kind='check' ORDER BY ts""", (learner_id,))
    best = {}
    for r in rows:
        best[(r["project_id"], r["step_id"])] = r
    series = sorted(best.values(), key=lambda r: r["ts"])
    for r in series:
        r["concepts"] = len(json.loads(r["concepts"] or "[]"))
    return series


def enjoyment(learner_id):
    rows = db.q("SELECT project_id, ts, fun, difficulty, note FROM reflections WHERE learner_id=? ORDER BY ts", (learner_id,))
    avg_fun = sum(r["fun"] for r in rows) / len(rows) if rows else None
    return {"reflections": rows, "avg_fun": round(avg_fun, 1) if avg_fun else None,
            "avg_difficulty": round(sum(r["difficulty"] for r in rows) / len(rows), 1) if rows else None}


# ---------------------------------------------------------------------------
# Adaptive guide path
# ---------------------------------------------------------------------------
def guide(learner_id):
    """Personalized next steps for the learner plus coaching notes for the parent."""
    prog = _progress(learner_id)
    statuses = project_status(learner_id, prog)
    pos = current_position(learner_id, statuses, prog)
    mastery = concept_mastery(learner_id, prog)
    style = learning_style(learner_id, prog)
    sched = schedule(learner_id, statuses)
    err = errors(learner_id)
    enj = enjoyment(learner_id)
    idea_data = ideas(learner_id)
    kid, parent = [], []
    learned = [m["concept"] for m in mastery if m["started"]]

    def add(target, kind, title, text, priority, action=None, emoji="👉"):
        target.append({"kind": kind, "title": title, "text": text, "priority": priority, "action": action, "emoji": emoji})

    if pos:
        add(kid, "next", f"Continue: {pos['project_title']}", f"Next mission: {pos['step_title']}", 100,
            {"type": "step", "project": pos["project"], "step": pos["step"]}, "🚀")
    else:
        add(kid, "done", "You finished the whole quest!", "Build anything you like in the Playground, or remix a favorite.", 100,
            {"type": "playground"}, "🎓")

    # weak concepts → practice side quests
    done_practice = {k[1] for k, r in prog.items() if k[0] == "_practice" and r["status"] == "done"}
    # weak = he's struggled with it (many hints/attempts, or lots of crashes), not merely "not finished yet"
    weak = [m for m in mastery if (m["steps_done"] and (m["avg_quality"] < 0.7 or m["errors"] / m["steps_done"] > 3))
            or m["tutor_questions"] >= 4]
    weak.sort(key=lambda m: m["score"])
    for m in weak[:2]:
        options = sorted([p for p in PRACTICE if p["concept"] == m["concept"] and p["id"] not in done_practice],
                         key=lambda p: p["difficulty"])
        if options:
            p = options[0]
            add(kid, "practice", f"Side quest: {p['title']}",
                f"A quick {m['label']} warm-up to level up that skill.", 80,
                {"type": "practice", "id": p["id"]}, "🗡️")
        add(parent, "concept", f"{m['label']} needs reinforcement",
            f"Mastery {round(m['score'] * 100)}% — {m['steps_done']}/{m['steps_total']} steps, "
            f"{m['errors']} errors on related steps. The app is suggesting practice side quests. "
            f"Ask him to explain {m['label'].lower()} to you in his own words — or to show you on the replay.", 70)

    # strong & fast → boss / remix
    last_done = next((p for p in reversed(statuses) if p["complete"]), None)
    if last_done:
        proj = next(p for p in PROJECTS if p["id"] == last_done["id"])
        fast = last_done["seconds"] and last_done["seconds"] < last_done["expected_seconds"] * 0.9
        clean = last_done["steps_total"] and last_done["first_try"] / last_done["steps_total"] >= 0.5
        if not last_done["boss_done"] and (fast or clean):
            add(kid, "boss", f"Boss challenge: {proj['boss']['title']}",
                f"You crushed {proj['title']}. Ready for its boss?", 75,
                {"type": "step", "project": proj["id"], "step": "boss"}, "👾")
        if not last_done["remixed"]:
            add(kid, "remix", f"Remix {proj['title']}", proj["remix"]["prompt"], 60,
                {"type": "remix", "project": proj["id"]}, "🎛️")
        if last_done["fun"] is None:
            add(kid, "reflect", "How was it?", f"Rate {proj['title']} — it helps tune your quest.", 65,
                {"type": "reflect", "project": proj["id"]}, "⭐")

    # frequent recent errors → targeted tip
    for e in err["by_type"]:
        if e["recent"] >= 5:
            add(kid, "tip", f"{e['emoji']} The {e['name']} keeps showing up",
                f"{e['desc']} {e['tip']}", 70, {"type": "bestiary"}, e["emoji"])
            add(parent, "errors", f"Recurring {e['type']} ({e['recent']} this week)",
                f"{e['tip']} If it's frustrating him, sit together for one fix and talk through the error message.", 55)
            break

    # schedule
    if sched["status"] == "behind":
        add(kid, "pace", "Focus mode", "Stick to the core missions this week — bosses and remixes can wait.", 50, None, "🎯")
        add(parent, "pace", "Behind the 6-week plan",
            f"{sched['actual_pct']}% done vs {sched['expected_pct']}% expected. Projected finish {sched['projected_finish'] or 'n/a'}. "
            "Consider 2–3 extra short sessions, or simply extend the plan — enjoyment matters more than the deadline.", 60)
    elif sched["status"] == "ahead":
        add(parent, "pace", "Ahead of schedule 🎉",
            "He's moving faster than planned. Encourage boss challenges, remixes and the Playground rather than rushing ahead.", 40)

    # hint reliance
    if style["raw"]["hints_per_step"] > 1.5:
        add(kid, "habit", "Detective mode 🕵️", "Before opening a hint, run your robot and watch the replay and the telemetry graph. Clues are everywhere!", 45)
        add(parent, "habit", "Leaning on hints",
            f"{style['raw']['hints_per_step']} hints per step on average. Normal early on; if it continues, try the "
            "'explain it to the rubber duck' trick — he explains the task out loud before asking for help.", 45)

    # enjoyment
    if enj["reflections"]:
        last = enj["reflections"][-1]
        if last["fun"] and last["fun"] <= 2:
            add(parent, "fun", "Last project wasn't much fun",
                f"He rated it {last['fun']}/5 fun, {last['difficulty']}/5 hard. "
                "Let him skip to the remix, pick his own twist, or pair-program one session with you.", 80)
            add(kid, "fun", "Make the next one yours", "Try the Playground or a remix with your own wild idea!", 55,
                {"type": "playground"}, "🎨")
        if last["difficulty"] and last["difficulty"] >= 5:
            add(parent, "difficulty", "Found the last project very hard",
                "Consider reviewing the lesson cards together, and point him to practice side quests.", 65)

    # ideas vs skills
    if idea_data["ideas"]:
        last_idea = idea_data["ideas"][-1]
        if last_idea["level"] <= 1 and len(learned) >= 6:
            add(kid, "ideas", "Idea booster 💥", "Your skills are growing fast — dream bigger! What if your robot could sense something new, or switch modes?", 40)
        if last_idea["analysis"].get("new_concepts"):
            add(parent, "ideas", "Ideas running ahead of skills",
                "His latest idea needs concepts he hasn't learned yet ("
                + ", ".join(kidast.CONCEPT_LABELS[c] for c in last_idea["analysis"]["new_concepts"])
                + "). Great sign of ambition — help him scope a small first version.", 35)

    # inactivity
    last_seen = db.scalar("SELECT MAX(last_seen) FROM learning_sessions WHERE learner_id=?", (learner_id,))
    if last_seen and db.now() - last_seen > 3 * DAY:
        add(parent, "inactive", "No robot building for a few days",
            f"Last active {dt.datetime.fromtimestamp(last_seen):%a %b %d}. A gentle nudge or a shared session can restart momentum.", 75)
        add(kid, "welcome", "Welcome back! 👋", "Your streak starts again today. One tiny step counts!", 90)

    from . import tutor
    ts = tutor.stats(learner_id)
    if ts["flagged"]:
        f = ts["flagged"][0]
        add(parent, "flagged", "⚠️ Sprocket flagged a message for you",
            f"On {dt.datetime.fromtimestamp(f['ts']):%a %b %d} he wrote to the AI tutor: \"{f['text'][:160]}\". "
            "Sprocket encouraged him to talk to a trusted adult. Please check in with him. (Full transcript: Parent Zone → AI Tutor.)", 99)
    rm = ts["recent_moods"]
    if rm.get("frustrated", 0) >= 3:
        add(parent, "mood", "Sounding frustrated this week",
            f"{rm['frustrated']} of his recent questions to Sprocket read as frustrated. A short break, pairing on one bug, "
            "or letting him jump to a remix can reset the mood.", 72)
    if style["raw"]["tutor_per_step"] > 3:
        add(parent, "tutor", "Asking the AI tutor a lot",
            f"About {style['raw']['tutor_per_step']} tutor questions per mission. Sprocket won't hand out answers, but encourage "
            "him to run the robot and study the replay first — that builds debugging muscles.", 45)
    if ts["by_concept"]:
        top, n = next(iter(ts["by_concept"].items()))
        if n >= 3:
            add(parent, "tutor_topic", f"Most-asked topic: {kidast.CONCEPT_LABELS.get(top, top)}",
                f"{n} questions to Sprocket were about {kidast.CONCEPT_LABELS.get(top, top).lower()}. A good one to talk through together.", 38)

    rs = robot_stats(learner_id)
    if rs["runs"] >= 10 and rs["crash_run_rate"] > 0.5:
        add(kid, "safety", "Gentle robot 🛡️", "Lots of runs end with a bump. Try reading the distance sensor and slowing down near walls!", 50,
            None, "🛡️")
        add(parent, "safety", "Many runs end in a crash",
            f"{round(rs['crash_run_rate'] * 100)}% of his runs bump into something. That's normal early on — it's how robots are "
            "debugged! Ask him to watch the replay and tell you exactly when it went wrong.", 42)
    if rs["crash_rate_early"] is not None and rs["crash_rate_late"] is not None and rs["crash_rate_late"] < rs["crash_rate_early"] - 0.15:
        add(parent, "safety_up", "Getting safer 👍",
            f"Crash rate fell from {round(rs['crash_rate_early'] * 100)}% of runs to {round(rs['crash_rate_late'] * 100)}%. "
            "He's learning to predict what the robot will do.", 30)
    if style["raw"].get("tune_ratio", 0) >= 0.5 and style["raw"].get("tune_edits", 0) >= 10:
        add(parent, "tuning", "He tunes by trial and error",
            "Most of his code changes only tweak numbers. That's real engineering — to deepen it, ask him to predict what a "
            "change will do before pressing Run, and to use robot.plot() to see the effect.", 36)
    if rs["runs"] >= 15 and rs["drive"]["sessions"] == 0:
        add(kid, "drive", "Take Bolt for a spin 🎮", "Drive mode lets you steer with the keyboard and watch every sensor live.", 25,
            {"type": "drive"}, "🎮")

    st = gamification.streak(learner_id)
    if st["current"] >= 2:
        add(kid, "streak", f"🔥 {st['current']}-day streak!", "Build something today to keep it going.", 30)

    kid.sort(key=lambda r: -r["priority"])
    parent.sort(key=lambda r: -r["priority"])

    # the path: projects in order with recommended side quests woven in
    path = []
    for ps in statuses:
        path.append({"type": "project", **ps})
        if pos and ps["id"] == pos["project"]:
            for r in kid:
                if r["kind"] == "practice":
                    path.append({"type": "practice", "title": r["title"], "action": r["action"]})
    return {"kid": kid[:6], "parent": parent, "path": path, "position": pos, "schedule": sched}


def full_report(learner_id):
    prog = _progress(learner_id)
    statuses = project_status(learner_id, prog)
    xp = gamification.total_xp(learner_id)
    return {
        "learner": db.one("SELECT * FROM learners WHERE id=?", (learner_id,)),
        "level": gamification.level_for(xp),
        "projects": statuses,
        "schedule": schedule(learner_id, statuses),
        "mastery": concept_mastery(learner_id, prog),
        "style": learning_style(learner_id, prog),
        "activity": activity(learner_id),
        "errors": errors(learner_id),
        "ideas": ideas(learner_id),
        "code_growth": code_growth(learner_id),
        "enjoyment": enjoyment(learner_id),
        "guide": guide(learner_id),
        "badges": gamification.badge_list(learner_id),
        "robot": robot_stats(learner_id),
        "xp_by_reason": db.q("""SELECT CASE WHEN instr(reason, ':') > 0 THEN substr(reason, 1, instr(reason, ':') - 1)
                                ELSE reason END r, SUM(amount) xp FROM xp_log WHERE learner_id=? GROUP BY r""", (learner_id,)),
    }
