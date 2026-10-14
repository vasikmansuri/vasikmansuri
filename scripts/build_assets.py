#!/usr/bin/env python3
"""Build the futuristic SVG panels shown in the profile README.

    pip install fonttools brotli
    python3 scripts/build_assets.py

Fonts (Orbitron, Space Grotesk, JetBrains Mono, all OFL), icons and the
GitHub avatar are downloaded once into scripts/.cache. Each SVG embeds only
the glyphs it uses, so the panels look the same on every OS.
"""
import base64
import html
import io
import pathlib
import re
import urllib.request

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
CACHE = ROOT / "scripts" / ".cache"
W = 1280

BG, PANEL, LINE = "#05070d", "#0a0f18", "#1a2332"
LIME, CYAN, VIOLET, PINK = "#c6ff3d", "#22d3ee", "#a78bfa", "#f472b6"
TEXT, MUTED, DIM = "#e6edf3", "#8b98ad", "#3b4659"

GOOGLE = "https://raw.githubusercontent.com/google/fonts/main/ofl"
FONT_SRC = {
    "orbitron": f"{GOOGLE}/orbitron/Orbitron%5Bwght%5D.ttf",
    "grotesk": f"{GOOGLE}/spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf",
    "mono": f"{GOOGLE}/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf",
}
FACES = {"Orb": ("orbitron", 800), "OrbM": ("orbitron", 600), "Grot": ("grotesk", 500), "Mono": ("mono", 500)}
FALLBACK = {"Orb": "Orbitron,'Arial Black',sans-serif", "OrbM": "Orbitron,Arial,sans-serif",
            "Grot": "'Segoe UI',Helvetica,Arial,sans-serif", "Mono": "Menlo,Consolas,monospace"}
AVATAR = "https://github.com/vasikmansuri.png?size=320"
SKILLICON = "https://skillicons.dev/icons?i={}&theme=dark"
SIMPLEICON = "https://cdn.jsdelivr.net/npm/simple-icons@13.0.0/icons/{}.svg"


# ---------------------------------------------------------------- downloads
def fetch(url, name):
    path = CACHE / name
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        path.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    return path.read_bytes()


def b64(data):
    return base64.b64encode(data).decode()


# -------------------------------------------------------------------- fonts
class Fonts:
    def __init__(self):
        self.raw, self.tt = {}, {}
        for face, (src, wght) in FACES.items():
            font = TTFont(io.BytesIO(fetch(FONT_SRC[src], f"{src}.ttf")))
            font = instancer.instantiateVariableFont(font, {"wght": wght})
            buf = io.BytesIO()
            font.save(buf)
            self.raw[face] = buf.getvalue()
            self.tt[face] = TTFont(io.BytesIO(self.raw[face]))

    def width(self, face, text, size, ls=0.0):
        font = self.tt[face]
        cmap, hmtx = font.getBestCmap(), font["hmtx"]
        upm = font["head"].unitsPerEm
        units = sum(hmtx[cmap.get(ord(c), ".notdef")][0] for c in text)
        return units * size / upm + ls * len(text)

    def css(self, text):
        rules = []
        for face, raw in self.raw.items():
            font = TTFont(io.BytesIO(raw))
            opts = subset.Options()
            opts.layout_features = ["kern"]
            sub = subset.Subsetter(opts)
            sub.populate(text=text + " ")
            sub.subset(font)
            font.flavor = "woff2"
            buf = io.BytesIO()
            font.save(buf)
            rules.append(f"@font-face{{font-family:'{face}';src:url(data:font/woff2;base64,{b64(buf.getvalue())}) format('woff2')}}")
            rules.append(f".{face.lower()}{{font-family:'{face}',{FALLBACK[face]}}}")
        return "".join(rules)


F = None  # set in main()

BASE_CSS = """
@keyframes blink{50%{opacity:0}}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes spinr{to{transform:rotate(-360deg)}}
@keyframes pulse{0%{transform:scale(1);opacity:.9}100%{transform:scale(2.6);opacity:0}}
@keyframes eq{0%,100%{transform:scaleY(.2)}50%{transform:scaleY(1)}}
.blink{animation:blink 1.1s step-end infinite}
.pulse{transform-box:fill-box;transform-origin:center;animation:pulse 2s ease-out infinite}
.eq{transform-box:fill-box;transform-origin:center;animation:eq 1.2s ease-in-out infinite}
"""

