"""Printable parent report: one self-contained HTML page built from analytics.full_report()."""
import datetime as dt
import html

from . import gamification

CATS = ["Quest milestones", "Bosses", "Remixes", "Side quests", "Skills & habits"]

CSS = """
:root { --text:#22252a; --muted:#6b6f76; --line:#e2e2dc; --bg:#ffffff; --soft:#f6f6f3; --accent:#50709e; --good:#3f8a67; --warn:#a77a26; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font: 14px/1.5 Inter, system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 900px; margin: 0 auto; padding: 32px 24px 48px; }
h1 { font-size: 1.6rem; margin: 0 0 4px; }
.titlebar { font-size: .95rem; font-weight: 600; color: var(--accent); letter-spacing: .02em; white-space: nowrap; margin-left: 8px; } h2 { font-size: 1.1rem; margin: 26px 0 10px; padding-bottom: 6px; border-bottom: 1px solid var(--line); }
.muted { color: var(--muted); } .small { font-size: .85rem; }
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 16px; }
.kpi { background: var(--soft); border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; }
.kpi .v { font-size: 1.3rem; font-weight: 650; } .kpi .l { color: var(--muted); font-size: .78rem; font-weight: 600; }
.bar { height: 8px; background: #ececE6; border-radius: 99px; overflow: hidden; }
.bar i { display: block; height: 100%; background: var(--accent); border-radius: 99px; }
.barrow { display: grid; grid-template-columns: 150px 1fr 60px; gap: 10px; align-items: center; margin: 6px 0; }
.barrow b { text-align: right; font-variant-numeric: tabular-nums; }
table { width: 100%; border-collapse: collapse; font-size: .86rem; }
th { text-align: left; color: var(--muted); font-weight: 600; border-bottom: 1px solid var(--line); padding: 6px; }
td { border-bottom: 1px solid var(--line); padding: 6px; vertical-align: top; }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
.note { border: 1px solid var(--line); border-left: 3px solid var(--accent); border-radius: 8px; padding: 8px 12px; margin: 8px 0; }
.note b { display: block; }
.badges { display: flex; flex-wrap: wrap; gap: 6px; }
.badge { border: 1px solid var(--line); border-radius: 999px; padding: 2px 10px; font-size: .82rem; background: var(--soft); }
.pill { display: inline-block; border-radius: 999px; padding: 0 8px; font-size: .78rem; font-weight: 600; background: var(--soft); border: 1px solid var(--line); }
.pill.good { color: var(--good); } .pill.warn { color: var(--warn); }
.print { position: fixed; right: 18px; top: 18px; }
.print button { font: 600 .9rem Inter, system-ui, sans-serif; padding: 7px 14px; border-radius: 8px; border: 1px solid var(--line); background: #fff; cursor: pointer; }
@media print { .print { display: none; } main { padding: 0; } h2 { break-after: avoid; } .note, tr { break-inside: avoid; } }
"""


def _e(v):
    return html.escape(str(v if v is not None else ""))


def _pct(v):
    return "—" if v is None else f"{round(v * 100)}%"


def _mins(sec):
    m = round((sec or 0) / 60)
    return f"{m} min" if m < 60 else f"{m // 60}h {m % 60}m"


def _bar(label, got, total):
    w = round(got / total * 100) if total else 0
    return f'<div class="barrow"><span>{_e(label)}</span><div class="bar"><i style="width:{w}%"></i></div><b>{got}/{total}</b></div>'


def text_bar(got, total, width=10):
    """A plain-text progress bar for places that can't show HTML (email subjects): ▰▰▰▱▱▱▱▱▱▱."""
    filled = 0 if not total else min(width, round(got / total * width))
    if got and not filled:
        filled = 1
    return "▰" * filled + "▱" * (width - filled)


def badge_progress(badges):
    """{"earned", "total", "categories": [{"name", "earned", "total"}]} — shared by the HTML and JSON exports."""
    cats = []
    for c in CATS:
        items = [b for b in badges if gamification.badge_category(b["id"]) == c]
        cats.append({"name": c, "earned": sum(1 for b in items if b["earned_at"]), "total": len(items)})
    return {"earned": sum(1 for b in badges if b["earned_at"]), "total": len(badges), "categories": cats}


