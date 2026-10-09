#!/usr/bin/env python3
"""
IDs and file fingerprints.

    ids.py next-id S|J|A|G|K [--count N]     # next free ID(s): S042, J0107, A12, G015, K004
    ids.py hash FILE [FILE ...]              # SHA-256 + duplicate check against the sources index

`next-id` reads the definitions (sources index rows, journal entries, achievement rows, G/K
headings) and, for S and J, every tag already used anywhere, so an ID is never handed out twice.
`hash` prints the full hash, the 12-character prefix stored in the index, and the source that
already has it (if any): a duplicate is not archived again.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import add_pool_arg, load_config, lpath, read_text, require_pool  # noqa: E402
from model import fmt_id, next_id, source_rows  # noqa: E402


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def cmd_next(a):
    pool = require_pool(a.pool)
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
    out = []
    for f in a.files:
        p = pathlib.Path(f)
        if not p.is_file():
            out.append({"file": f, "error": "not found"})
            continue
        full = sha256(p)
        out.append({"file": str(p), "sha256": full, "short": full[:12],
                    "duplicate_of": known.get(full[:12])})
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("next-id"); add_pool_arg(p)
    p.add_argument("kind", type=str.upper, choices=["S", "J", "A", "G", "K"])
    p.add_argument("--count", type=int, default=1)
    p.set_defaults(fn=cmd_next)
    p = sub.add_parser("hash"); add_pool_arg(p); p.add_argument("files", nargs="+")
    p.set_defaults(fn=cmd_hash)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
