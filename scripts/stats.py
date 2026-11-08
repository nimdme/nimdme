#!/usr/bin/env python3
"""Build the "On GitHub" stats panel from your own GitHub data.

  STATS_TOKEN=... python3 scripts/stats.py --user nimdme --out dist/stats.svg
  python3 scripts/stats.py --demo --out preview.svg     # fake data, no network

Token: a classic personal access token with read:user (add repo to include
private repositories in the language breakdown).
"""
import argparse, datetime, json, math, os, sys, urllib.request

INCLUDE_PRIVATE_LANGUAGES = True
LANG_COLORS = ["#f08a5d", "#e8917f", "#f6c46f", "#9886e6", "#8fb8cc", "#f2ab9a"]
OTHER = "#4a6476"

def gql(token, query, variables):
    req = urllib.request.Request("https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "nimdme-stats"})
    with urllib.request.urlopen(req, timeout=30) as r:
        p = json.load(r)
    if p.get("errors"):
        sys.exit(f"GitHub API error: {p['errors']}")
    return p["data"]

CAL = "contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}"

def fetch(user, token):
    q = f"""query($login:String!){{user(login:$login){{
      createdAt
      repositories(ownerAffiliations:OWNER,isFork:false,first:100){{totalCount nodes{{isPrivate stargazerCount
        languages(first:10,orderBy:{{field:SIZE,direction:DESC}}){{edges{{size node{{name}}}}}}}}}}
      contributionsCollection{{contributionYears totalCommitContributions totalPullRequestContributions totalIssueContributions {CAL}}}
    }}}}"""
    u = gql(token, q, {"login": user})["user"]
    years = sorted(u["contributionsCollection"]["contributionYears"])
    parts = " ".join(f'y{y}:contributionsCollection(from:"{y}-01-01T00:00:00Z",to:"{y}-12-31T23:59:59Z"){{{CAL}}}' for y in years)
    yd = gql(token, f"query($login:String!){{user(login:$login){{{parts}}}}}", {"login": user})["user"]
    days = {}
    for y in years:
        for w in yd[f"y{y}"]["contributionCalendar"]["weeks"]:
            for d in w["contributionDays"]:
                days[d["date"]] = d["contributionCount"]
    cc = u["contributionsCollection"]
    langs = {}
    stars = 0; public = 0
    for r in u["repositories"]["nodes"]:
        if not r["isPrivate"]:
            stars += r["stargazerCount"]; public += 1
        if r["isPrivate"] and not INCLUDE_PRIVATE_LANGUAGES:
            continue
        for e in r["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    last_year = [(d["date"], d["contributionCount"]) for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    return dict(days=days, last_year=last_year, year_total=cc["contributionCalendar"]["totalContributions"],
                commits=cc["totalCommitContributions"], prs=cc["totalPullRequestContributions"], issues=cc["totalIssueContributions"],
                langs=langs, stars=stars, repos=public, since=int(u["createdAt"][:4]))

def demo():
    import random
    rnd = random.Random(3); today = datetime.date.today(); days = {}
    d = datetime.date(2022, 6, 13)
    while d <= today:
        days[d.isoformat()] = 0 if rnd.random() < 0.7 else rnd.choice([1, 1, 2, 3, 5])
        d += datetime.timedelta(days=1)
    for k in range(6):
        days[(today - datetime.timedelta(days=k)).isoformat()] = 2
    start = today - datetime.timedelta(days=364)
    last = [(k, v) for k, v in sorted(days.items()) if k >= start.isoformat()]
    return dict(days=days, last_year=last, year_total=sum(v for _, v in last), commits=181, prs=4, issues=3,
                langs={"TypeScript": 49, "JavaScript": 19, "HTML": 20, "CSS": 12, "Python": 6, "Shell": 3}, stars=12, repos=14, since=2022)

def streaks(days):
    ds = sorted(days)
    best = cur = 0; best_end = best_start = None; run_start = None
    for k in ds:
        if days[k] > 0:
            if cur == 0: run_start = k
            cur += 1
            if cur > best: best, best_start, best_end = cur, run_start, k
        else:
            cur = 0
    today = datetime.date.today()
    day = today if days.get(today.isoformat(), 0) > 0 else today - datetime.timedelta(days=1)
    current = 0; cstart = None
    while days.get(day.isoformat(), 0) > 0:
        current += 1; cstart = day; day -= datetime.timedelta(days=1)
    return current, cstart, best, best_start, best_end

def fdate(s):
    if s is None: return ""
    d = s if isinstance(s, datetime.date) else datetime.date.fromisoformat(s)
    return f"{d.day} {d.strftime('%b %Y')}"

def f(x):
    s = ("%.1f" % x).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s

def build(D):
    W, H = 1000, 300
    SERIF = "Georgia,'Times New Roman',serif"; MONO = "'SFMono-Regular',Consolas,Menlo,monospace"; SANS = "'Segoe UI',Helvetica,Arial,sans-serif"
    total = sum(D["days"].values())
    cur, cstart, best, bstart, bend = streaks(D["days"])
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         f'aria-label="{total} contributions since {D["since"]}; {D["year_total"]} in the last year; current streak {cur} days; longest streak {best} days">']
    o.append('<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#14232e"/><stop offset="1" stop-color="#1d3344"/></linearGradient>'
             '<linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f08a5d" stop-opacity="0.35"/><stop offset="1" stop-color="#f08a5d" stop-opacity="0"/></linearGradient>'
             '<clipPath id="barclip"><rect x="0" y="0" width="0" height="20"><animate attributeName="width" from="0" to="440" begin="0.9s" dur="1.4s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.22 1 0.36 1"/></rect></clipPath></defs>')
    o.append(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14" fill="url(#bg)" stroke="#3b5a6f" stroke-width="2"/>')
    o.append(f'<text x="32" y="38" font-family="{SERIF}" font-size="18" fill="#9fb4c3"><tspan fill="#f08a5d" font-weight="700">{total:,}</tspan> contributions since {D["since"]}</text>')
    o.append(f'<text x="{W-32}" y="37" text-anchor="end" font-family="{MONO}" font-size="11" fill="#6f8798">{D["repos"]} public repos · {D["stars"]} stars earned · updated {fdate(datetime.date.today())}</text>')

    def rise(i, body):
        b = 0.15 + i * 0.12
        return (f'<g opacity="0" transform="translate(0,10)"><animate attributeName="opacity" from="0" to="1" begin="{b}s" dur="0.7s" fill="freeze"/>'
                f'<animateTransform attributeName="transform" type="translate" from="0,10" to="0,0" begin="{b}s" dur="0.9s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.22 1 0.36 1"/>{body}</g>')

    flame = ('<path d="M0,-11 C5,-5 7,-1 5,4 C4,8 -4,8 -5,4 C-6,0 -3,-3 -2,-6 C-1,-3 1,-2 1,-4 C1,-7 0,-9 0,-11Z" fill="#f08a5d">'
             '<animateTransform attributeName="transform" type="scale" values="1 1;0.94 1.06;1.03 0.96;1 1" dur="1.2s" repeatCount="indefinite"/></path>')
    tiles = [
        ("Last 12 months", f"{D['year_total']:,}", "contributions", None),
        ("Commits", f"{D['commits']:,}", f"{D['prs']} PRs · {D['issues']} issues, last 12 months", None),
        ("Current streak", f"{cur}", (f"day{'s' if cur != 1 else ''} · since {fdate(cstart)}" if cur else "no streak right now"), flame if cur else None),
        ("Longest streak", f"{best}", f"day{'s' if best != 1 else ''} · {fdate(bstart)} – {fdate(bend)}" if best else "", None),
    ]
    tw = (W - 64 - 3 * 14) / 4
    for i, (label, big, sub, icon) in enumerate(tiles):
        x = 32 + i * (tw + 14)
        body = (f'<rect x="{f(x)}" y="56" width="{f(tw)}" height="96" rx="10" fill="#162a37" stroke="#2c4659"/>'
                f'<text x="{f(x+16)}" y="78" font-family="{MONO}" font-size="11" fill="#6f8798">{label}</text>'
                f'<text x="{f(x+16)}" y="118" font-family="{SERIF}" font-size="34" font-weight="700" fill="#fdebe5">{big}</text>'
                f'<text x="{f(x+16)}" y="140" font-family="{SANS}" font-size="11" fill="#9fb4c3">{sub}</text>')
        if icon:
            body += f'<g transform="translate({f(x+tw-24)},84)">{icon}</g>'
        o.append(rise(i, body))

    # monthly sparkline for the last 12 months
    months = {}
    for d, c in D["last_year"]:
        months[d[:7]] = months.get(d[:7], 0) + c
    keys = sorted(months)[-12:]
    vals = [months[k] for k in keys]
    sx, sy, sw, sh = 32, 196, 470, 64
    mx = max(vals) or 1
    pts = [(sx + i * sw / (len(vals) - 1), sy + sh - v / mx * sh) for i, v in enumerate(vals)]
    line = "M" + " L".join(f"{f(x)},{f(y)}" for x, y in pts)
    area = line + f" L{f(pts[-1][0])},{sy+sh} L{f(pts[0][0])},{sy+sh}Z"
    o.append(f'<text x="{sx}" y="184" font-family="{MONO}" font-size="11" fill="#6f8798">contributions per month</text>')
    o.append(f'<path d="{area}" fill="url(#area)" opacity="0"><animate attributeName="opacity" from="0" to="1" begin="1.6s" dur="0.8s" fill="freeze"/></path>')
    o.append(f'<path d="{line}" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1" fill="none" stroke="#f08a5d" stroke-width="2" stroke-linejoin="round" stroke-linecap="round">'
             f'<animate attributeName="stroke-dashoffset" from="1" to="0" begin="0.8s" dur="1.6s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.4 0 0.2 1"/></path>')
    pk = vals.index(max(vals))
    px, py = pts[pk]
    o.append(f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="2.2s" dur="0.5s" fill="freeze"/><circle cx="{f(px)}" cy="{f(py)}" r="3.5" fill="#fdebe5"/>'
             f'<text x="{f(px)}" y="{f(py-9)}" text-anchor="middle" font-family="{MONO}" font-size="11" fill="#fdebe5">{max(vals)}</text></g>')
    for i, k in enumerate(keys):
        m = datetime.date.fromisoformat(k + "-01").strftime("%b")[0]
        o.append(f'<text x="{f(pts[i][0])}" y="{sy+sh+18}" text-anchor="middle" font-family="{MONO}" font-size="10" fill="#6f8798">{m}</text>')

    # languages
    lx, ly, lw = 528, 196, 440
    o.append(f'<text x="{lx}" y="184" font-family="{MONO}" font-size="11" fill="#6f8798">languages</text>')
    tot = sum(D["langs"].values()) or 1
    top = sorted(D["langs"].items(), key=lambda kv: -kv[1])[:5]
    rest = tot - sum(v for _, v in top)
    segs = [(n, v, LANG_COLORS[i]) for i, (n, v) in enumerate(top)] + ([("Other", rest, OTHER)] if rest / tot > 0.005 else [])
    x = 0; bar = ""
    for n, v, c in segs:
        w = v / tot * lw
        bar += f'<rect x="{f(x)}" y="0" width="{f(max(w-2,0))}" height="10" rx="3" fill="{c}"/>'
        x += w
    o.append(f'<g transform="translate({lx},{ly})"><rect width="{lw}" height="10" rx="3" fill="#162a37"/><g clip-path="url(#barclip)">{bar}</g></g>')
    for i, (n, v, c) in enumerate(segs):
        cx = lx + (i % 3) * 150; cy = ly + 34 + (i // 3) * 24
        o.append(rise(4 + i * 0.4, f'<circle cx="{cx+5}" cy="{cy-4}" r="4.5" fill="{c}"/>'
                 f'<text x="{cx+16}" y="{cy}" font-family="{SANS}" font-size="12" fill="#fdebe5">{n} <tspan fill="#6f8798">{v/tot*100:.1f}%</tspan></text>'))
    o.append('</svg>')
    return "\n".join(o)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=os.environ.get("GITHUB_USER", "nimdme"))
    ap.add_argument("--out", default="dist/stats.svg")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        D = demo()
    else:
        token = os.environ.get("STATS_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            sys.exit("Set STATS_TOKEN.")
        D = fetch(a.user, token)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(build(D))
    print(f"wrote {a.out}")

if __name__ == "__main__":
    main()
