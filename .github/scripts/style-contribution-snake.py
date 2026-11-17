"""Apply the profile palette and motion preferences to Platane/snk's SVG."""

import sys
from pathlib import Path
from xml.etree import ElementTree as XML

SVG = "http://www.w3.org/2000/svg"
THEME = """
:root {
  color-scheme: light dark;
  --panel: #faf7f2;
  --frame: #ded3c3;
  --cb: #d9cbbb;
  --ce: #ede6dc;
  --cs: #b34c18;
  --c1: #ddbb9c;
  --c2: #c58e64;
  --c3: #a5693c;
  --c4: #79451f;
}
@media (prefers-color-scheme: dark) {
  :root {
    --panel: #232120;
    --frame: #4d4138;
    --cb: #41352c;
    --ce: #322b27;
    --cs: #ffbb76;
    --c1: #73503a;
    --c2: #9a6947;
    --c3: #c48a5e;
    --c4: #e9ad79;
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


def style_snake(source, destination):
    XML.register_namespace("", SVG)
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
    Path(destination).write_text(XML.tostring(root, encoding="unicode") + "\n", encoding="utf-8")


if __name__ == "__main__":
    style_snake(*sys.argv[1:])
