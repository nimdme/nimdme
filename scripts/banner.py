#!/usr/bin/env python3
"""Generate the animated profile banner, themed by Kerala's seasons and festivals.

  python3 scripts/banner.py --out dist/banner.svg --readme README.md   # today's theme (IST)
  python3 scripts/banner.py --theme onam --out preview.svg             # force a theme

Festival dates that move every year live in FESTIVAL_DATES. Add the next year's dates
once a year (the script prints a reminder when the current year has none).
"""
import argparse, datetime, math, os, random, re
from zoneinfo import ZoneInfo

# Kerala's seasons
SEASON_BY_MONTH = {12: "winter", 1: "winter", 2: "winter", 3: "summer", 4: "summer", 5: "summer",
                   6: "monsoon", 7: "monsoon", 8: "monsoon", 9: "monsoon", 10: "thulavarsham", 11: "thulavarsham"}

# Festivals whose dates move: (theme, first day, last day), inclusive, IST.
# Eid dates depend on moon sighting; adjust if Kerala announces a different day.
FESTIVAL_DATES = [
    ("eid_fitr", "2026-03-19", "2026-03-22"), ("vishu", "2026-04-13", "2026-04-16"),
    ("pooram", "2026-04-25", "2026-04-27"), ("bakrid", "2026-05-26", "2026-05-29"),
    ("onam", "2026-08-16", "2026-08-28"), ("deepavali", "2026-11-06", "2026-11-09"),
    ("eid_fitr", "2027-03-08", "2027-03-11"), ("vishu", "2027-04-13", "2027-04-16"),
    ("pooram", "2027-04-17", "2027-04-18"), ("bakrid", "2027-05-16", "2027-05-18"),
    ("onam", "2027-09-02", "2027-09-14"), ("deepavali", "2027-10-27", "2027-10-30"),
]
# Festivals on the same dates every year: (theme, "MM-DD", "MM-DD")
YEARLY = [("keralapiravi", "11-01", "11-01"), ("christmas", "12-18", "12-26")]

BRAND = [["#d9705f", "#e8917f", "#f2ab9a", "#fbd0c4"], ["#7766d0", "#9886e6", "#b6a8f2", "#ddd4fc"], ["#dc9234", "#f0b055", "#f8c97d", "#fde4b2"]]
GOLD = ["#d9a21f", "#ecbb34", "#f5d264", "#fbe7a6"]
WHITE = ["#c7d0da", "#dfe5ec", "#eef2f6", "#ffffff"]
MAGENTA = ["#a8337a", "#c24b92", "#d977ad", "#efaacd"]
THEMES = {
    "winter": dict(flowers=[WHITE, ["#6f97bf", "#8fb2d4", "#b3cbe5", "#dce9f6"], ["#8a84c4", "#a6a1d6", "#c4c0e8", "#e5e3f7"]],
                   center="#ead9a2", particles=["mist", "fireflies"]),
    "summer": dict(flowers=[["#c2402a", "#d9553a", "#ea7b5a", "#f6ab8f"], GOLD, MAGENTA], center="#f6c46f", particles=["gulmohar"]),
    "monsoon": dict(flowers=[["#c4567f", "#d9789b", "#eaa0ba", "#f8d3e0"], ["#c9d6d3", "#e1ebe8", "#eff5f3", "#ffffff"], BRAND[1]],
                    center="#f2c14e", particles=["rain"]),
    "thulavarsham": dict(flowers=BRAND, center="#f6c46f", particles=["drizzle", "lightning"]),
    "vishu": dict(flowers=[GOLD, ["#c98a1a", "#dea52e", "#eec45e", "#f8e1a0"], ["#e0b21e", "#f0c93a", "#f8dc72", "#fdf0b8"]], center="#e8a948",
                  particles=["konna"], caption="Vishu, the Malayalam New Year, greeted at dawn with the Vishukkani and golden konna flowers.",
                  wiki="https://en.wikipedia.org/wiki/Vishu"),
    "pooram": dict(flowers=[["#a8202e", "#c43a45", "#dc6870", "#f2a3a7"], GOLD, ["#2f7f8f", "#3f9aa8", "#6fbcc6", "#b4e0e5"]], center="#f6c46f",
                   particles=[], overlays=["fireworks"], caption="Thrissur Pooram, Kerala's grandest temple festival, famous for its elephants, percussion and fireworks.",
                   wiki="https://en.wikipedia.org/wiki/Thrissur_Pooram"),
    "eid_fitr": dict(flowers=[WHITE, ["#4f9f86", "#6fb9a0", "#9fd3c0", "#d3eee4"], GOLD], center="#f2d48a", particles=["fireflies"], overlays=["crescent"],
                     caption="Eid al-Fitr (Cheriya Perunnal), marking the end of Ramadan.", wiki="https://en.wikipedia.org/wiki/Eid_al-Fitr"),
    "bakrid": dict(flowers=[WHITE, ["#4f9f86", "#6fb9a0", "#9fd3c0", "#d3eee4"], GOLD], center="#f2d48a", particles=["fireflies"], overlays=["crescent"],
                   caption="Eid al-Adha (Bakrid, or Valiya Perunnal), the Feast of Sacrifice.", wiki="https://en.wikipedia.org/wiki/Eid_al-Adha"),
    "onam": dict(flowers=[["#c93a43", "#ec8a24", "#f5d264", "#fdf6e3"], ["#7a3f8f", "#ec8a24", "#f5d264", "#ffffff"], ["#d9a21f", "#c93a43", "#f0913a", "#fdf6e3"]],
                 center="#f5d264", particles=["onam_petals"], overlays=["vallam"],
                 caption="Onam, Kerala's harvest festival, celebrating King Mahabali's homecoming with pookalams, sadya and snake boat races.",
                 wiki="https://en.wikipedia.org/wiki/Onam"),
    "deepavali": dict(flowers=[["#d9651a", "#ec8530", "#f5a95c", "#fbd3a6"], MAGENTA, GOLD], center="#f6c46f", particles=["fireflies"], overlays=["diyas"],
                      caption="Deepavali, the festival of lights.", wiki="https://en.wikipedia.org/wiki/Diwali"),
    "keralapiravi": dict(flowers=BRAND, center="#f6c46f", particles=["fireflies"], overlays=["palms"],
                         caption="Kerala Piravi, the anniversary of the formation of Kerala state on 1 November 1956.",
                         wiki="https://en.wikipedia.org/wiki/Kerala_Piravi"),
    "christmas": dict(flowers=[["#a8303a", "#c4424b", "#dc6b70", "#f2a0a2"], WHITE, ["#c98f2e", "#dfaa48", "#efc979", "#f9e3b0"]], center="#f2d48a",
                      particles=["fireflies"], overlays=["lanterns"], caption="Christmas, when star lanterns light up homes across Kerala.",
                      wiki="https://en.wikipedia.org/wiki/Christmas"),
}

