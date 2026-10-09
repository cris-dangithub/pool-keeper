#!/usr/bin/env python3
"""
Extract plain text from a source file, standard library only.

    extract.py FILE [-o OUT.txt]

- .docx / .docm / .dotx: body paragraphs in order, tables (one row per line, cells separated by
  " | "), list items ("- "), headings ("# "), headers, footers, footnotes, endnotes, and the
  hyperlink targets (LinkedIn, portfolio...). Text boxes are included with their paragraph.
- .txt .md .csv .tsv .json .yaml .yml .xml: copied as text.
- .html .htm: visible text.
- Anything else (.pdf, .pptx, .xlsx, images, .doc): exit 4 with what to use instead — the
  agent reads them with its own tools or skills (PDF reader, pptx/xlsx skills, image reading).
"""
from __future__ import annotations

import argparse
import html.parser
import pathlib
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import write_text  # noqa: E402,F401  (also reconfigures stdout to UTF-8)

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
TEXT_EXT = {".txt", ".md", ".csv", ".tsv", ".json", ".yaml", ".yml", ".xml"}
DOCX_EXT = {".docx", ".docm", ".dotx", ".dotm"}
ADVICE = {
    ".pdf": "read it with the agent's file reader (page ranges for long files) or a PDF skill; "
            "scanned PDFs: read the pages as images and transcribe",
    ".pptx": "use a pptx skill (e.g. anthropic-skills:pptx)",
    ".xlsx": "use an xlsx skill (e.g. anthropic-skills:xlsx); keep tables as tables",
    ".xls": "use an xlsx skill", ".doc": "convert to .docx first (Word/LibreOffice) or read it with a docx skill",
    ".png": "read the image and transcribe + describe it", ".jpg": "read the image and transcribe + describe it",
    ".jpeg": "read the image and transcribe + describe it", ".webp": "read the image and transcribe + describe it",
}


# --------------------------------------------------------------------------- docx
def _run_text(node) -> str:
    out = []
    for el in node.iter():
        tag = el.tag
        if tag == W + "t" and el.text:
            out.append(el.text)
        elif tag == W + "tab":
            out.append("\t")
        elif tag in (W + "br", W + "cr"):
            out.append("\n")
        elif tag == W + "noBreakHyphen":
            out.append("-")
    return "".join(out)


def _para(p) -> str:
    text = _run_text(p)
    if not text.strip():
        return ""
    ppr = p.find(W + "pPr")
    prefix = ""
    if ppr is not None:
        style = ppr.find(W + "pStyle")
        val = (style.get(W + "val") or "") if style is not None else ""
        if re.match(r"(?i)^(heading|title|ttulo|judul)", val):
            prefix = "# "
        elif ppr.find(W + "numPr") is not None or re.match(r"(?i)^list", val):
            prefix = "- "
    return prefix + text


def _table(tbl) -> list[str]:
    lines = []
    for tr in tbl.findall(W + "tr"):
        cells = []
        for tc in tr.findall(W + "tc"):
            parts = [t for t in (_run_text(p).strip() for p in tc.iter(W + "p")) if t]
            cells.append(" / ".join(parts))
        if any(cells):
            lines.append("| " + " | ".join(cells) + " |")
    return lines


def _block(container) -> list[str]:
    lines = []
    for child in container:
        if child.tag == W + "p":
            t = _para(child)
            if t:
                lines.append(t)
        elif child.tag == W + "tbl":
            lines += _table(child)
        elif child.tag in (W + "sdt",):  # content controls wrap paragraphs/tables
            content = child.find(W + "sdtContent")
            if content is not None:
                lines += _block(content)
    return lines


def docx_text(path: pathlib.Path) -> str:
    try:
        z = zipfile.ZipFile(path)
    except PermissionError:
        sys.exit("LOCKED: the file is open in another program; close it and try again.")
    except zipfile.BadZipFile:
        sys.exit("not a valid .docx (zip) file")
    with z:
        names = z.namelist()
        out = []
        body = ET.fromstring(z.read("word/document.xml")).find(W + "body")
        if body is not None:
            out += _block(body)
        extra = sorted(n for n in names if re.match(r"^word/(header\d*|footer\d*|footnotes|endnotes)\.xml$", n))
        for n in extra:
            root = ET.fromstring(z.read(n))
            if root.tag in (W + "footnotes", W + "endnotes"):
                lines = []
                for fn in root:
                    lines += _block(fn)
            else:
                lines = _block(root)
            if lines:
                out.append(f"\n=== {n} ===")
                out += lines
        links = []
        if "word/_rels/document.xml.rels" in names:
            rels = ET.fromstring(z.read("word/_rels/document.xml.rels"))
            for r in rels.iter(PKG_REL + "Relationship"):
                if r.get("TargetMode") == "External" and r.get("Type", "").endswith("/hyperlink"):
                    if r.get("Target") not in links:
                        links.append(r.get("Target"))
        if links:
            out.append("\n=== links ===")
            out += links
    return "\n".join(out).strip() + "\n"


# --------------------------------------------------------------------------- html
class _Visible(html.parser.HTMLParser):
    SKIP = {"script", "style", "noscript", "template"}
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article"}

    def __init__(self):
        super().__init__()
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_text(path: pathlib.Path) -> str:
    p = _Visible()
    p.feed(path.read_text(encoding="utf-8", errors="replace"))
    text = re.sub(r"[ \t]+", " ", "".join(p.parts))
    return re.sub(r"\n\s*\n+", "\n\n", text).strip() + "\n"


def extract(path) -> str:
    p = pathlib.Path(path)
    ext = p.suffix.lower()
    if ext in DOCX_EXT:
        return docx_text(p)
    if ext in TEXT_EXT:
        return p.read_text(encoding="utf-8", errors="replace")
    if ext in (".html", ".htm"):
        return html_text(p)
    raise ValueError(ADVICE.get(ext, "read it with the agent's own tools"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("-o", "--out", default=None)
    a = ap.parse_args(argv)
    p = pathlib.Path(a.file)
    if not p.is_file():
        sys.exit(f"not found: {a.file}")
    try:
        text = extract(p)
    except ValueError as e:
        print(f"UNSUPPORTED: {p.suffix or p.name} — {e}", file=sys.stderr)
        return 4
    if a.out:
        write_text(a.out, text)
        print(f"wrote {len(text.splitlines())} lines to {a.out}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
