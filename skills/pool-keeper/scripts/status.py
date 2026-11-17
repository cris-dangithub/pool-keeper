#!/usr/bin/env python3
"""
Numbers for the status report ("what is still missing?"). Read-only.

    status.py [--json]

Counts sources, positions, achievements, journal entries (last 30 days too), open questions vs
answered, open conflicts, "asked, never done" items, style rules and corrections, GitHub
sources and pending runs; says when the snapshot is older than the last change.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import (MARKER, add_pool_arg, load_config, load_strings, lpath, read_json,  # noqa: E402
                    read_text, require_pool)
from model import id_definitions, journal_entries  # noqa: E402


def sections(text: str) -> dict[str, str]:
    out, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            cur = m.group(1)
            out[cur] = ""
        elif cur:
            out[cur] += line + "\n"
    return out


def status(pool: pathlib.Path) -> dict:
    cfg = load_config(pool)
    s = load_strings(cfg.get("pool_language"), pool=pool)
    defs = id_definitions(pool, cfg)
    entries = journal_entries(pool, cfg)
    month_ago = (dt.date.today() - dt.timedelta(days=30)).isoformat()
    exp = lpath(pool, cfg, "experience")
    oq_file = lpath(pool, cfg, "open_questions")
    sec = sections(read_text(oq_file)) if oq_file.is_file() else {}
    open_q = len(re.findall(r"^\s*- \[ \]", sec.get(s["h_gaps"], ""), re.M))
    conflicts = len(re.findall(r"^\s*- \[ \]|^\s*- (?!\[x\])\S", sec.get(s["h_conflicts"], ""), re.M))
    not_done = len(re.findall(r"^\s*- \[x\]", sec.get(s["h_not_done"], ""), re.M))
    answered = len(re.findall(r"^\s*- \[x\]", sec.get(s["h_answered"], ""), re.M))
    marker = s["m"]["conflict"]
    conflict_marks = sum(read_text(p).count(marker) for p in pool.rglob("*.md")
                         if MARKER not in p.parts and p != oq_file)
    snap = lpath(pool, cfg, "snapshot")
    changelog = lpath(pool, cfg, "changelog")
    last_change = None
    if changelog.is_file():
        m = re.search(r"^##\s+(\d{4}-\d{2}-\d{2})", read_text(changelog), re.M)
        last_change = m.group(1) if m else None
    snap_date = None
    snap_empty = True
    if snap.is_file():
        snap_text = read_text(snap)
        m = re.search(r"(\d{4}-\d{2}-\d{2})", snap_text)
        snap_date = m.group(1) if m else None
        # an untouched template has only "–" values: it was never filled in
        values = re.findall(r"^- \*\*[^*]+:\*\*\s*(.*)$", snap_text, re.M)[1:]  # [0] = updated line
        snap_empty = all(v.strip() in ("–", "-", "") for v in values)
    gh_dir = pool / MARKER / "github" / "runs"
    pending = []
    for f in sorted(gh_dir.glob("*.json")) if gh_dir.is_dir() else []:
        run = read_json(f, {}) or {}
        if run.get("status") == "pending":
            pending.append(f.stem)
    return {
        "person": (cfg.get("person") or {}).get("name"),
        "sources": len(defs["S"]),
        "positions": len(list(exp.glob("*.md"))) if exp.is_dir() else 0,
        "achievements": len(defs["A"]),
        "journal_entries": len(entries),
        "journal_entries_last_30_days": sum(1 for e in entries if e.date >= month_ago),
        "style_rules": len(defs["G"]),
        "style_corrections": len(defs["K"]),
        "open_questions": open_q,
        "open_conflicts_listed": conflicts,
        "conflict_markers_in_files": conflict_marks,
        "asked_never_done": not_done,
        "answered": answered,
        "last_change": last_change,
        "snapshot_date": snap_date,
        "snapshot_stale": bool(snap_empty or (last_change and snap_date and snap_date < last_change)),
        "snapshot_empty": snap_empty,
        "domains_enabled": [k for k, v in (cfg.get("domains") or {}).items() if v],
        "github_sources": len((cfg.get("sources") or {}).get("github") or []),
        "github_pending_runs": pending,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_pool_arg(ap)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    r = status(require_pool(a.pool))
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        for k, v in r.items():
            print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
