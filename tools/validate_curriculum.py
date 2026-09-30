"""Validate the curriculum: every solution must pass its check, every starter must fail.

Usage: python tools/validate_curriculum.py [week_number ...]
"""
import importlib
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
CHECKER = os.path.join(ROOT, "app", "sandbox", "robocheck.py")
LIVE = os.path.join(ROOT, "app", "sandbox", "robolive.py")
from app.sandbox.kidast import CONCEPTS  # noqa: E402

CONCEPTS = set(CONCEPTS)
HTML_OK = {"p", "b", "i", "code", "pre", "ul", "li", "br", "ol", "em", "strong"}


def check(source, snippet, arena):
    t0 = time.time()
    p = subprocess.run([sys.executable, CHECKER], input=json.dumps({"source": source, "check": snippet, "arena": arena}),
                       capture_output=True, text=True, timeout=30)
    try:
        r = json.loads(p.stdout)
    except json.JSONDecodeError:
        r = {"passed": False, "message": "checker produced no JSON: " + p.stderr[-800:], "checker_error": True}
    r["secs"] = round(time.time() - t0, 2)
    return r


def live(source, arena):
    p = subprocess.run([sys.executable, LIVE], input=json.dumps({"source": source, "arena": arena}),
                       capture_output=True, text=True, timeout=30)
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return {"error": {"type": "runner", "msg": p.stderr[-800:]}}


def items_for(mod):
    for p in getattr(mod, "PROJECTS", []):
        for s in p["steps"] + ([p["boss"]] if p.get("boss") else []):
            yield f"{p['id']}/{s['id']}", s
    for pr in getattr(mod, "PRACTICE", []):
        yield f"practice/{pr['id']}", pr


def html_problems(key, field, html):
    import re
    bad = {t for t in re.findall(r"</?([a-zA-Z0-9]+)", html or "") if t.lower() not in HTML_OK}
    return [f"{key}: {field} uses tags {sorted(bad)}"] if bad else []


def structural(mod):
    problems = []
    for p in getattr(mod, "PROJECTS", []):
        for key in ("id", "week", "order", "title", "emoji", "tagline", "story", "concepts",
                    "expected_minutes", "steps", "boss", "remix", "real_world"):
            if key not in p:
                problems.append(f"{p.get('id')}: missing {key}")
        if len(p.get("steps", [])) != 5:
            problems.append(f"{p.get('id')}: needs exactly 5 steps (has {len(p.get('steps', []))})")
        if "arena" not in p.get("remix", {}):
            problems.append(f"{p.get('id')}: remix needs an arena")
        for c in p.get("concepts", []):
            if c not in CONCEPTS:
                problems.append(f"{p['id']}: unknown concept {c}")
        ids = [s.get("id") for s in p.get("steps", [])]
        if ids != [f"s{i}" for i in range(1, len(ids) + 1)]:
            problems.append(f"{p.get('id')}: step ids must be s1..s5, got {ids}")
        if (p.get("boss") or {}).get("id") != "boss":
            problems.append(f"{p.get('id')}: boss id must be 'boss'")
        for s in p.get("steps", []) + [p.get("boss") or {}]:
            k = f"{p['id']}/{s.get('id')}"
            for key in ("id", "title", "learn", "task", "goals", "arena", "starter", "hints", "solution", "check", "concepts", "xp"):
                if key not in s:
                    problems.append(f"{k}: missing {key}")
            if len(s.get("hints", [])) != 3:
                problems.append(f"{k}: needs exactly 3 hints")
            for c in s.get("concepts", []):
                if c not in CONCEPTS:
                    problems.append(f"{k}: unknown concept {c}")
            problems += html_problems(k, "learn", s.get("learn")) + html_problems(k, "task", s.get("task"))
    for pr in getattr(mod, "PRACTICE", []):
        k = f"practice/{pr.get('id')}"
        if pr.get("concept") not in CONCEPTS:
            problems.append(f"{k}: unknown concept {pr.get('concept')}")
        for key in ("id", "concept", "title", "difficulty", "task", "goals", "arena", "starter", "hints", "solution", "check", "xp"):
            if key not in pr:
                problems.append(f"{k}: missing {key}")
        if not str(pr.get("id", "")).startswith("p_"):
            problems.append(f"{k}: practice ids must start with p_")
        problems += html_problems(k, "task", pr.get("task"))
    return problems


def validate(week):
    mod = importlib.import_module(f"app.curriculum.week{week}")
    problems = structural(mod)
    items = list(items_for(mod))
    remixes = [(f"{p['id']}/remix-arena", p) for p in getattr(mod, "PROJECTS", []) if p.get("remix", {}).get("arena")]

    def one(ks):
        key, s = ks
        out = []
        good = check(s["solution"], s["check"], s["arena"])
        if not good.get("passed"):
            out.append(f"{key}: SOLUTION FAILS -> {good.get('message')}")
        elif good["secs"] > 6:
            out.append(f"{key}: check is slow ({good['secs']}s)")
        bad = check(s["starter"], s["check"], s["arena"])
        if bad.get("passed"):
            out.append(f"{key}: starter already passes")
        if bad.get("checker_error"):
            out.append(f"{key}: checker error on starter -> {bad.get('message')}")
        lv = live(s["solution"], s["arena"])
        if lv.get("error"):
            out.append(f"{key}: solution crashes when Run in the arena -> {lv['error']}")
        return out, good.get("secs", 0)

    def remix(kp):
        key, p = kp
        lv = live(p["steps"][-1]["solution"], p["remix"]["arena"])
        return [f"{key}: last solution crashes in the remix arena -> {lv['error']}"] if lv.get("error") else []

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(one, items))
        rres = list(ex.map(remix, remixes))
    for out, _ in results:
        problems += out
    for out in rres:
        problems += out
    slowest = max((s for _, s in results), default=0)
    return len(items), problems, slowest


def main():
    weeks = [int(a) for a in sys.argv[1:]] or [1, 2, 3, 4, 5, 6]
    total, all_problems = 0, []
    for w in weeks:
        try:
            n, probs, slow = validate(w)
        except ModuleNotFoundError:
            print(f"week {w}: (missing)")
            continue
        total += n
        all_problems += probs
        print(f"week {w}: {n} items, {len(probs)} problems, slowest check {slow}s")
        for p in probs:
            print("   -", p)
    # ids must be unique across the whole program
    from collections import Counter
    seen = Counter()
    for w in weeks:
        try:
            mod = importlib.import_module(f"app.curriculum.week{w}")
        except ModuleNotFoundError:
            continue
        seen.update(p["id"] for p in getattr(mod, "PROJECTS", []))
        seen.update(p["id"] for p in getattr(mod, "PRACTICE", []))
    for k, n in seen.items():
        if n > 1:
            all_problems.append(f"duplicate id across weeks: {k}")
            print("   - duplicate id across weeks:", k)
    print(f"\n{total} items checked, {len(all_problems)} problems")
    sys.exit(1 if all_problems else 0)


if __name__ == "__main__":
    main()