def theme_for(day):
    for key, a, b in FESTIVAL_DATES:
        if datetime.date.fromisoformat(a) <= day <= datetime.date.fromisoformat(b):
            return key
    md = day.strftime("%m-%d")
    for key, a, b in YEARLY:
        if a <= md <= b:
            return key
    return SEASON_BY_MONTH[day.month]

T = 54.0; CYC = 18.0
cx, cy = 930, 185
WY = 334            # water line
K = 0.45            # reflection squash
BG0, BG1 = "#14232e", "#233f52"
STROKE = "#3b5a6f"; CORAL, ORANGE, PEACH, MUTED = "#e8917f", "#f08a5d", "#fdebe5", "#9fb4c3"
SERIF = "Georgia,'Times New Roman',serif"; SANS = "'Segoe UI',Helvetica,Arial,sans-serif"
DRY = ["#6b4f40", "#7b604d", "#8d725d", "#a28771"]
CEN_CORE = "#7a3b1d"; CEN_DRY = "#55402f"; DOT_DRY = "#8a6f5a"
LAYERS = [(8, 140, 34, 0, 55, 0.0), (8, 112, 29, 22.5, 45, 0.5), (6, 84, 23, 10, 35, 1.0), (5, 56, 17, 0, 28, 1.5)]

def f(x, d=1):
    s = ("%." + str(d) + "f") % x
    if "." in s: s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s

def track(attr, pts, ttype=None, ease="0.45 0 0.25 1", linear=False, dur=T):
    pts = list(pts)
    if pts[0][0] > 0: pts.insert(0, (0, pts[0][1]))
    out = []; last = -1
    for t, v in pts:
        if t <= last: t = last + 0.002
        out.append((t, v)); last = t
    assert out[-1][0] < dur - 0.01, (attr, out[-1])
    out.append((dur, out[-1][1]))
    kt = ";".join(f(t / dur, 4) for t, _ in out); vals = ";".join(v for _, v in out)
    el = "animateTransform" if ttype else "animate"
    tt = f' type="{ttype}"' if ttype else ""
    if linear:
        mode = 'calcMode="linear"'
    else:
        sp = [("0 0 1 1" if out[i + 1][0] - out[i][0] < 0.06 else ease) for i in range(len(out) - 1)]
        mode = f'calcMode="spline" keySplines="{";".join(sp)}"'
    return f'<{el} attributeName="{attr}"{tt} values="{vals}" keyTimes="{kt}" {mode} dur="{dur:g}s" repeatCount="indefinite"/>'

def once(attr, frm, to, begin, dur, ttype=None):
    tt = f' type="{ttype}"' if ttype else ""
    el = "animateTransform" if ttype else "animate"
    return (f'<{el} attributeName="{attr}"{tt} from="{frm}" to="{to}" begin="{begin}s" dur="{dur}s" fill="freeze" '
            f'calcMode="spline" keyTimes="0;1" keySplines="0.22 1 0.36 1"/>')

def petal_path(L, hw):
    return (f"M0,0 C{f(-hw)},{f(-L*.15)} {f(-hw*1.1)},{f(-L*.7)} {f(-hw*.25)},{f(-L*.95)} "
            f"Q0,{f(-L*1.05)} {f(hw*.25)},{f(-L*.95)} C{f(hw*1.1)},{f(-L*.7)} {f(hw)},{f(-L*.15)} 0,0Z")

def fall_path(df, dx, amp, fr, ph, spin, wob, gr, ph2, land, N=16):
    pos = []; rot = []
    for k in range(N + 1):
        s = k / N
        x = dx * s + amp * math.sin(2 * math.pi * fr * s + ph) * (0.35 + 0.65 * s) * (1 - s * 0.6)
        y = land * (0.3 * s + 0.7 * s * s) - 8 * math.sin(math.pi * min(s / 0.15, 1))
        pos.append((s, x, y))
        rot.append((s, spin * s + wob * math.sin(2 * math.pi * gr * s + ph2)))
    return pos, rot

def drifters(rnd, count, colors, shape):
    o = []
    for _ in range(count):
        x0 = rnd.uniform(380, 1150); drift = rnd.uniform(60, 200); d = rnd.uniform(10, 17); b = -rnd.uniform(0, d)
        sway = rnd.uniform(10, 26); c = rnd.choice(colors)
        p = f"M0,0 C{f(sway)},120 {f(-sway+drift*0.5)},260 {f(drift)},420"
        spin = rnd.choice([-1, 1]) * rnd.uniform(200, 540)
        o.append(f'<g transform="translate({f(x0)},-12)"><animateMotion dur="{f(d)}s" begin="{f(b)}s" repeatCount="indefinite" path="{p}"/>'
                 f'<g><animateTransform attributeName="transform" type="rotate" from="0" to="{f(spin)}" dur="{f(d)}s" begin="{f(b)}s" repeatCount="indefinite"/>{shape(c)}</g></g>')
    return o

