"""XP, levels, streaks and badges."""
import datetime as dt

from . import db

LEVEL_TITLES = ["Spare Part", "Bolt Tightener", "Motor Starter", "Sensor Scout", "Loop Pilot",
                "Line Rider", "Control Tuner", "Navigator", "Gripper Guru", "Maze Solver",
                "Robot Architect", "Chief Roboticist"]


def level_for(xp):
    """Level n needs 50*n*(n+1) XP in total (100, 300, 600, 1000, ...)."""
    n = 0
    while xp >= 50 * (n + 1) * (n + 2):
        n += 1
    lo, hi = 50 * n * (n + 1), 50 * (n + 1) * (n + 2)
    return {"level": n + 1, "title": LEVEL_TITLES[min(n, len(LEVEL_TITLES) - 1)],
            "xp": xp, "into": xp - lo, "needed": hi - lo}


def total_xp(learner_id):
    return db.scalar("SELECT SUM(amount) FROM xp_log WHERE learner_id=?", (learner_id,))


def award_xp(learner_id, amount, reason):
    if amount:
        db.ex("INSERT INTO xp_log(learner_id, ts, amount, reason) VALUES(?,?,?,?)",
              (learner_id, db.now(), int(amount), reason))
    return amount


def active_days(learner_id):
    rows = db.q("SELECT day, SUM(seconds) s FROM time_log WHERE learner_id=? GROUP BY day HAVING s >= 60 ORDER BY day",
                (learner_id,))
    return [r["day"] for r in rows]


def streak(learner_id):
    days = set(active_days(learner_id))
    today = dt.date.today()
    d = today if today.isoformat() in days else today - dt.timedelta(days=1)
    n = 0
    while d.isoformat() in days:
        n += 1
        d -= dt.timedelta(days=1)
    best, cur, prev = 0, 0, None
    for day in sorted(days):
        x = dt.date.fromisoformat(day)
        cur = cur + 1 if prev and (x - prev).days == 1 else 1
        best = max(best, cur)
        prev = x
    return {"current": n, "best": best}


BADGES = {
    "first_run": ("🔌", "Powered On", "Ran your very first robot program"),
    "first_step": ("👣", "First Steps", "Completed your first mission"),
    "first_project": ("🏆", "Project Pro", "Finished a whole project"),
    "bug_hunter": ("🔍", "Bug Hunter", "Defeated 5 different kinds of bugs"),
    "persistent": ("💪", "Never Give Up", "Passed a mission after 5+ tries"),
    "no_hints": ("🧠", "Solo Engineer", "Finished a project without any hints"),
    "speedy": ("⚡", "Speed Builder", "Finished a project faster than expected"),
    "careful": ("🛡️", "Zero Scratches", "Finished 10 missions without a single crash"),
    "sensor_5": ("📡", "Sensor Collector", "Used 5 different kinds of sensors"),
    "gem_50": ("💎", "Gem Hoarder", "Collected 50 gems across all runs"),
    "marathon": ("🛞", "Road Trip", "Drove 100 metres in total"),
    "driver": ("🎮", "Test Driver", "Drove for 5 minutes in Drive mode"),
    "builder": ("🏗️", "Arena Architect", "Designed 3 of your own arenas"),
    "remixer": ("🎛️", "Remix Master", "Remixed 3 projects your own way"),
    "big_thinker": ("💡", "Big Thinker", "Had an idea rated Architect or higher"),
    "explorer": ("🧭", "Explorer", "Ran 10 experiments in the Playground"),
    "practice_half": ("🗡️", "Halfway Hero", "Cleared 21 side quests — halfway there!"),
    "practice_pro": ("🥋", "Practice Pro", "Cleared every side quest in RoboQuest"),
    "boss_1": ("👾", "Boss Beater", "Beat your first boss challenge"),
    "boss_5": ("🐲", "Boss Crusher", "Beat 5 boss challenges"),
    "streak_3": ("🔥", "On Fire", "Built robots 3 days in a row"),
    "streak_7": ("🌋", "Unstoppable", "Built robots 7 days in a row"),
    "week_1": ("1️⃣", "Week 1 Done", "Made it move — bosses, remixes and side quests done"),
    "week_2": ("2️⃣", "Week 2 Done", "Robots that sense"),
    "week_3": ("3️⃣", "Week 3 Done", "Followed the line"),
    "week_4": ("4️⃣", "Week 4 Done", "Know where you are"),
    "week_5": ("5️⃣", "Week 5 Done", "Grab & build"),
    "week_6": ("🎓", "Graduate", "Finished the whole 6-week RoboQuest — every boss, remix and side quest!"),
}


def badge_list(learner_id):
    earned = {r["badge_id"]: r["earned_at"] for r in db.q("SELECT * FROM badges WHERE learner_id=?", (learner_id,))}
    return [{"id": k, "emoji": v[0], "name": v[1], "desc": v[2], "earned_at": earned.get(k)} for k, v in BADGES.items()]


