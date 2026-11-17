#!/usr/bin/env python3
"""
Consistency checks for a pool. Read-only.

    lint.py [--json] [--strict]

Errors (exit 1):
  - layout keys missing from the config, or missing files/folders for enabled keys
  - a source tag [S###] / [J####] used but not defined (sources index / journal)
  - duplicate IDs (S, J, A, G, K)
  - malformed journal lines, entries outside a day heading
  - the open-questions file has no "asked, never done" section (needed by delegation)
Warnings:
  - IDs defined out of order (S in the index, A/G/K in their files)
  - journal entries without an `Original:` line, unknown tags, entries in the wrong month file
  - experience files citing a source that has no "original text" section there
  - index rows whose folder does not exist, repeated SHA-256 prefixes
`--strict` turns warnings into errors.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import (CORE_DIR_KEYS, CORE_FILE_KEYS, DOMAIN_KEYS, NAME_KEYS, add_pool_arg,  # noqa: E402
                    load_config, load_strings, lpath, parse_date, read_text, require_pool)
from model import (RESERVED_KIND, alias_map, all_tags, find_tags, id_definitions,  # noqa: E402
                   journal_entries, journal_files, source_rows, strip_code, tag_vocabulary)

# every language's "original text" heading is accepted (pools may mix after a language change)
ORIGINAL_HEADINGS = {"original text", "texto original", "bullet asli", "teks asli", "kalimat asli"}


def lint(pool: pathlib.Path) -> dict:
    cfg = load_config(pool)
    errors, warnings = [], []
    E, W = errors.append, warnings.append
    layout = cfg.get("layout") or {}
    doms = cfg.get("domains") or {}

    # 1. layout -----------------------------------------------------------------------
    for k in CORE_FILE_KEYS + CORE_DIR_KEYS + NAME_KEYS:
        if k not in layout:
            E(f"layout: key '{k}' missing from config (run `pk refresh`)")
    for k in DOMAIN_KEYS:
        if doms.get(k) and k not in layout:
            E(f"layout: enabled domain '{k}' has no path in config")
    for k in CORE_FILE_KEYS + CORE_DIR_KEYS + [d for d in DOMAIN_KEYS if doms.get(d)]:
        if k in layout and not (pool / layout[k].rstrip("/")).exists():
            E(f"layout: {k} -> {layout[k]} does not exist (run `pk refresh`)")
    if errors:
        return {"errors": errors, "warnings": warnings}

    # 2. definitions --------------------------------------------------------------------
    defs = id_definitions(pool, cfg)
    for kind, items in defs.items():
        seen = {}
        for i, f, ln in items:
            if i in seen:
                E(f"duplicate {i}: {seen[i]} and {f}:{ln}")
            else:
                seen[i] = f"{f}:{ln}"
        if kind in ("S", "A", "G", "K"):
            nums = [int(i[1:]) for i, _, _ in items]
            bad = [items[n][0] for n in range(1, len(nums)) if nums[n] < nums[n - 1]]
            if bad:
                W(f"{kind} IDs out of order in {items[0][1]}: " + ", ".join(bad[:10]))
    defined = {i for items in defs.values() for i, _, _ in items}

    # 3. tags ---------------------------------------------------------------------------
    orphans = collections.defaultdict(list)
    for tag, f, ln in all_tags(pool, cfg):
        if tag not in defined:
            orphans[tag].append(f"{f}:{ln}")
    for tag, where in sorted(orphans.items()):
        E(f"orphan tag [{tag}] (not in the sources index / journal): " + ", ".join(where[:5])
          + (" ..." if len(where) > 5 else ""))

    # 4. sources index ------------------------------------------------------------------
    idx = lpath(pool, cfg, "sources_index")
    rows = source_rows(read_text(idx)) if idx.is_file() else []
    src_dir = lpath(pool, cfg, "sources")
    shas = collections.defaultdict(list)
    for r in rows:
        if r.kind.strip() == RESERVED_KIND:
            W(f"{r.id}: reserved but never filled in (an ingest was interrupted? complete it, or "
              f"mark the row 'not used')")
            continue
        folder = r.folder.rstrip("/")
        if folder and folder not in ("–", "-") and not (src_dir / folder).exists():
            W(f"{r.id}: folder '{folder}' not found in {layout['sources']}")
        key = r.sha.strip("`").upper()
        if re.fullmatch(r"[0-9A-F]{8,}", key):
            shas[key[:12]].append(r.id)
    for k, ids in shas.items():
        if len(ids) > 1:
            W(f"same SHA-256 prefix {k} in {', '.join(ids)} (duplicate file archived twice?)")

    # 5. journal ------------------------------------------------------------------------
    problems: list[str] = []
    entries = journal_entries(pool, cfg, problems)
    for p in problems:
        E(p)
    vocab = tag_vocabulary(pool, cfg)
    amap = alias_map(vocab)
    unknown = collections.Counter()
    for e in entries:
        for p in e.problems:
            E(f"{e.file}:{e.line} {e.id}: {p}")
        if not e.original:
            W(f"{e.file}:{e.line} {e.id}: no `Original:` line (the verbatim text is the source)")
        if e.date and not pathlib.PurePosixPath(e.file).name.startswith(e.date[:7]):
            W(f"{e.file}:{e.line} {e.id}: dated {e.date} but stored in {pathlib.PurePosixPath(e.file).name}")
        for t in e.tags:
            if t not in amap:
                unknown[t] += 1
    days = load_strings(cfg.get("pool_language"), pool=pool).get("weekdays") or []
    for jf in journal_files(pool, cfg):
        for ln, line in enumerate(read_text(jf).splitlines(), 1):
            m = re.match(r"^##\s+(\d{4}-\d{2}-\d{2})\s+\(([^)]+)\)", line)
            if m and len(days) == 7:
                want = days[parse_date(m.group(1)).weekday()]
                if m.group(2).strip().lower() != want.lower():
                    W(f"{jf.relative_to(pool).as_posix()}:{ln}: {m.group(1)} is {want}, heading says {m.group(2)}")
    if unknown:
        W("journal tags not in the vocabulary: " + ", ".join(f"#{t} ({n})" for t, n in unknown.most_common())
          + " — add them with `pk journal tags --add`")

    # 6. original-text sections in experience files ------------------------------------
    exp = lpath(pool, cfg, "experience")
    for f in sorted(exp.glob("*.md")) if exp.is_dir() else []:
        text = read_text(f)
        covered = set()
        for line in strip_code(text).splitlines():
            m = re.match(r"^#{2,4}\s+(.+)$", line)
            if m and any(h in m.group(1).lower() for h in ORIGINAL_HEADINGS):
                covered.update(t for t, _ in find_tags(m.group(1)))
        cited = {t for t, _ in find_tags(text) if t.startswith("S")}
        missing = sorted(cited - covered)
        if missing:
            W(f"{f.relative_to(pool).as_posix()}: no original-text section for " + ", ".join(missing)
              + " (fine for web research / chat facts without wording to keep)")

    # 7. delegation compatibility -------------------------------------------------------
    oq = lpath(pool, cfg, "open_questions")
    strings = load_strings(cfg.get("pool_language"), pool=pool)
    need = strings.get("h_not_done", "Asked, never done")
    if oq.is_file() and not re.search(r"^##\s+" + re.escape(need) + r"\s*$", read_text(oq), re.M):
        E(f"{layout['open_questions']}: section '## {need}' missing (delegated 'not done' items go there)")

    return {"errors": errors, "warnings": warnings,
            "counts": {k: len(v) for k, v in defs.items()}}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_pool_arg(ap)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args(argv)
    pool = require_pool(a.pool)
    r = lint(pool)
    if a.strict:
        r["errors"] += r["warnings"]
        r["warnings"] = []
    r["ok"] = not r["errors"]
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        for e in r["errors"]:
            print(f"ERROR   {e}")
        for w in r["warnings"]:
            print(f"warning {w}")
        counts = r.get("counts") or {}
        print(f"{'OK' if r['ok'] else 'FAILED'}: {len(r['errors'])} error(s), {len(r['warnings'])} warning(s)"
              + (" · IDs " + ", ".join(f"{k}={v}" for k, v in counts.items()) if counts else ""))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
