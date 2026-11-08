#!/usr/bin/env python3
"""Turn a GitHub contribution calendar into an animated SVG flower garden.

Usage:
  GITHUB_TOKEN=... python3 scripts/garden.py --user USERNAME --out dist/contribution-garden.svg
  python3 scripts/garden.py --demo --out preview.svg      # fake data, no network
"""
import argparse, datetime, json, math, os, random, sys, urllib.request, zlib

PALETTE = ["#e8917f", "#9482e6", "#f2b45a", "#f2ab9a", "#8fb8cc"]  # coral, lavender, gold, blush, mist
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

def symbols():
    def petals(n, cy, rx, ry, op=1, extra=""):
        return "".join(f'<ellipse cx="0" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}" transform="rotate({f(k*360/n)})" opacity="{op}"{extra}/>' for k in range(n))
    s1 = (f'<symbol id="s1" overflow="visible"><path d="M0,4 L0,-1" stroke="{SAGE}" stroke-width="1.2" stroke-linecap="round" fill="none"/>'
          f'<ellipse cx="-2.2" cy="1.6" rx="2.3" ry="1" transform="rotate(-35 -2.2 1.6)" fill="{SAGE}"/>'
          f'<ellipse cx="2.2" cy="0.6" rx="2.3" ry="1" transform="rotate(35 2.2 0.6)" fill="{SAGE}"/>'
          f'<circle cx="0" cy="-2.6" r="2.3" fill="currentColor"/></symbol>')
    s2 = (f'<symbol id="s2" overflow="visible"><g fill="currentColor">{petals(5,-3.4,2.2,3.6)}</g>'
          f'<circle r="1.7" fill="#f6c46f"/></symbol>')
    s3 = (f'<symbol id="s3" overflow="visible"><g fill="currentColor">{petals(6,-4.4,2.7,4.6)}</g>'
          f'<g fill="#fff" opacity="0.28">{petals(6,-3.6,1.2,2.6)}</g><circle r="2.2" fill="#f6c46f"/></symbol>')
    s4 = (f'<symbol id="s4" overflow="visible"><circle r="13" fill="currentColor" opacity="0.14"><animate attributeName="opacity" values="0.08;0.26;0.08" dur="3.6s" repeatCount="indefinite"/></circle>'
          f'<g fill="currentColor">{petals(8,-5.4,2.9,5.6)}</g><g fill="currentColor" opacity="0.8" transform="rotate(22.5)">{petals(8,-3.8,2.2,3.8)}</g>'
          f'<g fill="#fff" opacity="0.25">{petals(8,-4.4,1.1,3)}</g><circle r="2.8" fill="#f6c46f"/><circle r="1.2" fill="#7a3b1d" opacity="0.6"/></symbol>')
    return s1 + s2 + s3 + s4

def build(weeks, total):
    W, H = 1000, 218
    X0, Y0, STEP = 40, 54, 17.5
    counts = [c for w in weeks for _, c, _ in w]
    lv = levels(counts)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Contribution garden: {total} contributions in the last year">']
    o.append('<defs><linearGradient id="gbg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#14232e"/><stop offset="1" stop-color="#1d3344"/></linearGradient>'
             + symbols() + '</defs>')
    o.append(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14" fill="url(#gbg)" stroke="#3b5a6f" stroke-width="2"/>')
    o.append(f'<text x="{X0}" y="34" font-family="Georgia,\'Times New Roman\',serif" font-size="17" fill="#9fb4c3"><tspan fill="#f08a5d" font-weight="700">{total:,}</tspan> contributions in the last year, grown into a garden</text>')

    soil, plants, months = [], [], []
    last_m, last_col = None, -9
    for col, week in enumerate(weeks):
        x = X0 + col * STEP
        m = datetime.date.fromisoformat(week[0][0]).strftime("%b")
        if m != last_m and col - last_col >= 3:
            months.append(f'<text x="{f(x)}" y="{f(Y0+7*STEP+16)}" font-family="\'SFMono-Regular\',Consolas,Menlo,monospace" font-size="11" fill="#6f8798">{m}</text>')
            last_col = col
        last_m = m
        for date, c, wd in week:
            y = Y0 + wd * STEP + STEP / 2
            cx = x + STEP / 2
            L = lv(c)
            if L == 0:
                soil.append(f'<circle cx="{f(cx)}" cy="{f(y)}" r="1.5"/>')
                continue
            h = zlib.crc32(date.encode())
            color = PALETTE[h % len(PALETTE)]
            rot = (h >> 3) % 360
            amp = 3 + (h >> 9) % 5
            sdur = 5 + (h >> 12) % 40 / 10
            sbeg = ((h >> 16) % 50) / 10
            delay = col * 0.035 + ((h >> 20) % 30) / 100
            sway = (f'<animateTransform attributeName="transform" type="rotate" values="{-amp};{amp};{-amp}" dur="{f(sdur)}s" begin="{f(sbeg)}s" '
                    f'repeatCount="indefinite" calcMode="spline" keySplines="0.45 0 0.55 1;0.45 0 0.55 1"/>')
            grow = (f'<animateTransform attributeName="transform" type="scale" values="0;1.15;1" keyTimes="0;0.65;1" dur="0.9s" begin="{f(delay)}s" fill="freeze" '
                    f'calcMode="spline" keySplines="0.3 0 0.4 1;0.4 0 0.6 1"/>')
            plants.append(f'<g transform="translate({f(cx)},{f(y)})"><g transform="scale(0)">{grow}<g>{sway}'
                          f'<use href="#s{L}" color="{color}" transform="rotate({rot})"/></g></g></g>')
    o.append('<g fill="#2a4558" opacity="0.9">' + "".join(soil) + '</g>')
    o.append("".join(plants))
    o.extend(months)
    # legend
    lx, ly = W - 40 - 150, Y0 + 7 * STEP + 12
    o.append(f'<text x="{lx-8}" y="{ly+4}" text-anchor="end" font-family="\'SFMono-Regular\',Consolas,Menlo,monospace" font-size="11" fill="#6f8798">less</text>')
    for i in range(4):
        o.append(f'<use href="#s{i+1}" x="{lx + i*30 + 8}" y="{ly}" color="{PALETTE[i % len(PALETTE)]}"/>')
    o.append(f'<text x="{lx+130}" y="{ly+4}" font-family="\'SFMono-Regular\',Consolas,Menlo,monospace" font-size="11" fill="#6f8798">more</text>')
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