def rain(rnd, streaks, ripples):
    o = []
    for _ in range(streaks):
        x = rnd.uniform(-20, 1220); d = rnd.uniform(0.8, 1.3); end = rnd.uniform(WY - 6, 398)
        o.append(f'<line x1="0" y1="0" x2="-3" y2="15" stroke="#bcd4e6" stroke-width="1" stroke-linecap="round" opacity="{f(rnd.uniform(0.18,0.4),2)}" transform="translate({f(x)},-20)">'
                 f'<animateMotion dur="{f(d,2)}s" begin="{f(-rnd.uniform(0,d),2)}s" repeatCount="indefinite" path="M0,0 L-{f(end*0.2)},{f(end+20)}"/></line>')
    for _ in range(ripples):
        x, y = rnd.uniform(640, 1190), rnd.uniform(WY + 5, 395); d = rnd.uniform(1.3, 2.2); b = rnd.uniform(0, 3)
        o.append(f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="0" ry="0" fill="none" stroke="#dbe7f2" stroke-width="0.8" opacity="0">'
                 f'<animate attributeName="rx" values="0;11" dur="{f(d)}s" begin="{f(b)}s" repeatCount="indefinite"/>'
                 f'<animate attributeName="ry" values="0;2.4" dur="{f(d)}s" begin="{f(b)}s" repeatCount="indefinite"/>'
                 f'<animate attributeName="opacity" values="0.55;0" dur="{f(d)}s" begin="{f(b)}s" repeatCount="indefinite"/></ellipse>')
    return o

def particles(kind, rnd):
    o = []
    if kind == "fireflies":
        for _ in range(14):
            x, y = rnd.uniform(620, 1180), rnd.uniform(40, 310)
            rx, ry, d, b, tw = rnd.uniform(10, 34), rnd.uniform(8, 24), rnd.uniform(11, 20), rnd.uniform(0, 8), rnd.uniform(3.5, 7)
            c = rnd.choice(["#fde3b0", "#fde3b0", "#fdebe5", "#f2ab9a"])
            p = f"M0,0 a{f(rx)},{f(ry)} 0 1,0 {f(2*rx)},0 a{f(rx)},{f(ry)} 0 1,0 {f(-2*rx)},0"
            o.append(f'<g transform="translate({f(x)},{f(y)})" opacity="0"><animate attributeName="opacity" values="0;0.9;0.25;0.8;0" dur="{f(tw)}s" begin="{f(b)}s" repeatCount="indefinite"/>'
                     f'<animateMotion dur="{f(d)}s" begin="{f(b)}s" repeatCount="indefinite" path="{p}"/><circle r="7" fill="url(#ffg)"/><circle r="{f(rnd.uniform(1.3,2.1))}" fill="{c}"/></g>')
    elif kind == "mist":
        for _ in range(6):
            y = rnd.uniform(285, 370); w = rnd.uniform(220, 380); d = rnd.uniform(40, 70); x = rnd.uniform(400, 1000)
            o.append(f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(w)}" ry="{f(rnd.uniform(14,26))}" fill="#dbe7f2" opacity="{f(rnd.uniform(0.06,0.12),2)}" filter="url(#mistblur)">'
                     f'<animateTransform attributeName="transform" type="translate" values="0,0;{f(rnd.uniform(-160,160))},0;0,0" dur="{f(d)}s" repeatCount="indefinite" calcMode="spline" keySplines="0.45 0 0.55 1;0.45 0 0.55 1"/></ellipse>')
    elif kind in ("gulmohar", "konna"):
        cols = ["#d9553a", "#ea7b5a", "#c2402a", "#f6ab8f"] if kind == "gulmohar" else ["#f5d264", "#ecbb34", "#fbe7a6", "#e0b21e"]
        o += drifters(rnd, 18 if kind == "gulmohar" else 26, cols, lambda c: f'<ellipse rx="3.8" ry="2.2" fill="{c}" opacity="0.88"/>')
    elif kind == "onam_petals":
        o += drifters(rnd, 22, ["#ec8a24", "#f5d264", "#c93a43", "#fdf6e3", "#f0913a"], lambda c: f'<ellipse rx="3.4" ry="2" fill="{c}" opacity="0.9"/>')
    elif kind == "rain":
        o += rain(rnd, 80, 16)
    elif kind == "drizzle":
        o += rain(rnd, 34, 8)
    elif kind == "lightning":
        o.append('<rect width="1200" height="400" fill="#dbe7f2" opacity="0"><animate attributeName="opacity" values="0;0;0.16;0.02;0.11;0;0" '
                 'keyTimes="0;0.6;0.605;0.612;0.62;0.64;1" dur="23s" repeatCount="indefinite"/></rect>')
    return o

