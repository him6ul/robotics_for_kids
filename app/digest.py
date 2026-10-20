"""Parent emails over SMTP: a weekly progress digest and a daily activity email, plus a small scheduler.

* Weekly: once per ISO week at the chosen day/hour (off until enabled).
* Daily: once per learner per day *on days he actually used RoboQuest*, at the chosen hour (default 20:00),
  to the daily recipients (default him6ul@gmail.com). If the app was off at that hour it catches up at the
  next start (up to 2 days back), so an active day is never silently skipped.

Both need the SMTP account configured in Parent Zone → Settings. They only send while RoboQuest is running.
"""
import asyncio
import datetime as dt
import html
import smtplib
import ssl
import time
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from . import analytics, db
from . import observability as obs
from .report import badge_progress, text_bar

DEFAULT_DAILY_RECIPIENTS = ["him6ul@gmail.com"]
DEFAULTS = {"enabled": False, "smtp_host": "", "smtp_port": 587, "security": "starttls", "username": "",
            "password": "", "from_addr": "", "recipients": [], "weekday": 6, "hour": 18,
            "daily_enabled": True, "daily_recipients": list(DEFAULT_DAILY_RECIPIENTS), "daily_hour": 20}
MIN_ACTIVE_SECONDS = 60          # a "day of activity" = at least a minute of active time, a run, or a test
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS email_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL, learner_id INTEGER, week TEXT, kind TEXT, recipients TEXT, subject TEXT, status TEXT, error TEXT
);
"""


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)
    if "email_log" not in db.TABLES:
        db.TABLES.append("email_log")


# ---------------------------------------------------------------------------
# settings (the password is stored locally and never sent back to the browser)
# ---------------------------------------------------------------------------
def settings():
    s = dict(DEFAULTS)
    s.update(db.get_setting("email", {}) or {})
    return s


def public_settings():
    s = settings()
    s["has_password"] = bool(s.pop("password"))
    s["smtp_ready"] = bool(s["smtp_host"] and (s["from_addr"] or s["username"]))
    s["configured"] = bool(s["smtp_ready"] and s["recipients"])
    s["daily_configured"] = bool(s["smtp_ready"] and s["daily_recipients"])
    s["next_daily"] = next_daily_time(s).isoformat(timespec="minutes") if s["daily_enabled"] else None
    s["last"] = db.q("SELECT ts, learner_id, week, kind, recipients, status, error FROM email_log ORDER BY ts DESC LIMIT 8")
    s["next_send"] = next_send_time(s).isoformat(timespec="minutes") if s["enabled"] else None
    return s


def save_settings(new):
    s = settings()
    for k in ("smtp_host", "username", "from_addr"):
        if k in new:
            s[k] = str(new[k]).strip()[:200]
    if "smtp_port" in new:
        s["smtp_port"] = max(1, min(65535, int(new["smtp_port"])))
    if new.get("security") in ("starttls", "ssl", "none"):
        s["security"] = new["security"]
    for key in ("recipients", "daily_recipients"):
        if key in new:
            s[key] = _addresses(new[key])
    if "daily_hour" in new:
        s["daily_hour"] = max(0, min(23, int(new["daily_hour"])))
    if "daily_enabled" in new:
        s["daily_enabled"] = bool(new["daily_enabled"])
    if "weekday" in new:
        s["weekday"] = max(0, min(6, int(new["weekday"])))
    if "hour" in new:
        s["hour"] = max(0, min(23, int(new["hour"])))
    if new.get("password"):                     # blank = keep the saved one
        s["password"] = str(new["password"])
    if new.get("clear_password"):
        s["password"] = ""
    if "enabled" in new:
        s["enabled"] = bool(new["enabled"])
    db.set_setting("email", s)
    return s


def _addresses(raw):
    """Comma/semicolon/newline separated (or a list) → de-duplicated list of plausible addresses (max 10)."""
    items = raw if isinstance(raw, list) else str(raw).replace(";", ",").replace("\n", ",").split(",")
    out = []
    for a in (str(x).strip() for x in items):
        if "@" in a and "." in a.split("@")[-1] and " " not in a and a.lower() not in [o.lower() for o in out]:
            out.append(a[:200])
    return out[:10]


def redacted(s):
    return {k: ("•••" if k == "password" and v else v) for k, v in s.items()}


# ---------------------------------------------------------------------------
# the digest
# ---------------------------------------------------------------------------
def _e(v):
    return html.escape(str(v if v is not None else ""))


def _bar_rows(label, got, total, color="#50709e"):
    pct = round(got / total * 100) if total else 0
    fill = max(pct, 1) if got else 0
    return f"""<tr><td style="padding:4px 10px 4px 0;font-size:13px;color:#444;white-space:nowrap">{_e(label)}</td>