def render(r):
    L, s, a, st, rb = r["learner"], r["schedule"], r["activity"], r["style"], r["robot"]
    projects = r["projects"]
    bp = badge_progress(r["badges"])
    built = sum(1 for p in projects if p["complete"])
    steps = sum(p["steps_done"] for p in projects)
    total_steps = sum(p["steps_total"] for p in projects)
    pill = {"ahead": "good", "on track": "good", "behind": "warn"}.get(s["status"], "")
    earned = sorted([b for b in r["badges"] if b["earned_at"]], key=lambda b: b["earned_at"])
    out = [f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>RoboQuest report — {_e(L['name'])} — 🏅 {text_bar(bp['earned'], bp['total'])} {bp['earned']}/{bp['total']} badges</title><style>{CSS}</style></head><body>
<div class="print"><button onclick="window.print()">Print / save as PDF</button></div><main>
<h1>RoboQuest progress report <span class="titlebar">🏅 {text_bar(bp['earned'], bp['total'])} {bp['earned']}/{bp['total']}</span></h1>
<div class="muted">{_e(L['avatar'])} {_e(L['name'])} · robot “{_e(L.get('robot_name', 'Bolt'))}” · plan started {_e(s['start_date'])} ·
generated {dt.datetime.now():%b %d, %Y %H:%M}</div>
<div class="kpis">
  <div class="kpi"><div class="v">{built}/{len(projects)}</div><div class="l">Robots built</div></div>
  <div class="kpi"><div class="v"><span class="pill {pill}">{_e(s['status'])}</span></div><div class="l">Schedule · day {s['days_in'] + 1} of 42</div></div>
  <div class="kpi"><div class="v">{_mins(a['total_minutes'] * 60)}</div><div class="l">Active building time · {a['sessions']} sessions</div></div>
  <div class="kpi"><div class="v">Lv {r['level']['level']}</div><div class="l">{_e(r['level']['title'])} · {r['level']['xp']} XP</div></div>
</div>

<h2>Progress</h2>
{_bar("Missions", steps, total_steps)}
{_bar("Bosses beaten", sum(1 for p in projects if p['boss_done']), len(projects))}
{_bar("Remixes built", sum(1 for p in projects if p['remixed']), len(projects))}
<p class="muted small">Plan expects {s['expected_pct']}% by today; actual {s['actual_pct']}%. Planned finish {_e(s['planned_finish'])}
{('· projected finish at current pace <b>' + _e(s['projected_finish']) + '</b>') if s.get('projected_finish') else ''}.</p>

<h2>Badges collected</h2>
{_bar("All badges", bp['earned'], bp['total'])}
{''.join(_bar(c['name'], c['earned'], c['total']) for c in bp['categories'])}
<div class="badges" style="margin-top:10px">{''.join(f'<span class="badge">{_e(b["emoji"])} {_e(b["name"])}</span>' for b in earned) or '<span class="muted">No badges yet.</span>'}</div>

<h2>Coaching notes</h2>
{''.join(f'<div class="note"><b>{_e(n["title"])}</b><span class="muted">{_e(n["text"])}</span></div>' for n in r['guide']['parent']) or '<p class="muted">Nothing needs attention right now.</p>'}

<h2>How he learns</h2>
<p><b>{_e(st['persona']['emoji'])} {_e(st['persona']['name'])}</b> — <span class="muted">{_e(st['persona']['desc'])}</span></p>
<table><tr>{''.join(f'<th class="n">{_e(k)}</th>' for k in st['traits'])}</tr>
<tr>{''.join(f'<td class="n">{round(v * 100)}</td>' for v in st['traits'].values())}</tr></table>
<p class="muted small">First-try pass rate {_pct(st['raw']['first_try_rate'])} · {st['raw']['hints_per_step']} hints per mission ·
{st['raw']['runs_per_check']} runs per test · code changes: {st['raw'].get('tune_edits', 0)} tunes / {st['raw'].get('small_edits', 0)} edits /
{st['raw'].get('rewrites', 0)} rewrites · runs with a robot crash {_pct(rb['crash_run_rate'])} · {rb['distance_m']} m driven · {rb['sensor_kinds']} sensor types used</p>

<h2>Robotics concepts</h2>
<table><tr><th>Concept</th><th>Status</th><th class="n">Mastery</th><th class="n">Missions</th><th class="n">Used on his own</th></tr>
{''.join(f'<tr><td>{_e(m["label"])}</td><td>{_e(m["status"])}</td><td class="n">{_pct(m["score"])}</td><td class="n">{m["steps_done"]}/{m["steps_total"]}</td><td class="n">{m["independent_uses"]}</td></tr>' for m in r['mastery'])}
</table>

<h2>Projects</h2>
<table><tr><th>Project</th><th class="n">Missions</th><th>Boss</th><th>Remix</th><th class="n">Time</th><th class="n">Expected</th><th class="n">Tests</th><th class="n">Hints</th><th>Fun / hard</th></tr>
{''.join(f'<tr><td>{_e(p["emoji"])} {_e(p["title"])}</td><td class="n">{p["steps_done"]}/{p["steps_total"]}</td><td>{"✓" if p["boss_done"] else "—"}</td><td>{"✓" if p["remixed"] else "—"}</td><td class="n">{_mins(p["seconds"])}</td><td class="n">{_mins(p["expected_seconds"])}</td><td class="n">{p["attempts"]}</td><td class="n">{p["hints"]}</td><td>{f"{p['fun']} / {p['difficulty']}" if p["fun"] else "—"}</td></tr>' for p in projects)}
</table>
<p class="muted small" style="margin-top:24px">Generated by RoboQuest on this computer. All data stays local.</p>
</main></body></html>"""]
    return "".join(out)
