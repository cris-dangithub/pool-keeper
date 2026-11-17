"""Shared helpers for the pool-keeper scripts: paths, pool discovery, config, layout, strings.

The skill folder is the engine (read-only at runtime). Everything about a person lives in a
*pool*: a folder that contains `.pool-keeper/config.json`. Scripts never use fixed file names
for pool content; they resolve canonical keys (profile, journal, sources_index...) through the
`layout` stored in the config.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import re
import sys
import unicodedata

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_DIR / "templates"
VERSION = "0.2.0"

MARKER = ".pool-keeper"
CONFIG_NAME = "config.json"
STRINGS_OVERRIDE = "strings.json"
LOCK_NAME = "ids.lock"
LEGACY_DIR = "legacy"

# Journal tokens: written in the pool language (strings → journal_tokens), read in any of these.
JOURNAL_TOKENS_EN = {"qty": "qty:", "rec": "rec:", "link": "link:", "original": "Original:",
                     "promoted": "Promoted:"}
JOURNAL_TOKEN_ALIASES = {
    "qty": ["qty", "jumlah", "cantidad"],
    "rec": ["rec", "dicatat", "registrado"],
    "link": ["link", "tautan", "enlace"],
    "original": ["Original", "Asli"],
    "promoted": ["Promoted", "Dipromosikan", "Promovido"],
}

# canonical keys -------------------------------------------------------------------------
CORE_FILE_KEYS = [
    "readme", "snapshot", "profile", "education", "skills", "certifications_languages",
    "achievements", "narrative_positioning", "stories", "other", "keywords",
    "open_questions", "changelog", "sources_index",
    "journal_readme", "writing_style_readme", "writing_style_patterns",
    "writing_style_rules", "writing_style_corrections",
]
CORE_DIR_KEYS = ["experience", "journal", "writing_style", "sources"]
DOMAIN_KEYS = ["preferences_values", "goals", "availability", "personal_life"]
NAME_KEYS = ["source_notes"]  # file names used inside folders, not paths
ALL_LAYOUT_KEYS = CORE_FILE_KEYS + CORE_DIR_KEYS + DOMAIN_KEYS + NAME_KEYS

EXIT_NO_POOL = 3

# Windows consoles default to a legacy code page; pool text is full of non-ASCII.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


# --------------------------------------------------------------------------- basics
def today() -> str:
    return dt.date.today().isoformat()


def now() -> str:
    return dt.datetime.now().replace(microsecond=0).isoformat()


def slugify(text: str, max_len: int = 48) -> str:
    """ASCII, lowercase, dash-separated. 'Café Ñandú S.A.' -> 'cafe-nandu-s-a'."""
    t = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    if len(t) > max_len:
        t = t[:max_len].rsplit("-", 1)[0] or t[:max_len]
    return t or "untitled"


def read_json(path, default=None):
    p = pathlib.Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(path, data) -> None:
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def read_text(path) -> str:
    return pathlib.Path(path).read_text(encoding="utf-8", errors="replace")


def write_text(path, text: str) -> None:
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


def parse_date(value: str) -> dt.date:
    return dt.date.fromisoformat(value.strip()[:10])


class PoolLock:
    """Exclusive lock on a pool while IDs are handed out, so two sessions writing to the same
    pool at the same time never get the same S/J number. A lock older than `stale` seconds is
    considered abandoned (a crashed session) and taken over."""

    def __init__(self, pool, timeout: float = 30.0, stale: float = 120.0):
        self.path = pathlib.Path(pool) / MARKER / LOCK_NAME
        self.timeout, self.stale = timeout, stale

    def __enter__(self):
        import time  # noqa: PLC0415
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, f"{os.getpid()} {now()}\n".encode())
                os.close(fd)
                return self
            except FileExistsError:
                try:
                    if time.time() - self.path.stat().st_mtime > self.stale:
                        self.path.unlink()
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() > deadline:
                    raise SystemExit(f"LOCKED: {self.path} is held by another session; retry in a moment.")
                time.sleep(0.05)

    def __exit__(self, *exc):
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
        return False


# --------------------------------------------------------------------------- registry
def home_dir() -> pathlib.Path:
    """~/.pool-keeper (override with POOL_KEEPER_HOME, used by tests)."""
    env = os.environ.get("POOL_KEEPER_HOME")
    return pathlib.Path(env).expanduser() if env else pathlib.Path.home() / ".pool-keeper"


def registry_path() -> pathlib.Path:
    return home_dir() / "pools.json"


def load_registry() -> dict:
    return read_json(registry_path(), {"version": 1, "pools": {}}) or {"version": 1, "pools": {}}


def save_registry(reg: dict) -> None:
    write_json(registry_path(), reg)


def is_pool(path) -> bool:
    return (pathlib.Path(path) / MARKER / CONFIG_NAME).is_file()


# --------------------------------------------------------------------------- discovery
def find_pool(spec: str | None = None, start=None) -> dict:
    """Locate the pool. Order: explicit --pool (path or registry name) -> POOL_KEEPER_POOL ->
    walk up from `start`/cwd looking for `.pool-keeper/` -> registry (~/.pool-keeper/pools.json).

    Returns {"status": "ok"|"NO_POOL"|"AMBIGUOUS", "pool": str|None, "via": str, "candidates": [...]}
    """
    reg = load_registry().get("pools", {})

    def by_spec(s: str, via: str):
        p = pathlib.Path(s).expanduser()
        if is_pool(p):
            return {"status": "ok", "pool": str(p.resolve()), "via": via, "candidates": []}
        if s in reg and is_pool(reg[s]["path"]):
            return {"status": "ok", "pool": str(pathlib.Path(reg[s]["path"]).resolve()),
                    "via": f"{via} (registry name)", "candidates": []}
        return None

    if spec:
        r = by_spec(spec, "--pool")
        return r or {"status": "NO_POOL", "pool": None, "via": "--pool",
                     "candidates": [], "detail": f"{spec!r} is neither a pool folder nor a registered name"}
    env = os.environ.get("POOL_KEEPER_POOL")
    if env:
        r = by_spec(env, "POOL_KEEPER_POOL")
        return r or {"status": "NO_POOL", "pool": None, "via": "POOL_KEEPER_POOL", "candidates": [],
                     "detail": f"POOL_KEEPER_POOL={env!r} is not a pool"}
    cur = pathlib.Path(start or os.getcwd()).resolve()
    for d in [cur, *cur.parents]:
        if is_pool(d):
            return {"status": "ok", "pool": str(d), "via": "folder", "candidates": []}
    live = {k: v for k, v in reg.items() if is_pool(v.get("path", ""))}
    if len(live) == 1:
        (name, entry), = live.items()
        return {"status": "ok", "pool": str(pathlib.Path(entry["path"]).resolve()),
                "via": f"registry ({name})", "candidates": []}
    if len(live) > 1:
        return {"status": "AMBIGUOUS", "pool": None, "via": "registry",
                "candidates": [{"name": k, "person": v.get("person", ""), "path": v["path"]}
                               for k, v in sorted(live.items())]}
    return {"status": "NO_POOL", "pool": None, "via": "none", "candidates": []}


def require_pool(spec: str | None = None) -> pathlib.Path:
    r = find_pool(spec)
    if r["status"] == "ok":
        return pathlib.Path(r["pool"])
    if r["status"] == "AMBIGUOUS":
        names = ", ".join(f"{c['name']} ({c['person']})" for c in r["candidates"])
        print(f"AMBIGUOUS: several pools are registered: {names}. Ask whose pool it is, then pass "
              f"--pool <name> or set POOL_KEEPER_POOL.", file=sys.stderr)
    else:
        print("NO_POOL: no .pool-keeper/config.json here, in any parent folder, in "
              "POOL_KEEPER_POOL or in the registry. Run the setup (references/setup.md). "
              + r.get("detail", ""), file=sys.stderr)
    sys.exit(EXIT_NO_POOL)


def add_pool_arg(parser) -> None:
    parser.add_argument("--pool", default=None,
                        help="pool folder or registered name (default: auto-discovery)")


# --------------------------------------------------------------------------- config
def config_path(pool) -> pathlib.Path:
    return pathlib.Path(pool) / MARKER / CONFIG_NAME


def load_config(pool) -> dict:
    return read_json(config_path(pool), {}) or {}


def save_config(pool, cfg: dict) -> None:
    write_json(config_path(pool), cfg)


def lpath(pool, cfg: dict, key: str) -> pathlib.Path:
    """Absolute path of a canonical layout key."""
    layout = cfg.get("layout") or {}
    if key not in layout:
        sys.exit(f"LAYOUT_KEY_MISSING: {key!r} is not in the pool layout (run `pk lint`).")
    return pathlib.Path(pool) / layout[key].rstrip("/")


# --------------------------------------------------------------------------- layout & strings
def builtin_languages() -> list[str]:
    return sorted(p.stem for p in (TEMPLATES / "layout").glob("*.json"))


def load_layout(lang: str | None = None, layout_json: str | None = None) -> dict:
    """The layout map for `lang` (en/es/id built in) or from a JSON file. Missing keys fall
    back to English so a partial translation still produces a complete pool."""
    base = read_json(TEMPLATES / "layout" / "en.json")
    base.pop("_comment", None)
    if layout_json:
        custom = read_json(layout_json)
    elif lang and (TEMPLATES / "layout" / f"{lang}.json").is_file():
        custom = read_json(TEMPLATES / "layout" / f"{lang}.json")
    else:
        custom = {}
    custom = {k: v for k, v in (custom or {}).items() if not k.startswith("_")}
    out = dict(base)
    out.update(custom)
    return out


def load_strings(lang: str | None = None, strings_json: str | None = None, pool=None) -> dict:
    """Headings and marker words in the pool language. Order: explicit JSON file -> the pool's
    own override (.pool-keeper/strings.json) -> built-in language -> English fallback per key."""
    base = read_json(TEMPLATES / "strings" / "en.json")
    custom = {}
    if strings_json:
        custom = read_json(strings_json) or {}
    elif pool and (pathlib.Path(pool) / MARKER / STRINGS_OVERRIDE).is_file():
        custom = read_json(pathlib.Path(pool) / MARKER / STRINGS_OVERRIDE) or {}
    elif lang and (TEMPLATES / "strings" / f"{lang}.json").is_file():
        custom = read_json(TEMPLATES / "strings" / f"{lang}.json")
    out = dict(base)
    out.update({k: v for k, v in custom.items() if not k.startswith("_")})
    return out


def pool_strings(pool, cfg: dict) -> dict:
    return load_strings(cfg.get("pool_language"), pool=pool)


def journal_tokens(strings: dict) -> dict:
    """Tokens used when writing journal entries in the pool language (falls back to English)."""
    out = dict(JOURNAL_TOKENS_EN)
    out.update({k: v for k, v in (strings.get("journal_tokens") or {}).items() if k in out and v})
    return out


# --------------------------------------------------------------------------- rendering
_PLACEHOLDER = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")


def flatten(prefix: str, value, out: dict) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            flatten(f"{prefix}.{k}" if prefix else k, v, out)
    else:
        out[prefix] = value


def render(text: str, ctx: dict) -> str:
    flat: dict = {}
    flatten("", ctx, flat)

    def rep(m):
        k = m.group(1)
        if k not in flat:
            return m.group(0)
        v = flat[k]
        return ", ".join(map(str, v)) if isinstance(v, list) else str(v)

    return _PLACEHOLDER.sub(rep, text)


def weekday_name(date: dt.date, strings: dict) -> str:
    days = strings.get("weekdays") or ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
                                       "Saturday", "Sunday"]
    return days[date.weekday()]


def iter_md(pool, skip_keys=("sources",), cfg=None):
    """Markdown files of the pool, excluding .pool-keeper, .git, the sources archive folder and
    the instruction files (they describe the pool, they are not content)."""
    pool = pathlib.Path(pool)
    cfg = cfg or load_config(pool)
    skip = {MARKER, ".git"}
    for k in skip_keys:
        v = (cfg.get("layout") or {}).get(k)
        if v:
            skip.add(v.strip("/").split("/")[0])
    for p in sorted(pool.rglob("*.md")):
        rel = p.relative_to(pool)
        if rel.parts[0] in skip or rel.as_posix() in ("CLAUDE.md", "AGENTS.md"):
            continue
        yield p
