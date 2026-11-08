#!/usr/bin/env python3
"""Turn a GitHub contribution calendar into an animated night sky: each active day is a star,
brighter on busier days, with streaks joined into constellations.

Usage:
  GITHUB_TOKEN=... python3 scripts/garden.py --user USERNAME --out dist/contribution-garden.svg
  python3 scripts/garden.py --demo --out preview.svg      # fake data, no network
"""
import argparse, datetime, json, math, os, random, sys, urllib.request, zlib

LEVEL_COLORS = {1: "#8fa6b4", 2: "#f2ab9a", 3: "#e8917f", 4: "#f08a5d"}  # bud, blush, coral, orange
SAGE = "#78a894"
QUERY = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
totalContributions weeks{contributionDays{date contributionCount weekday}}}}}}"""

def fetch(user, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "contribution-garden"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload or not payload.get("data", {}).get("user"):
        sys.exit(f"GitHub API error: {payload.get('errors') or 'user not found'}")
    cal = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [[(d["date"], d["contributionCount"], d["weekday"]) for d in w["contributionDays"]] for w in cal["weeks"]]
    return weeks, cal["totalContributions"]

def demo():
    rnd = random.Random(5)
    end = datetime.date.today()
    start = end - datetime.timedelta(days=364)
    start -= datetime.timedelta(days=(start.weekday() + 1) % 7)  # back to Sunday
    weeks, day, total = [], start, 0
    while day <= end:
        w = []
        for _ in range(7):
            if day > end:
                break
            c = 0 if rnd.random() < 0.55 else rnd.choice([1, 1, 2, 3, 5, 8, 13])
            total += c
            w.append((day.isoformat(), c, (day.weekday() + 1) % 7))
            day += datetime.timedelta(days=1)
        weeks.append(w)
    return weeks, total

def f(x):
    s = ("%.1f" % x).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s

def levels(counts):
    nz = sorted(c for c in counts if c > 0)
    if not nz:
        return lambda c: 0
    q = lambda p: nz[int(p * (len(nz) - 1))]
    t1, t2, t3 = q(0.25), q(0.5), q(0.75)
    def lv(c):
        if c <= 0: return 0
        if c <= t1: return 1
        if c <= t2: return 2
        if c <= t3: return 3
        return 4
    return lv

def star_path(r, inner=0.28):
    pts = []
    for k in range(8):
        ang = -math.pi / 2 + k * math.pi / 4
        rr = r if k % 2 == 0 else r * inner
        pts.append(f"{f(rr*math.cos(ang))},{f(rr*math.sin(ang))}")
    return "M" + " L".join(pts) + "Z"

STAR = {  # level: (core radius, sparkle size, colour, glow radius)
    1: (1.5, 0, "#8fa6b4", 0),
    2: (1.9, 0, "#dbe7f2", 5),
    3: (1.6, 5.5, "#fdebe5", 7),
    4: (2.0, 7.5, "#f6c46f", 10),
}

def star(L, extra=""):
    core, sp, col, gl = STAR[L]
    g = ""
    if gl:
        g += f'<circle r="{gl}" fill="url(#halo{L})"/>'
    if sp:
        g += f'<path d="{star_path(sp)}" fill="{col}"/>'
    g += f'<circle r="{core}" fill="{col}"/>'
    return g

def build(weeks, total):
    W, H = 1000, 222
    STEP, Y0 = 17.5, 58
    X0 = (W - len(weeks) * STEP) / 2
    days = [(d, c, wd, col) for col, w in enumerate(weeks) for d, c, wd in w]
    lv = levels([c for _, c, _, _ in days])
    pos = {d: (X0 + col * STEP + STEP / 2, Y0 + wd * STEP + STEP / 2) for d, c, wd, col in days}

    # longest streak
    best = cur = 0
    for _, c, _, _ in days:
        cur = cur + 1 if c > 0 else 0
        best = max(best, cur)

    mono = "font-family=\"'SFMono-Regular',Consolas,Menlo,monospace\" font-size=\"11\" fill=\"#6f8798\""
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Contribution sky: {total} contributions in the last year, longest streak {best} days">']
    halos = "".join(f'<radialGradient id="halo{L}"><stop offset="0" stop-color="{STAR[L][2]}" stop-opacity="0.35"/><stop offset="1" stop-color="{STAR[L][2]}" stop-opacity="0"/></radialGradient>' for L in (2, 3, 4))
    o.append('<defs><linearGradient id="gbg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#101d28"/><stop offset="1" stop-color="#1a2f40"/></linearGradient>'
             '<linearGradient id="shoot" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fdebe5" stop-opacity="0"/></linearGradient>'
             + halos + '</defs>')
    o.append(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14" fill="url(#gbg)" stroke="#3b5a6f" stroke-width="2"/>')
    o.append(f'<text x="{f(X0)}" y="36" font-family="Georgia,\'Times New Roman\',serif" font-size="17" fill="#9fb4c3">'
             f'<tspan fill="#f08a5d" font-weight="700">{total:,}</tspan> contributions in the last year'
             f'<tspan fill="#6f8798"> · longest streak {best} day{"s" if best != 1 else ""}</tspan></text>')

    # faint dust for quiet days
    o.append('<g fill="#2f4a5e" opacity="0.5">' + "".join(
        f'<circle cx="{f(pos[d][0])}" cy="{f(pos[d][1])}" r="0.9"/>' for d, c, _, _ in days if c == 0) + '</g>')

    # constellations: join consecutive active days
    lines = []
    for (d1, c1, _, col), (d2, c2, _, _) in zip(days, days[1:]):
        if c1 > 0 and c2 > 0:
            (x1, y1), (x2, y2) = pos[d1], pos[d2]
            length = math.hypot(x2 - x1, y2 - y1)
            lines.append(f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" stroke-dasharray="{f(length)}" stroke-dashoffset="{f(length)}">'
                         f'<animate attributeName="stroke-dashoffset" from="{f(length)}" to="0" begin="{f(1.2 + col*0.04)}s" dur="0.8s" fill="freeze"/></line>')
    o.append('<g stroke="#8fa6b4" stroke-width="0.8" stroke-opacity="0.35" stroke-linecap="round">' + "".join(lines) + '</g>')

    # stars: fade in left to right, then twinkle
    for d, c, _, col in days:
        L = lv(c)
        if L == 0:
            continue
        x, y = pos[d]
        h = zlib.crc32(d.encode())
        tw = ""
        if L >= 2:
            dur = 2.5 + (h % 35) / 10
            lo = 0.55 if L >= 3 else 0.7
            tw = f'<animate attributeName="opacity" values="1;{lo};1" dur="{f(dur)}s" begin="{f((h >> 8) % 40 / 10)}s" repeatCount="indefinite"/>'
        rot = (h >> 4) % 45 if L >= 3 else 0
        o.append(f'<g transform="translate({f(x)},{f(y)})" opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{f(col*0.03)}s" dur="0.6s" fill="freeze"/>'
                 f'<g transform="rotate({rot})">{tw}{star(L)}</g></g>')

    # an occasional shooting star across the panel
    o.append('<g opacity="0"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.7;0.71;0.74;0.76;1" dur="24s" repeatCount="indefinite"/>'
             '<animateTransform attributeName="transform" type="translate" values="900,40;900,40;640,120;640,120" keyTimes="0;0.7;0.76;1" dur="24s" repeatCount="indefinite"/>'
             '<g transform="rotate(-17)"><rect x="0" y="-0.6" width="70" height="1.2" rx="0.6" fill="url(#shoot)"/><circle r="1.4" fill="#fff"/></g></g>')

    # month labels
    last_m, last_col = None, -9
    for col, week in enumerate(weeks):
        m = datetime.date.fromisoformat(week[0][0]).strftime("%b")
        if m != last_m and col - last_col >= 3 and col < len(weeks) - 2:
            o.append(f'<text x="{f(X0 + col*STEP)}" y="{f(Y0+7*STEP+16)}" {mono}>{m}</text>')
            last_col = col
        last_m = m

    # legend
    rx = X0 + len(weeks) * STEP
    o.append(f'<text x="{f(rx)}" y="35" text-anchor="end" {mono}>more</text>')
    for i, L in enumerate((4, 3, 2, 1)):
        o.append(f'<g transform="translate({f(rx - 44 - i*22)},31)">{star(L)}</g>')
    o.append(f'<text x="{f(rx - 44 - 3*22 - 14)}" y="35" text-anchor="end" {mono}>less</text>')
    o.append('</svg>')
    return "\n".join(o)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=os.environ.get("GITHUB_USER") or os.environ.get("GITHUB_REPOSITORY_OWNER"))
    ap.add_argument("--out", default="dist/contribution-garden.svg")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        weeks, total = demo()
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token or not a.user:
            sys.exit("Set GITHUB_TOKEN and --user (or GITHUB_USER).")
        weeks, total = fetch(a.user, token)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(build(weeks, total))
    print(f"wrote {a.out} ({total} contributions)")

if __name__ == "__main__":
    main()
