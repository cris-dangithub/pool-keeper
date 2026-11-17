#!/usr/bin/env python3
"""
Pool management: find, create and configure a knowledge pool.

    pool.py find                                   # pool path, or NO_POOL / AMBIGUOUS (JSON)
    pool.py init --root DIR --name "Full Name" --ui-language es --pool-language en
                 [--layout en|es|id | --layout-json FILE] [--strings-json FILE]
                 [--domains goals,availability] [--country CO] [--official-source URL ...]
                 [--web-research auto|ask|off] [--max-questions 1] [--git]
                 [--default-context SLUG] [--translate-originals] [--never-copy TEXT ...]
                 [--no-delegation] [--registry-name NAME] [--no-register] [--no-skill-path]
    pool.py adopt --root DIR --name ... (same options as init) [--map KEY=PATH ...]
                  [--legacy-skill-dir DIR] [--dry-run]
                                                   # manage an existing pool: keeps every file
                                                   # and name, maps them to layout keys, creates
                                                   # only what is missing
    pool.py refresh                                # create missing files, rewrite instruction blocks
    pool.py config show | get KEY | set KEY=VALUE ...
    pool.py registry list | add NAME PATH | remove NAME
    pool.py template KEY                           # a template rendered in the pool language
    pool.py strings                                # marker words and headings of the pool language
    pool.py git-commit -m MESSAGE                  # only when config git=true

Never overwrites an existing pool file: `init` and `refresh` only create what is missing.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import (CORE_DIR_KEYS, CORE_FILE_KEYS, DOMAIN_KEYS, LEGACY_DIR, MARKER,  # noqa: E402
                    NAME_KEYS, SKILL_DIR, STRINGS_OVERRIDE, TEMPLATES, VERSION, add_pool_arg,
                    builtin_languages,
                    find_pool, is_pool, load_config, load_layout, load_registry, load_strings,
                    read_text, render, require_pool, save_config, save_registry, slugify,
                    today, write_text)

BLOCK_START, BLOCK_END = "<!-- pool-keeper:start -->", "<!-- pool-keeper:end -->"

# canonical key -> template file (templates/pool/<name>.md)
TEMPLATE_FOR = {k: k for k in CORE_FILE_KEYS + DOMAIN_KEYS}
TEMPLATE_FOR["experience"] = "experience_entry"

DEFAULT_NEVER_COPY = [
    "national ID / passport / tax numbers",
    "bank account and card numbers",
    "passwords, tokens, API keys",
    "names and contacts of third parties in work documents (keep structure and counts only)",
    "health data unless the person explicitly asks to store it",
]

LANG_NAMES = {"en": "English", "es": "Spanish (Español)", "id": "Indonesian (Bahasa Indonesia)"}


# --------------------------------------------------------------------------- rendering
def context(pool: pathlib.Path, cfg: dict) -> dict:
    strings = load_strings(cfg.get("pool_language"), pool=pool)
    layout = cfg.get("layout") or {}
    files = {k: pathlib.PurePosixPath(v).name for k, v in layout.items()}
    git_line = ("yes — pool-keeper commits after each ingest (`pk git-commit`); never pushes."
                if cfg.get("git") else "no — this pool does not use git commits.")
    show_path = cfg.get("show_skill_path", True)
    skill_line = (f"\nIf the skill is not auto-loaded, open `{SKILL_DIR / 'SKILL.md'}` and follow it."
                  if show_path else
                  "\nIf the skill is not auto-loaded, install the `pool-keeper` plugin "
                  "(`/plugin install pool-keeper@pool-keeper`).")
    deleg = bool((cfg.get("delegation") or {}).get("allowed", True))
    return {
        "t": strings, "m": strings.get("m", {}), "layout": layout, "file": files,
        "name": (cfg.get("person") or {}).get("name", ""), "today": today(),
        "ui_language": LANG_NAMES.get(cfg.get("ui_language"), cfg.get("ui_language", "")),
        "pool_language": LANG_NAMES.get(cfg.get("pool_language"), cfg.get("pool_language", "")),
        "git_line": git_line, "skill_line": skill_line,
        "delegation_allowed": "yes" if deleg else "no",
        "delegation_word": "allowed" if deleg else "not allowed",
        "structure_table": structure_table(cfg, strings),
        "layout_table": "\n".join(f"| {k} | `{v}` |" for k, v in layout.items()
                                  if k in enabled_keys(cfg) or k == "source_notes"),
    }


def enabled_keys(cfg: dict) -> list[str]:
    doms = cfg.get("domains") or {}
    return [k for k in CORE_FILE_KEYS + CORE_DIR_KEYS] + [k for k in DOMAIN_KEYS if doms.get(k)]


def structure_table(cfg: dict, strings: dict) -> str:
    layout = cfg.get("layout") or {}
    order = ["snapshot", "profile", "experience", "education", "skills", "certifications_languages",
             "achievements", "journal", "narrative_positioning", "stories", "writing_style",
             "other", *DOMAIN_KEYS, "keywords", "open_questions", "changelog", "sources"]
    rows = [f"| {strings.get('col_file', 'File')} | {strings.get('col_contents', 'Contents')} |", "|---|---|"]
    keys = enabled_keys(cfg)
    for k in order:
        if k in keys and k in layout:
            rows.append(f"| `{layout[k]}` | {strings.get('desc_' + k, '')} |")
    return "\n".join(rows)


def template_text(key: str) -> str:
    name = TEMPLATE_FOR.get(key, key)
    p = TEMPLATES / "pool" / f"{name}.md"
    if not p.is_file():
        sys.exit(f"no template for {key!r}")
    return read_text(p)


def rendered(key: str, pool, cfg) -> str:
    return render(template_text(key), context(pathlib.Path(pool), cfg))


# --------------------------------------------------------------------------- instruction blocks
def write_block(path: pathlib.Path, block: str) -> str:
    block = f"{BLOCK_START}\n{block.strip()}\n{BLOCK_END}\n"
    if path.is_file():
        cur = read_text(path)
        if BLOCK_START in cur and BLOCK_END in cur:
            new = re.sub(re.escape(BLOCK_START) + r".*?" + re.escape(BLOCK_END) + r"\n?",
                         lambda _m: block, cur, flags=re.S)
            write_text(path, new)
            return "updated"
        write_text(path, cur.rstrip() + "\n\n" + block)
        return "appended"
    write_text(path, block)
    return "created"


def refresh_instructions(pool: pathlib.Path, cfg: dict) -> dict:
    ctx = context(pool, cfg)
    block = render(read_text(TEMPLATES / "instructions" / "block.md"), ctx)
    out = {name: write_block(pool / name, block) for name in ("CLAUDE.md", "AGENTS.md")}
    # A pointer SKILL.md inside the pool, so tools that scan a pool for its managing skill
    # (cv-tailor's manager probe) find the delegation rules without the plugin being in the pool.
    stub = render(read_text(TEMPLATES / "instructions" / "manager_skill.md"), ctx)
    write_text(pool / MARKER / "manager" / "SKILL.md", stub)
    out["manager_stub"] = f"{MARKER}/manager/SKILL.md"
    return out


def create_missing(pool: pathlib.Path, cfg: dict) -> list[str]:
    created = []
    layout = cfg["layout"]
    for key in enabled_keys(cfg):
        rel = layout.get(key)
        if not rel:
            continue
        target = pool / rel.rstrip("/")
        if key in CORE_DIR_KEYS:
            if not target.exists():
                target.mkdir(parents=True, exist_ok=True)
                created.append(rel)
            continue
        if not target.exists():
            write_text(target, rendered(key, pool, cfg).rstrip() + "\n")
            created.append(rel)
    return created


# --------------------------------------------------------------------------- commands
def cmd_find(a):
    print(json.dumps(find_pool(a.pool), ensure_ascii=False, indent=2))
    return 0


def cmd_init(a):
    root = pathlib.Path(a.root).expanduser().resolve()
    if is_pool(root) and not a.force:
        sys.exit(f"ALREADY_INITIALISED: {root} is already a pool (use `pk refresh`).")
    layout = load_layout(a.layout or a.pool_language, a.layout_json)
    if a.strings_json:
        load_strings(strings_json=a.strings_json)  # validate it parses
    existing = [v for k, v in layout.items() if k not in ("readme", "changelog", "source_notes")
                and (root / v.rstrip("/")).exists()]
    if existing and not a.allow_existing:
        sys.exit("NOT_EMPTY: this folder already has pool-like content (" + ", ".join(existing[:5])
                 + "). To manage an existing pool use `pk adopt` (keeps every file and name); "
                   "--allow-existing only adds what is missing without indexing old files.")
    root.mkdir(parents=True, exist_ok=True)
    cfg = build_config(a, layout)
    out = write_pool(root, cfg, a)
    print(json.dumps(dict(out, config=cfg), ensure_ascii=False, indent=2))
    return 0


def build_config(a, layout: dict) -> dict:
    domains = {k: False for k in DOMAIN_KEYS}
    for d in (a.domains or "").split(","):
        d = d.strip()
        if not d:
            continue
        if d not in domains:
            sys.exit(f"unknown domain {d!r}; choose from {', '.join(DOMAIN_KEYS)}")
        domains[d] = True
    return {
        "version": 1,
        "pool_keeper": VERSION,
        "created": today(),
        "person": {"name": a.name},
        "ui_language": a.ui_language,
        "pool_language": a.pool_language,
        "keep_original_language": not a.translate_originals,
        "domains": domains,
        "layout": layout,
        "country": a.country or "",
        "official_sources": a.official_source or [],
        "web_research": a.web_research,
        "questions": {"policy": "minimal", "max_per_report": a.max_questions},
        "sensitive": {"never_copy": DEFAULT_NEVER_COPY + (a.never_copy or [])},
        "delegation": {"allowed": not a.no_delegation,
                       "not_done_section": f"{layout['open_questions']} → "
                                           f"{load_strings(a.pool_language, a.strings_json)['h_not_done']}"},
        "journal": {"default_context": a.default_context or ""},
        "sources": {"github": []},
        "git": bool(a.git),
        "show_skill_path": not a.no_skill_path,
    }


def write_pool(root: pathlib.Path, cfg: dict, a) -> dict:
    """Config, strings override, missing files, instruction blocks, registry, git (init/adopt)."""
    (root / MARKER).mkdir(parents=True, exist_ok=True)
    save_config(root, cfg)
    if a.strings_json:
        shutil.copyfile(a.strings_json, root / MARKER / STRINGS_OVERRIDE)
    write_text(root / MARKER / ".gitignore", "github/runs/\nids.lock\n")
    created = create_missing(root, cfg)
    blocks = refresh_instructions(root, cfg)
    reg_name = None
    if not a.no_register:
        reg = load_registry()
        reg_name = a.registry_name or slugify(a.name)
        reg.setdefault("pools", {})[reg_name] = {"path": str(root), "person": a.name, "added": today()}
        save_registry(reg)
    git = git_init(root) if a.git else None
    return {"pool": str(root), "registered_as": reg_name, "created": created,
            "instructions": blocks, "git": git}


# --------------------------------------------------------------------------- adopt
_PREFIX = re.compile(r"^\d+[_-]")
IGNORED_TOP = {"CLAUDE.md", "AGENTS.md", MARKER, ".git", ".gitignore", ".gitattributes"}


def bare(name: str) -> str:
    """'00_profil.md' -> 'profil.md': the name without its numeric ordering prefix."""
    return _PREFIX.sub("", name).lower()


def match_layout(root: pathlib.Path, wanted: dict, overrides: dict) -> dict:
    """Map every canonical key to what already exists in `root`.

    For each key: an explicit override, else the exact path of the language layout, else the one
    entry of the same kind (file/folder) in the same parent folder whose name matches without the
    numeric prefix (`00_profil.md` ↔ `01_profil.md`). Nested keys (journal_readme...) look inside
    the folder their parent key was mapped to."""
    found, missing, ambiguous = {}, [], {}
    dir_keys = [k for k in wanted if wanted[k].endswith("/")]
    order = dir_keys + [k for k in wanted if k not in dir_keys]
    for key in order:
        if key in NAME_KEYS:
            continue
        want = wanted[key]
        is_dir = want.endswith("/")
        if key in overrides:
            rel = overrides[key].replace("\\", "/").strip("/") + ("/" if is_dir else "")
            if not (root / rel.rstrip("/")).exists():
                sys.exit(f"MAP_NOT_FOUND: --map {key}={overrides[key]} does not exist in {root}")
            found[key] = rel
            continue
        parts = want.rstrip("/").split("/")
        parent = "/".join(parts[:-1])
        for pk, pv in found.items():  # a nested key follows its parent's real folder name
            if pk in dir_keys and parent and wanted[pk].rstrip("/") == parent:
                parent = pv.rstrip("/")
        exact = f"{parent}/{parts[-1]}" if parent else parts[-1]
        if (root / exact).exists() and (root / exact).is_dir() == is_dir:
            found[key] = exact + ("/" if is_dir else "")
            continue
        base = root / parent if parent else root
        cands = [p for p in (base.iterdir() if base.is_dir() else [])
                 if p.is_dir() == is_dir and bare(p.name) == bare(parts[-1])]
        if len(cands) == 1:
            rel = (f"{parent}/" if parent else "") + cands[0].name
            found[key] = rel + ("/" if is_dir else "")
        elif len(cands) > 1:
            ambiguous[key] = sorted(c.name for c in cands)
        else:
            missing.append(key)
    return {"found": found, "missing": missing, "ambiguous": ambiguous}


def source_notes_name(root: pathlib.Path, sources_rel: str | None, default: str) -> str:
    """The notes file name the existing sources use most (e.g. catatan.md), else the default."""
    if not sources_rel:
        return default
    counts: dict = {}
    for d in (root / sources_rel.rstrip("/")).glob("*/"):
        for f in d.glob("*.md"):
            counts[f.name] = counts.get(f.name, 0) + 1
    return max(counts, key=counts.get) if counts else default


def move_legacy_skill(root: pathlib.Path, rel: str) -> dict:
    """Move an old pool-specific skill out of sight of skill scanners (cv-tailor's manager probe
    reads every SKILL.md inside a pool): into .pool-keeper/legacy/<name>/, SKILL.md renamed."""
    src = (root / rel).resolve()
    if not src.is_dir() or root.resolve() not in src.parents:
        sys.exit(f"LEGACY_NOT_FOUND: {rel} is not a folder inside the pool")
    name = src.name
    skill_md = src / "SKILL.md"
    if skill_md.is_file():
        m = re.search(r"^name:\s*(\S+)", read_text(skill_md), re.M)
        name = m.group(1) if m else name
    dest = root / MARKER / LEGACY_DIR / name
    if dest.exists():
        sys.exit(f"LEGACY_EXISTS: {dest} already exists")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))
    if (dest / "SKILL.md").is_file():
        (dest / "SKILL.md").rename(dest / "SKILL.legacy.md")
    return {"from": rel, "to": dest.relative_to(root).as_posix()}


def cmd_adopt(a):
    root = pathlib.Path(a.root).expanduser().resolve()
    if is_pool(root):
        sys.exit(f"ALREADY_INITIALISED: {root} is already a pool (use `pk refresh`).")
    if not root.is_dir():
        sys.exit(f"NOT_FOUND: {root} is not a folder")
    wanted = load_layout(a.layout or a.pool_language, a.layout_json)
    overrides = {}
    for kv in a.map or []:
        k, _, v = kv.partition("=")
        if k.strip() not in wanted or not v.strip():
            sys.exit(f"bad --map {kv!r}: use key=relative/path with a key from: {', '.join(wanted)}")
        overrides[k.strip()] = v.strip()
    m = match_layout(root, wanted, overrides)
    if m["ambiguous"]:
        sys.exit("AMBIGUOUS_LAYOUT: several candidates for "
                 + "; ".join(f"{k}: {', '.join(v)}" for k, v in m["ambiguous"].items())
                 + ". Pass --map key=path for each.")
    core = [k for k in ("profile", "open_questions", "sources_index") if k in m["found"]]
    if len(core) < 2:
        sys.exit("NOT_A_POOL: this folder does not look like a knowledge pool (no profile / open "
                 "questions / sources index found). Use `pk init` in an empty folder instead, and "
                 "ingest these files as sources.")
    layout = dict(wanted)
    layout.update(m["found"])
    layout["source_notes"] = source_notes_name(root, m["found"].get("sources"), wanted["source_notes"])
    used_top = {v.strip("/").split("/")[0] for v in layout.values()} | IGNORED_TOP
    legacy_top = (a.legacy_skill_dir or "").replace("\\", "/").strip("/").split("/")[0]
    unmapped = sorted(p.name for p in root.iterdir()
                      if p.name not in used_top and p.name != legacy_top and p.name not in ("README.md", "CHANGELOG.md"))
    strings = load_strings(a.pool_language, a.strings_json)
    oq = root / layout["open_questions"]
    has_not_done = oq.is_file() and re.search(r"^##\s+" + re.escape(strings["h_not_done"]) + r"\s*$",
                                             read_text(oq), re.M) is not None
    chosen = {d.strip() for d in (a.domains or "").split(",") if d.strip()}
    enabled = enabled_keys({"domains": {d: d in chosen for d in DOMAIN_KEYS}})
    plan = {"pool": str(root), "mapped": m["found"],
            "will_create": {k: layout[k] for k in m["missing"] if k in enabled},
            "source_notes": layout["source_notes"], "unmapped_kept_as_is": unmapped,
            "legacy_skill": a.legacy_skill_dir or None,
            "not_done_section_present": has_not_done}
    if a.dry_run:
        print(json.dumps(dict(plan, dry_run=True), ensure_ascii=False, indent=2))
        return 0
    legacy = move_legacy_skill(root, a.legacy_skill_dir) if a.legacy_skill_dir else None
    cfg = build_config(a, layout)
    cfg["adopted"] = {"on": today(), "from_layout": a.layout or a.pool_language,
                      "legacy_skill": legacy["to"] if legacy else None}
    out = write_pool(root, cfg, a)
    warn = [] if has_not_done else [f"{layout['open_questions']} has no '## {strings['h_not_done']}' "
                                    "section: add it (delegated 'not done' answers go there)"]
    print(json.dumps(dict(plan, **out, legacy_moved=legacy, warnings=warn), ensure_ascii=False, indent=2))
    return 0


def git_init(root: pathlib.Path) -> str:
    exe = shutil.which("git")
    if not exe:
        return "git not installed: commits disabled until it is"
    if not (root / ".git").exists():
        subprocess.run([exe, "init", "-q"], cwd=root, check=False)
        return "initialised"
    return "already a git repository"


def cmd_refresh(a):
    pool = require_pool(a.pool)
    cfg = load_config(pool)
    # new layout keys from a newer version are added with the pool language's defaults
    defaults = load_layout(cfg.get("pool_language"))
    added = [k for k in defaults if k not in cfg.get("layout", {})]
    for k in added:
        cfg["layout"][k] = defaults[k]
    if added:
        save_config(pool, cfg)
    created = create_missing(pool, cfg)
    blocks = refresh_instructions(pool, cfg)
    print(json.dumps({"pool": str(pool), "layout_keys_added": added, "created": created,
                      "instructions": blocks}, ensure_ascii=False, indent=2))
    return 0


def parse_value(v: str):
    try:
        return json.loads(v)
    except ValueError:
        return v


def cmd_config(a):
    pool = require_pool(a.pool)
    cfg = load_config(pool)
    if a.action == "show":
        print(json.dumps({"pool": str(pool), "config": cfg}, ensure_ascii=False, indent=2))
        return 0
    if a.action == "get":
        cur = cfg
        for part in a.args[0].split("."):
            cur = cur.get(part) if isinstance(cur, dict) else None
        print(json.dumps(cur, ensure_ascii=False, indent=2))
        return 0
    for kv in a.args:
        key, _, val = kv.partition("=")
        parts = key.strip().split(".")
        cur = cfg
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = parse_value(val.strip())
    save_config(pool, cfg)
    touched = {kv.split("=")[0].split(".")[0] for kv in a.args}
    if touched & {"ui_language", "pool_language", "domains", "delegation", "git", "person",
                  "layout", "show_skill_path"}:
        create_missing(pool, cfg)
        refresh_instructions(pool, cfg)
    print(json.dumps(cfg, ensure_ascii=False, indent=2))
    return 0


def cmd_registry(a):
    reg = load_registry()
    pools = reg.setdefault("pools", {})
    if a.action == "list":
        print(json.dumps({k: dict(v, exists=is_pool(v.get("path", ""))) for k, v in pools.items()},
                         ensure_ascii=False, indent=2))
        return 0
    if a.action == "add":
        name, path = a.args[0], str(pathlib.Path(a.args[1]).expanduser().resolve())
        if not is_pool(path):
            sys.exit(f"{path} is not a pool")
        pools[name] = {"path": path, "person": (load_config(path).get("person") or {}).get("name", ""),
                       "added": today()}
    elif a.action == "remove":
        pools.pop(a.args[0], None)
    save_registry(reg)
    print(json.dumps(pools, ensure_ascii=False, indent=2))
    return 0


def cmd_template(a):
    pool = require_pool(a.pool)
    print(rendered(a.key, pool, load_config(pool)))
    return 0


def cmd_strings(a):
    pool = require_pool(a.pool)
    cfg = load_config(pool)
    s = load_strings(cfg.get("pool_language"), pool=pool)
    keep = {k: v for k, v in s.items() if k == "m" or k.startswith(("h_", "f_", "star_", "g_", "k_",
                                                                     "src_", "kind_", "cl_"))
            or k in ("weekdays", "journal_title", "not_done_format", "journal_tokens", "journal_personal")}
    print(json.dumps({"pool_language": cfg.get("pool_language"), "builtin": builtin_languages(),
                      "strings": keep}, ensure_ascii=False, indent=2))
    return 0


def cmd_git_commit(a):
    pool = require_pool(a.pool)
    cfg = load_config(pool)
    if not cfg.get("git"):
        print("GIT_DISABLED: config git=false; nothing committed.")
        return 0
    exe = shutil.which("git")
    if not exe:
        print("git is not installed; nothing committed.")
        return 0
    if not (pool / ".git").exists():
        git_init(pool)
    subprocess.run([exe, "add", "-A"], cwd=pool, check=True)
    r = subprocess.run([exe, "commit", "-q", "-m", a.message], cwd=pool, capture_output=True, text=True)
    print((r.stdout or r.stderr).strip() or "committed")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("find"); add_pool_arg(p); p.set_defaults(fn=cmd_find)

    def pool_args(p):
        p.add_argument("--root", required=True)
        p.add_argument("--name", required=True)
        p.add_argument("--ui-language", required=True)
        p.add_argument("--pool-language", required=True)
        p.add_argument("--layout", default=None, help="built-in layout: " + ", ".join(builtin_languages()))
        p.add_argument("--layout-json", default=None, help="translated layout for other languages")
        p.add_argument("--strings-json", default=None, help="translated headings for other languages")
        p.add_argument("--domains", default="", help="comma list of " + ", ".join(DOMAIN_KEYS))
        p.add_argument("--country", default="")
        p.add_argument("--official-source", action="append")
        p.add_argument("--web-research", choices=["auto", "ask", "off"], default="auto")
        p.add_argument("--max-questions", type=int, default=1)
        p.add_argument("--never-copy", action="append")
        p.add_argument("--default-context", default="")
        p.add_argument("--translate-originals", action="store_true",
                       help="store original text translated (default: keep its language)")
        p.add_argument("--no-delegation", action="store_true")
        p.add_argument("--git", action="store_true")
        p.add_argument("--registry-name", default=None)
        p.add_argument("--no-register", action="store_true")
        p.add_argument("--no-skill-path", action="store_true",
                       help="do not write this machine's skill path into CLAUDE.md/AGENTS.md")

    p = sub.add_parser("init")
    pool_args(p)
    p.add_argument("--allow-existing", action="store_true")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("adopt", help="manage an existing pool: keep every file and name")
    pool_args(p)
    p.add_argument("--map", action="append", metavar="KEY=PATH",
                   help="force a layout key to an existing path (repeatable)")
    p.add_argument("--legacy-skill-dir", default=None,
                   help="old pool-specific skill folder inside the pool to retire into .pool-keeper/legacy/")
    p.add_argument("--dry-run", action="store_true", help="only print the mapping")
    p.set_defaults(fn=cmd_adopt)

    p = sub.add_parser("refresh"); add_pool_arg(p); p.set_defaults(fn=cmd_refresh)

    p = sub.add_parser("config"); add_pool_arg(p)
    p.add_argument("action", choices=["show", "get", "set"]); p.add_argument("args", nargs="*")
    p.set_defaults(fn=cmd_config)

    p = sub.add_parser("registry")
    p.add_argument("action", choices=["list", "add", "remove"]); p.add_argument("args", nargs="*")
    p.set_defaults(fn=cmd_registry)

    p = sub.add_parser("template"); add_pool_arg(p); p.add_argument("key"); p.set_defaults(fn=cmd_template)
    p = sub.add_parser("strings"); add_pool_arg(p); p.set_defaults(fn=cmd_strings)
    p = sub.add_parser("git-commit"); add_pool_arg(p); p.add_argument("-m", "--message", required=True)
    p.set_defaults(fn=cmd_git_commit)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