def evaluate_badges(learner_id, projects):
    """Grant any newly earned badges. Returns list of new badge dicts."""
    import json
    have = {r["badge_id"] for r in db.q("SELECT badge_id FROM badges WHERE learner_id=?", (learner_id,))}
    L = (learner_id,)
    done = {(r["project_id"], r["step_id"]): r for r in
            db.q("SELECT * FROM step_progress WHERE learner_id=? AND status='done'", L)}
    finished = [p for p in projects if all((p["id"], s["id"]) in done for s in p["steps"])]
    earned = set()
    if db.scalar("SELECT COUNT(*) FROM runs WHERE learner_id=?", L):
        earned.add("first_run")
    if any(k[0] != "_practice" for k in done):
        earned.add("first_step")
    if finished:
        earned.add("first_project")
    fixed_types = db.q("""SELECT DISTINCT r.error_type FROM runs r WHERE r.learner_id=? AND r.ok=0 AND r.error_type IS NOT NULL
                          AND EXISTS (SELECT 1 FROM runs r2 WHERE r2.learner_id=r.learner_id AND r2.project_id=r.project_id
                                      AND r2.step_id=r.step_id AND r2.ts>r.ts AND r2.ok=1)""", L)
    if len(fixed_types) >= 5:
        earned.add("bug_hunter")
    if any(r["attempts"] >= 5 for r in done.values()):
        earned.add("persistent")
    for p in finished:
        rows = [done[(p["id"], s["id"])] for s in p["steps"]]
        if sum(r["hints_used"] for r in rows) == 0:
            earned.add("no_hints")
        secs = sum(r["seconds"] for r in rows)
        if 0 < secs < p["expected_minutes"] * 60 * 0.8:
            earned.add("speedy")
    if sum(1 for r in done.values() if r["crashes"] == 0) >= 10:
        earned.add("careful")
    kinds = set()
    for r in db.q("SELECT DISTINCT sensors FROM runs WHERE learner_id=? AND sensors IS NOT NULL", L):
        for ch in json.loads(r["sensors"] or "[]"):
            kinds.add(ch.split("_")[0])
    if len(kinds) >= 5:
        earned.add("sensor_5")
    if db.scalar("SELECT SUM(gems) FROM runs WHERE learner_id=?", L) + \
            db.scalar("SELECT SUM(gems) FROM drive_sessions WHERE learner_id=?", L) >= 50:
        earned.add("gem_50")
    if db.scalar("SELECT SUM(distance) FROM runs WHERE learner_id=?", L) + \
            db.scalar("SELECT SUM(distance) FROM drive_sessions WHERE learner_id=?", L) >= 10000:
        earned.add("marathon")
    if db.scalar("SELECT SUM(seconds) FROM drive_sessions WHERE learner_id=?", L) >= 300:
        earned.add("driver")
    if db.scalar("SELECT COUNT(*) FROM arenas WHERE learner_id=?", L) >= 3:
        earned.add("builder")
    if db.scalar("SELECT COUNT(DISTINCT project_id) FROM remixes WHERE learner_id=?", L) >= 3:
        earned.add("remixer")
    if db.scalar("SELECT MAX(level) FROM ideas WHERE learner_id=?", L) >= 4:
        earned.add("big_thinker")
    if db.scalar("SELECT COUNT(*) FROM runs WHERE learner_id=? AND mode='playground'", L) >= 10:
        earned.add("explorer")
    from .curriculum import PRACTICE
    if sum(1 for pr in PRACTICE if ("_practice", pr["id"]) in done) >= 21:
        earned.add("practice_half")
    if PRACTICE and all(("_practice", pr["id"]) in done for pr in PRACTICE):
        earned.add("practice_pro")
    bosses = sum(1 for k in done if k[1] == "boss")
    if bosses >= 1:
        earned.add("boss_1")
    if bosses >= 5:
        earned.add("boss_5")
    st = streak(learner_id)["best"]
    if st >= 3:
        earned.add("streak_3")
    if st >= 7:
        earned.add("streak_7")
    # a week counts as done only when every project in it has its missions, its boss AND a remix done
    remixed = {r["project_id"] for r in db.q("SELECT DISTINCT project_id FROM remixes WHERE learner_id=?", L)}
    finished_ids = {p["id"] for p in finished if (p["id"], "boss") in done and p["id"] in remixed}
    from .curriculum import week_practice
    for w in range(1, 7):
        wk = [p for p in projects if p["week"] == w]
        quests_done = all(("_practice", pr["id"]) in done for pr in week_practice(w))
        if wk and quests_done and all(p["id"] in finished_ids for p in wk):
            earned.add(f"week_{w}")
    new = []
    for b in sorted(earned - have):
        db.ex("INSERT OR IGNORE INTO badges(learner_id, badge_id, earned_at) VALUES(?,?,?)", (learner_id, b, db.now()))
        e, n, d = BADGES[b]
        new.append({"id": b, "emoji": e, "name": n, "desc": d})
        award_xp(learner_id, 25, f"badge:{b}")
    return new
