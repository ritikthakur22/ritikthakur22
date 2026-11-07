"""Render this year's GitHub contributions as animated SVG cards (dark + light).

Usage: GITHUB_TOKEN=... python3 scripts/year.py <user> <out_dir>
       python3 scripts/year.py --selftest
"""
import json, os, sys, urllib.request
from datetime import date, datetime, timedelta, timezone

THEMES = {
    "dark": dict(bg="#050816", edge="#1c3a57", text="#eafbff", muted="#6f8aa0", bar="#00d9ff", track="#0c1a2e"),
    "light": dict(bg="#f7fcff", edge="#cbe3ef", text="#0b1a2e", muted="#5b7689", bar="#0096c7", track="#e3f0f7"),
}
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
QUERY = """query($u:String!,$from:DateTime!){user(login:$u){contributionsCollection(from:$from){
totalCommitContributions totalRepositoryContributions
contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""


def fetch(user, year):
    body = json.dumps({"query": QUERY, "variables": {"u": user, "from": f"{year}-01-01T00:00:00Z"}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "User-Agent": "profile-year"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]["contributionsCollection"]


def stats(cc, year):
    days = [(d["date"], d["contributionCount"]) for w in cc["contributionCalendar"]["weeks"]
            for d in w["contributionDays"] if d["date"].startswith(str(year))]
    months = [0] * 12
    streak = best = active = 0
    for day, n in sorted(days):
        months[int(day[5:7]) - 1] += n
        active += n > 0
        streak = streak + 1 if n else 0
        best = max(best, streak)
    peak = max(range(12), key=lambda i: months[i])
    return dict(total=cc["contributionCalendar"]["totalContributions"], commits=cc["totalCommitContributions"],
                repos=cc["totalRepositoryContributions"], months=months, peak=peak, best=best, active=active)


def svg(s, year, theme, through):
    c = THEMES[theme]
    w, h = 880, 270
    tiles = [(f"{s['total']:,}", "contributions"), (f"{s['commits']:,}", "commits"),
             (str(s["repos"]), "repos created"), (f"{s['best']}d", "longest streak"), (str(s["active"]), "active days")]
    tile_svg = "".join(
        f'<g class="up" style="animation-delay:{.1 + i * .08:.2f}s"><text x="{40 + i * 112}" y="112" class="big">{v}</text>'
        f'<text x="{40 + i * 112}" y="134" class="m">{label}</text></g>' for i, (v, label) in enumerate(tiles))
    top = max(s["months"]) or 1
    bars = []
    for i, n in enumerate(s["months"]):
        x, bh = 618 + i * 19, max(3, round(n / top * 150))
        fill = c["bar"] if i == s["peak"] else c["bar"] + "88"
        bars.append(f'<rect x="{x}" y="66" width="12" height="150" rx="3" fill="{c["track"]}"/>'
                    f'<rect class="bar" style="animation-delay:{.3 + i * .05:.2f}s" x="{x}" y="{216 - bh}" width="12" height="{bh}" rx="3" fill="{fill}"/>'
                    f'<text x="{x + 6}" y="236" class="tiny" text-anchor="middle">{MONTHS[i][0]}</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{year} on GitHub: {s['total']} contributions, busiest month {MONTHS[s['peak']]}">
<style>
.big {{ font: 800 30px "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif; fill: {c["text"]}; }}
.m {{ font: 500 13px "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif; fill: {c["muted"]}; }}
.tiny {{ font: 600 11px "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif; fill: {c["muted"]}; }}
.h {{ font: 700 13px "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif; letter-spacing: 2px; fill: #00b4d8; }}
.up {{ opacity: 0; animation: up .7s cubic-bezier(.16,1,.3,1) forwards; }}
.bar {{ transform-origin: 0 216px; transform-box: view-box; transform: scaleY(0); animation: grow .9s cubic-bezier(.16,1,.3,1) forwards; }}
@keyframes up {{ from {{ opacity: 0; transform: translateY(12px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes grow {{ to {{ transform: scaleY(1); }} }}
@media (prefers-reduced-motion: reduce) {{ .up, .bar {{ animation: none; opacity: 1; transform: none; }} }}
</style>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="16" fill="{c["bg"]}" stroke="{c["edge"]}"/>
<text x="40" y="44" class="h">{year} IN REVIEW</text>
<text x="40" y="66" class="m">through {through:%b %d}</text>
{tile_svg}
<g class="up" style="animation-delay:.6s"><text x="40" y="200" class="m">Busiest month</text>
<text x="40" y="230" class="big" style="font-size:24px">{MONTHS[s['peak']]} · {s['months'][s['peak']]} contributions</text></g>
{"".join(bars)}
</svg>
'''


def selftest():
    start = date(2026, 1, 1)
    counts = {start + timedelta(d): (3 if 40 <= d < 47 else 1 if d % 10 == 0 else 0) for d in range(365)}
    cc = {"totalCommitContributions": 30, "totalRepositoryContributions": 2, "contributionCalendar": {
        "totalContributions": sum(counts.values()),
        "weeks": [{"contributionDays": [{"date": str(day), "contributionCount": n} for day, n in counts.items()]},
                  {"contributionDays": [{"date": "2025-12-31", "contributionCount": 9}]}]}}
    s = stats(cc, 2026)
    assert s["best"] == 7 and s["peak"] == 1, s  # Feb 10-16 is the 7-day streak
    assert sum(s["months"]) == s["total"] and s["active"] == 7 + sum(1 for d in range(365) if d % 10 == 0 and not 40 <= d < 47)
    out = svg(s, 2026, "light", datetime(2026, 11, 7))
    assert out.count('class="bar"') == 12 and "FEB" not in out and "Feb · " in out
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
        sys.exit()
    user, out_dir = sys.argv[1], sys.argv[2]
    now = datetime.now(timezone.utc)
    s = stats(fetch(user, now.year), now.year)
    os.makedirs(out_dir, exist_ok=True)
    for theme in THEMES:
        with open(os.path.join(out_dir, f"year-{theme}.svg"), "w") as f:
            f.write(svg(s, now.year, theme, now))
