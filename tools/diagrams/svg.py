"""svg.py - tiny SVG helper shared by every diagram script.

One palette for the whole repo (see README "The color code"):
    blue    = activations      amber   = weights
    magenta = partial sums     green   = finished outputs
    violet  = compute / array  slate   = control
"""
from xml.sax.saxutils import escape

C = dict(
    ink="#1E293B", muted="#475569", faint="#94A3B8", line="#CBD5E1", bg="#F8FAFC", white="#FFFFFF",
    act="#2563EB", act_bg="#DBEAFE", act_dk="#1E3A8A",
    wt="#D97706", wt_bg="#FEF3C7", wt_dk="#92400E",
    ps="#C026D3", ps_bg="#FAE8FF", ps_dk="#86198F",
    out="#059669", out_bg="#D1FAE5", out_dk="#065F46",
    mxu="#7C3AED", mxu_bg="#EDE9FE", mxu_dk="#4C1D95",
    ctl="#64748B", ctl_bg="#E2E8F0",
    red="#DC2626", red_bg="#FEE2E2", cyan="#0891B2", cyan_bg="#CFFAFE",
)
FONT = "Segoe UI, Helvetica, Arial, sans-serif"
MONO = "Consolas, Menlo, monospace"


class Svg:
    def __init__(self, w, h, title=None, subtitle=None):
        self.w, self.h, self.parts = w, h, []
        self.parts.append(f'<rect width="{w}" height="{h}" fill="{C["bg"]}"/>')
        for col, nm in [(C["act"], "B"), (C["wt"], "A"), (C["ps"], "M"), (C["out"], "G"),
                        (C["ctl"], "S"), (C["mxu"], "V"), (C["red"], "R")]:
            self.parts.insert(0, f'<marker id="a{nm}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
                                 f'markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{col}"/></marker>')
        self._marker = {C["act"]: "aB", C["wt"]: "aA", C["ps"]: "aM", C["out"]: "aG",
                        C["ctl"]: "aS", C["mxu"]: "aV", C["red"]: "aR"}
        if title:
            self.text(30, 42, title, 26, weight=700)
        if subtitle:
            for i, line in enumerate(subtitle if isinstance(subtitle, list) else [subtitle]):
                self.text(30, 68 + 20 * i, line, 14, C["muted"])

    def add(self, s):
        self.parts.append(s)
        return self

    def text(self, x, y, s, size=13, fill=None, weight=400, anchor="start", mono=False, rotate=None, italic=False):
        tr = f' transform="rotate({rotate} {x} {y})"' if rotate else ""
        st = ' font-style="italic"' if italic else ""
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill or C["ink"]}" '
                 f'font-weight="{weight}" text-anchor="{anchor}"{st} '
                 f'font-family="{MONO if mono else FONT}"{tr}>{escape(str(s))}</text>')

    def rect(self, x, y, w, h, fill, stroke=None, sw=1.5, rx=6, dash=None, opacity=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        o = f' fill-opacity="{opacity}"' if opacity is not None else ""
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}"{o} '
                 f'stroke="{stroke or "none"}" stroke-width="{sw}"{d}/>')

    def circle(self, x, y, r, fill, stroke=None, sw=2):
        self.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" stroke="{stroke or "none"}" stroke-width="{sw}"/>')

    def line(self, x1, y1, x2, y2, stroke, sw=2, arrow=False, dash=None, start_arrow=False):
        m = f' marker-end="url(#{self._marker.get(stroke, "aS")})"' if arrow else ""
        ms = f' marker-start="url(#{self._marker.get(stroke, "aS")})"' if start_arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" '
                 f'stroke-width="{sw}"{m}{ms}{d}/>')

    def path(self, d, stroke, sw=2, fill="none", arrow=False, dash=None):
        m = f' marker-end="url(#{self._marker.get(stroke, "aS")})"' if arrow else ""
        ds = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<path d="{d}" stroke="{stroke}" stroke-width="{sw}" fill="{fill}"{m}{ds}/>')

    def box(self, x, y, w, h, title, sub=None, kind="ctl", size=15):
        fill, stroke, dark = C[f"{kind}_bg"], C[kind], C.get(f"{kind}_dk", C["ink"])
        self.rect(x, y, w, h, fill, stroke, 2.2, 10)
        if sub:
            self.text(x + w / 2, y + h / 2 - 3, title, size, dark, 700, "middle")
            for i, s in enumerate(sub if isinstance(sub, list) else [sub]):
                self.text(x + w / 2, y + h / 2 + 16 + 15 * i, s, 12, dark, 400, "middle")
        else:
            self.text(x + w / 2, y + h / 2 + 5, title, size, dark, 700, "middle")

    def legend(self, x, y, items, w=190):
        self.rect(x, y, w, 14 + 22 * len(items), C["white"], C["line"], 1, 8)
        for i, (col, label) in enumerate(items):
            self.line(x + 14, y + 18 + 22 * i, x + 40, y + 18 + 22 * i, col, 4)
            self.text(x + 50, y + 22 + 22 * i, label, 12, C["muted"])

    def save(self, path):
        with open(path, "w") as fh:
            fh.write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
                     f'font-family="{FONT}">\n<defs>' +
                     "".join(p for p in self.parts if p.startswith("<marker")) + "</defs>\n" +
                     "\n".join(p for p in self.parts if not p.startswith("<marker")) + "\n</svg>\n")
        print("  wrote", path)
