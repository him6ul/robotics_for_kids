"""SQLite storage. One file (data/roboquest.db), created on first start."""
import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("ROBOQUEST_DB", os.path.join(ROOT, "data", "roboquest.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS learners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    avatar TEXT NOT NULL DEFAULT '🤖',
    theme TEXT NOT NULL DEFAULT 'slate',
    robot_color TEXT NOT NULL DEFAULT '#5b8def',
    robot_name TEXT NOT NULL DEFAULT 'Bolt',
    sound INTEGER NOT NULL DEFAULT 1,
    start_date TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);

CREATE TABLE IF NOT EXISTS step_progress (
    learner_id INTEGER, project_id TEXT, step_id TEXT,
    status TEXT NOT NULL DEFAULT 'started',
    started_at REAL, completed_at REAL,
    attempts INTEGER NOT NULL DEFAULT 0,
    hints_used INTEGER NOT NULL DEFAULT 0,
    runs INTEGER NOT NULL DEFAULT 0,
    errors INTEGER NOT NULL DEFAULT 0,
    crashes INTEGER NOT NULL DEFAULT 0,
    seconds INTEGER NOT NULL DEFAULT 0,
    first_try INTEGER NOT NULL DEFAULT 0,
    xp INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (learner_id, project_id, step_id)
);
CREATE TABLE IF NOT EXISTS code_saves (
    learner_id INTEGER, project_id TEXT, step_id TEXT, code TEXT, updated_at REAL,
    PRIMARY KEY (learner_id, project_id, step_id)
);
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id INTEGER, project_id TEXT, step_id TEXT, ts REAL, kind TEXT,
    code TEXT, lines INTEGER, complexity INTEGER, concepts TEXT
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id INTEGER, project_id TEXT, step_id TEXT, mode TEXT, ts REAL,
    duration_ms INTEGER, ok INTEGER, error_type TEXT, error_line INTEGER, error_msg TEXT,
    output_chars INTEGER, sim_time REAL, distance REAL, crashes INTEGER, gems INTEGER,
    sensors TEXT, end_reason TEXT, arena TEXT
);
CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id INTEGER, project_id TEXT, step_id TEXT, ts REAL,
    passed INTEGER, message TEXT, duration_ms INTEGER, scenarios INTEGER, scenario TEXT
);
CREATE TABLE IF NOT EXISTS hints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id INTEGER, project_id TEXT, step_id TEXT, ts REAL, level INTEGER
);
CREATE TABLE IF NOT EXISTS time_log (
    learner_id INTEGER, project_id TEXT, step_id TEXT, day TEXT, seconds INTEGER,
    PRIMARY KEY (learner_id, project_id, step_id, day)
);
CREATE TABLE IF NOT EXISTS learning_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id INTEGER, started_at REAL, last_seen REAL, active_seconds INTEGER
);
CREATE TABLE IF NOT EXISTS ideas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id INTEGER, project_id TEXT, ts REAL, text TEXT,
    score INTEGER, level INTEGER, analysis TEXT,
    status TEXT NOT NULL DEFAULT 'idea', built_complexity INTEGER
);
CREATE TABLE IF NOT EXISTS remixes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id INTEGER, project_id TEXT, idea_id INTEGER, ts REAL,
    code TEXT, complexity INTEGER, base_complexity INTEGER, concepts TEXT, xp INTEGER, arena TEXT
);
CREATE TABLE IF NOT EXISTS reflections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id INTEGER, project_id TEXT, ts REAL, fun INTEGER, difficulty INTEGER, note TEXT
);
CREATE TABLE IF NOT EXISTS arenas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id INTEGER, name TEXT, spec TEXT, complexity INTEGER, created_at REAL, updated_at REAL
);
CREATE TABLE IF NOT EXISTS drive_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id INTEGER, arena TEXT, started_at REAL, seconds REAL, distance REAL, crashes INTEGER,
    gems INTEGER, gems_total INTEGER
);
CREATE TABLE IF NOT EXISTS xp_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id INTEGER, ts REAL, amount INTEGER, reason TEXT
);
CREATE TABLE IF NOT EXISTS badges (
    learner_id INTEGER, badge_id TEXT, earned_at REAL,
    PRIMARY KEY (learner_id, badge_id)
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL, actor TEXT, action TEXT, entity TEXT, entity_id TEXT,
    details TEXT, ip TEXT, user_agent TEXT, hash TEXT
);
CREATE TABLE IF NOT EXISTS metrics_minute (
    minute INTEGER, name TEXT, count INTEGER, total REAL, max REAL,
    PRIMARY KEY (minute, name)
);
CREATE TABLE IF NOT EXISTS app_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL, source TEXT, message TEXT, detail TEXT
);
CREATE INDEX IF NOT EXISTS ix_runs_l ON runs(learner_id, ts);
CREATE INDEX IF NOT EXISTS ix_checks_l ON checks(learner_id, ts);
CREATE INDEX IF NOT EXISTS ix_snap_l ON snapshots(learner_id, ts);
CREATE INDEX IF NOT EXISTS ix_snap_step ON snapshots(learner_id, project_id, step_id);
CREATE INDEX IF NOT EXISTS ix_audit_ts ON audit_log(ts);
CREATE INDEX IF NOT EXISTS ix_audit_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS ix_audit_actor ON audit_log(actor, ts);
CREATE INDEX IF NOT EXISTS ix_xp_l ON xp_log(learner_id, ts);
"""

TABLES = ["learners", "step_progress", "code_saves", "snapshots", "runs", "checks", "hints",
          "time_log", "learning_sessions", "ideas", "remixes", "reflections", "arenas", "drive_sessions",
          "xp_log", "badges", "audit_log", "metrics_minute", "app_errors", "settings"]
LEARNER_TABLES = ["step_progress", "code_saves", "snapshots", "runs", "checks", "hints", "time_log",
                  "learning_sessions", "ideas", "remixes", "reflections", "arenas", "drive_sessions",
                  "xp_log", "badges"]

_local = threading.local()
_write_lock = threading.RLock()


def conn():
    c = getattr(_local, "conn", None)
    if c is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        c = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        _local.conn = c
    return c


def init():
    with _write_lock:
        conn().executescript(SCHEMA)
        conn().commit()


def q(sql, args=()):
    return [dict(r) for r in conn().execute(sql, args).fetchall()]


def one(sql, args=()):
    r = conn().execute(sql, args).fetchone()
    return dict(r) if r else None


def scalar(sql, args=(), default=0):
    r = conn().execute(sql, args).fetchone()
    return r[0] if r and r[0] is not None else default


def ex(sql, args=()):
    with _write_lock:
        cur = conn().execute(sql, args)
        conn().commit()
        return cur.lastrowid


@contextmanager
def tx():
    with _write_lock:
        c = conn()
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise


def get_setting(key, default=None):
    r = one("SELECT value FROM settings WHERE key=?", (key,))
    return json.loads(r["value"]) if r else default


def set_setting(key, value):
    ex("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
       (key, json.dumps(value)))


def now():
    return time.time()