def overlay(kind, rnd):
    o = []
    if kind == "fireworks":
        for k in range(5):
            x, y = rnd.uniform(580, 1170), rnd.uniform(40, 150); d = rnd.uniform(6, 9); b = k * 1.7 + rnd.uniform(0, 0.8)
            c = rnd.choice(["#f6c46f", "#e8917f", "#fdebe5", "#9886e6", "#6fbcc6", "#f2a0a2"]); n = 22; R = rnd.uniform(45, 75)
            for i in range(n):
                ang = 2 * math.pi * i / n; dx, dy = R * math.cos(ang), R * math.sin(ang)
                o.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="1.8" fill="{c}" opacity="0">'
                         f'<animateTransform attributeName="transform" type="translate" values="0,0;{f(dx)},{f(dy)};{f(dx*1.12)},{f(dy*1.12+16)};{f(dx*1.12)},{f(dy*1.12+16)}" keyTimes="0;0.1;0.24;1" '
                         f'calcMode="spline" keySplines="0.1 0.8 0.3 1;0.3 0 0.7 1;0 0 1 1" dur="{f(d)}s" begin="{f(b)}s" repeatCount="indefinite"/>'
                         f'<animate attributeName="opacity" values="0;1;0;0" keyTimes="0;0.02;0.24;1" dur="{f(d)}s" begin="{f(b)}s" repeatCount="indefinite"/></circle>')
    elif kind == "crescent":
        o.append('<g transform="translate(650,80)"><circle r="70" fill="url(#moonglow)"/>'
                 '<path d="M0,-24 A24,24 0 1,0 0,24 A19,19 0 1,1 0,-24Z" fill="#fbefd0" transform="rotate(-20)"/>'
                 '<circle cx="34" cy="-14" r="1.8" fill="#fff"><animate attributeName="opacity" values="1;0.4;1" dur="3s" repeatCount="indefinite"/></circle></g>')
    elif kind == "vallam":
        hull = "M0,-6 Q4,0 14,0 L296,0 Q336,-6 342,-74 L347,-84 Q335,-81 334,-70 Q326,-22 288,-12 L10,-12 Q2,-11 0,-6Z"
        rowers = ""
        for i in range(14):
            x = 26 + i * 18
            rowers += (f'<g transform="translate({x},-12)"><g><animateTransform attributeName="transform" type="rotate" values="8;-6;8" dur="1.1s" repeatCount="indefinite" calcMode="spline" keySplines="0.45 0 0.55 1;0.45 0 0.55 1"/>'
                       f'<line x1="0" y1="-2" x2="-12" y2="20" stroke="#b08a5a" stroke-width="1.6" stroke-linecap="round"/></g>'
                       f'<g><animateTransform attributeName="transform" type="rotate" values="-6;6;-6" dur="1.1s" repeatCount="indefinite" calcMode="spline" keySplines="0.45 0 0.55 1;0.45 0 0.55 1"/>'
                       f'<rect x="-3" y="-3" width="6" height="4" rx="1" fill="#efe6cf"/><line x1="0" y1="-3" x2="0" y2="-10" stroke="#6b4630" stroke-width="3.2" stroke-linecap="round"/>'
                       f'<circle cx="0" cy="-13.5" r="3.2" fill="#2e1d13"/><rect x="-3.2" y="-15.5" width="6.4" height="1.6" fill="#c93a43"/></g></g>')
        umbrella = ('<g transform="translate(168,-12)"><line x1="0" y1="0" x2="0" y2="-40" stroke="#b08a5a" stroke-width="1.4"/>'
                    '<path d="M-13,-38 Q0,-54 13,-38Z" fill="#c93a43"/><path d="M-13,-38 Q0,-41 13,-38" stroke="#f5d264" stroke-width="1.6" fill="none"/>'
                    + "".join(f'<circle cx="{-12+k*4}" cy="-36" r="1.1" fill="#f5d264"/>' for k in range(7)) + '</g>')
        helm = ('<g transform="translate(300,-12)"><line x1="0" y1="-2" x2="22" y2="24" stroke="#b08a5a" stroke-width="2" stroke-linecap="round"/>'
                '<rect x="-3" y="-4" width="6" height="5" rx="1" fill="#efe6cf"/><line x1="0" y1="-4" x2="0" y2="-14" stroke="#6b4630" stroke-width="3.2" stroke-linecap="round"/>'
                '<circle cx="0" cy="-17.5" r="3.2" fill="#2e1d13"/></g>')
        trim = '<path d="M10,-12 L288,-12 Q326,-22 334,-70" stroke="#d9a21f" stroke-width="1.6" fill="none"/>' + "".join(
            f'<circle cx="{30+k*26}" cy="-6" r="1.4" fill="#d9a21f"/>' for k in range(11))
        boat = f'<path d="{hull}" fill="#3b2416"/>{trim}<circle cx="344" cy="-82" r="2.4" fill="#d9a21f"/>'
        wake = ('<ellipse cx="400" cy="1" rx="90" ry="2.4" fill="url(#wake)"/>'
                + "".join(f'<path d="M-4,2 Q-14,{6+k*3} -26,{8+k*4}" stroke="#dbe7f2" stroke-width="0.9" fill="none" opacity="0"><animate attributeName="opacity" values="0;0.5;0" dur="1.6s" begin="{k*0.5}s" repeatCount="indefinite"/></path>' for k in range(3)))
        full = f'{wake}{boat}{rowers}{umbrella}{helm}'
        o.append(f'<g opacity="0"><animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;0.06;0.76;0.84;1" dur="46s" repeatCount="indefinite"/>'
                 f'<animateTransform attributeName="transform" type="translate" values="1230,378;400,378;400,378" keyTimes="0;0.84;1" dur="46s" repeatCount="indefinite"/>'
                 f'<g transform="scale(0.72)"><g><animateTransform attributeName="transform" type="translate" values="0,0;0,-2;0,0" dur="2.2s" repeatCount="indefinite" calcMode="spline" keySplines="0.45 0 0.55 1;0.45 0 0.55 1"/>'
                 f'<g transform="scale(1,-0.45)" opacity="0.22">{boat}{rowers}{umbrella}</g>{full}</g></g></g>')
    elif kind == "diyas":
        for k in range(7):
            x, y = 640 + k * 82 + rnd.uniform(-20, 20), rnd.uniform(WY + 12, 390); sc = 0.7 + (y - WY) / 70 * 0.5; d = rnd.uniform(0.7, 1.2)
            o.append(f'<g transform="translate({f(x)},{f(y)}) scale({f(sc,2)})"><g><animateTransform attributeName="transform" type="translate" values="0,0;0,-1.5;0,0" dur="{f(rnd.uniform(3,5))}s" repeatCount="indefinite"/>'
                     f'<ellipse cx="0" cy="9" rx="5" ry="10" fill="#f5a95c" opacity="0.12"/><circle cy="-6" r="16" fill="url(#diyaglow)"><animate attributeName="opacity" values="0.7;1;0.8;1;0.7" dur="{f(d*2)}s" repeatCount="indefinite"/></circle>'
                     f'<path d="M-10,0 Q0,9 10,0 Q6,-2 0,-1.5 Q-6,-2 -10,0Z" fill="#a85b2e"/><path d="M-10,0 Q0,3 10,0" stroke="#d98a4e" stroke-width="1" fill="none"/>'
                     f'<path d="M0,-12 C3,-7 3,-3 0,-1.5 C-3,-3 -3,-7 0,-12Z" fill="#ffd86b"><animateTransform attributeName="transform" type="scale" values="1 1;0.9 1.12;1.05 0.94;1 1" dur="{f(d)}s" repeatCount="indefinite"/></path>'
                     f'<path d="M0,-8 C1.4,-5.5 1.4,-3.5 0,-2.5 C-1.4,-3.5 -1.4,-5.5 0,-8Z" fill="#fff6d8"/></g></g>')
    elif kind == "palms":
        for x, h, lean in [(1075, 78, -10), (1128, 98, 8), (1176, 70, 14)]:
            tx, ty = x + lean, WY - h
            fr = "".join(f'<path d="M0,0 Q{f(28*math.cos(a))},{f(-14+28*math.sin(a))} {f(44*math.cos(a))},{f(8+44*math.sin(a))}" stroke="#0c161e" stroke-width="3" fill="none" stroke-linecap="round"/>'
                         for a in [math.radians(v) for v in (-170, -140, -110, -70, -40, -10, 15, 165)])
            o.append(f'<g opacity="0.9"><path d="M{x},{WY} Q{f(x+lean*0.2)},{f(WY-h*0.55)} {f(tx)},{f(ty)}" stroke="#0c161e" stroke-width="4.5" fill="none" stroke-linecap="round"/>'
                     f'<g transform="translate({f(tx)},{f(ty)})"><g><animateTransform attributeName="transform" type="rotate" values="-3;3;-3" dur="{f(rnd.uniform(5,8))}s" repeatCount="indefinite" calcMode="spline" keySplines="0.45 0 0.55 1;0.45 0 0.55 1"/>{fr}</g></g></g>')
    elif kind == "lanterns":
        star = "M0,-18 L4.6,-6.3 17.1,-5.6 7.4,2.4 10.6,14.6 0,7.6 -10.6,14.6 -7.4,2.4 -17.1,-5.6 -4.6,-6.3Z"
        for x, L, c in [(640, 70, "#e8505b"), (1120, 52, "#f6c46f"), (1175, 92, "#fdebe5")]:
            o.append(f'<g transform="translate({x},0)"><g><animateTransform attributeName="transform" type="rotate" values="-4;4;-4" dur="{f(rnd.uniform(4,6))}s" repeatCount="indefinite" calcMode="spline" keySplines="0.45 0 0.55 1;0.45 0 0.55 1"/>'
                     f'<line x1="0" y1="0" x2="0" y2="{L-18}" stroke="#9fb4c3" stroke-width="0.8" opacity="0.6"/><g transform="translate(0,{L})">'
                     f'<circle r="40" fill="{c}" opacity="0.12"><animate attributeName="opacity" values="0.08;0.2;0.08" dur="3s" repeatCount="indefinite"/></circle>'
                     f'<path d="{star}" fill="{c}" stroke="#fff" stroke-opacity="0.5" stroke-width="0.8"/><circle r="4" fill="#fff8e0" opacity="0.8"/>'
                     f'<line x1="-5" y1="13" x2="-7" y2="30" stroke="{c}" stroke-width="1.2"/><line x1="5" y1="13" x2="7" y2="30" stroke="{c}" stroke-width="1.2"/></g></g></g>')
    return o

