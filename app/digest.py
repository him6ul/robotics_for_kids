"""Weekly parent email: build the digest, send it over SMTP, and a small scheduler that sends it once a week.

Off until a parent configures SMTP in Parent Zone → Settings → Weekly email. It only sends while RoboQuest is
running; if the app was off at the scheduled time it sends at the next start in the same week.
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
from .report import badge_progress

DEFAULTS = {"enabled": False, "smtp_host": "", "smtp_port": 587, "security": "starttls", "username": "",
            "password": "", "from_addr": "", "recipients": [], "weekday": 6, "hour": 18}
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
    s["configured"] = bool(s["smtp_host"] and s["recipients"] and (s["from_addr"] or s["username"]))
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
    if "recipients" in new:
        raw = new["recipients"] if isinstance(new["recipients"], list) else str(new["recipients"]).replace(";", ",").split(",")
        s["recipients"] = [r.strip() for r in raw if "@" in r.strip()][:10]
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
    subject = f"RoboQuest weekly: {L['name']} — {bp['earned']}/{bp['total']} badges, {s['actual_pct']}% of the quest"
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


def _send(s, subject, text, html_body):
    if not (s["smtp_host"] and s["recipients"]):
        raise EmailError("Set the SMTP server and at least one recipient first.")
    msg = EmailMessage()
    sender = s["from_addr"] or s["username"]
    msg["From"] = formataddr(("RoboQuest", sender))
    msg["To"] = ", ".join(s["recipients"])
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
        except Exception as e:  # noqa: BLE001
            obs.app_error("email.scheduler", e)
        await asyncio.sleep(300)
