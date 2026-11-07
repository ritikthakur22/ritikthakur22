"""Render recent public GitHub activity as animated SVG cards (dark + light).

Usage: python3 scripts/activity.py <user> <out_dir>    (GITHUB_TOKEN optional)
       python3 scripts/activity.py --selftest
"""
import json, os, sys, urllib.request
from datetime import datetime, timezone
from xml.sax.saxutils import escape

MAX_ROWS = 6
HIDE = {"4jean/lav_sms"}  # repos never shown on the card; add more as "owner/name"
THEMES = {
    "dark": dict(bg="#050816", edge="#1c3a57", text="#dcefff", muted="#6f8aa0", row="#0c1a2e"),
    "light": dict(bg="#f7fcff", edge="#cbe3ef", text="#12324a", muted="#5b7689", row="#ffffff"),
}
DOT = {"push": "#00d9ff", "release": "#22c55e", "create": "#a78bfa", "star": "#f5b301", "pr": "#3b82f6", "issue": "#f97316"}


def fetch(user):
    req = urllib.request.Request(f"https://api.github.com/users/{user}/events/public?per_page=100",
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "profile-activity"})
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def rows(events, user):
    out, pushes = [], {}
    for e in sorted(events, key=lambda e: e["created_at"], reverse=True):
        repo, p, t = e["repo"]["name"], e.get("payload", {}), e["type"]
        if repo == f"{user}/{user}" or repo in HIDE:
            continue  # skip this profile repo's own churn and hidden repos
        short = repo.split("/", 1)[1] if repo.startswith(user + "/") else repo
        day = e["created_at"][:10]
        if t == "PushEvent":
            key = (repo, day)
            if key in pushes:
                pushes[key][2] += 1
                continue
            item = ["push", None, 1, e["created_at"], short]
            pushes[key] = item
        elif t == "ReleaseEvent" and p.get("action") == "published":
            tag = (p.get("release") or {}).get("tag_name", "")
            item = ["release", f"Released {tag} of {short}".replace("  ", " "), 0, e["created_at"], short]
        elif t == "CreateEvent" and p.get("ref_type") == "repository":
            item = ["create", f"Created {short}", 0, e["created_at"], short]
        elif t == "PublicEvent":
            item = ["create", f"Open-sourced {short}", 0, e["created_at"], short]
        elif t == "WatchEvent":
            item = ["star", f"Starred {repo}", 0, e["created_at"], short]
        elif t == "PullRequestEvent" and p.get("action") in ("opened", "closed"):
            pr = p.get("pull_request") or {}
            verb = "Merged" if pr.get("merged") else ("Opened" if p["action"] == "opened" else None)
            if not verb:
                continue
            item = ["pr", f"{verb} PR #{pr.get('number', '')} in {short}", 0, e["created_at"], short]
        elif t == "IssuesEvent" and p.get("action") == "opened":
            item = ["issue", f"Opened issue #{(p.get('issue') or {}).get('number', '')} in {short}", 0, e["created_at"], short]
        else:
            continue
        out.append(item)
        if len(out) >= MAX_ROWS:
            break
    for it in out:
        if it[0] == "push":
            it[1] = f"Pushed updates to {it[4]}" + (f"  ×{it[2]}" if it[2] > 1 else "")
    return [(k, text, ts) for k, text, _, ts, _ in out]


def ago(ts, now):
    d = (now - datetime.fromisoformat(ts.replace("Z", "+00:00"))).days
    return "today" if d < 1 else "yesterday" if d < 2 else f"{d}d ago" if d < 30 else f"{d // 30}mo ago"


def svg(items, theme, now):
    c = THEMES[theme]
    w, top, rh = 880, 64, 46
    h = top + max(len(items), 1) * rh + 18
    body = []
    for i, (kind, text, ts) in enumerate(items):
        y = top + i * rh
        body.append(
            f'<g class="row" style="animation-delay:{0.15 + i * 0.12:.2f}s">'
            f'<rect x="20" y="{y}" width="{w - 40}" height="{rh - 8}" rx="10" fill="{c["row"]}" stroke="{c["edge"]}"/>'
            f'<circle cx="42" cy="{y + 19}" r="5" fill="{DOT[kind]}"/>'
            f'<text x="60" y="{y + 24}" class="t">{escape(text[:80])}</text>'
            f'<text x="{w - 36}" y="{y + 24}" class="m" text-anchor="end">{ago(ts, now)}</text></g>')
    if not items:
        body.append(f'<text x="40" y="{top + 24}" class="m">No recent public activity.</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Recent GitHub activity">
<style>
.t {{ font: 500 15px "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif; fill: {c["text"]}; }}
.m {{ font: 500 13px "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif; fill: {c["muted"]}; }}
.h {{ font: 700 13px "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif; letter-spacing: 2px; fill: #00b4d8; }}
.row {{ opacity: 0; animation: in .6s cubic-bezier(.16,1,.3,1) forwards; }}
@keyframes in {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: none; }} }}
@media (prefers-reduced-motion: reduce) {{ .row {{ animation: none; opacity: 1; }} }}
</style>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="16" fill="{c["bg"]}" stroke="{c["edge"]}"/>
<text x="24" y="38" class="h">RECENT ACTIVITY</text>
<text x="{w - 24}" y="38" class="m" text-anchor="end">updated {now:%b %d, %Y}</text>
{"".join(body)}
</svg>
'''


def selftest():
    ev = lambda t, repo, ts, **p: {"type": t, "repo": {"name": repo}, "created_at": ts, "payload": p}
    events = [
        ev("PushEvent", "u/app", "2026-11-05T10:00:00Z"),
        ev("PushEvent", "u/app", "2026-11-05T09:00:00Z"),
        ev("PushEvent", "u/u", "2026-11-05T11:00:00Z"),
        ev("ReleaseEvent", "u/app", "2026-11-04T09:00:00Z", action="published", release={"tag_name": "v1.2"}),
        ev("WatchEvent", "other/lib", "2026-11-03T09:00:00Z", action="started"),
        ev("CreateEvent", "u/new", "2026-11-02T09:00:00Z", ref_type="branch"),
        ev("CreateEvent", "u/new", "2026-11-02T08:00:00Z", ref_type="repository"),
        ev("PullRequestEvent", "u/app", "2026-11-01T09:00:00Z", action="closed", pull_request={"number": 7, "merged": True}),
        ev("WatchEvent", "4jean/lav_sms", "2026-11-01T08:00:00Z", action="started"),
    ]
    r = rows(events, "u")
    assert [t for _, t, _ in r] == ["Pushed updates to app  ×2", "Released v1.2 of app", "Starred other/lib",
                                    "Created new", "Merged PR #7 in app"], r
    now = datetime(2026, 11, 6, tzinfo=timezone.utc)
    assert ago("2026-11-05T10:00:00Z", now) == "today" and ago("2026-10-01T00:00:00Z", now) == "1mo ago"
    out = svg(r, "dark", now)
    assert out.count('class="row"') == 5 and "<script" not in out
    assert "&lt;b&gt;" in svg([("push", "<b>", "2026-11-05T10:00:00Z")], "light", now)  # text is escaped
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
        sys.exit()
    user, out_dir = sys.argv[1], sys.argv[2]
    now = datetime.now(timezone.utc)
    items = rows(fetch(user), user)
    os.makedirs(out_dir, exist_ok=True)
    for theme in THEMES:
        with open(os.path.join(out_dir, f"activity-{theme}.svg"), "w") as f:
            f.write(svg(items, theme, now))
