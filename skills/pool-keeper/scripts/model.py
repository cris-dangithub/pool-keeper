"""Readers for the structured parts of a pool: source index rows, ID definitions, source tags,
journal entries and the journal tag vocabulary. Pure functions over text, so they are easy to
test and shared by ids.py, journal.py, lint.py and status.py.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import pathlib
import re

from common import iter_md, load_config, lpath, read_text

PAD = {"S": 3, "J": 4, "A": 2, "G": 3, "K": 3}

_FENCE = re.compile(r"```.*?```", re.S)
_INLINE = re.compile(r"`[^`\n]*`")
_BRACKET = re.compile(r"\[([^\[\]\n]{1,120})\]")
_TAG_IN = re.compile(r"\b([SJ])(\d{3,})\b")


def strip_fences(text: str) -> str:
    """Blank out fenced code blocks (keeping line numbers): format examples are not data."""
    return _FENCE.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def strip_code(text: str) -> str:
    """Remove fenced blocks and inline code: format examples there are not real references."""
    return _INLINE.sub("", strip_fences(text))


def fmt_id(kind: str, n: int) -> str:
    return f"{kind}{n:0{PAD[kind]}d}"


# --------------------------------------------------------------------------- tags
def find_tags(text: str) -> list[tuple[str, int]]:
    """Source tags `[S001]`, `[S002 diploma]`, `[S001, S004]`, `[J0012]` with their line numbers.
    Only brackets that start with an ID count, so prose like "[see S001]" is ignored."""
    out = []
    clean = strip_code(text)
    for lineno, line in enumerate(clean.splitlines(), 1):
        for m in _BRACKET.finditer(line):
            inner = m.group(1).strip()
            if not re.match(r"^[SJ]\d{3,}\b", inner):
                continue
            for k, n in _TAG_IN.findall(inner):
                if (k == "S" and len(n) >= 3) or (k == "J" and len(n) >= 4):
                    out.append((f"{k}{n}", lineno))
    return out


# --------------------------------------------------------------------------- definitions
_ROW_ID = re.compile(r"^\|\s*([A-Z])(\d{2,})\s*\|")
_HEAD_ID = re.compile(r"^#{2,4}\s+([A-Z])(\d{2,})\b")


def definitions_in(text: str, kind: str, rows=True, heads=True) -> list[tuple[str, int]]:
    out = []
    for lineno, line in enumerate(strip_code(text).splitlines(), 1):
        for rx, on in ((_ROW_ID, rows), (_HEAD_ID, heads)):
            if not on:
                continue
            m = rx.match(line)
            if m and m.group(1) == kind:
                out.append((f"{kind}{m.group(2)}", lineno))
    return out


@dataclasses.dataclass
class SourceRow:
    id: str
    date: str
    folder: str
    kind: str
    summary: str
    sha: str
    line: int


def source_rows(index_text: str) -> list[SourceRow]:
    rows = []
    for lineno, line in enumerate(strip_fences(index_text).splitlines(), 1):
        m = re.match(r"^\|\s*(S\d{3,})\s*\|(.*)$", line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(2).rstrip().rstrip("|").split("|")]
        cells += [""] * (5 - len(cells))
        folder = cells[1].strip("`").strip()
        rows.append(SourceRow(m.group(1), cells[0], folder, cells[2], cells[3], cells[4], lineno))
    return rows


def id_definitions(pool, cfg=None) -> dict[str, list[tuple[str, str, int]]]:
    """kind -> [(id, relative file, line)] for every defined ID in the pool."""
    pool = pathlib.Path(pool)
    cfg = cfg or load_config(pool)
    out: dict[str, list] = {k: [] for k in PAD}

    def rel(p):
        return pathlib.Path(p).relative_to(pool).as_posix()

    idx = lpath(pool, cfg, "sources_index")
    if idx.is_file():
        out["S"] = [(r.id, rel(idx), r.line) for r in source_rows(read_text(idx))]
    for e in journal_entries(pool, cfg):
        out["J"].append((e.id, e.file, e.line))
    for kind, key, rows, heads in (("A", "achievements", True, True),
                                   ("G", "writing_style_rules", False, True),
                                   ("K", "writing_style_corrections", False, True)):
        p = lpath(pool, cfg, key)
        if p.is_file():
            out[kind] = [(i, rel(p), ln) for i, ln in definitions_in(read_text(p), kind, rows, heads)]
    return out


def all_tags(pool, cfg=None) -> list[tuple[str, str, int]]:
    """Every source tag used in the pool's content files (not in the sources archive)."""
    pool = pathlib.Path(pool)
    cfg = cfg or load_config(pool)
    out = []
    files = list(iter_md(pool, cfg=cfg))
    idx = lpath(pool, cfg, "sources_index")
    if idx.is_file():
        files.append(idx)
    for p in files:
        rel = p.relative_to(pool).as_posix()
        for tag, ln in find_tags(read_text(p)):
            out.append((tag, rel, ln))
    return out