<td style="width:100%;padding:4px 0"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse">
<tr>{f'<td width="{fill}%" style="background:{color};height:8px;border-radius:4px 0 0 4px;font-size:0;line-height:0">&nbsp;</td>' if fill else ''}
<td style="background:#e8e8e3;height:8px;font-size:0;line-height:0">&nbsp;</td></tr></table></td>
<td style="padding:4px 0 4px 10px;font-size:13px;font-weight:600;text-align:right;white-space:nowrap">{got}/{total}</td></tr>"""


def week_key(d=None):
    y, w, _ = (d or dt.date.today()).isocalendar()
    return f"{y}-W{w:02d}"


def build(learner_id):
    r = analytics.full_report(learner_id)
    L, projects, s = r["learner"], r["projects"], r["schedule"]
    bp = badge_progress(r["badges"])
    since = time.time() - 7 * 86400
    week_minutes = round(db.scalar("SELECT SUM(seconds) FROM time_log WHERE learner_id=? AND day>=?",
                                   (learner_id, (dt.date.today() - dt.timedelta(days=6)).isoformat())) / 60)
    week_missions = db.scalar("""SELECT COUNT(*) FROM step_progress WHERE learner_id=? AND status='done' AND completed_at>=?
                                 AND project_id!='_practice'""", (learner_id, since))
    week_quests = db.scalar("""SELECT COUNT(*) FROM step_progress WHERE learner_id=? AND status='done' AND completed_at>=?
                               AND project_id='_practice'""", (learner_id, since))
    new_badges = [b for b in r["badges"] if b["earned_at"] and b["earned_at"] >= since]
    week_runs = db.scalar("SELECT COUNT(*) FROM runs WHERE learner_id=? AND ts>=?", (learner_id, since))
    pos = r["guide"]["position"]
    nxt = f"{pos['project_title']} — {pos['step_title']}" if pos else "Everything is finished! 🎓"
    total_steps = sum(p["steps_total"] for p in projects)
    done_steps = sum(p["steps_done"] for p in projects)
    notes = r["guide"]["parent"][:3]
    subject = f"RoboQuest weekly: {L['name']} — 🏅 {text_bar(bp['earned'], bp['total'])} {bp['earned']}/{bp['total']} badges, {s['actual_pct']}% of the quest"
    kpi = lambda v, l: (f'<td style="padding:10px 12px;background:#f6f6f3;border:1px solid #e2e2dc;border-radius:8px">'
                        f'<div style="font-size:18px;font-weight:700">{v}</div><div style="font-size:12px;color:#6b6f76">{l}</div></td>')
    body = f"""<!doctype html><html><body style="margin:0;background:#f4f4f1;font-family:-apple-system,'Segoe UI',Inter,Arial,sans-serif;color:#22252a">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border:1px solid #e2e2dc;border-radius:12px">
<tr><td style="padding:22px 24px 6px">
  <div style="font-size:12px;color:#6b6f76;font-weight:600;letter-spacing:.06em">ROBOQUEST · WEEKLY UPDATE</div>
  <div style="font-size:20px;font-weight:700;margin-top:4px">{_e(L['avatar'])} {_e(L['name'])}'s week</div>
  <div style="font-size:13px;color:#6b6f76">Week {s['calendar_week']} of 6 · schedule: <b>{_e(s['status'])}</b> ({s['actual_pct']}% done, plan {s['expected_pct']}%)</div>