def build(theme):
    S = THEMES[theme]; FRESH = S["flowers"]; rnd = random.Random(21)
    accents = [fl[1] for fl in FRESH]
    o = []; a = o.append
    a('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 400" width="1200" height="400" role="img" aria-label="Niranjan MD. Systems, art, research, life.">')
    stop_pts = [(0, accents[0])] + [x for c in (1, 2) for x in ((c * CYC + 0.8, accents[c - 1]), (c * CYC + 0.82, accents[c]))]
    a(f'''<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{BG0}"/><stop offset="1" stop-color="{BG1}"/></linearGradient>
<radialGradient id="glow" cx="{cx/1200}" cy="0.46" r="0.3"><stop offset="0" stop-color="{accents[0]}" stop-opacity="0.10"/><stop offset="1" stop-color="{accents[0]}" stop-opacity="0"/></radialGradient>
<radialGradient id="fglow" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="{accents[0]}" stop-opacity="0.38">{track("stop-color", stop_pts)}</stop><stop offset="1" stop-color="{accents[0]}" stop-opacity="0">{track("stop-color", stop_pts)}</stop></radialGradient>
<radialGradient id="ffg" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#fde3b0" stop-opacity="0.9"/><stop offset="1" stop-color="#fde3b0" stop-opacity="0"/></radialGradient>
<pattern id="dots" width="28" height="28" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.1" fill="{STROKE}" opacity="0.4"/></pattern>
<linearGradient id="rule" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{CORAL}" stop-opacity="0"/><stop offset="0.3" stop-color="{CORAL}"/><stop offset="0.7" stop-color="{ORANGE}"/><stop offset="1" stop-color="{ORANGE}" stop-opacity="0"/></linearGradient>
<linearGradient id="water" x1="0" y1="0" x2="1" y2="0"><stop offset="0.3" stop-color="#0b1720" stop-opacity="0"/><stop offset="0.55" stop-color="#0b1720" stop-opacity="0.55"/><stop offset="1" stop-color="#0b1720" stop-opacity="0.65"/></linearGradient>
<linearGradient id="surface" x1="0" y1="0" x2="1" y2="0"><stop offset="0.35" stop-color="{PEACH}" stop-opacity="0"/><stop offset="0.75" stop-color="{PEACH}" stop-opacity="0.35"/><stop offset="1" stop-color="{PEACH}" stop-opacity="0.1"/></linearGradient>
<linearGradient id="mfade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="1"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<radialGradient id="moonglow"><stop offset="0" stop-color="#fbefd0" stop-opacity="0.35"/><stop offset="1" stop-color="#fbefd0" stop-opacity="0"/></radialGradient>
<linearGradient id="wake" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#dbe7f2" stop-opacity="0.35"/><stop offset="1" stop-color="#dbe7f2" stop-opacity="0"/></linearGradient>
<radialGradient id="diyaglow"><stop offset="0" stop-color="#ffd86b" stop-opacity="0.75"/><stop offset="1" stop-color="#ffb04a" stop-opacity="0"/></radialGradient>
<filter id="mistblur" x="-50%" y="-200%" width="200%" height="500%"><feGaussianBlur stdDeviation="14"/></filter>
<linearGradient id="ss" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="1"/><stop offset="1" stop-color="{PEACH}" stop-opacity="0"/></linearGradient>
<clipPath id="wclip"><rect x="0" y="{WY}" width="1200" height="{400-WY}"/></clipPath>
<mask id="rmask" maskUnits="userSpaceOnUse" x="0" y="0" width="1200" height="400"><rect x="0" y="{WY}" width="1200" height="{400-WY}" fill="url(#mfade)"/></mask>
<filter id="ripple" x="560" y="{WY}" width="640" height="{400-WY}" filterUnits="userSpaceOnUse"><feTurbulence type="fractalNoise" baseFrequency="0.01 0.09" numOctaves="1" seed="4"><animate attributeName="baseFrequency" values="0.01 0.09;0.013 0.12;0.01 0.09" dur="9s" repeatCount="indefinite"/></feTurbulence><feDisplacementMap in="SourceGraphic" scale="7" xChannelSelector="R" yChannelSelector="G"/><feGaussianBlur stdDeviation="0.7"/></filter>
</defs>
<rect width="1200" height="400" fill="url(#bg)"/><rect width="1200" height="400" fill="url(#dots)"/><rect width="1200" height="400" fill="url(#glow)"/>''')

    # night sky
    a(f'<g opacity="0">{once("opacity","0","1",0,3)}')
    for _ in range(60):
        x, y = rnd.uniform(10, 1190), rnd.uniform(8, 300) ** 1.0
        if rnd.random() < 0.5: y = rnd.uniform(8, 150)
        op = rnd.uniform(0.25, 0.7); d = rnd.uniform(2.5, 7); c = rnd.choice(["#fdebe5", "#dbe7f2", "#f6dcb0"])
        a(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(rnd.uniform(0.5,1.3),2)}" fill="{c}" opacity="{f(op,2)}"><animate attributeName="opacity" values="{f(op,2)};{f(op*0.2,2)};{f(op,2)}" dur="{f(d)}s" begin="{f(rnd.uniform(0,d))}s" repeatCount="indefinite"/></circle>')
    for (x0, y0, ts, dist) in [(1160, 36, 12, 320), (660, 24, 41, 260)]:
        vx, vy = -dist, dist * 0.42
        ang = math.degrees(math.atan2(-vy, -vx))
        pts = [(0, f"{x0},{y0}"), (ts, f"{x0},{y0}"), (ts + 1.1, f"{f(x0+vx)},{f(y0+vy)}"), (ts + 1.15, f"{x0},{y0}")]
        op = [(0, "0"), (ts, "0"), (ts + 0.15, "1"), (ts + 0.75, "1"), (ts + 1.1, "0")]
        a(f'<g opacity="0">{track("transform", pts, ttype="translate", linear=True, dur=61)}{track("opacity", op, dur=61)}'
          f'<g transform="rotate({f(ang)})"><rect x="0" y="-0.8" width="120" height="1.6" rx="0.8" fill="url(#ss)"/><circle r="1.7" fill="#fff"/></g></g>')
    for ov in S.get("overlays", []):
        if ov in ("fireworks", "crescent", "lanterns"):
            o.extend(overlay(ov, rnd))
    a('</g>')

    # glow disc
    gp = [(0, "0")]
    for c in range(3):
        b = c * CYC; gp += [(b + 0.9, "0"), (b + 5.5, "1"), (b + 9.5, "0.8"), (b + 14.5, "0")]
    a(f'<circle cx="{cx}" cy="{cy}" r="210" fill="url(#fglow)" opacity="0">{track("opacity", gp)}</circle>')

    # pond
    a(f'<g opacity="0">{once("opacity","0","1",0.4,2.5)}<rect x="0" y="{WY}" width="1200" height="{400-WY}" fill="url(#water)"/>'
      f'<rect x="0" y="{WY}" width="1200" height="1" fill="url(#surface)"/>')
    for _ in range(9):
        x, y, w = rnd.uniform(700, 1150), rnd.uniform(WY + 8, 392), rnd.uniform(24, 80); d = rnd.uniform(4, 8)
        a(f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="1" rx="0.5" fill="{PEACH}" opacity="0.12"><animate attributeName="opacity" values="0.03;0.2;0.03" dur="{f(d)}s" begin="{f(rnd.uniform(0,d))}s" repeatCount="indefinite"/>'
          f'<animateTransform attributeName="transform" type="translate" values="0,0;{f(rnd.uniform(-14,14))},0;0,0" dur="{f(d*1.6)}s" repeatCount="indefinite"/></rect>')
    a('</g>')
    a(f'<g clip-path="url(#wclip)"><g mask="url(#rmask)"><g opacity="0.32" filter="url(#ripple)"><use href="#head" transform="translate(0,{f(WY*(1+K))}) scale(1,{-K})"/></g></g></g>')

    # flower head
    ripples = []
    o.append(f'<g id="head" transform="translate({cx},{cy})">')
    dp = [(0, "0,0")]
    for c in range(3):
        b = c * CYC; dp += [(b + 8.2, "0,0"), (b + 11.2, "0,8"), (b + 17.85, "0,8"), (b + 17.9, "0,0")]
    a(f'<g>{track("transform", dp, ttype="translate")}')

    def faller(li, i, n, L, tw, delay, cols):
        theta = LAYERS[li][3] + i * 360 / n; cc = L * 0.5
        fo = [(0, "0")]; ft = [(0, "0,0")]; tr = [(0, "0")]; un = [(0, f(tw))]
        sc = [(0, "0.1 0.05")]; fl = [(0, cols[0])]
        rcx = [(0, "0")]; rcy = [(0, "0")]; rrx = [(0, "0")]; rry = [(0, "0")]; rop = [(0, "0")]
        for c in range(3):
            b = c * CYC
            ta = b + 0.8 + 0.04 * li; tu = b + 1.5 + delay * 0.6 + i * 0.05
            w0 = b + 8.2 + 0.1 * li; w1 = b + 11.2
            tf = b + 10.6 + 0.45 * li + i * 0.08 + rnd.uniform(0, 0.25)
            df = 3.2 + rnd.uniform(0, 0.6); tl = tf + df; te = tl + 1.3
            land = rnd.uniform(150, 192); curl = rnd.uniform(-10, 10)
            pos, rot = fall_path(df, rnd.uniform(-170, 150), rnd.uniform(14, 34), rnd.uniform(1.2, 2.0), rnd.uniform(0, 6.28),
                                 rnd.choice([-1, 1]) * rnd.uniform(150, 320), rnd.uniform(20, 50), rnd.uniform(1.2, 2.2), rnd.uniform(0, 6.28), land)
            xe, ye = pos[-1][1], pos[-1][2]; drift = rnd.uniform(-14, 14); re = rot[-1][1]
            fo += [(ta - 0.02, "0"), (ta + 0.6, "1"), (tl + 0.25, "1"), (te, "0")]
            ft += [(tf + s * df, f"{f(x)},{f(y)}") for s, x, y in pos] + [(te, f"{f(xe+drift)},{f(ye)}"), (te + 0.1, "0,0")]
            tr += [(tf + s * df, f(r)) for s, r in rot] + [(te, f(re + drift * 1.5)), (te + 0.1, "0")]
            un += [(ta, f(tw)), (tu, f(tw)), (tu + 4.0, "0"), (w0, "0"), (w1, f(curl)), (te, f(curl)), (te + 0.1, f(tw))]
            sc += [(ta - 0.01, "0.1 0.05"), (ta + 0.65, "0.5 0.2"), (tu, "0.5 0.2"), (tu + 3.5, "1.05 1.04"), (tu + 4.5, "1 1"),
                   (w0, "1 1"), (w1, "0.84 0.72"), (tl, "0.8 0.68"), (tl + 0.6, "0.74 0.42"), (te, "0.74 0.42"), (te + 0.1, "0.1 0.05")]
            if c > 0:
                fl += [(ta - 0.6, DRY[li]), (ta - 0.58, cols[c])]
                rcx += [(b + 0.4, rcx[-1][1]), (b + 0.42, f(xe))]; rcy += [(b + 0.4, rcy[-1][1]), (b + 0.42, f(ye))]
            else:
                rcx = [(0, f(xe))]; rcy = [(0, f(ye))]
            fl += [(w0, cols[c]), (w1, DRY[li])]
            rrx += [(tl, "0"), (tl + 1.5, "30"), (tl + 1.55, "0")]
            rry += [(tl, "0"), (tl + 1.5, "6"), (tl + 1.55, "0")]
            rop += [(tl, "0"), (tl + 0.1, "0.5"), (tl + 1.5, "0")]
        fl.sort(key=lambda p: p[0])
        ripples.append(f'<ellipse fill="none" stroke="{PEACH}" stroke-width="1" rx="0" ry="0" opacity="0">{track("cx", rcx)}{track("cy", rcy)}'
                       f'{track("rx", rrx, ease="0.2 0.6 0.4 1")}{track("ry", rry, ease="0.2 0.6 0.4 1")}{track("opacity", rop)}</ellipse>')
        return theta, cc, fo, ft, tr, un, sc, fl

    for li, (n, L, hw, off, tw, delay) in enumerate(LAYERS):
        cols = [FRESH[c][li] for c in range(3)]
        for i in range(n):
            theta, cc, fo, ft, tr, un, sc, fl = faller(li, i, n, L, tw, delay, cols)
            a(f'<g opacity="0">{track("opacity", fo)}{track("transform", ft, ttype="translate", linear=True)}')
            a(f'<g transform="rotate({f(theta)}) translate(0,{f(-cc)})"><g>{track("transform", tr, ttype="rotate", linear=True)}')
            a(f'<g transform="translate(0,{f(cc)})"><g>{track("transform", un, ttype="rotate")}<g>{track("transform", sc, ttype="scale")}')
            a(f'<path d="{petal_path(L, hw)}" fill="{cols[0]}" stroke="#0e1a22" stroke-opacity="0.3" stroke-width="0.8">{track("fill", fl, ease="0.4 0 0.6 1")}</path>')
            a(f'<path d="{petal_path(L*0.78, hw*0.5)}" transform="translate(0,{f(-L*0.07)})" fill="#fff" opacity="0.16"/>')
            a(f'<line x1="0" y1="{f(-L*0.1)}" x2="0" y2="{f(-L*0.8)}" stroke="#fff" stroke-opacity="0.22" stroke-width="1.2" stroke-linecap="round"/>')
            a('</g></g></g></g></g></g>')

    # centre
    co = [(0, "0")]; ct = [(0, "0,0")]; cs = [(0, "0")]; cf = [(0, S["center"])]; cd = [(0, PEACH)]
    for c in range(3):
        b = c * CYC; ta = b + 0.8; tc = b + 13.2; dc = 3.0; tl = tc + dc; te = tl + 1.3
        pos, _ = fall_path(dc, rnd.uniform(-40, 40), 12, 1.4, 1.0, 0, 0, 1, 0, 168)
        xe, ye = pos[-1][1], pos[-1][2]
        co += [(ta - 0.02, "0"), (ta + 0.6, "1"), (tl + 0.25, "1"), (te, "0")]
        ct += [(tc + s * dc, f"{f(x)},{f(y)}") for s, x, y in pos] + [(te, f"{f(xe+6)},{f(ye)}"), (te + 0.1, "0,0")]
        cs += [(ta - 0.01, "0"), (b + 1.8, "1"), (tl, "0.8"), (te, "0.7"), (te + 0.1, "0")]
        if c > 0:
            cf += [(ta - 0.6, CEN_DRY), (ta - 0.58, S["center"])]; cd += [(ta - 0.6, DOT_DRY), (ta - 0.58, PEACH)]
        cf += [(b + 8.2, S["center"]), (b + 11.2, CEN_DRY)]; cd += [(b + 8.2, PEACH), (b + 11.2, DOT_DRY)]
    dots = "".join(f'<circle cx="{f(24*math.cos(k*math.pi/6))}" cy="{f(24*math.sin(k*math.pi/6))}" r="2.4"/>' for k in range(12))
    dots += "".join(f'<circle cx="{f(33*math.cos(k*math.pi/9+0.17))}" cy="{f(33*math.sin(k*math.pi/9+0.17))}" r="1.6"/>' for k in range(18))
    a(f'<g opacity="0">{track("opacity", co)}{track("transform", ct, ttype="translate", linear=True)}<g>{track("transform", cs, ttype="scale")}')
    a(f'<g fill="{PEACH}">{track("fill", cd, ease="0.4 0 0.6 1")}{dots}</g>')
    a(f'<circle r="17" fill="{S["center"]}">{track("fill", cf, ease="0.4 0 0.6 1")}</circle><circle r="9" fill="{CEN_CORE}" opacity="0.55"/>')
    a('</g></g>')
    a('</g></g>')  # droop, head

    for ov in S.get("overlays", []):
        if ov in ("vallam", "diyas", "palms"):
            a(f'<g opacity="0">{once("opacity","0","1",0.8,2.5)}' + "".join(overlay(ov, rnd)) + '</g>')
    # ripples sit on the water, outside the reflected head
    a(f'<g transform="translate({cx},{cy+8})">' + "".join(ripples) + '</g>')

    # seasonal particles
    a(f'<g opacity="0">{once("opacity","0","1",1.0,3)}' + "".join(x for k in S["particles"] for x in particles(k, rnd)) + '</g>')

    # entrance text
    a(f'<g transform="translate(0,16)" opacity="0">{once("opacity","0","1",0.2,1.4)}{once("transform","0,16","0,0",0.2,1.4,"translate")}'
      f'<text x="70" y="190" font-family="{SERIF}" font-size="76" font-weight="700" fill="{PEACH}" letter-spacing="-1">Niranjan MD</text></g>')
    words = ["Systems", " · Art", " · Research", " · "]
    spans = ""
    for k, w in enumerate(words):
        inner = w + ('<tspan font-style="italic">Life</tspan>' if k == 3 else "")
        spans += f'<tspan fill-opacity="0">{inner}{once("fill-opacity","0","1",1.0+k*0.3,0.8)}</tspan>'
    a(f'<g transform="translate(0,10)">{once("transform","0,10","0,0",0.9,1.6,"translate")}'
      f'<text x="72" y="238" font-family="{SANS}" font-size="21" fill="{ORANGE}" letter-spacing="0.5">{spans}</text></g>')
    for k, (y, line) in enumerate([(288, "Just doing whatever I want to,"), (316, "whenever I want to, however I want to.")]):
        bg = 2.3 + k * 0.35
        a(f'<g transform="translate(0,10)" opacity="0">{once("opacity","0","1",bg,1.2)}{once("transform","0,10","0,0",bg,1.2,"translate")}'
          f'<text x="72" y="{y}" font-family="{SERIF}" font-size="19" font-style="italic" fill="{MUTED}">{line}</text></g>')
    a('<rect x="0" y="396" width="1200" height="4" fill="url(#rule)"/>')
    a('</svg>')
    return "\n".join(o)

def update_readme(path, theme):
    t = THEMES[theme]
    body = ""
    if t.get("caption"):
        body = (f'<p align="center"><sub><i>Today\u2019s banner celebrates {t["caption"]}</i> '
                f'<a href="{t["wiki"]}">Read more on Wikipedia</a></sub></p>')
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    new = re.sub(r"(<!-- festival:start -->).*?(<!-- festival:end -->)", lambda m: m.group(1) + ("\n" + body + "\n" if body else "") + m.group(2), text, flags=re.S)
    if new != text:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new)
        print(f"updated festival caption in {path}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", default="auto", choices=["auto"] + list(THEMES))
    ap.add_argument("--out", default="assets/banner.svg")
    ap.add_argument("--readme", help="README to update with the festival caption")
    a = ap.parse_args()
    today = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).date()
    if not any(d.startswith(str(today.year)) for _, d, _ in FESTIVAL_DATES):
        print(f"::warning::No festival dates for {today.year} in FESTIVAL_DATES; add this year's dates.")
    theme = theme_for(today) if a.theme == "auto" else a.theme
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(build(theme))
    if a.readme:
        update_readme(a.readme, theme)
    print(f"wrote {a.out} ({theme})")

if __name__ == "__main__":
    main()
