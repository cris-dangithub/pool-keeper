#!/usr/bin/env python3
"""
IDs and file fingerprints.

    ids.py next-id S|J|A|G|K [--count N]     # next free ID(s): S042, J0107, A12, G015, K004
    ids.py next-id S --reserve FOLDER [--reserve FOLDER ...]
                                             # take the ID(s) AND write placeholder index rows
    ids.py hash FILE [FILE ...]              # SHA-256 + duplicate check against the sources index

`next-id` reads the definitions (sources index rows, journal entries, achievement rows, G/K
headings) and, for S and J, every tag already used anywhere, so an ID is never handed out twice.
With `--reserve` (S only) the lookup and a placeholder row per folder in the sources index happen
under a pool lock, so two sessions ingesting at the same time can never get the same S number;
the ingest then fills the row in place (kind "(reserved)" until then — `pk lint` warns).
`hash` prints the full hash, the 12-character prefix stored in the index, and the source that
already has it (if any): a duplicate is not archived again.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import (PoolLock, add_pool_arg, load_config, lpath, read_text,  # noqa: E402
                    require_pool, today, write_text)
from model import RESERVED_KIND, fmt_id, next_id, source_rows  # noqa: E402


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def insert_rows(index_text: str, rows: list[str]) -> str:
    """Insert table rows after the last S row of the sources index (or after the table's
    separator line when the table is still empty)."""
    lines = index_text.split("\n")
    last = max((i for i, l in enumerate(lines) if re.match(r"^\|\s*S\d{3,}\s*\|", l)), default=None)
    if last is None:
        last = next((i for i, l in enumerate(lines) if re.match(r"^\|\s*:?-{3,}", l)), None)
    if last is None:
        sys.exit("INDEX_TABLE_MISSING: the sources index has no table to add rows to.")
    lines[last + 1:last + 1] = rows
    return "\n".join(lines)


def cmd_next(a):
    pool = require_pool(a.pool)
    if a.reserve:
        if a.kind != "S":
            sys.exit("--reserve is only for S IDs (journal IDs are reserved by `pk journal add`).")
        cfg = load_config(pool)
        idx = lpath(pool, cfg, "sources_index")
        with PoolLock(pool):
            first = next_id(pool, "S", cfg)
            n = int(first[1:])
            ids = [fmt_id("S", n + i) for i in range(len(a.reserve))]
            rows = [f"| {i} | {today()} | `{folder.strip().rstrip('/')}/` | {RESERVED_KIND} | "
                    f"{RESERVED_KIND} | – |" for i, folder in zip(ids, a.reserve)]
            write_text(idx, insert_rows(read_text(idx), rows))
        print(json.dumps([{"id": i, "folder": f} for i, f in zip(ids, a.reserve)],
                         ensure_ascii=False, indent=2))
        return 0
    first = next_id(pool, a.kind)
    kind, n = first[0], int(first[1:])
    ids = [fmt_id(kind, n + i) for i in range(a.count)]
    print("\n".join(ids))
    return 0


def cmd_hash(a):
    pool = require_pool(a.pool)
    cfg = load_config(pool)
    idx = lpath(pool, cfg, "sources_index")
    rows = source_rows(read_text(idx)) if idx.is_file() else []
    known = {}
    for r in rows:
        key = r.sha.strip("`").upper()
        if len(key) >= 8 and all(c in "0123456789ABCDEF" for c in key):
            known.setdefault(key[:12], r.id)
    # files already inside the archive (e.g. members of an unzipped ZIP source) by size, hashed lazily
    src_dir = lpath(pool, cfg, "sources")
    folders = {r.folder.strip().rstrip("/"): r.id for r in rows}
    by_size: dict = {}
    if src_dir.is_dir():
        for q in src_dir.rglob("*"):
            if q.is_file() and q.name not in ("extracted.txt", cfg["layout"].get("source_notes", "")):
                by_size.setdefault(q.stat().st_size, []).append(q)
    out = []
    for f in a.files:
        p = pathlib.Path(f)
        if not p.is_file():
            out.append({"file": f, "error": "not found"})
            continue
        full = sha256(p)
        dup_file = None
        for q in by_size.get(p.stat().st_size, []):
            if q.resolve() != p.resolve() and sha256(q) == full:
                dup_file = q.relative_to(pool).as_posix()
                break
        dup = known.get(full[:12])
        if not dup and dup_file:
            top = pathlib.PurePosixPath(dup_file).relative_to(
                pathlib.PurePosixPath(src_dir.relative_to(pool).as_posix())).parts[0]
            dup = folders.get(top)
        out.append({"file": str(p), "sha256": full, "short": full[:12],
                    "duplicate_of": dup, "same_file_in_archive": dup_file})
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("next-id"); add_pool_arg(p)
    p.add_argument("kind", type=str.upper, choices=["S", "J", "A", "G", "K"])
    p.add_argument("--count", type=int, default=1)
    p.add_argument("--reserve", action="append", metavar="FOLDER",
                   help="S only: write a placeholder index row for this source folder (repeatable)")
    p.set_defaults(fn=cmd_next)
    p = sub.add_parser("hash"); add_pool_arg(p); p.add_argument("files", nargs="+")
    p.set_defaults(fn=cmd_hash)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