DEFS = f"""
<filter id="glow" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="7" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="soft" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<linearGradient id="neon" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{LIME}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>
<linearGradient id="fadeR" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{LIME}" stop-opacity=".7"/><stop offset="1" stop-color="{LIME}" stop-opacity="0"/></linearGradient>
<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#0e1522" stroke-width="1"/></pattern>
"""


def esc(s):
    return html.escape(s, quote=False)


def doc(name, height, body, label, css="", defs=""):
    text = html.unescape("".join(re.findall(r">([^<>]+)<", body)))
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}" role="img" aria-label="{html.escape(label)}">'
        f"<defs><style>{F.css(text)}{BASE_CSS}{css}</style>{DEFS}{defs}</defs>"
        f'<rect width="{W}" height="{height}" rx="20" fill="{BG}"/>'
        f'<rect width="{W}" height="{height}" rx="20" fill="url(#grid)"/>'
        f"{body}"
        f'<rect x=".5" y=".5" width="{W - 1}" height="{height - 1}" rx="20" fill="none" stroke="{LINE}"/>'
        "</svg>"
    )
    (OUT / name).write_text(svg)
    print(f"  {name:<18} {len(svg) / 1024:6.1f} KB")


# --------------------------------------------------------------- components
def t(x, y, s, face, size, fill, anchor="start", ls=0, extra=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" class="{face.lower()}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" letter-spacing="{ls}" {extra}>{esc(s)}</text>')


def header(num, title, meta, y=54):
    tw = F.width("Orb", title, 22, 4)
    mw = F.width("Mono", meta, 12, 1)
    x1, x2 = 118 + tw + 18, W - 40 - mw - 18
    return (t(40, y, num, "Orb", 22, LIME, ls=2, extra='filter="url(#soft)"')
            + t(84, y, "//", "Mono", 18, DIM)
            + t(118, y, title, "Orb", 22, TEXT, ls=4)
            + f'<line x1="{x1:.0f}" y1="{y - 8}" x2="{x2:.0f}" y2="{y - 8}" stroke="url(#fadeR)" stroke-width="1.5"/>'
            + t(W - 40, y - 2, meta, "Mono", 12, MUTED, "end", 1))


def panel(x, y, w, h, accent=LIME, fill=PANEL):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" stroke="{LINE}"/>'
    L = 16
    for cx, cy, dx, dy in ((x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        s += (f'<path d="M{cx + dx * L} {cy}H{cx}V{cy + dy * L}" fill="none" stroke="{accent}" stroke-width="2" '
              f'opacity=".85" transform="translate({dx * 4} {dy * 4})"/>')
    return s


def chip(x, y, s, color, size=12):
    w = F.width("Mono", s, size, 1) + 26
    h = size + 16
    return (f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{h}" rx="{h / 2}" fill="{color}" fill-opacity=".08" stroke="{color}" stroke-opacity=".55"/>'
            + t(x + w / 2, y + h / 2 + size * 0.36, s, "Mono", size, color, "middle", 1)), w


def floor(top, bottom, idp, speed=2.6):
    """Synthwave-style perspective grid scrolling toward the viewer."""
    vx, n = W / 2, 8
    ys = [top + (bottom - top) * (k / n) ** 2 for k in range(n + 2)]
    css, lines = "", ""
    for k in range(n + 1):
        css += f"@keyframes {idp}h{k}{{to{{transform:translateY({ys[k + 1] - ys[k]:.1f}px)}}}}"
        lines += f'<line x1="0" x2="{W}" y1="{ys[k]:.1f}" y2="{ys[k]:.1f}" style="animation:{idp}h{k} {speed}s linear infinite"/>'
    for i in range(-22, 23):
        lines += f'<line x1="{vx + i * 14:.0f}" y1="{top}" x2="{vx + i * 120:.0f}" y2="{bottom}"/>'
    defs = (f'<linearGradient id="{idp}m" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="#fff" stop-opacity=".9"/></linearGradient>'
            f'<mask id="{idp}k"><rect y="{top}" width="{W}" height="{bottom - top}" fill="url(#{idp}m)"/></mask>'
            f'<clipPath id="{idp}c"><rect y="{top}" width="{W}" height="{bottom - top}" rx="20"/></clipPath>')
    body = (f'<g mask="url(#{idp}k)" clip-path="url(#{idp}c)" stroke="{CYAN}" stroke-opacity=".45" stroke-width="1">{lines}</g>'
            f'<line x1="0" x2="{W}" y1="{top}" y2="{top}" stroke="url(#neon)" stroke-opacity=".6" filter="url(#soft)"/>')
    return body, css, defs


# ------------------------------------------------------------------ panels
def hero():
    H, cx, cy = 520, 250, 248
    avatar = b64(fetch(AVATAR, "avatar.jpg"))
    defs = (f'<radialGradient id="g1" cx="{cx / W:.3f}" cy="{cy / H:.3f}" r=".35"><stop offset="0" stop-color="{LIME}" stop-opacity=".22"/><stop offset="1" stop-color="{LIME}" stop-opacity="0"/></radialGradient>'
            f'<radialGradient id="g2" cx=".85" cy=".1" r=".5"><stop offset="0" stop-color="{VIOLET}" stop-opacity=".16"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></radialGradient>'
            f'<clipPath id="av"><circle cx="{cx}" cy="{cy}" r="118"/></clipPath>')
    s = f'<rect width="{W}" height="{H}" rx="20" fill="url(#g1)"/><rect width="{W}" height="{H}" rx="20" fill="url(#g2)"/>'

    fl, css, fdefs = floor(432, H, "hf")
    s += fl
    defs += fdefs

    # telemetry bar
    s += t(40, 42, "SYS://VASIKMANSURI  ▸  PROFILE v3.0", "Mono", 12, MUTED, ls=1)
    s += t(W - 40, 42, "23.02°N  72.57°E   ·   UTC+05:30", "Mono", 12, MUTED, "end", 1)

    # avatar with HUD rings
    s += (f'<circle cx="{cx}" cy="{cy}" r="122" fill="{LIME}" opacity=".18" filter="url(#glow)"/>'
          f'<image href="data:image/jpeg;base64,{avatar}" x="{cx - 130}" y="{cy - 130}" width="260" height="260" clip-path="url(#av)"/>'
          f'<circle cx="{cx}" cy="{cy}" r="118" fill="none" stroke="{LIME}" stroke-width="2"/>')
    origin = f"transform-origin:{cx}px {cy}px"
    s += f'<circle cx="{cx}" cy="{cy}" r="134" fill="none" stroke="{LIME}" stroke-width="2" stroke-dasharray="2 7" style="{origin};animation:spin 40s linear infinite"/>'
    s += f'<circle cx="{cx}" cy="{cy}" r="150" fill="none" stroke="{CYAN}" stroke-width="2.5" stroke-dasharray="90 40 14 40 160 60" opacity=".85" style="{origin};animation:spinr 24s linear infinite"/>'
    ticks = ""
    for a in range(0, 360, 5):
        long = a % 30 == 0
        ticks += (f'<line x1="{cx}" y1="{cy - 166}" x2="{cx}" y2="{cy - (178 if long else 171)}" '
                  f'stroke="{LIME if long else DIM}" stroke-width="{2 if long else 1}" transform="rotate({a} {cx} {cy})"/>')
    s += f'<g style="{origin};animation:spin 90s linear infinite">{ticks}</g>'
    s += (f'<g style="{origin};animation:spin 7s linear infinite"><circle cx="{cx}" cy="{cy - 150}" r="5" fill="{LIME}" filter="url(#soft)"/></g>'
          f'<g style="{origin};animation:spinr 11s linear infinite"><circle cx="{cx}" cy="{cy + 134}" r="3.5" fill="{CYAN}" filter="url(#soft)"/></g>')

    # identity
    x0 = 490
    prompt = "> boot --profile vasikmansuri"
    s += t(x0, 136, prompt, "Mono", 15, CYAN)
    s += f'<rect class="blink" x="{x0 + F.width("Mono", prompt, 15) + 6:.0f}" y="123" width="9" height="16" fill="{CYAN}"/>'
    name = "VASIK MANSURI"
    css += ("@keyframes gl1{0%,88%,100%{opacity:0;transform:none}89%{opacity:.8;transform:translate(-5px,1px)}91%{opacity:.8;transform:translate(4px,-1px)}93%{opacity:0}}"
            "@keyframes gl2{0%,89%,100%{opacity:0;transform:none}90%{opacity:.7;transform:translate(5px,-2px)}92%{opacity:.7;transform:translate(-3px,1px)}94%{opacity:0}}")
    s += t(x0, 216, name, "Orb", 62, PINK, ls=2, extra='opacity="0" style="animation:gl1 5s infinite"')
    s += t(x0, 216, name, "Orb", 62, CYAN, ls=2, extra='opacity="0" style="animation:gl2 5s infinite"')
    s += t(x0, 216, name, "Orb", 62, "url(#neon)", ls=2, extra='filter="url(#glow)"')
    s += t(x0 + 2, 262, "TECHNICAL LEAD  //  AI ENGINEER", "OrbM", 21, TEXT, ls=5)
    s += t(x0, 312, "I build AI voice agents that hold real phone calls,", "Grot", 20, MUTED)
    s += t(x0, 340, "and the custom LLM models that power them.", "Grot", 20, MUTED)
    x = x0
    for label, color in (("AI VOICE CALLING", LIME), ("CUSTOM LLMs", CYAN), ("6+ YEARS", VIOLET), ("AHMEDABAD · IN", PINK)):
        c, w = chip(x, 370, label, color)
        s += c
        x += w + 12

    # scanline
    css += f"@keyframes scan{{from{{transform:translateY(-20px)}}to{{transform:translateY({H}px)}}}}"
    s += f'<rect width="{W}" height="2" fill="{LIME}" opacity=".18" style="animation:scan 7s linear infinite"/>'
    doc("hero.svg", H, s, "Vasik Mansuri, Technical Lead and AI Engineer. Builds AI voice agents and custom LLM models.", css, defs)


def about():
    H = 440
    s = header("01", "SYSTEM_PROFILE", "[ SECTOR 01 · IDENTITY ]")
    s += panel(40, 88, 600, 320, LIME)
    s += t(66, 120, "PROFILE.SYS", "Mono", 12, DIM, ls=2) + t(614, 120, "● VERIFIED", "Mono", 11, LIME, "end", 1)
    rows = [("ROLE", "Technical Lead & AI Engineer", TEXT),
            ("COMPANY", "Vnnovate Solutions Pvt. Ltd.", TEXT),
            ("EXPERIENCE", "6+ years · shipping since 2019", TEXT),
            ("FOCUS", "AI voice agents · Custom LLMs · RAG", LIME),
            ("STACK", "Node.js · TypeScript · React · Vue · Laravel", TEXT),
            ("CLOUD", "AWS · GCP · Docker · CI/CD", TEXT),
            ("BASE", "Ahmedabad, India", TEXT)]
    for i, (k, v, color) in enumerate(rows):
        y = 162 + i * 34
        s += t(66, y, k, "Mono", 12, MUTED, ls=1.5) + t(206, y, v, "Grot", 16, color)
        if i < len(rows) - 1:
            s += f'<line x1="66" x2="614" y1="{y + 13}" y2="{y + 13}" stroke="{LINE}" stroke-dasharray="2 5"/>'

    s += panel(660, 88, 580, 320, CYAN)
    s += t(686, 120, "LIVE_CALL.STREAM", "Mono", 12, DIM, ls=2)
    s += f'<circle class="blink" cx="1134" cy="116" r="4.5" fill="{PINK}"/>' + t(1214, 120, "REC 00:06", "Mono", 11, PINK, "end", 1)
    bars = ""
    for i in range(56):
        x = 690 + i * 9.3
        dur = 0.7 + (i * 37 % 11) / 10
        bars += (f'<rect class="eq" x="{x:.1f}" y="146" width="4" height="58" rx="2" fill="url(#neon)" '
                 f'style="animation-duration:{dur:.2f}s;animation-delay:-{(i * 13 % 9) / 10:.1f}s"/>')
    s += f'<g filter="url(#soft)">{bars}</g>'
    s += f'<line x1="686" x2="1214" y1="228" y2="228" stroke="{LINE}"/>'
    lines = [("00:02", "CALLER", CYAN, [("Hi, can I move my interview to Thursday?", TEXT)]),
             ("00:03", "AGENT ", LIME, [('fn:checkCalendar("thu") ', VIOLET), ("✓", LIME)]),
             ("00:05", "AGENT ", LIME, [("Thursday 3 PM is free. Booking it now.", TEXT)]),
             ("00:06", "AGENT ", LIME, [("fn:bookMeeting() ", VIOLET), ("✓ invite sent", LIME)])]
    css = ""
    for i, (ts, who, wc, parts) in enumerate(lines):
        start = 6 + i * 14
        css += f"@keyframes ln{i}{{0%,{start}%{{opacity:0}}{start + 3}%,92%{{opacity:1}}100%{{opacity:0}}}}"
        spans = "".join(f'<tspan fill="{c}">{esc(p)}</tspan>' for p, c in parts)
        s += (f'<text x="686" y="{262 + i * 34}" class="mono" font-size="13" xml:space="preserve" style="animation:ln{i} 12s infinite;animation-delay:-6s">'
              f'<tspan fill="{DIM}">[{ts}] </tspan><tspan fill="{wc}">{who} ▸ </tspan>{spans}</text>')
    doc("about.svg", H, s, "System profile: Technical Lead and AI Engineer at Vnnovate Solutions, 6+ years, focused on AI voice agents and custom LLMs. Demo transcript of an AI voice agent booking a meeting.", css)


ICONS = {  # Feather icons (MIT), 24px grid
    "phone": '<path d="M15.05 5A5 5 0 0 1 19 8.95M15.05 1A9 9 0 0 1 23 8.94M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>',
    "cpu": '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3"/>',
    "graph": '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.59 13.51l6.83 3.98M15.41 6.51l-6.82 3.98"/>',
    "server": '<rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><path d="M6 6h.01M6 18h.01"/>',
}


def ai_modules():
    H = 590
    s = header("02", "AI_MODULES", "[ SECTOR 02 · CAPABILITIES ]")
    mods = [("01", "VOICE CALLING AGENTS", "telephony · realtime · voice", "phone", LIME,
             ["Twilio Voice ⇄ OpenAI Realtime API, streamed live",
              "Silence & noise thresholds for natural turn-taking",
              "Function calls mid-call: booking, lookups, CRM updates"]),
            ("02", "CUSTOM LLM MODELS", "llm · rag · inference", "cpu", CYAN,
             ["My own LLM models, built for specific product tasks",
              "Served behind production APIs alongside GPT-4",
              "RAG pipelines grounded in company data"]),
            ("03", "AGENT ORCHESTRATION", "langchain · tools · webhooks", "graph", VIOLET,
             ["LangChain context management for multi-turn tasks",
              "Tools wired to real business APIs and webhooks",
              "Calendar sync with Google Workspace & Microsoft Graph"]),
            ("04", "AI IN PRODUCTION", "node · redis · docker · ci/cd", "server", PINK,
             ["Node.js services with Redis queues and caching",
              "Dockerised deploys on AWS & GCP with CI/CD",
              "Leading the team that ships it, end to end"])]
    w, h = 580, 226
    per = 2 * (w + h)
    css = f"@keyframes trace{{to{{stroke-dashoffset:-{per}}}}}"
    for i, (num, title, sub, icon, color, bullets) in enumerate(mods):
        x, y = 40 + (i % 2) * 620, 88 + (i // 2) * 246
        s += panel(x, y, w, h, color)
        s += (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="none" stroke="{color}" stroke-width="2" '
              f'stroke-dasharray="150 {per - 150}" filter="url(#soft)" style="animation:trace {7 + i}s linear infinite;animation-delay:-{i * 1.7:.1f}s"/>')
        s += t(x + 28, y + 36, f"MODULE_{num}", "Mono", 11, DIM, ls=2)
        c, cw = chip(0, 0, "● DEPLOYED", color, 10)
        s += f'<g transform="translate({x + w - 28 - cw:.1f} {y + 20})">{c}</g>'
        s += (f'<rect x="{x + 28}" y="{y + 56}" width="58" height="58" rx="12" fill="{color}" fill-opacity=".07" stroke="{color}" stroke-opacity=".5"/>'
              f'<g transform="translate({x + 40} {y + 68}) scale(1.4)" fill="none" stroke="{color}" stroke-width="1.6" '
              f'stroke-linecap="round" stroke-linejoin="round" filter="url(#soft)">{ICONS[icon]}</g>')
        s += t(x + 106, y + 84, title, "Orb", 19, TEXT, ls=1.5)
        s += t(x + 106, y + 106, sub, "Mono", 12, color, ls=1)
        for j, b in enumerate(bullets):
            by = y + 152 + j * 27
            s += t(x + 30, by, "▹", "Mono", 14, color) + t(x + 52, by, b, "Grot", 15.5, MUTED)
    doc("ai-modules.svg", H, s, "AI modules: voice calling agents, custom LLM models, agent orchestration with LangChain, and AI in production.", css)


def tile_skill(slug):
    return f"data:image/svg+xml;base64,{b64(fetch(SKILLICON.format(slug), f'skill-{slug}.svg'))}"


def tile_simple(x, y, slug, color):
    svg = fetch(SIMPLEICON.format(slug), f"si-{slug}.svg").decode()
    d = re.search(r'<path d="([^"]+)"', svg).group(1)
    return (f'<rect x="{x}" y="{y}" width="56" height="56" rx="13" fill="#242938"/>'
            f'<g transform="translate({x + 14} {y + 14}) scale(1.1667)"><path d="{d}" fill="{color}"/></g>')


def tile_text(x, y, label, color, face="Orb", size=15):
    return (f'<rect x="{x}" y="{y}" width="56" height="56" rx="13" fill="#242938"/>'
            + t(x + 28, y + 28 + size * 0.36, label, face, size, color, "middle"))


def stack():
    def sk(*pairs):
        return [("sk", slug, None, label) for slug, label in pairs]

    rows = [("AI & VOICE", [("si", "openai", "#ffffff", "OpenAI"), ("si", "langchain", CYAN, "LangChain"),
                            ("si", "twilio", "#F22F46", "Twilio"), ("tx", "LLM", LIME, "LLMs"),
                            ("tx", "RAG", VIOLET, "RAG"), ("fx", "ƒ(x)", CYAN, "Functions")]),
            ("BACKEND", sk(("nodejs", "Node.js"), ("express", "Express"), ("ts", "TypeScript"),
                           ("graphql", "GraphQL"), ("laravel", "Laravel"), ("php", "PHP"))),
            ("FRONTEND", sk(("react", "React"), ("vue", "Vue"), ("js", "JavaScript"),
                            ("tailwind", "Tailwind"), ("bootstrap", "Bootstrap"), ("html", "HTML5"))),
            ("DATA & CLOUD", sk(("mysql", "MySQL"), ("mongodb", "MongoDB"), ("redis", "Redis"),
                                ("firebase", "Firebase"), ("aws", "AWS"), ("gcp", "GCP"))),
            ("DEVOPS", sk(("docker", "Docker"), ("nginx", "Nginx"), ("linux", "Linux"),
                          ("githubactions", "Actions"), ("git", "Git"), ("postman", "Postman")))]
    rh = 112
    H = 88 + len(rows) * rh + 20 + 32
    s = header("03", "TECH_ARSENAL", "[ SECTOR 03 · LOADOUT ]")
    s += panel(40, 88, 1200, len(rows) * rh + 20, CYAN)
    s += f'<line x1="300" x2="300" y1="108" y2="{88 + len(rows) * rh}" stroke="{LINE}"/>'
    for i, (label, items) in enumerate(rows):
        y0 = 98 + i * rh
        s += t(70, y0 + 52, label, "OrbM", 15, LIME if i == 0 else TEXT, ls=3)
        s += t(70, y0 + 74, f"[{len(items):02d} modules loaded]", "Mono", 11, DIM, ls=1)
        for j, (kind, slug, c, name) in enumerate(items):
            x, y = 328 + j * 150, y0 + 18
            if kind == "sk":
                s += f'<image href="{tile_skill(slug)}" x="{x}" y="{y}" width="56" height="56"/>'
            elif kind == "si":
                s += tile_simple(x, y, slug, c)
            elif kind == "fx":
                s += tile_text(x, y, slug, c, "Mono", 17)
            else:
                s += tile_text(x, y, slug, c)
            s += t(x + 68, y + 33, name, "Grot", 14, MUTED)
        if i < len(rows) - 1:
            s += f'<line x1="70" x2="1210" y1="{y0 + rh}" y2="{y0 + rh}" stroke="{LINE}" stroke-dasharray="2 6"/>'
    doc("stack.svg", H, s, "Tech stack. AI and voice: OpenAI, LangChain, Twilio, custom LLMs, RAG, function calling. Backend: Node.js, Express, TypeScript, GraphQL, Laravel, PHP. Frontend: React, Vue, JavaScript, Tailwind, Bootstrap, HTML. Data and cloud: MySQL, MongoDB, Redis, Firebase, AWS, GCP. DevOps: Docker, Nginx, Linux, GitHub Actions, Git, Postman.")


def wrap(text, face, size, maxw):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if F.width(face, trial, size) > maxw and cur:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + [cur]


def missions():
    items = [("M-01", "NURTUREME · AI RECRUITING PLATFORM", "TECHNICAL LEAD", LIME,
              "Built “Stella”, an AI voice agent that phones candidates over Twilio + OpenAI Realtime, with LangChain orchestration, AI matching and automated calendar booking.",
              ["OpenAI Realtime", "LangChain", "Twilio", "Node.js", "Redis", "AWS"]),
             ("M-02", "CUSTOM LLM MODELS", "CREATOR", CYAN,
              "Built my own LLM models for domain-specific tasks and plugged them into production products with RAG and function calling.",
              ["Custom LLMs", "RAG", "Function Calling", "Node.js"]),
             ("M-03", "JAGUAR LAND ROVER SA · DEALER MANAGEMENT", "CORE ARCHITECTURE", VIOLET,
              "Nationwide dealership backend for Jaguar Land Rover South Africa: inventory sync pipelines, lead tracking portals and live analytics dashboards.",
              ["Node.js", "Vue", "React", "Laravel", "MongoDB", "GCP"]),
             ("M-04", "HIGH-TRAFFIC APIs & MICROSERVICES", "SENIOR ENGINEER", PINK,
              "Secure REST and GraphQL APIs for web and mobile apps, tuned with DB indexing, Redis caching and background queues.",
              ["GraphQL", "Node.js", "Redis", "MySQL", "Docker"])]
    step, h = 140, 124
    H = 88 + len(items) * step + 30
    s = header("04", "MISSION_LOG", "[ SECTOR 04 · SHIPPED ]")
    for i, (mid, title, role, color, desc, tags) in enumerate(items):
        y = 88 + i * step
        s += panel(40, y, 1200, h, color)
        s += f'<rect x="40" y="{y + 18}" width="3" height="{h - 36}" fill="{color}" filter="url(#soft)"/>'
        s += t(70, y + 50, mid, "Orb", 22, color, ls=1, extra='filter="url(#soft)"')
        s += f'<circle class="blink" cx="75" cy="{y + 76}" r="3.5" fill="{color}"/>' + t(85, y + 80, "SHIPPED", "Mono", 10, MUTED, ls=1.5)
        s += t(176, y + 40, title, "Orb", 16, TEXT, ls=1)
        s += t(176, y + 62, f"ROLE ▸ {role}", "Mono", 11, color, ls=1.5)
        for j, line in enumerate(wrap(desc, "Grot", 15, 660)[:2]):
            s += t(176, y + 88 + j * 20, line, "Grot", 15, MUTED)
        tx, ty = 880, y + 26
        for tag in tags:
            w = F.width("Mono", tag, 11, .5) + 20
            if tx + w > 1212:
                tx, ty = 880, ty + 30
            s += (f'<rect x="{tx:.1f}" y="{ty}" width="{w:.1f}" height="22" rx="6" fill="{color}" fill-opacity=".07" stroke="{color}" stroke-opacity=".35"/>'
                  + t(tx + w / 2, ty + 15, tag, "Mono", 11, TEXT, "middle", .5))
            tx += w + 8
    s += t(40, H - 14, "// most professional work is closed source and owned by clients or my employer", "Mono", 11, DIM)
    doc("missions.svg", H, s, "Projects: NurtureMe AI recruiting platform with the Stella voice agent; custom LLM models; Jaguar Land Rover South Africa dealer management system; high-traffic APIs and microservices.")


def timeline():
    H = 390
    s = header("05", "CAREER_TIMELINE", "[ SECTOR 05 · TRAJECTORY ]")
    css = "@keyframes flowline{to{stroke-dashoffset:-32}}"
    s += f'<line x1="90" x2="1190" y1="206" y2="206" stroke="{DIM}" stroke-width="2"/>'
    s += (f'<line x1="90" x2="1190" y1="206" y2="206" stroke="url(#neon)" stroke-width="2" stroke-dasharray="6 10" '
          f'style="animation:flowline 1.2s linear infinite" filter="url(#soft)"/>')
    stops = [("DEC 2019", "WEB DEVELOPER", "Elsner Technologies", "1Y 9M", False),
             ("SEP 2021", "FULL STACK DEVELOPER", "Vnnovate Solutions", "2Y 10M", False),
             ("JUL 2024", "SENIOR SOFTWARE ENGINEER", "Vnnovate Solutions", "1Y", False),
             ("JUL 2025 → NOW", "TECHNICAL LEAD", "Vnnovate Solutions", "ACTIVE", True)]
    for i, (date, role, org, dur, cur) in enumerate(stops):
        x = 190 + i * 300
        s += t(x, 172, date, "Mono", 13, LIME if cur else CYAN, "middle", 1)
        if cur:
            s += f'<circle class="pulse" cx="{x}" cy="206" r="10" fill="none" stroke="{LIME}" stroke-width="2"/>'
        s += f'<circle cx="{x}" cy="206" r="9" fill="{LIME if cur else BG}" stroke="{LIME if cur else CYAN}" stroke-width="3" filter="url(#soft)"/>'
        s += t(x, 252, role, "OrbM", 13, LIME if cur else TEXT, "middle", 1)
        s += t(x, 276, org, "Grot", 15, MUTED, "middle")
        s += t(x, 298, dur, "Mono", 11, LIME if cur else DIM, "middle", 1.5)
    s += panel(40, 322, 1200, 46, VIOLET)
    s += t(66, 350, "EDU ▸", "Mono", 12, VIOLET, ls=1.5)
    s += t(124, 350, "MCA · GLS University (2018–2020)      ◆      BCA · St. Xavier's College (2015–2018)", "Grot", 15, MUTED,
           extra='xml:space="preserve"')
    doc("timeline.svg", H, s, "Career: Web Developer at Elsner Technologies (2019), Full Stack Developer at Vnnovate Solutions (2021), Senior Software Engineer (2024), Technical Lead (2025 to now). MCA, GLS University; BCA, St. Xavier's College.", css)


def section(name, num, title, meta):
    doc(name, 84, header(num, title, meta, y=50), f"Section {num}: {title.replace('_', ' ').title()}")


def footer():
    H = 230
    fl, css, defs = floor(120, H, "ff", 3.2)
    s = fl
    s += t(W / 2, 64, "END OF TRANSMISSION", "Orb", 28, "url(#neon)", "middle", 8, 'filter="url(#glow)"')
    s += t(W / 2, 94, "thanks for stopping by  ·  let's build something intelligent", "Mono", 13, MUTED, "middle", 1,
           'xml:space="preserve"')
    doc("footer.svg", H, s, "End of transmission. Thanks for stopping by.", css, defs)


def main():
    global F
    OUT.mkdir(exist_ok=True)
    F = Fonts()
    print("Building panels:")
    hero(); about(); ai_modules(); stack(); missions(); timeline()
    section("sec-oss.svg", "06", "OPEN_SOURCE", "[ SECTOR 06 · PUBLIC REPOS ]")
    section("sec-uplink.svg", "07", "UPLINK", "[ SECTOR 07 · CONTACT ]")
    footer()


if __name__ == "__main__":
    main()
