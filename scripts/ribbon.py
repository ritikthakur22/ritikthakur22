"""Build assets/stack-ribbon.svg (and -light.svg): two rows of tech icons scrolling in opposite directions.

Icons come from skillicons.dev (MIT) once, at build time, and are embedded, so the
README doesn't depend on that site staying up. Re-run after changing ROWS:
    python3 scripts/ribbon.py
"""
import re, urllib.request

ROWS = [
    "ts js kotlin dart py java cs cpp c react nextjs tailwind html css androidstudio flutter".split(),
    "nodejs nestjs express fastapi postgres sqlite prisma firebase git githubactions vercel cloudflare linux bash vscode gradle".split(),
]
SIZE, GAP, W, ROW_H = 56, 18, 880, 76
STEP = SIZE + GAP


def icon(name, theme):
    req = urllib.request.Request(f"https://skillicons.dev/icons?i={name}&theme={theme}", headers={"User-Agent": "profile-ribbon"})
    with urllib.request.urlopen(req, timeout=30) as r:
        svg = r.read().decode()
    assert "<svg" in svg and len(svg) > 300, f"unknown icon {name}"
    # prefix ids so gradients from different icons can't collide once inlined
    svg = re.sub(r'id="([^"]+)"', rf'id="{name}-\1"', svg)
    svg = re.sub(r'url\(#([^)]+)\)', rf'url(#{name}-\1)', svg)
    svg = re.sub(r'href="#([^"]+)"', rf'href="#{name}-\1"', svg)
    return re.sub(r'<svg[^>]*?width="48" height="48"', "<svg", svg.strip(), count=1)


def build(theme):
    cache = {n: icon(n, theme) for row in ROWS for n in row}
    rows = []
    for r, names in enumerate(ROWS):
        span = len(names) * STEP
        items = []
        for k in range(2):  # two copies side by side so the loop is seamless
            for i, n in enumerate(names):
                x = k * span + i * STEP
                items.append(cache[n].replace("<svg", f'<svg x="{x}" y="0" width="{SIZE}" height="{SIZE}"', 1))
        cls = "l" if r == 0 else "r"
        rows.append(f'<g transform="translate(0 {10 + r * ROW_H})"><g class="{cls}" style="--span:-{span}px">{"".join(items)}</g></g>')
    span0, span1 = (len(n) * STEP for n in ROWS)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{10 + 2 * ROW_H}" viewBox="0 0 {W} {10 + 2 * ROW_H}" role="img" aria-label="Tech stack: {', '.join(n for row in ROWS for n in row)}">
<style>
.l {{ animation: left 40s linear infinite; }}
.r {{ animation: right 40s linear infinite; }}
@keyframes left {{ from {{ transform: translateX(0); }} to {{ transform: translateX(-{span0}px); }} }}
@keyframes right {{ from {{ transform: translateX(-{span1}px); }} to {{ transform: translateX(0); }} }}
@media (prefers-reduced-motion: reduce) {{ .l, .r {{ animation: none; }} }}
</style>
<defs>
<linearGradient id="fade" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".08" stop-color="#fff"/><stop offset=".92" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<mask id="edges"><rect width="{W}" height="{10 + 2 * ROW_H}" fill="url(#fade)"/></mask>
</defs>
<g mask="url(#edges)">{"".join(rows)}</g>
</svg>
'''


if __name__ == "__main__":
    for theme, path in (("dark", "assets/stack-ribbon.svg"), ("light", "assets/stack-ribbon-light.svg")):
        out = build(theme)
        assert len(re.findall(r"<svg x=", out)) == 2 * sum(len(r) for r in ROWS)
        with open(path, "w") as f:
            f.write(out)
        print(f"wrote {path} ({len(out) // 1024} KB)")