</td></tr>
<tr><td style="padding:12px 24px"><table role="presentation" width="100%" cellpadding="0" cellspacing="6"><tr>
  {kpi(f"{week_minutes} min", "building this week")}{kpi(week_missions, "missions passed")}{kpi(week_quests, "side quests")}{kpi(week_runs, "robot runs")}
</tr></table></td></tr>
<tr><td style="padding:6px 24px"><div style="font-size:15px;font-weight:700;margin-bottom:6px">Badges collected</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
  {_bar_rows("All badges", bp["earned"], bp["total"])}
  {''.join(_bar_rows(c["name"], c["earned"], c["total"], "#7f99bd") for c in bp["categories"])}
  </table>
  <div style="font-size:13px;color:#444;margin-top:8px">{('New this week: ' + ', '.join(f'{_e(b["emoji"])} {_e(b["name"])}' for b in new_badges)) if new_badges else 'No new badges this week.'}</div>
</td></tr>
<tr><td style="padding:14px 24px 6px"><div style="font-size:15px;font-weight:700;margin-bottom:6px">Quest progress</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
  {_bar_rows("Missions", done_steps, total_steps)}
  {_bar_rows("Bosses beaten", sum(1 for p in projects if p["boss_done"]), len(projects))}
  {_bar_rows("Remixes built", sum(1 for p in projects if p["remixed"]), len(projects))}
  </table>
  <div style="font-size:13px;color:#444;margin-top:8px">Up next: <b>{_e(nxt)}</b></div>
</td></tr>
<tr><td style="padding:14px 24px 6px"><div style="font-size:15px;font-weight:700;margin-bottom:6px">Coaching notes</div>
  {''.join(f'<div style="border:1px solid #e2e2dc;border-left:3px solid #50709e;border-radius:6px;padding:8px 10px;margin:6px 0;font-size:13px"><b>{_e(n["title"])}</b><br><span style="color:#555">{_e(n["text"])}</span></div>' for n in notes) or '<div style="font-size:13px;color:#555">Nothing needs your attention this week. 👍</div>'}
