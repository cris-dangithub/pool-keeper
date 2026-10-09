#!/usr/bin/env python3
"""
Activity journal: write entries deterministically and answer "how many / when / what" questions.

    journal.py add --date YYYY-MM-DD --desc TEXT --original TEXT [--tag t ...] [--context SLUG]
                   [--qty N --unit UNIT] [--recorded YYYY-MM-DD] [--link URL] [--promoted KEY]
                   [--dry-run]
    journal.py stats [--tag T ...] [--any] [--context C] [--from D] [--to D] [--text WORDS]
                     [--group-by tag|context|day|week|month] [--list] [--json]
    journal.py tags [--add TAG --definition TEXT [--aliases a,b]]
    journal.py next-id

`add` assigns the next global J#### ID, creates the monthly file (`YYYY-MM.md`) and the day
heading when missing, keeps day headings in date order, and appends the entry at the end of
its day. Tags are resolved through the vocabulary (aliases -> canonical tag); an unknown tag is
accepted but reported, so the agent can add it to the vocabulary (`tags --add`).

`stats` is deterministic: it counts entries and sums quantities per unit, and always lists the
J IDs it counted. Phrase results as "at least N recorded": the journal only knows what was told.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import (add_pool_arg, load_config, lpath, parse_date, pool_strings, read_text,  # noqa: E402
                    require_pool, today, weekday_name, write_text)
from model import (DAY_RE, alias_map, iso_week, journal_entries, next_id,  # noqa: E402
                   tag_vocabulary)


# --------------------------------------------------------------------------- writing
def norm_context(c: str | None) -> str:
    return (c or "").strip().lstrip("@").strip()


def norm_tag(t: str) -> str:
    return re.sub(r"\s+", "-", t.strip().lstrip("#").lower())


def entry_line(jid, desc, tags, context, qty, unit, recorded, link) -> str:
    parts = [f"- **{jid}**", desc.strip().replace(" · ", " - ")]
    if tags:
        parts.append(" ".join(f"#{t}" for t in tags))
    if context:
        parts.append(f"@{context}")
    if qty is not None:
        q = int(qty) if float(qty).is_integer() else qty
        parts.append(f"qty: {q} {unit}".rstrip())
    if recorded:
        parts.append(f"rec: {recorded}")
    if link:
        parts.append(f"link: {link}")
    return " · ".join(parts)


def insert_entry(text: str, date: str, header: str, block: list[str]) -> str:
    """Insert `block` at the end of day `date`, creating the day heading in date order."""
    lines = text.rstrip("\n").split("\n") if text.strip() else []
    days = [(i, DAY_RE.match(l).group(1)) for i, l in enumerate(lines) if DAY_RE.match(l)]
    for n, (i, d) in enumerate(days):
        if d == date:
            end = days[n + 1][0] if n + 1 < len(days) else len(lines)
            while end > i + 1 and not lines[end - 1].strip():
                end -= 1
            lines[end:end] = block
            return "\n".join(lines) + "\n"
    new = ["", header, *block]
    later = [i for i, d in days if d > date]
    if later:
        pos = later[0]
        lines[pos:pos] = new[1:] + [""]
    else:
        while lines and not lines[-1].strip():
            lines.pop()
        lines += new
    return "\n".join(lines) + "\n"


def cmd_add(a):
    pool = require_pool(a.pool)
    cfg = load_config(pool)
    strings = pool_strings(pool, cfg)
    date = parse_date(a.date).isoformat()
    if a.recorded:
        a.recorded = parse_date(a.recorded).isoformat()
    vocab = tag_vocabulary(pool, cfg)
    amap = alias_map(vocab)
    tags, unknown = [], []
    for t in a.tag or []:
        for piece in t.split(","):
            if not piece.strip():
                continue
            n = norm_tag(piece)
            canon = amap.get(n)
            if canon is None:
                unknown.append(n)
                canon = n
            if canon not in tags:
                tags.append(canon)
    context = norm_context(a.context) or norm_context((cfg.get("journal") or {}).get("default_context"))
    jid = next_id(pool, "J", cfg)
    line = entry_line(jid, a.desc, tags, context, a.qty, a.unit or "", a.recorded, a.link)
    block = [line, f'  - Original: "{a.original.strip()}"']
    if a.promoted:
        block.append(f"  - Promoted: {a.promoted}")
    jdir = lpath(pool, cfg, "journal")
    f = jdir / f"{date[:7]}.md"
    header = f"## {date} ({weekday_name(parse_date(date), strings)})"
    text = read_text(f) if f.is_file() else f"# {strings.get('journal_title', 'Journal')} — {date[:7]}\n"
    new = insert_entry(text, date, header, block)
    if not a.dry_run:
        write_text(f, new)
    print(json.dumps({"id": jid, "file": f.relative_to(pool).as_posix(), "line": line,
                      "unknown_tags": unknown, "dry_run": bool(a.dry_run)}, ensure_ascii=False, indent=2))
    return 0


# --------------------------------------------------------------------------- stats
def select(entries, tags=(), any_tag=False, context=None, start=None, end=None, text=None, amap=None):
    amap = amap or {}
    want = [amap.get(norm_tag(t), norm_tag(t)) for t in tags]
    ctx = norm_context(context).lower() if context else None
    words = [w.lower() for w in (text or "").split()]
    out = []
    for e in entries:
        etags = {amap.get(t, t) for t in e.tags}
        if want:
            hit = any(t in etags for t in want) if any_tag else all(t in etags for t in want)
            if not hit:
                continue
        if ctx:
            ec = e.context.lower()
            if ctx.endswith(("*", ":", "/")):
                if not ec.startswith(ctx.rstrip("*")):
                    continue
            elif ec != ctx:
                continue
        if start and e.date < start:
            continue
        if end and e.date > end:
            continue
        if words:
            hay = f"{e.description} {e.original}".lower()
            if not all(w in hay for w in words):
                continue
        out.append(e)
    return out


def summarize(entries) -> dict:
    qty = collections.defaultdict(float)
    for e in entries:
        if e.qty is not None:
            qty[e.unit or "(no unit)"] += e.qty
    dates = sorted(e.date for e in entries if e.date)
    return {
        "entries": len(entries),
        "qty_by_unit": {k: (int(v) if v.is_integer() else v) for k, v in sorted(qty.items())},
        "first": dates[0] if dates else None,
        "last": dates[-1] if dates else None,
        "ids": [e.id for e in sorted(entries, key=lambda x: (x.date, x.num))],
    }


def group_key(e, by: str, amap) -> list[str]:
    if by == "tag":
        return sorted({amap.get(t, t) for t in e.tags}) or ["(no tag)"]
    if by == "context":
        return [e.context or "(no context)"]
    if by == "day":
        return [e.date]
    if by == "week":
        return [iso_week(e.date)] if e.date else ["(no date)"]
    if by == "month":
        return [e.date[:7]]
    return ["all"]


def cmd_stats(a):
    pool = require_pool(a.pool)
    cfg = load_config(pool)
    amap = alias_map(tag_vocabulary(pool, cfg))
    start = parse_date(a.date_from).isoformat() if a.date_from else None
    end = parse_date(a.date_to).isoformat() if a.date_to else None
    entries = select(journal_entries(pool, cfg), a.tag or [], a.any, a.context, start, end, a.text, amap)
    result = {"filter": {"tags": a.tag or [], "any": a.any, "context": a.context, "from": start,
                         "to": end, "text": a.text},
              "total": summarize(entries)}
    if a.group_by:
        groups = collections.defaultdict(list)
        for e in entries:
            for k in group_key(e, a.group_by, amap):
                groups[k].append(e)
        result["group_by"] = a.group_by
        result["groups"] = {k: summarize(v) for k, v in sorted(groups.items())}
    if a.list:
        result["entries"] = [{"id": e.id, "date": e.date, "description": e.description, "tags": e.tags,
                              "context": e.context, "qty": e.qty, "unit": e.unit, "file": e.file}
                             for e in sorted(entries, key=lambda x: (x.date, x.num))]
    result["phrase"] = (f"at least {len(entries)} recorded entr{'y' if len(entries) == 1 else 'ies'}"
                        + (f" ({', '.join(f'{v} {k}' for k, v in result['total']['qty_by_unit'].items())})"
                           if result["total"]["qty_by_unit"] else ""))
    if a.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    t = result["total"]
    print(f"{result['phrase']}; {t['first'] or '-'} → {t['last'] or '-'}")
    print("ids: " + (", ".join(t["ids"]) or "-"))
    for k, g in (result.get("groups") or {}).items():
        q = "; ".join(f"{v} {u}" for u, v in g["qty_by_unit"].items())
        print(f"  {k}: {g['entries']}" + (f" ({q})" if q else "") + f"  [{', '.join(g['ids'])}]")
    for e in result.get("entries") or []:
        print(f"  {e['id']} {e['date']} {e['description']}  #{' #'.join(e['tags'])}  @{e['context']}")
    return 0


# --------------------------------------------------------------------------- vocabulary
def cmd_tags(a):
    pool = require_pool(a.pool)
    cfg = load_config(pool)
    vocab = tag_vocabulary(pool, cfg)
    if a.add:
        tag = norm_tag(a.add)
        if tag in vocab or tag in alias_map(vocab):
            sys.exit(f"tag #{tag} already exists (or is an alias of #{alias_map(vocab).get(tag)})")
        p = lpath(pool, cfg, "journal_readme")
        aliases = ", ".join(norm_tag(x) for x in (a.aliases or "").split(",") if x.strip())
        row = f"| #{tag} | {(a.definition or '').strip()} | {aliases} |"
        text = read_text(p).rstrip("\n")
        write_text(p, text + "\n" + row + "\n")
        print(json.dumps({"added": row}, ensure_ascii=False))
        return 0
    amap = alias_map(vocab)
    usage = collections.Counter()
    for e in journal_entries(pool, cfg):
        for t in e.tags:
            usage[amap.get(t, t)] += 1
    out = {"vocabulary": {t: dict(v, uses=usage.get(t, 0)) for t, v in sorted(vocab.items())},
           "unknown_in_use": {t: n for t, n in sorted(usage.items()) if t not in vocab}}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_next(a):
    print(next_id(require_pool(a.pool), "J"))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add"); add_pool_arg(p)
    p.add_argument("--date", default=today())
    p.add_argument("--desc", required=True)
    p.add_argument("--original", required=True, help="verbatim text as told, any language")
    p.add_argument("--tag", action="append")
    p.add_argument("--context", default=None)
    p.add_argument("--qty", type=float, default=None)
    p.add_argument("--unit", default="")
    p.add_argument("--recorded", default=None, help="date it was told, when later than --date")
    p.add_argument("--link", default=None)
    p.add_argument("--promoted", default=None)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_add)

    p = sub.add_parser("stats"); add_pool_arg(p)
    p.add_argument("--tag", action="append")
    p.add_argument("--any", action="store_true", help="match any of the tags (default: all)")
    p.add_argument("--context", default=None, help="exact context, or a prefix ending in ':' '/' or '*'")
    p.add_argument("--from", dest="date_from", default=None)
    p.add_argument("--to", dest="date_to", default=None)
    p.add_argument("--text", default=None)
    p.add_argument("--group-by", choices=["tag", "context", "day", "week", "month"], default=None)
    p.add_argument("--list", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_stats)

    p = sub.add_parser("tags"); add_pool_arg(p)
    p.add_argument("--add", default=None)
    p.add_argument("--definition", default=None)
    p.add_argument("--aliases", default=None)
    p.set_defaults(fn=cmd_tags)

    p = sub.add_parser("next-id"); add_pool_arg(p); p.set_defaults(fn=cmd_next)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
