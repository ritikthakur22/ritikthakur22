"""Render the latest release of each public repo as animated SVG cards (dark + light).

Usage: GITHUB_TOKEN=... python3 scripts/releases.py <user> <out_dir>
       python3 scripts/releases.py --selftest
"""
import json, os, sys, urllib.request
from datetime import datetime, timezone
from xml.sax.saxutils import escape

MAX_ROWS = 5
HIDE = {"revanced-YT", "game"}  # repos left off the card
NAMES = {"battery-info_app": "PowerGyan", "wifi_analyzer_app": "Wi-Fi Analyzer", "fastshare_app": "FastShare for Android",
         "com.ritikqrscanner.app": "QR Scanner & Reader", "scientific-calcr-pro": "Scientific CalcR Pro",
         "morphe-patches": "Morphe Patches", "Echo_Loop": "Echo Loop", "guptrix": "Guptrix"}
THEMES = {
    "dark": dict(bg="#050816", edge="#1c3a57", text="#eafbff", muted="#6f8aa0", row="#0c1a2e", tag="#00d9ff", tagbg="#06283a"),
    "light": dict(bg="#f7fcff", edge="#cbe3ef", text="#0b1a2e", muted="#5b7689", row="#ffffff", tag="#00739a", tagbg="#e0f4fa"),
}
QUERY = """query($u:String!){user(login:$u){repositories(first:100,ownerAffiliations:OWNER,privacy:PUBLIC,orderBy:{field:PUSHED_AT,direction:DESC}){
nodes{name releases(first:1,orderBy:{field:CREATED_AT,direction:DESC}){totalCount nodes{tagName publishedAt isPrerelease}}}}}}"""
FONT = '"Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif'


def fetch(user):
    body = json.dumps({"query": QUERY, "variables": {"u": user}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "User-Agent": "profile-releases"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]["repositories"]["nodes"]


def rows(repos):
    out = []
    for r in repos:
        rel = r["releases"]
        if r["name"] in HIDE or not rel["nodes"] or not rel["nodes"][0]["publishedAt"]:
            continue  # drafts have no publishedAt
        n = rel["nodes"][0]
        out.append((n["publishedAt"], NAMES.get(r["name"], r["name"]), n["tagName"], rel["totalCount"], n["isPrerelease"]))
    return sorted(out, reverse=True)[:MAX_ROWS]


def ago(ts, now):
    d = (now - datetime.fromisoformat(ts.replace("Z", "+00:00"))).days
    return "today" if d < 1 else "yesterday" if d < 2 else f"{d}d ago" if d < 30 else f"{d // 30}mo ago"


def svg(items, theme, now):
    c = THEMES[theme]
    w, top, rh = 880, 64, 50
    h = top + max(len(items), 1) * rh + 16
    body = []
    for i, (ts, name, tag, count, pre) in enumerate(items):
        y = top + i * rh
        tag_txt = tag + (" · pre" if pre else "")
        tw = len(tag_txt) * 7.8 + 22
        nx = 280  # fixed column so the tags line up
        body.append(
            f'<g class="row" style="animation-delay:{.15 + i * .12:.2f}s">'
            f'<rect x="20" y="{y}" width="{w - 40}" height="{rh - 10}" rx="12" fill="{c["row"]}" stroke="{c["edge"]}"/>'
            f'<path d="M{38} {y + 12}l8 8-8 8-8-8z" fill="{c["tag"]}" class="gem"/>'
            f'<text x="64" y="{y + 26}" class="t">{escape(name)}</text>'
            f'<rect x="{nx:.0f}" y="{y + 9}" width="{tw:.0f}" height="22" rx="11" fill="{c["tagbg"]}"/>'
            f'<text x="{nx + tw / 2:.0f}" y="{y + 24}" class="tag" text-anchor="middle">{escape(tag_txt)}</text>'
            f'<text x="{w - 150}" y="{y + 26}" class="m" text-anchor="end">{count} release{"s" if count != 1 else ""}</text>'
            f'<text x="{w - 36}" y="{y + 26}" class="m" text-anchor="end">{ago(ts, now)}</text></g>')
    if not items:
        body.append(f'<text x="40" y="{top + 24}" class="m">No releases yet.</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Latest releases: {escape(', '.join(f'{n} {t}' for _, n, t, _, _ in items))}">
<style>
.t {{ font: 600 15px {FONT}; fill: {c["text"]}; }}
.m {{ font: 500 13px {FONT}; fill: {c["muted"]}; }}
.tag {{ font: 700 12px ui-monospace, "SF Mono", Menlo, Consolas, monospace; fill: {c["tag"]}; }}
.h {{ font: 700 13px {FONT}; letter-spacing: 2px; fill: #00b4d8; }}
.row {{ opacity: 0; animation: in .6s cubic-bezier(.16,1,.3,1) forwards; }}
.gem {{ transform-box: fill-box; transform-origin: center; animation: spin 6s linear infinite; }}
@keyframes in {{ from {{ opacity: 0; transform: translateX(-14px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} .row {{ opacity: 1; }} }}
</style>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="16" fill="{c["bg"]}" stroke="{c["edge"]}"/>
<text x="24" y="38" class="h">RELEASE RADAR</text>
<text x="{w - 24}" y="38" class="m" text-anchor="end">updated {now:%b %d, %Y}</text>
{"".join(body)}
</svg>
'''


def selftest():
    rel = lambda name, ts, tag, n, pre=False: {"name": name, "releases": {"totalCount": n, "nodes": [{"tagName": tag, "publishedAt": ts, "isPrerelease": pre}] if n else []}}
    repos = [rel("battery-info_app", "2026-10-28T12:00:00Z", "v1.0.6", 12), rel("revanced-YT", "2026-11-01T00:00:00Z", "4", 4),
             rel("none", None, "", 0), rel("x", "2026-09-01T00:00:00Z", "v0.1", 1, True),
             {"name": "draft", "releases": {"totalCount": 1, "nodes": [{"tagName": "v9", "publishedAt": None, "isPrerelease": False}]}}]
    r = rows(repos)
    assert [(n, t) for _, n, t, _, _ in r] == [("PowerGyan", "v1.0.6"), ("x", "v0.1")], r
    out = svg(r, "dark", datetime(2026, 11, 7, tzinfo=timezone.utc))
    assert out.count('class="row"') == 2 and "12 releases" in out and "1 release<" in out and "v0.1 · pre" in out
    assert "&lt;x&gt;" in svg([("2026-11-01T00:00:00Z", "<x>", "v1", 1, False)], "light", datetime(2026, 11, 7, tzinfo=timezone.utc))
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
        sys.exit()
    user, out_dir = sys.argv[1], sys.argv[2]
    now = datetime.now(timezone.utc)
    items = rows(fetch(user))
    os.makedirs(out_dir, exist_ok=True)
    for theme in THEMES:
        with open(os.path.join(out_dir, f"releases-{theme}.svg"), "w") as f:
            f.write(svg(items, theme, now))