</td></tr>
<tr><td style="padding:14px 24px 22px;font-size:12px;color:#8a8e94">Full details: open RoboQuest → Parent Zone. Sent by RoboQuest from your own computer.</td></tr>
</table></td></tr></table></body></html>"""
    text = "\n".join([
        f"RoboQuest weekly update — {L['name']}",
        f"Schedule: {s['status']} ({s['actual_pct']}% done, plan {s['expected_pct']}%)",
        f"This week: {week_minutes} min · {week_missions} missions · {week_quests} side quests · {week_runs} robot runs",
        f"Badges collected: {bp['earned']}/{bp['total']} (" + ", ".join(f"{c['name']} {c['earned']}/{c['total']}" for c in bp["categories"]) + ")",
        f"New badges: {', '.join(b['name'] for b in new_badges) or 'none'}",
        f"Missions {done_steps}/{total_steps} · bosses {sum(1 for p in projects if p['boss_done'])}/{len(projects)} · remixes {sum(1 for p in projects if p['remixed'])}/{len(projects)}",
        f"Up next: {nxt}",
        "", "Coaching notes:", *[f"- {n['title']}: {n['text']}" for n in notes],
    ])
    return {"subject": subject, "html": body, "text": text, "badge_progress": bp}


# ---------------------------------------------------------------------------
# sending
# ---------------------------------------------------------------------------
class EmailError(Exception):
    pass


def _send(s, subject, text, html_body, recipients=None):
    recipients = s["recipients"] if recipients is None else recipients
    if not (s["smtp_host"] and recipients):
        raise EmailError("Set the SMTP server and at least one recipient first.")
    msg = EmailMessage()
    sender = s["from_addr"] or s["username"]
    msg["From"] = formataddr(("RoboQuest", sender))
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain=sender.split("@")[-1] if "@" in sender else None)
    msg.set_content(text)
    msg.add_alternative(html_body, subtype="html")
    ctx = ssl.create_default_context()
    try:
        if s["security"] == "ssl":
            server = smtplib.SMTP_SSL(s["smtp_host"], s["smtp_port"], timeout=20, context=ctx)
        else:
            server = smtplib.SMTP(s["smtp_host"], s["smtp_port"], timeout=20)
        with server:
            if s["security"] == "starttls":
                server.starttls(context=ctx)
            if s["username"]:
                server.login(s["username"], s["password"])
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        raise EmailError("The SMTP server rejected the username/password. (For Gmail, use an app password.)")
    except (smtplib.SMTPException, OSError) as e:
        raise EmailError(f"Couldn't send: {type(e).__name__}: {e}")


def send_digest(learner_id, kind="weekly", actor="system", request=None):
    s = settings()
    d = build(learner_id)
    wk = week_key()
    t0 = time.perf_counter()
    try:
        _send(s, d["subject"] if kind == "weekly" else "[Test] " + d["subject"], d["text"], d["html"])
    except EmailError as e:
        db.ex("INSERT INTO email_log(ts, learner_id, week, kind, recipients, subject, status, error) VALUES(?,?,?,?,?,?,?,?)",
              (time.time(), learner_id, wk, kind, ", ".join(s["recipients"]), d["subject"], "failed", str(e)[:300]))
        obs.record("email.failed")
        obs.audit(actor, "email.failed", "learner", learner_id, {"kind": kind, "week": wk, "error": str(e)[:200]}, request)
        raise
    obs.record("email.sent", (time.perf_counter() - t0) * 1000)
    db.ex("INSERT INTO email_log(ts, learner_id, week, kind, recipients, subject, status, error) VALUES(?,?,?,?,?,?,?,?)",
          (time.time(), learner_id, wk, kind, ", ".join(s["recipients"]), d["subject"], "sent", None))
    obs.audit(actor, "email.sent", "learner", learner_id,
              {"kind": kind, "week": wk, "recipients": len(s["recipients"]), "badges": f"{d['badge_progress']['earned']}/{d['badge_progress']['total']}"},
              request)
    return {"ok": True, "subject": d["subject"], "recipients": s["recipients"]}


# ---------------------------------------------------------------------------
# daily activity email
# ---------------------------------------------------------------------------
def _day_bounds(day):
    start = dt.datetime.combine(day, dt.time()).timestamp()
    return start, start + 86400


def day_activity(learner_id, day):
    """Everything he did on one calendar day (local time)."""
    a, b = _day_bounds(day)
    L = (learner_id, a, b)
    from .curriculum import BY_ID, PRACTICE_BY_ID
    secs = db.scalar("SELECT SUM(seconds) FROM time_log WHERE learner_id=? AND day=?", (learner_id, day.isoformat()))
    passed = db.q("""SELECT project_id, step_id FROM step_progress WHERE learner_id=? AND status='done'
                     AND completed_at>=? AND completed_at<? ORDER BY completed_at""", L)
    missions, quests, bosses = [], [], []
    for r in passed:
        if r["project_id"] == "_practice":
            pr = PRACTICE_BY_ID.get(r["step_id"])
            quests.append(pr["title"] if pr else r["step_id"])
        elif r["project_id"] in BY_ID:
            p = BY_ID[r["project_id"]]
            if r["step_id"] == "boss":
                bosses.append(f"{p['emoji']} {p['title']}: {p['boss']['title']}")
            else:
                st = next((x for x in p["steps"] if x["id"] == r["step_id"]), None)
                missions.append(f"{p['emoji']} {p['title']}: {st['title'] if st else r['step_id']}")
    remixes = [f"{BY_ID[r['project_id']]['emoji']} {BY_ID[r['project_id']]['title']}" for r in
               db.q("SELECT DISTINCT project_id FROM remixes WHERE learner_id=? AND ts>=? AND ts<?", L) if r["project_id"] in BY_ID]
    from . import gamification
    badges = [f"{gamification.BADGES[r['badge_id']][0]} {gamification.BADGES[r['badge_id']][1]}" for r in
              db.q("SELECT badge_id FROM badges WHERE learner_id=? AND earned_at>=? AND earned_at<? ORDER BY earned_at", L)
              if r["badge_id"] in gamification.BADGES]
    runs = db.one("SELECT COUNT(*) n, COALESCE(SUM(crashes),0) c, COALESCE(SUM(distance),0) d, SUM(ok=0) e FROM runs WHERE learner_id=? AND ts>=? AND ts<?", L)
    tests = db.one("SELECT COUNT(*) n, COALESCE(SUM(passed),0) p FROM checks WHERE learner_id=? AND ts>=? AND ts<?", L)
    return {
        "minutes": round((secs or 0) / 60), "seconds": secs or 0,
        "sessions": db.scalar("SELECT COUNT(*) FROM learning_sessions WHERE learner_id=? AND last_seen>=? AND started_at<?", L),
        "missions": missions, "side_quests": quests, "bosses": bosses, "remixes": remixes, "badges": badges,
        "runs": runs["n"], "crashes": runs["c"], "errors": runs["e"] or 0, "distance_m": round(runs["d"] / 100, 1),
        "tests": tests["n"], "tests_passed": tests["p"],
        "hints": db.scalar("SELECT COUNT(*) FROM hints WHERE learner_id=? AND ts>=? AND ts<?", L),
        "ideas": db.scalar("SELECT COUNT(*) FROM ideas WHERE learner_id=? AND ts>=? AND ts<?", L),
        "drive_minutes": round(db.scalar("SELECT SUM(seconds) FROM drive_sessions WHERE learner_id=? AND started_at>=? AND started_at<?", L) / 60, 1),
        "xp": db.scalar("SELECT SUM(amount) FROM xp_log WHERE learner_id=? AND ts>=? AND ts<?", L),
    }


def had_activity(act):
    return act["seconds"] >= MIN_ACTIVE_SECONDS or act["runs"] or act["tests"]


def build_daily(learner_id, day=None):
    day = day or dt.date.today()
    act = day_activity(learner_id, day)
    r = analytics.full_report(learner_id)
    L, projects, sched = r["learner"], r["projects"], r["schedule"]
    bp = badge_progress(r["badges"])
    pos = r["guide"]["position"]
    nxt = f"{pos['project_title']} — {pos['step_title']}" if pos else "Everything is finished! 🎓"
    total_steps = sum(p["steps_total"] for p in projects)
    done_steps = sum(p["steps_done"] for p in projects)
    streak = r["activity"]["streak"]["current"]
    day_label = day.strftime("%A, %b %d")
    n_m = len(act["missions"]) + len(act["bosses"])
    subject = (f"RoboQuest today: {L['name']} — {act['minutes']} min, {n_m} mission{'' if n_m == 1 else 's'}, "
               f"🏅 {text_bar(bp['earned'], bp['total'])} {bp['earned']}/{bp['total']}")

    def items(title, xs):
        if not xs:
            return ""
        return (f'<div style="font-size:13px;margin:8px 0 2px;font-weight:700">{_e(title)}</div>'
                + "".join(f'<div style="font-size:13px;color:#444;padding:2px 0">• {_e(x)}</div>' for x in xs))

    kpi = lambda v, l: (f'<td style="padding:10px 12px;background:#f6f6f3;border:1px solid #e2e2dc;border-radius:8px">'
                        f'<div style="font-size:18px;font-weight:700">{v}</div><div style="font-size:12px;color:#6b6f76">{l}</div></td>')
    done_today = act["missions"] or act["bosses"] or act["side_quests"] or act["remixes"]
    body = f"""<!doctype html><html><body style="margin:0;background:#f4f4f1;font-family:-apple-system,'Segoe UI',Inter,Arial,sans-serif;color:#22252a">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border:1px solid #e2e2dc;border-radius:12px">
