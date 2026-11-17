"""Render the profile's animated snake and static contribution calendar."""

import sys
from pathlib import Path
from xml.etree import ElementTree as XML

SVG = "http://www.w3.org/2000/svg"
THEME = """
:root {
  color-scheme: light dark;
  --panel: #f8fafc;
  --frame: #e2e8f0;
  --cb: #cbd5e1;
  --ce: #f1f5f9;
  --cs: #2563eb;
  --c1: #bfdbfe;
  --c2: #93c5fd;
  --c3: #3b82f6;
  --c4: #1d4ed8;
}
@media (prefers-color-scheme: dark) {
  :root {
    --panel: #0d1117;
    --frame: #30363d;
    --cb: #21262d;
    --ce: #161b22;
    --cs: #38bdf8;
    --c1: #1e3a8a;
    --c2: #1d4ed8;
    --c3: #2563eb;
    --c4: #38bdf8;
  }
}
.panel { fill: var(--panel); stroke: var(--frame); }
.c, .s, .u { animation-play-state: paused; }
.s, .u { visibility: hidden; }
@media (prefers-reduced-motion: no-preference) {
  .c, .s, .u { animation-play-state: running; }
  .s, .u { visibility: visible; }
}
"""


def save_svg(root, destination):
    XML.register_namespace("", SVG)
    Path(destination).write_text(XML.tostring(root, encoding="unicode") + "\n", encoding="utf-8")


def save_static_calendar(root, destination):
    for element in list(root):
        if {"s", "u"}.intersection(element.get("class", "").split()):
            root.remove(element)
    style = root.find(f"{{{SVG}}}style")
    style.text += "\n.c { animation: none !important; }\n"
    save_svg(root, destination)


def style_snake(source, animated, static):
    root = XML.parse(source).getroot()
    namespace = f"{{{SVG}}}"
    allowed_tags = {namespace + name for name in ("svg", "desc", "style", "rect")}
    for element in root.iter():
        if element.tag not in allowed_tags or any(
            attr.lower().startswith("on") or attr.endswith("href") for attr in element.attrib
        ):
            raise ValueError("Unexpected content from the contribution SVG generator")

    styles = root.findall(namespace + "style")
    if root.tag != namespace + "svg" or len(styles) != 1 or not styles[0].text or "--ce:" not in styles[0].text:
        raise ValueError("Expected a Platane/snk SVG")
    style = styles[0]
    if "@import" in style.text.lower() or "url(" in style.text.lower():
        raise ValueError("The contribution SVG must be self-contained")

    x, y, width, height = map(float, root.attrib["viewBox"].split())
    panel = XML.Element(namespace + "rect", {
        "class": "panel", "rx": "14",
        "x": f"{x + 0.5:g}", "y": f"{y + 0.5:g}",
        "width": f"{width - 1:g}", "height": f"{height - 1:g}",
    })
    style.text += THEME
    root.insert(list(root).index(style) + 1, panel)
    save_svg(root, animated)
    save_static_calendar(root, static)


if __name__ == "__main__":
    style_snake(*sys.argv[1:])