def next_id(pool, kind: str, cfg=None) -> str:
    kind = kind.upper()
    if kind not in PAD:
        raise ValueError(f"unknown ID kind {kind!r} (use S, J, A, G or K)")
    defs = id_definitions(pool, cfg)[kind]
    nums = [int(i[1:]) for i, _, _ in defs]
    if kind in ("S", "J"):  # a tag already used somewhere must never be handed out again
        nums += [int(t[1:]) for t, _, _ in all_tags(pool, cfg) if t[0] == kind]
    return fmt_id(kind, (max(nums) if nums else 0) + 1)


# --------------------------------------------------------------------------- journal
DAY_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\b")
ENTRY_RE = re.compile(r"^- \*\*(J\d{4,})\*\*(.*)$")
SUB_RE = re.compile(r"^\s{2,}- (Original|Promoted):\s*(.*)$")
MONTH_FILE = re.compile(r"^\d{4}-\d{2}\.md$")


@dataclasses.dataclass
class Entry:
    id: str
    date: str
    description: str
    tags: list
    context: str
    qty: float | None
    unit: str
    recorded: str
    link: str
    original: str
    promoted: str
    file: str
    line: int
    problems: list

    @property
    def num(self) -> int:
        return int(self.id[1:])


def parse_entry_parts(rest: str) -> dict:
    out = {"description": "", "tags": [], "context": "", "qty": None, "unit": "", "recorded": "",
           "link": "", "problems": []}
    rest = rest.strip()
    if rest.startswith("·"):
        rest = rest[1:]
    desc = []
    for part in [p.strip() for p in re.split(r"\s+·\s+", rest) if p.strip()]:
        if part.startswith("#") and all(t.startswith("#") for t in part.split()):
            out["tags"] += [t[1:].lower() for t in part.split() if len(t) > 1]
        elif part.startswith("@"):
            out["context"] = part[1:].strip()
        elif part.lower().startswith("qty:"):
            m = re.match(r"qty:\s*([0-9]+(?:[.,][0-9]+)?)\s*(.*)$", part, re.I)
            if m:
                out["qty"] = float(m.group(1).replace(",", "."))
                out["unit"] = m.group(2).strip()
            else:
                out["problems"].append(f"unreadable quantity {part!r}")
        elif part.lower().startswith("rec:"):
            out["recorded"] = part[4:].strip()
        elif part.lower().startswith("link:"):
            out["link"] = part[5:].strip()
        else:
            desc.append(part)
    out["description"] = " · ".join(desc)
    if not out["description"]:
        out["problems"].append("no description")
    return out


def parse_journal_file(text: str, rel: str) -> tuple[list[Entry], list[str]]:
    entries, problems = [], []
    day = None
    cur = None
    for lineno, line in enumerate(text.splitlines(), 1):
        m = DAY_RE.match(line)
        if m:
            day = m.group(1)
            cur = None
            continue
        m = ENTRY_RE.match(line)
        if m:
            parts = parse_entry_parts(m.group(2))
            if day is None:
                parts["problems"].append("entry before any '## YYYY-MM-DD' day heading")
            cur = Entry(id=m.group(1), date=day or "", file=rel, line=lineno, original="",
                        promoted="", **parts)
            entries.append(cur)
            continue
        if line.startswith("- **J"):
            problems.append(f"{rel}:{lineno}: malformed journal entry line")
            continue
        m = SUB_RE.match(line)
        if m and cur is not None:
            val = m.group(2).strip()
            if m.group(1) == "Original":
                if len(val) >= 2 and val[0] == val[-1] == '"':
                    val = val[1:-1]
                cur.original = val
            else:
                cur.promoted = val
    return entries, problems


def journal_files(pool, cfg=None) -> list[pathlib.Path]:
    cfg = cfg or load_config(pool)
    d = lpath(pool, cfg, "journal")
    return sorted(p for p in d.glob("*.md") if MONTH_FILE.match(p.name)) if d.is_dir() else []


def journal_entries(pool, cfg=None, problems: list | None = None) -> list[Entry]:
    pool = pathlib.Path(pool)
    cfg = cfg or load_config(pool)
    out = []
    for p in journal_files(pool, cfg):
        es, probs = parse_journal_file(read_text(p), p.relative_to(pool).as_posix())
        out += es
        if problems is not None:
            problems += probs
    return out


def tag_vocabulary(pool, cfg=None) -> dict[str, dict]:
    """canonical tag -> {"definition", "aliases"} from the journal README table."""
    cfg = cfg or load_config(pool)
    p = lpath(pool, cfg, "journal_readme")
    vocab = {}
    if not p.is_file():
        return vocab
    for line in strip_code(read_text(p)).splitlines():
        m = re.match(r"^\|\s*#([^\s|]+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$", line)
        if m:
            aliases = [a.strip().lstrip("#").lower() for a in m.group(3).split(",") if a.strip()]
            vocab[m.group(1).lower()] = {"definition": m.group(2), "aliases": aliases}
    return vocab


def alias_map(vocab: dict) -> dict[str, str]:
    out = {}
    for tag, v in vocab.items():
        out[tag] = tag
        for a in v["aliases"]:
            out.setdefault(a, tag)
    return out


def iso_week(date: str) -> str:
    y, w, _ = dt.date.fromisoformat(date).isocalendar()
    return f"{y}-W{w:02d}"
