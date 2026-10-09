#!/usr/bin/env python3
"""
Check what pool-keeper needs. Standard library only.

    doctor.py [--json] [--pool NAME|PATH]

Essential: Python 3.9+. Optional: gh (GitHub ingestion; with the accounts it is logged into),
git (pools with `git: true`). Also reports which pool would be used here and how it was found.
Exit 0 when the essentials are ready.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import VERSION, add_pool_arg, find_pool, load_config, registry_path  # noqa: E402


def gh_accounts(exe: str) -> tuple[bool, str]:
    r = subprocess.run([exe, "auth", "status"], capture_output=True, text=True)
    text = (r.stdout + r.stderr)
    accounts = sorted({ln.split("account", 1)[1].split()[0] for ln in text.splitlines() if " account " in ln})
    if r.returncode == 0 and accounts:
        return True, "logged in as " + ", ".join(accounts)
    return False, "installed but not logged in: run `gh auth login`"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_pool_arg(ap)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    rows = []

    def row(name, ok, detail, essential):
        rows.append({"check": name, "ok": ok, "detail": detail, "essential": essential})

    row("python >= 3.9", sys.version_info >= (3, 9), sys.version.split()[0], True)
    gh = shutil.which("gh")
    if gh:
        ok, detail = gh_accounts(gh)
        row("gh (GitHub CLI)", ok, detail, False)
    else:
        row("gh (GitHub CLI)", False, "not installed (only needed for GitHub ingestion): https://cli.github.com", False)
    git = shutil.which("git")
    row("git", bool(git), git or "not installed (only needed for pools with git: true)", False)
    found = find_pool(a.pool)
    if found["status"] == "ok":
        cfg = load_config(found["pool"])
        detail = (f"{found['pool']} (via {found['via']}; person: {(cfg.get('person') or {}).get('name')}; "
                  f"ui={cfg.get('ui_language')}, pool={cfg.get('pool_language')})")
        row("pool", True, detail, False)
    elif found["status"] == "AMBIGUOUS":
        row("pool", False, "AMBIGUOUS: " + ", ".join(c["name"] for c in found["candidates"])
            + " — ask whose pool, then use --pool NAME", False)
    else:
        row("pool", False, "NO_POOL: run the setup (references/setup.md)", False)
    row("registry", registry_path().is_file(), str(registry_path()), False)
    ok = all(r["ok"] for r in rows if r["essential"])
    if a.json:
        print(json.dumps({"version": VERSION, "ok": ok, "checks": rows, "pool": found}, ensure_ascii=False, indent=2))
    else:
        print(f"pool-keeper {VERSION}")
        for r in rows:
            mark = "ok " if r["ok"] else ("ERR" if r["essential"] else " - ")
            print(f"[{mark}] {r['check']}: {r['detail']}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