<tr><td style="padding:22px 24px 6px">
  <div style="font-size:12px;color:#6b6f76;font-weight:600;letter-spacing:.06em">ROBOQUEST · DAILY ACTIVITY</div>
  <div style="font-size:20px;font-weight:700;margin-top:4px">{_e(L['avatar'])} {_e(L['name'])} — {_e(day_label)}</div>
  <div style="font-size:13px;color:#6b6f76">Week {sched['calendar_week']} of 6 · {_e(sched['status'])} · 🔥 {streak}-day streak</div>
</td></tr>
<tr><td style="padding:12px 24px"><table role="presentation" width="100%" cellpadding="0" cellspacing="6"><tr>
  {kpi(f"{act['minutes']} min", "active today")}{kpi(len(act['missions']) + len(act['bosses']), "missions passed")}
  {kpi(act['side_quests'].__len__(), "side quests")}{kpi(f"+{act['xp']}", "XP earned")}
</tr></table></td></tr>
<tr><td style="padding:4px 24px">
  <div style="font-size:15px;font-weight:700;margin-bottom:2px">Today's progress</div>
  {items("Missions passed", act["missions"])}{items("Bosses beaten 👾", act["bosses"])}{items("Side quests", act["side_quests"])}
  {items("Remixes built 🎛️", act["remixes"])}{items("New badges", act["badges"])}
  {'' if done_today else '<div style="font-size:13px;color:#555">No missions finished today — he was experimenting and practising.</div>'}
  <div style="font-size:13px;color:#555;margin-top:10px">{act['runs']} robot runs ({act['crashes']} bumps, {act['errors']} with a code error) ·
    {act['tests_passed']}/{act['tests']} tests passed · {act['hints']} hints · {act['distance_m']} m driven
    {f"· {act['drive_minutes']} min in Drive mode" if act['drive_minutes'] else ""}{f" · {act['ideas']} new ideas" if act['ideas'] else ""}</div>
