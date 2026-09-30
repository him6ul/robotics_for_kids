"""Audit trail, runtime metrics, error capture and system health."""
import hashlib
import json
import os
import platform
import shutil
import sys
import threading
import time
import traceback
from collections import defaultdict, deque

from . import db

STARTED = time.time()

# ---------------------------------------------------------------------------
# Audit log: who did what, when, from where. Append-only from the app's side.
# ---------------------------------------------------------------------------


def _row_hash(prev, ts, actor, action, entity, entity_id, details, ip, ua):
    blob = json.dumps([prev, round(ts, 6), actor, action, entity, entity_id, details, ip, ua], ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


def audit(actor, action, entity=None, entity_id=None, details=None, request=None):
    """Append one audit row. Each row carries sha256(previous hash + row), so edits or deletions are detectable."""
    ip = ua = None
    if request is not None:
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent", "")[:200]
    ts = time.time()
    eid = None if entity_id is None else str(entity_id)
    det = json.dumps(details, default=str, ensure_ascii=False) if details is not None else None
    with db.tx() as c:
        prev = c.execute("SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
        h = _row_hash(prev[0] if prev else "", ts, actor, action, entity, eid, det, ip, ua)
        c.execute("INSERT INTO audit_log(ts, actor, action, entity, entity_id, details, ip, user_agent, hash) "
                  "VALUES(?,?,?,?,?,?,?,?,?)", (ts, actor, action, entity, eid, det, ip, ua, h))


def verify_audit_chain():
    """Walk the whole chain. Returns {"ok", "rows", "first_bad_id"}."""
    prev = ""
    n = 0
    for r in db.conn().execute("SELECT * FROM audit_log ORDER BY id"):
        n += 1
        h = _row_hash(prev, r["ts"], r["actor"], r["action"], r["entity"], r["entity_id"], r["details"],
                      r["ip"], r["user_agent"])
        if h != r["hash"]:
            return {"ok": False, "rows": n, "first_bad_id": r["id"]}
        prev = r["hash"]
    return {"ok": True, "rows": n, "first_bad_id": None}


def audit_query(actor=None, action=None, entity=None, since=None, until=None, text=None, limit=200, offset=0):
    where, args = [], []
    for col, val in (("actor", actor), ("action", action), ("entity", entity)):
        if val:
            where.append(f"{col} = ?")
            args.append(val)
    if since:
        where.append("ts >= ?")
        args.append(since)
    if until:
        where.append("ts <= ?")
        args.append(until)
    if text:
        where.append("(details LIKE ? OR action LIKE ? OR entity_id LIKE ?)")
        args += [f"%{text}%"] * 3
    w = ("WHERE " + " AND ".join(where)) if where else ""
    rows = db.q(f"SELECT * FROM audit_log {w} ORDER BY ts DESC LIMIT ? OFFSET ?", (*args, limit, offset))
    total = db.scalar(f"SELECT COUNT(*) FROM audit_log {w}", args)
    facets = {
        "actions": db.q("SELECT action, COUNT(*) n FROM audit_log GROUP BY action ORDER BY n DESC"),
        "actors": db.q("SELECT actor, COUNT(*) n FROM audit_log GROUP BY actor ORDER BY n DESC"),
    }
    return {"rows": rows, "total": total, "facets": facets}


# ---------------------------------------------------------------------------
# Metrics: in-memory recent samples + per-minute rollups persisted to SQLite
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_minute = defaultdict(lambda: [0, 0.0, 0.0])      # name -> [count, total, max] for the current minute
_current_minute = int(time.time() // 60)
_recent = defaultdict(lambda: deque(maxlen=500))   # name -> recent values (for percentiles)
_gauges = {}
_counters = defaultdict(int)


def _flush_locked(minute):
    rows = [(minute, name, c, t, m) for name, (c, t, m) in _minute.items()]
    _minute.clear()
    if rows:
        with db.tx() as c:
            c.executemany("""INSERT INTO metrics_minute(minute, name, count, total, max) VALUES(?,?,?,?,?)
                             ON CONFLICT(minute, name) DO UPDATE SET count=count+excluded.count,
                             total=total+excluded.total, max=MAX(max, excluded.max)""", rows)


def record(name, value=1.0):
    global _current_minute
    m = int(time.time() // 60)
    with _lock:
        if m != _current_minute:
            _flush_locked(_current_minute)
            _current_minute = m
        s = _minute[name]
        s[0] += 1
        s[1] += value
        s[2] = max(s[2], value)
        _recent[name].append(value)
        _counters[name] += 1


def gauge(name, value):
    _gauges[name] = value


def flush():
    with _lock:
        _flush_locked(_current_minute)


def _pct(values, p):
    if not values:
        return None
    v = sorted(values)
    return round(v[min(len(v) - 1, int(len(v) * p))], 1)


def app_error(source, exc):
    detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-4000:]
    try:
        db.ex("INSERT INTO app_errors(ts, source, message, detail) VALUES(?,?,?,?)",
              (time.time(), source, f"{type(exc).__name__}: {exc}", detail))
    except Exception:  # noqa: BLE001 - never let error logging crash the app
        pass
    record("app.errors")


def snapshot(hours=24):
    """Everything the Monitoring page shows."""
    flush()
    since = int((time.time() - hours * 3600) // 60)
    series = defaultdict(list)
    for r in db.q("SELECT minute, name, count, total, max FROM metrics_minute WHERE minute >= ? ORDER BY minute", (since,)):
        series[r["name"]].append(r)
    # roll up to 10-minute buckets for charts
    def bucket(name, field="count", size=10):
        out = defaultdict(float)
        for r in series.get(name, []):
            out[r["minute"] // size * size] += r[field]
        return [{"t": k * 60, "v": round(v, 1)} for k, v in sorted(out.items())]

    req_names = sorted({n for n in series if n.startswith("http.")})
    routes = []
    for n in req_names:
        rows = series[n]
        c = sum(r["count"] for r in rows)
        routes.append({"route": n[5:], "count": c, "avg_ms": round(sum(r["total"] for r in rows) / c, 1) if c else 0,
                       "max_ms": round(max(r["max"] for r in rows), 1),
                       "p95_ms": _pct(list(_recent[n]), 0.95)})
    routes.sort(key=lambda r: -r["count"])
    db_size = os.path.getsize(db.DB_PATH) if os.path.exists(db.DB_PATH) else 0
    wal = db.DB_PATH + "-wal"
    disk = shutil.disk_usage(os.path.dirname(db.DB_PATH))
    try:
        import resource
        rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024)
    except Exception:  # noqa: BLE001
        rss_mb = None
    tables = {t: db.scalar(f"SELECT COUNT(*) FROM {t}") for t in db.TABLES}
    runner = {
        "runs": sum(r["count"] for r in series.get("runner.duration_ms", [])),
        "p50_ms": _pct(list(_recent["runner.duration_ms"]), 0.5),
        "p95_ms": _pct(list(_recent["runner.duration_ms"]), 0.95),
        "killed": sum(r["count"] for r in series.get("runner.killed", [])),
        "output_limit": sum(r["count"] for r in series.get("runner.output_limit", [])),
        "crashes": sum(r["count"] for r in series.get("runner.kid_error", [])),
        "sim_seconds": round(sum(r["total"] for r in series.get("runner.sim_seconds", [])), 1),
        "frames": round(sum(r["total"] for r in series.get("runner.frames", []))),
        "payload_kb_p95": _pct(list(_recent["runner.payload_kb"]), 0.95),
        "robot_crashes": round(sum(r["total"] for r in series.get("runner.robot_crashes", []))),
    }
    teleop = {
        "sessions": sum(r["count"] for r in series.get("teleop.session", [])),
        "ticks": sum(r["count"] for r in series.get("teleop.tick_ms", [])),
        "p95_ms": _pct(list(_recent["teleop.tick_ms"]), 0.95),
    }
    checker = {
        "checks": sum(r["count"] for r in series.get("checker.duration_ms", [])),
        "p50_ms": _pct(list(_recent["checker.duration_ms"]), 0.5),
        "p95_ms": _pct(list(_recent["checker.duration_ms"]), 0.95),
        "timeouts": sum(r["count"] for r in series.get("checker.timeout", [])),
        "internal_errors": sum(r["count"] for r in series.get("checker.internal_error", [])),
        "pass_rate": None,
    }
    passed = sum(r["count"] for r in series.get("checker.passed", []))
    if checker["checks"]:
        checker["pass_rate"] = round(passed / checker["checks"], 2)
    tutor_rows = series.get("tutor.latency_ms", [])
    tutor_calls = sum(r["count"] for r in tutor_rows)
    tutor = {
        "calls": tutor_calls,
        "avg_ms": round(sum(r["total"] for r in tutor_rows) / tutor_calls) if tutor_calls else None,
        "p95_ms": _pct(list(_recent["tutor.latency_ms"]), 0.95),
        "tokens_in": round(sum(r["total"] for r in series.get("tutor.tokens_in", []))),
        "tokens_out": round(sum(r["total"] for r in series.get("tutor.tokens_out", []))),
        "errors": sum(r["count"] for r in series.get("tutor.errors", [])),
        "refused": sum(r["count"] for r in series.get("tutor.refused", [])),
    }
    http_total = sum(r["count"] for r in routes)
    http_errors = sum(r["count"] for r in series.get("http.status_5xx", [])) if "http.status_5xx" in series else 0
    return {
        "health": {
            "status": "ok",
            "uptime_sec": round(time.time() - STARTED),
            "started_at": STARTED,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "pid": os.getpid(),
            "rss_mb": round(rss_mb, 1) if rss_mb else None,
            "db_path": db.DB_PATH,
            "db_bytes": db_size + (os.path.getsize(wal) if os.path.exists(wal) else 0),
            "disk_free_gb": round(disk.free / 1e9, 1),
        },
        "gauges": dict(_gauges),
        "http": {"total": http_total, "routes": routes[:25], "series": bucket("http.all"),
                 "latency_series": bucket("http.all", "max")},
        "runner": runner, "runner_series": bucket("runner.duration_ms"),
        "checker": checker, "checker_series": bucket("checker.duration_ms"),
        "tutor": tutor, "tutor_series": bucket("tutor.latency_ms"),
        "teleop": teleop, "active": dict(_gauges),
        "errors": db.q("SELECT id, ts, source, message FROM app_errors ORDER BY ts DESC LIMIT 25"),
        "error_count_24h": db.scalar("SELECT COUNT(*) FROM app_errors WHERE ts >= ?", (time.time() - 86400,)),
        "tables": tables,
        "hours": hours,
        "http_5xx": http_errors,
    }


def data_overview():
    """Data-catalog view: what is collected, how much, and how it grows."""
    catalog = {
        "learners": "Learner profiles (name, avatar, theme, plan start date)",
        "step_progress": "Per-step status, attempts, hints, runs, errors, active seconds, XP",
        "code_saves": "Latest autosaved code per mission",
        "snapshots": "Code history captured on every run/check/remix with size, complexity and concepts",
        "runs": "Every simulation run: duration, success, error, robot time, distance driven, crashes, gems, sensors used",
        "checks": "Every 'Check my robot' attempt, how many test arenas ran, and the result",
        "hints": "Every hint opened (which level)",
        "time_log": "Active (not idle) seconds per learner/project/step/day",
        "learning_sessions": "Continuous learning sessions (start, last seen, active seconds)",
        "ideas": "Idea journal entries with complexity score and analysis",
        "remixes": "Remixed programs and their complexity vs the original",
        "arenas": "Arenas he designed in the Arena Builder (layout JSON and design complexity)",
        "drive_sessions": "Drive-mode (keyboard driving) sessions: time, distance, crashes, gems",
        "reflections": "Fun / difficulty ratings after projects",
        "xp_log": "Every XP award and its reason",
        "badges": "Badges earned",
        "audit_log": "Audit trail of all meaningful actions (learner, parent, system)",
        "metrics_minute": "Per-minute system metrics (HTTP, simulator, checker, teleop, tutor)",
        "app_errors": "Server-side exceptions",
        "settings": "App settings (parent PIN hash, preferences, AI tutor settings)",
        "tutor_messages": "AI tutor (Sprocket) conversations and code reviews, with question type, concept, mood, tokens and latency",
    }
    tables = []
    for t in db.TABLES:
        cols = [r["name"] for r in db.q(f"PRAGMA table_info({t})")]
        ts_col = next((c for c in ("ts", "created_at", "started_at", "updated_at", "earned_at") if c in cols), None)
        info = {"table": t, "description": catalog.get(t, ""), "rows": db.scalar(f"SELECT COUNT(*) FROM {t}"),
                "columns": cols}
        if ts_col:
            info["first"] = db.scalar(f"SELECT MIN({ts_col}) FROM {t}", default=None)
            info["last"] = db.scalar(f"SELECT MAX({ts_col}) FROM {t}", default=None)
        tables.append(info)
    daily = db.q("""SELECT date(ts, 'unixepoch', 'localtime') d, 'runs' k, COUNT(*) n FROM runs GROUP BY d
                    UNION ALL SELECT date(ts, 'unixepoch', 'localtime'), 'checks', COUNT(*) FROM checks GROUP BY 1
                    UNION ALL SELECT date(ts, 'unixepoch', 'localtime'), 'hints', COUNT(*) FROM hints GROUP BY 1
                    UNION ALL SELECT date(ts, 'unixepoch', 'localtime'), 'snapshots', COUNT(*) FROM snapshots GROUP BY 1
                    UNION ALL SELECT date(ts, 'unixepoch', 'localtime'), 'audit', COUNT(*) FROM audit_log GROUP BY 1
                    UNION ALL SELECT date(started_at, 'unixepoch', 'localtime'), 'drives', COUNT(*) FROM drive_sessions GROUP BY 1
                    ORDER BY 1""")
    quality = {
        "runs_without_learner": db.scalar("SELECT COUNT(*) FROM runs WHERE learner_id NOT IN (SELECT id FROM learners)"),
        "orphan_progress": db.scalar("SELECT COUNT(*) FROM step_progress WHERE learner_id NOT IN (SELECT id FROM learners)"),
        "sessions_open": db.scalar("SELECT COUNT(*) FROM learning_sessions WHERE last_seen > ?", (time.time() - 300,)),
        "checks_without_step": db.scalar("SELECT COUNT(*) FROM checks c WHERE NOT EXISTS (SELECT 1 FROM step_progress s WHERE s.learner_id=c.learner_id AND s.project_id=c.project_id AND s.step_id=c.step_id)"),
        "negative_durations": db.scalar("SELECT COUNT(*) FROM runs WHERE duration_ms < 0 OR sim_time < 0"),
        "audit_gaps_24h": _audit_gaps(),
    }
    return {"tables": tables, "daily": daily, "quality": quality}


def _audit_gaps():
    """Audit ids are sequential; a gap would mean rows were removed outside the app."""
    rows = db.q("SELECT id FROM audit_log WHERE ts >= ? ORDER BY id", (time.time() - 86400,))
    ids = [r["id"] for r in rows]
    return sum(b - a - 1 for a, b in zip(ids, ids[1:]) if b - a > 1)
