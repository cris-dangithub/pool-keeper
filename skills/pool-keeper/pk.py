#!/usr/bin/env python3
"""
pool-keeper command launcher. Standard library only: no environment to install.

    python <skill>/pk.py <command> [args...]        # python3 on macOS/Linux if python is missing

Commands:
    doctor                    python, gh (+ accounts), git, which pool is found here
    find                      locate the pool (JSON: ok / NO_POOL / AMBIGUOUS)
    init ...                  create a pool: config, templates, CLAUDE.md/AGENTS.md block, registry
    adopt ...                 manage an EXISTING pool: keep every file/name, map it, add what is missing
    refresh                  create missing files (new domains), rewrite the instruction blocks
    config show|get|set ...   read or change .pool-keeper/config.json
    registry list|add|remove  the pools of every person (~/.pool-keeper/pools.json)
    template KEY              a file template rendered in the pool language (e.g. experience)
    strings                   marker words and headings to use in the pool language
    next-id S|J|A|G|K         next free ID (S --reserve FOLDER: take it + placeholder index row)
    hash FILE...              SHA-256 + duplicate check against the sources index
    extract FILE [-o OUT]     text from .docx (tables, headers, footers, links), .html, text files
    journal add|stats|tags|next-id ...   the activity journal
    github add|status|sync|commit-run|show ...   GitHub history -> work units
    lint                      consistency checks (orphan tags, duplicate IDs, layout, journal...)
    status                    numbers for the status report
    git-commit -m MSG         commit the pool (only when config git=true; never pushes)

Every command accepts --pool NAME|PATH to choose the pool explicitly (default: POOL_KEEPER_POOL,
then the current folder and its parents, then the registry). Exit codes: 1 lint errors,
2 usage, 3 NO_POOL / AMBIGUOUS, 4 unsupported file type, 5 gh missing.
"""
import os
import pathlib
import subprocess
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent
SCRIPTS = SKILL_DIR / "scripts"
COMMANDS = {
    "doctor": ("doctor.py", []),
    "find": ("pool.py", ["find"]),
    "init": ("pool.py", ["init"]),
    "adopt": ("pool.py", ["adopt"]),
    "refresh": ("pool.py", ["refresh"]),
    "config": ("pool.py", ["config"]),
    "registry": ("pool.py", ["registry"]),
    "template": ("pool.py", ["template"]),
    "strings": ("pool.py", ["strings"]),
    "git-commit": ("pool.py", ["git-commit"]),
    "next-id": ("ids.py", ["next-id"]),
    "hash": ("ids.py", ["hash"]),
    "extract": ("extract.py", []),
    "journal": ("journal.py", []),
    "github": ("github.py", []),
    "lint": ("lint.py", []),
    "status": ("status.py", []),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd not in COMMANDS:
        print(f"unknown command {cmd!r}\n{__doc__}")
        return 2
    script, prefix = COMMANDS[cmd]
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, str(SCRIPTS / script), *prefix, *args], env=env).returncode


if __name__ == "__main__":
    sys.exit(main())