</td></tr>
<tr><td style="padding:14px 24px 6px"><div style="font-size:15px;font-weight:700;margin-bottom:6px">Overall</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
  {_bar_rows("Missions", done_steps, total_steps)}
  {_bar_rows("Badges", bp["earned"], bp["total"], "#7f99bd")}
  </table>
  <div style="font-size:13px;color:#444;margin-top:8px">Up next: <b>{_e(nxt)}</b></div>
</td></tr>
<tr><td style="padding:14px 24px 22px;font-size:12px;color:#8a8e94">Sent by RoboQuest on your computer because {_e(L['name'])} was active today.
  Change recipients in Parent Zone → Settings → Daily activity email.</td></tr>
</table></td></tr></table></body></html>"""
    text = "\n".join(x for x in [
        f"RoboQuest daily activity — {L['name']} — {day_label}",
        f"Active {act['minutes']} min · {len(act['missions']) + len(act['bosses'])} missions · {len(act['side_quests'])} side quests · +{act['xp']} XP · {streak}-day streak",
        *(["Missions: " + "; ".join(act["missions"])] if act["missions"] else []),
        *(["Bosses: " + "; ".join(act["bosses"])] if act["bosses"] else []),
        *(["Side quests: " + "; ".join(act["side_quests"])] if act["side_quests"] else []),
        *(["Remixes: " + "; ".join(act["remixes"])] if act["remixes"] else []),
        *(["New badges: " + ", ".join(act["badges"])] if act["badges"] else []),
        f"{act['runs']} robot runs ({act['crashes']} bumps) · {act['tests_passed']}/{act['tests']} tests passed · {act['hints']} hints",
        f"Overall: missions {done_steps}/{total_steps} · badges {bp['earned']}/{bp['total']} {text_bar(bp['earned'], bp['total'])}",
        f"Up next: {nxt}",
    ])
    return {"subject": subject, "html": body, "text": text, "activity": act, "had_activity": bool(had_activity(act))}


def send_daily(learner_id, day=None, kind="daily", actor="system", request=None):
    s = settings()
    day = day or dt.date.today()
    d = build_daily(learner_id, day)
    recips = s["daily_recipients"]
    try:
        _send(s, d["subject"] if kind == "daily" else "[Test] " + d["subject"], d["text"], d["html"], recips)
    except EmailError as e:
        db.ex("INSERT INTO email_log(ts, learner_id, week, kind, recipients, subject, status, error) VALUES(?,?,?,?,?,?,?,?)",
              (time.time(), learner_id, day.isoformat(), kind, ", ".join(recips), d["subject"], "failed", str(e)[:300]))
        obs.record("email.failed")
        obs.audit(actor, "email.failed", "learner", learner_id, {"kind": kind, "day": day.isoformat(), "error": str(e)[:200]}, request)
        raise
    obs.record("email.sent")
    db.ex("INSERT INTO email_log(ts, learner_id, week, kind, recipients, subject, status, error) VALUES(?,?,?,?,?,?,?,?)",
          (time.time(), learner_id, day.isoformat(), kind, ", ".join(recips), d["subject"], "sent", None))
    obs.audit(actor, "email.sent", "learner", learner_id,
              {"kind": kind, "day": day.isoformat(), "recipients": len(recips), "minutes": d["activity"]["minutes"]}, request)
    return {"ok": True, "subject": d["subject"], "recipients": recips}


def next_daily_time(s, now=None):
    now = now or dt.datetime.now()
    slot = now.replace(hour=s["daily_hour"], minute=0, second=0, microsecond=0)
    return slot if now < slot else slot + dt.timedelta(days=1)


def due_daily(now=None):
    """[(learner_id, day)] whose daily email is due: an active day, past the send hour, not yet sent (catch up 2 days)."""
    s = settings()
    if not (s["daily_enabled"] and s["daily_recipients"]):
        return []
    now = now or dt.datetime.now()
    days = [now.date() - dt.timedelta(days=k) for k in (2, 1)]
    if now.hour >= s["daily_hour"]:
        days.append(now.date())
    out = []
    for L in db.q("SELECT id FROM learners"):
        for day in days:
            key = day.isoformat()
            if db.scalar("SELECT COUNT(*) FROM email_log WHERE learner_id=? AND week=? AND kind='daily' AND status='sent'", (L["id"], key)):
                continue
            if db.scalar("""SELECT COUNT(*) FROM email_log WHERE learner_id=? AND week=? AND kind='daily' AND status='failed'
                            AND ts > ?""", (L["id"], key, time.time() - 3600)) >= 2:
                continue                       # back off after repeated failures
            if had_activity(day_activity(L["id"], day)):
                out.append((L["id"], day))
    return out


# ---------------------------------------------------------------------------
# scheduler
# ---------------------------------------------------------------------------
def next_send_time(s, now=None):
    now = now or dt.datetime.now()
    this_week = (now - dt.timedelta(days=now.weekday())).replace(hour=s["hour"], minute=0, second=0, microsecond=0) \
        + dt.timedelta(days=s["weekday"])
    return this_week if now < this_week else this_week + dt.timedelta(days=7)


def due_learners(now=None):
    """Learners whose weekly email for this ISO week is due and not yet sent."""
    s = settings()
    if not s["enabled"]:
        return []
    now = now or dt.datetime.now()
    slot = (now - dt.timedelta(days=now.weekday())).replace(hour=s["hour"], minute=0, second=0, microsecond=0) \
        + dt.timedelta(days=s["weekday"])
    if now < slot:
        return []
    wk = week_key(now.date())
    out = []
    for L in db.q("SELECT id FROM learners"):
        if not db.scalar("SELECT COUNT(*) FROM email_log WHERE learner_id=? AND week=? AND kind='weekly' AND status='sent'", (L["id"], wk)):
            fails = db.scalar("""SELECT COUNT(*) FROM email_log WHERE learner_id=? AND week=? AND kind='weekly' AND status='failed'
                                 AND ts > ?""", (L["id"], wk, time.time() - 3600))
            if fails < 2:                        # back off after repeated failures (retry next hour)
                out.append(L["id"])
    return out


async def scheduler_loop():
    while True:
        try:
            for lid in due_learners():
                try:
                    await asyncio.to_thread(send_digest, lid)
                except EmailError:
                    pass
            if settings()["smtp_host"]:
                for lid, day in due_daily():
                    try:
                        await asyncio.to_thread(send_daily, lid, day)
                    except EmailError:
                        pass
        except Exception as e:  # noqa: BLE001
            obs.app_error("email.scheduler", e)
        await asyncio.sleep(300)
