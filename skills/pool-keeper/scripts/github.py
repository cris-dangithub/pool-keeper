#!/usr/bin/env python3
"""
GitHub history -> work units for the pool. Read-only on GitHub (gh api GET only).

    github.py add --owner NAME[:user|org[:ACCOUNT]] ... --identity LOGIN_OR_EMAIL ...
                  [--include GLOB ...] [--exclude GLOB ...] [--since YYYY-MM-DD] [--max-units N]
    github.py status
    github.py sync [--since today|week|YYYY-MM-DD] [--repo OWNER/REPO] [--full] [--source I]
                   [--branches] [--max-units N]
    github.py commit-run RUN_ID [--discard]
    github.py show RUN_ID

Config (`sources.github[]` in .pool-keeper/config.json), several people/accounts supported:

    {"owners": [{"name": "octocat", "kind": "user", "account": "octocat"},
                {"name": "acme-inc", "kind": "org", "account": "octo-work"}],
     "identities": ["octocat", "octo@acme.com"],      # only work authored by these counts
     "repos": {"include": ["acme-inc/*"], "exclude": ["*/legacy-*"]},
     "since": "2024-01-01", "max_units_per_run": 25}

`sync` lists the person's new commits and PRs, drops noise (merges, bots, lockfile-only,
version bumps, formatting-only, typo fixes), groups the rest into WORK UNITS (a PR, else a
branch, else a same-day same-topic series), extracts Jira keys and tracker URLs, and writes
`.pool-keeper/github/runs/<run>.json` (+ a notes draft per repo) for the agent. It never moves
the per-repo cursor (`.pool-keeper/github/<owner>__<repo>.json`): only `commit-run`, run after
the agent wrote the pool, marks the run's commits as recorded. So an interrupted run is simply
offered again, and a second pass never duplicates anything. Units beyond --max-units stay for
the next run (oldest first), which is how a first full-history sync proceeds in batches.

Each account's token is read with `gh auth token --user ACCOUNT` and passed as GH_TOKEN, so the
user's active gh account is never switched. Exit 5 when gh is missing.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import fnmatch
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import (MARKER, add_pool_arg, load_config, now, read_json, require_pool,  # noqa: E402
                    save_config, today, write_json, write_text)

EXIT_NO_GH = 5

# --------------------------------------------------------------------------- noise & parsing
LOCKFILES = {
    "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb",
    "poetry.lock", "pipfile.lock", "uv.lock", "pdm.lock", "cargo.lock", "gemfile.lock",
    "composer.lock", "go.sum", "mix.lock", "pubspec.lock", "podfile.lock", "flake.lock",
    "packages.lock.json", "gradle.lockfile", "deno.lock",
}
VERSION_FILES = {"package.json", "pyproject.toml", "setup.cfg", "setup.py", "version", "version.txt",
                 "changelog.md", "cargo.toml", "pom.xml", "build.gradle", "__version__.py", "_version.py",
                 "chart.yaml", "manifest.json"}
BOT_RE = re.compile(r"(\[bot\]$|^dependabot|^renovate|^github-actions|^snyk-bot|^greenkeeper|-bot$|^bot$)", re.I)
MERGE_RE = re.compile(r"^Merge (pull request|branch|remote-tracking branch|tag) ", re.I)
BUMP_RE = re.compile(
    r"^(chore(\((release|deps|version)\))?!?:\s*(release|bump|v?\d)|bump(ed|s)?\b.*\b(version|to v?\d|v?\d+\.\d+)"
    r"|release v?\d+\.\d+|v?\d+\.\d+\.\d+(-[\w.]+)?$|version bump|prepare (for )?release|\[release\])", re.I)
FORMAT_RE = re.compile(
    r"^(style(\(.+\))?!?:|(run |apply )?(prettier|black|isort|gofmt|rustfmt|ruff format|clang-format)\b"
    r"|(re)?format(ted|ting)?\b|lint(ing)?( fix(es)?)?$|fix(ed)? (lint|linting|formatting|indentation|whitespace)"
    r"|whitespace\b|trailing (whitespace|spaces))", re.I)
TYPO_RE = re.compile(r"^(fix(ed|es)?:?\s+)?(a\s+)?typos?\b|^typo\b|\bfix(ed)? (a |some )?typos?\b", re.I)
JIRA_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")
JIRA_FALSE = {"UTF", "ISO", "SHA", "RFC", "CVE", "HTTP", "HTTPS", "TLS", "SSL", "AES", "MD", "PEP",
              "GPT", "ES", "X", "BASE", "INT", "UINT", "IPV", "WIN", "GMT", "UTC", "COVID", "H", "S", "JDK"}
TRACKER_RE = re.compile(
    r"https?://[^\s)\]>\"']*(?:atlassian\.net|/browse/[A-Z]|linear\.app|trello\.com/c/|youtrack|"
    r"clickup\.com|app\.asana\.com|shortcut\.com|/-/issues/|/issues/\d|/_workitems/|monday\.com|"
    r"notion\.so)[^\s)\]>\"']*")
CONV_RE = re.compile(r"^(\w+)(?:\(([^)]+)\))?!?:\s*(.+)$")


def subject(msg: str) -> str:
    return (msg or "").strip().splitlines()[0].strip() if (msg or "").strip() else ""


def jira_keys(*texts) -> list[str]:
    out = []
    for t in texts:
        for k in JIRA_RE.findall(t or ""):
            if k.split("-")[0] in JIRA_FALSE or k in out:
                continue
            out.append(k)
    return out


def tracker_urls(*texts) -> list[str]:
    out = []
    for t in texts:
        for u in TRACKER_RE.findall(t or ""):
            u = u.rstrip(".,;:")
            if u not in out:
                out.append(u)
    return out


def is_identity(c: dict, identities: set[str]) -> bool:
    for k in ("author_login", "author_email", "author_name"):
        v = (c.get(k) or "").strip().lower()
        if v and v in identities:
            return True
    return False


def noise_reason(c: dict) -> str | None:
    """Why a commit is noise, or None when it is real work. Uses message, author and, when
    known, the list of files it touched."""
    subj = subject(c.get("message", ""))
    login = c.get("author_login") or ""
    if (c.get("parents") or 1) > 1 or MERGE_RE.match(subj):
        return "merge"
    if BOT_RE.search(login) or BOT_RE.search(c.get("author_name") or ""):
        return "bot"
    files = c.get("files")
    names = [pathlib.PurePosixPath(f["filename"]).name.lower() for f in files] if files else []
    if names and all(n in LOCKFILES for n in names):
        return "lockfile-only"
    if BUMP_RE.search(subj) and (not names or all(n in VERSION_FILES or n in LOCKFILES for n in names)):
        return "version-bump"
    if FORMAT_RE.search(subj):
        return "formatting-only"
    if TYPO_RE.search(subj):
        changed = sum((f.get("additions") or 0) + (f.get("deletions") or 0) for f in files or [])
        if not files or changed <= 20:
            return "typo"
    return None


def topic(c: dict) -> str:
    """Topic of a commit for same-day grouping: Jira key > conventional-commit scope > the
    top-level folder it touched most > 'misc'."""
    msg = c.get("message", "")
    keys = jira_keys(msg, c.get("branch") or "")
    if keys:
        return keys[0]
    m = CONV_RE.match(subject(msg))
    if m and m.group(2):
        return m.group(2).lower()
    files = c.get("files") or []
    if files:
        tops = collections.Counter(
            (f["filename"].split("/")[0] if "/" in f["filename"] else "(root)") for f in files)
        return tops.most_common(1)[0][0]
    return "misc"


def key_files(commits: list[dict], limit=15) -> list[dict]:
    agg: dict[str, dict] = {}
    for c in commits:
        for f in c.get("files") or []:
            a = agg.setdefault(f["filename"], {"file": f["filename"], "status": f.get("status", ""),
                                                "additions": 0, "deletions": 0})
            a["additions"] += f.get("additions") or 0
            a["deletions"] += f.get("deletions") or 0
    ranked = sorted(agg.values(), key=lambda x: -(x["additions"] + x["deletions"]))
    return [f for f in ranked if pathlib.PurePosixPath(f["file"]).name.lower() not in LOCKFILES][:limit]


def unit_id(repo: str, shas: list[str], extra: str = "") -> str:
    h = hashlib.sha1((repo + "|" + extra + "|" + ",".join(sorted(shas))).encode()).hexdigest()
    return "u-" + h[:10]


def make_unit(repo: str, kind: str, commits: list[dict], title: str, pr=None, branch=None,
              private=False) -> dict:
    commits = sorted(commits, key=lambda c: (c["date"], c["sha"]))
    texts = [c.get("message", "") for c in commits] + [branch or ""]
    if pr:
        texts += [pr.get("title", ""), pr.get("body") or "", pr.get("head") or ""]
    dates = sorted({c["date"][:10] for c in commits})
    shas = [c["sha"] for c in commits]
    return {
        "unit_id": unit_id(repo, shas, f"pr{pr['number']}" if pr else ""),
        "repo": repo, "private": bool(private), "kind": kind, "title": title,
        "date_first": dates[0] if dates else (pr or {}).get("created_at", "")[:10],
        "date_last": dates[-1] if dates else (pr or {}).get("updated_at", "")[:10],
        "dates": dates,
        "commits": [{"sha": c["sha"], "short": c["sha"][:7], "date": c["date"],
                     "subject": subject(c.get("message", "")), "message": c.get("message", "")[:2000],
                     "url": c.get("url", "")} for c in commits],
        "pr": ({k: pr.get(k) for k in ("number", "title", "state", "merged_at", "created_at", "updated_at",
                                         "url", "head", "labels")} | {"body": (pr.get("body") or "")[:4000],
                                                                      "merged": bool(pr.get("merged_at"))}
               if pr else None),
        "branch": branch or (pr or {}).get("head"),
        "jira_keys": jira_keys(*texts),
        "tracker_urls": tracker_urls(*texts),
        "key_files": key_files(commits),
        "stats": {"commits": len(commits),
                  "additions": sum(f.get("additions") or 0 for c in commits for f in c.get("files") or []),
                  "deletions": sum(f.get("deletions") or 0 for c in commits for f in c.get("files") or []),
                  "files": len({f["filename"] for c in commits for f in c.get("files") or []})},
    }


def group_units(repo: str, commits: list[dict], prs: list[dict], default_branch: str = "main",
                private=False, pr_states: dict | None = None) -> list[dict]:
    """Commits -> work units. A PR groups its commits; else a non-default branch; else commits of
    the same day and topic. PRs with no new commits whose state changed since the last recorded
    run (e.g. merged) become 'pr-update' units."""
    pr_states = pr_states or {}
    by_sha = {c["sha"]: c for c in commits}
    used: set[str] = set()
    units = []
    for pr in sorted(prs, key=lambda p: p.get("created_at") or ""):
        mine = [by_sha[s] for s in pr.get("commits") or [] if s in by_sha and s not in used]
        if mine:
            used.update(c["sha"] for c in mine)
            units.append(make_unit(repo, "pr", mine, pr.get("title") or f"PR #{pr['number']}", pr=pr,
                                   private=private))
        else:
            state = "merged" if pr.get("merged_at") else pr.get("state", "")
            prev = pr_states.get(str(pr["number"]))
            if prev is not None and prev != state:
                u = make_unit(repo, "pr-update", [], pr.get("title") or f"PR #{pr['number']}", pr=pr,
                              private=private)
                u["unit_id"] = unit_id(repo, [], f"pr{pr['number']}-{state}")
                u["previous_state"] = prev
                units.append(u)
    rest = [c for c in commits if c["sha"] not in used]
    branches = collections.defaultdict(list)
    series = collections.defaultdict(list)
    for c in rest:
        b = c.get("branch")
        if b and b != default_branch:
            branches[b].append(c)
        else:
            series[(c["date"][:10], topic(c))].append(c)
    for b, cs in branches.items():
        units.append(make_unit(repo, "branch", cs, b, branch=b, private=private))
    for (day, top), cs in series.items():
        title = subject(cs[0].get("message", "")) if len(cs) == 1 else f"{top} ({len(cs)} commits, {day})"
        units.append(make_unit(repo, "series", cs, title, private=private))
    return sorted(units, key=lambda u: (u["date_first"] or "", u["unit_id"]))


def pr_state(pr: dict) -> str:
    return "merged" if pr.get("merged_at") else pr.get("state", "")


# --------------------------------------------------------------------------- fetchers
class GhError(RuntimeError):
    pass


class LiveFetcher:
    """GitHub through the gh CLI. GET requests only."""

    def __init__(self):
        self.exe = shutil.which("gh")
        if not self.exe:
            print("GH_MISSING: the GitHub CLI (gh) is not installed. Install it from "
                  "https://cli.github.com, run `gh auth login` once per account, then retry.",
                  file=sys.stderr)
            sys.exit(EXIT_NO_GH)
        self.tokens: dict[str, str] = {}
        self.errors: list[str] = []

    def _env(self, account):
        env = dict(os.environ)
        if account:
            if account not in self.tokens:
                r = subprocess.run([self.exe, "auth", "token", "--user", account], capture_output=True, text=True)
                self.tokens[account] = r.stdout.strip() if r.returncode == 0 else ""
                if not self.tokens[account]:
                    self.errors.append(f"no gh token for account {account!r}: run `gh auth login` for it")
            if self.tokens[account]:
                env["GH_TOKEN"] = self.tokens[account]
        return env

    def api_lines(self, path: str, jq: str, account=None, paginate=False) -> list:
        args = [self.exe, "api", "-X", "GET", path, "--jq", jq]
        if paginate:
            args.insert(2, "--paginate")
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", env=self._env(account))
        if r.returncode != 0:
            self.errors.append(f"gh api {path}: {r.stderr.strip()[:300]}")
            return []
        out = []
        for line in r.stdout.splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    out.append(line)
        return out

    def list_repos(self, owner: dict) -> list[dict]:
        if owner.get("kind") == "org":
            path = f"orgs/{owner['name']}/repos?per_page=100"
        else:
            path = "user/repos?affiliation=owner,collaborator,organization_member&per_page=100"
        rows = self.api_lines(path, ".[]|{full_name,pushed_at,private,default_branch,language}",
                              owner.get("account"), paginate=True)
        if owner.get("kind") != "org":
            rows = [r for r in rows if r["full_name"].lower().startswith(owner["name"].lower() + "/")]
        return rows

    def commits(self, repo: str, since: str | None, identities: list[str], account=None,
                branch: str | None = None) -> list[dict]:
        jq = ('.[]|{sha, date: .commit.author.date, author_login: (.author.login // ""), '
              'author_name: .commit.author.name, author_email: .commit.author.email, '
              'message: .commit.message, parents: (.parents|length), url: .html_url}')
        out = {}
        for ident in identities:
            q = f"repos/{repo}/commits?per_page=100&author={ident}"
            if since:
                q += f"&since={since}T00:00:00Z"
            if branch:
                q += f"&sha={branch}"
            for c in self.api_lines(q, jq, account, paginate=True):
                if isinstance(c, dict):
                    c["branch"] = branch
                    out.setdefault(c["sha"], c)
        return list(out.values())

    def commit_files(self, repo: str, sha: str, account=None) -> list[dict]:
        rows = self.api_lines(f"repos/{repo}/commits/{sha}",
                              ".files[]?|{filename, status, additions, deletions}", account)
        return [r for r in rows if isinstance(r, dict)]

    def prs(self, repo: str, identities: list[str], since: str | None, account=None) -> list[dict]:
        jq = ('.[]|{number, title, body, state, merged_at, created_at, updated_at, url: .html_url, '
              'user: .user.login, head: .head.ref, labels: [.labels[].name]}')
        ids = {i.lower() for i in identities}
        out = []
        for page in (1, 2, 3):
            rows = self.api_lines(f"repos/{repo}/pulls?state=all&sort=updated&direction=desc&per_page=100&page={page}",
                                  jq, account)
            rows = [r for r in rows if isinstance(r, dict)]
            for r in rows:
                if since and (r.get("updated_at") or "")[:10] < since:
                    continue
                if (r.get("user") or "").lower() in ids:
                    out.append(r)
            if len(rows) < 100 or (since and rows and (rows[-1].get("updated_at") or "")[:10] < since):
                break
        for r in out:
            r["commits"] = [s for s in self.api_lines(f"repos/{repo}/pulls/{r['number']}/commits?per_page=100",
                                                      ".[].sha", account) if isinstance(s, str)]
        return out

    def branches(self, repo: str, account=None) -> list[str]:
        return [b for b in self.api_lines(f"repos/{repo}/branches?per_page=100", ".[].name", account,
                                          paginate=True) if isinstance(b, str)]


class FixtureFetcher:
    """Offline fetcher for tests: same interface, data from a JSON file."""

    def __init__(self, path):
        self.data = read_json(path)
        self.errors: list[str] = []

    def list_repos(self, owner):
        return list(self.data.get("repos", {}).get(owner["name"], []))

    def commits(self, repo, since, identities, account=None, branch=None):
        ids = {i.lower() for i in identities}
        out = []
        for c in self.data.get("commits", {}).get(repo, []):
            if since and c["date"][:10] < since:
                continue
            if branch is not None and (c.get("branch") or None) != branch:
                continue
            if is_identity(c, ids):
                out.append({k: v for k, v in c.items() if k != "files"} | {"branch": c.get("branch")})
        return out

    def commit_files(self, repo, sha, account=None):
        for c in self.data.get("commits", {}).get(repo, []):
            if c["sha"] == sha:
                return c.get("files") or []
        return []

    def prs(self, repo, identities, since, account=None):
        ids = {i.lower() for i in identities}
        return [p for p in self.data.get("prs", {}).get(repo, [])
                if (p.get("user") or "").lower() in ids and not (since and (p.get("updated_at") or "")[:10] < since)]

    def branches(self, repo, account=None):
        return sorted({c.get("branch") for c in self.data.get("commits", {}).get(repo, []) if c.get("branch")})


# --------------------------------------------------------------------------- state
def gh_dir(pool) -> pathlib.Path:
    return pathlib.Path(pool) / MARKER / "github"


def cursor_path(pool, repo: str) -> pathlib.Path:
    return gh_dir(pool) / (repo.replace("/", "__") + ".json")


def load_cursor(pool, repo) -> dict:
    return read_json(cursor_path(pool, repo), {}) or {}


def resolve_since(value: str | None) -> str | None:
    if not value:
        return None
    v = value.strip().lower()
    if v == "today":
        return today()
    if v == "week":
        return (dt.date.today() - dt.timedelta(days=7)).isoformat()
    if v == "month":
        return (dt.date.today() - dt.timedelta(days=30)).isoformat()
    return dt.date.fromisoformat(v[:10]).isoformat()


def repo_selected(full: str, src: dict, only: str | None) -> bool:
    if only:
        return full.lower() == only.lower()
    rules = src.get("repos") or {}
    inc, exc = rules.get("include") or [], rules.get("exclude") or []
    name = full.split("/", 1)[-1]
    if inc and not any(fnmatch.fnmatch(full, g) or fnmatch.fnmatch(name, g) for g in inc):
        return False
    return not any(fnmatch.fnmatch(full, g) or fnmatch.fnmatch(name, g) for g in exc)


# --------------------------------------------------------------------------- sync
def sync(pool, src_index: int, src: dict, fetcher, since_arg=None, only_repo=None, full=False,
         branches=False, max_units=None, detail_limit=300) -> dict:
    identities = [i for i in src.get("identities") or []]
    ids = {i.lower() for i in identities}
    if not identities:
        sys.exit("this GitHub source has no identities: add the logins/emails the person commits with "
                 "(`pk github add ... --identity X`)")
    forced_since = resolve_since(since_arg)
    repos_out, all_units = [], []
    for owner in src.get("owners") or []:
        account = owner.get("account")
        for r in fetcher.list_repos(owner):
            full_name = r["full_name"]
            if not repo_selected(full_name, src, only_repo):
                continue
            cur = load_cursor(pool, full_name)
            seen = set(cur.get("seen_shas") or [])
            if forced_since:
                since = forced_since
            elif cur.get("last_date") and not full:
                since = (dt.date.fromisoformat(cur["last_date"][:10]) - dt.timedelta(days=1)).isoformat()
            else:
                since = resolve_since(src.get("since"))
            if since and (r.get("pushed_at") or "9999")[:10] < since:
                continue
            commits = {c["sha"]: c for c in fetcher.commits(full_name, since, identities, account)}
            default = r.get("default_branch") or "main"
            if branches:
                for b in fetcher.branches(full_name, account):
                    if b == default:
                        continue
                    for c in fetcher.commits(full_name, since, identities, account, branch=b):
                        commits.setdefault(c["sha"], c)
            own = [c for c in commits.values() if is_identity(c, ids)]
            new = [c for c in own if full or c["sha"] not in seen]
            filtered, kept = [], []
            for c in sorted(new, key=lambda x: x["date"]):
                reason = noise_reason(c)  # first pass: merge / bot by metadata
                if reason:
                    filtered.append({"sha": c["sha"], "date": c["date"], "subject": subject(c["message"]),
                                     "reason": reason})
                    continue
                if len(kept) < detail_limit:
                    c["files"] = fetcher.commit_files(full_name, c["sha"], account)
                reason = noise_reason(c)  # second pass: with the files touched
                if reason:
                    filtered.append({"sha": c["sha"], "date": c["date"], "subject": subject(c["message"]),
                                     "reason": reason})
                else:
                    kept.append(c)
            prs = fetcher.prs(full_name, identities, since, account)
            units = group_units(full_name, kept, prs, default, bool(r.get("private")), cur.get("prs") or {})
            for u in units:
                u["already_recorded"] = bool(u["commits"]) and all(c["sha"] in seen for c in u["commits"])
            repos_out.append({"repo": full_name, "private": bool(r.get("private")), "account": account,
                              "default_branch": default, "since": since,
                              "cursor_before": {k: cur.get(k) for k in ("last_date", "last_sha")},
                              "commits_seen_now": len(own), "new_commits": len(new),
                              "filtered": filtered, "units": [u["unit_id"] for u in units]})
            all_units += units
    all_units.sort(key=lambda u: (u["date_first"] or "", u["unit_id"]))
    cap = max_units or src.get("max_units_per_run") or 0
    included = all_units[:cap] if cap else all_units
    remaining = len(all_units) - len(included)
    inc_ids = {u["unit_id"] for u in included}
    for ro in repos_out:
        ro["units"] = [u for u in ro["units"] if u in inc_ids]
        if remaining:  # filtered commits newer than the last included unit wait for their batch
            last = max((u["date_last"] for u in included if u["repo"] == ro["repo"]), default="")
            ro["filtered"] = [f for f in ro["filtered"] if f["date"][:10] <= last] if last else []
    runs = gh_dir(pool) / "runs"
    base = run_id = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    n = 1
    while (runs / f"{run_id}.json").exists():
        n += 1
        run_id = f"{base}-{n}"
    run = {"run": run_id, "created": now(), "status": "pending", "source": src_index,
           "identities": identities, "since_arg": since_arg, "full": full,
           "repos": [ro for ro in repos_out if ro["units"] or ro["filtered"]],
           "units": included, "remaining_units": remaining,
           "errors": list(getattr(fetcher, "errors", [])),
           "next_step": ("Write the pool (one source per repo + one journal entry per unit), then run "
                         f"`pk github commit-run {run_id}`. Units with already_recorded=true are skipped.")}
    write_json(runs / f"{run_id}.json", run)
    for ro in run["repos"]:
        write_text(runs / run_id / (ro["repo"].replace("/", "__") + ".notes.md"),
                   notes_draft(ro, [u for u in included if u["repo"] == ro["repo"]], identities))
    return run


def notes_draft(repo_info: dict, units: list[dict], identities: list[str]) -> str:
    """Skeleton of sources/<date>_github-<owner>-<repo>/notes.md: every deterministic fact
    (dates, SHAs, URLs, keys) is filled; WHAT and WHY are left for the agent."""
    lines = [f"# GitHub — {repo_info['repo']}" + ("  🔒 private" if repo_info["private"] else ""),
             "", f"- Sync date: {today()}", f"- Identities: {', '.join(identities)}",
             f"- Account: {repo_info.get('account') or '(active gh account)'}",
             f"- Window: since {repo_info.get('since') or 'beginning'}", ""]
    for u in units:
        lines.append(f"## {u['date_first']} — {u['title']} ({u['kind']}, {u['unit_id']})")
        if u["pr"]:
            state = "merged" if u["pr"]["merged"] else u["pr"]["state"]
            lines.append(f"- PR #{u['pr']['number']} ({state}): {u['pr']['url']}")
        if u.get("branch"):
            lines.append(f"- Branch: `{u['branch']}`")
        for c in u["commits"]:
            lines.append(f"- {c['date'][:10]} `{c['short']}` {c['subject']} — {c['url']}")
        if u["jira_keys"]:
            lines.append(f"- Jira / tracker keys: {', '.join(u['jira_keys'])}")
        if u["tracker_urls"]:
            lines.append(f"- Tracker links: {', '.join(u['tracker_urls'])}")
        if u["key_files"]:
            lines.append("- Key files: " + ", ".join(f"`{f['file']}`" for f in u["key_files"][:8]))
        lines += ["- WHAT: <diff summary, key files; never copy code>",
                  "- WHY: <from messages, PR body, issues, tracker; mark (inference) if deduced>",
                  "- Result: <merged / closed / open / pushed>", "- Technologies: <...>", ""]
    return "\n".join(lines)


def commit_run(pool, run_id: str, discard=False) -> dict:
    path = gh_dir(pool) / "runs" / f"{run_id}.json"
    run = read_json(path)
    if not run:
        sys.exit(f"run {run_id} not found")
    if run.get("status") != "pending":
        sys.exit(f"run {run_id} is already {run.get('status')}")
    if discard:
        run["status"] = "discarded"
        run["closed"] = now()
        write_json(path, run)
        return {"run": run_id, "status": "discarded"}
    by_repo = collections.defaultdict(list)
    for u in run["units"]:
        by_repo[u["repo"]].append(u)
    touched = []
    for ro in run["repos"]:
        repo = ro["repo"]
        cur = load_cursor(pool, repo)
        seen = list(cur.get("seen_shas") or [])
        seen_set = set(seen)
        dates = []
        for u in by_repo.get(repo, []):
            for c in u["commits"]:
                if c["sha"] not in seen_set:
                    seen.append(c["sha"])
                    seen_set.add(c["sha"])
                dates.append((c["date"], c["sha"]))
            if u.get("pr"):
                cur.setdefault("prs", {})[str(u["pr"]["number"])] = "merged" if u["pr"]["merged"] else u["pr"]["state"]
        for f in ro.get("filtered") or []:
            if f["sha"] not in seen_set:
                seen.append(f["sha"])
                seen_set.add(f["sha"])
            dates.append((f["date"], f["sha"]))
        if dates:
            last_date, last_sha = max(dates)
            if not cur.get("last_date") or last_date > cur["last_date"]:
                cur["last_date"], cur["last_sha"] = last_date, last_sha
        cur.update({"repo": repo, "seen_shas": seen, "updated": now(),
                    "runs": (cur.get("runs") or []) + [run_id]})
        write_json(cursor_path(pool, repo), cur)
        touched.append(repo)
    run["status"] = "committed"
    run["closed"] = now()
    write_json(path, run)
    return {"run": run_id, "status": "committed", "repos": touched,
            "units_recorded": len(run["units"]), "remaining_units": run.get("remaining_units", 0)}


# --------------------------------------------------------------------------- commands
def sources_of(cfg) -> list[dict]:
    return (cfg.get("sources") or {}).get("github") or []


def parse_owner(spec: str) -> dict:
    parts = spec.split(":")
    name = parts[0].strip()
    kind = (parts[1].strip() if len(parts) > 1 and parts[1].strip() else "user")
    if kind not in ("user", "org"):
        sys.exit(f"owner kind must be user or org: {spec!r}")
    account = parts[2].strip() if len(parts) > 2 and parts[2].strip() else (name if kind == "user" else None)
    return {"name": name, "kind": kind, "account": account}


def cmd_add(a):
    pool = require_pool(a.pool)
    cfg = load_config(pool)
    src = {"owners": [parse_owner(o) for o in a.owner],
           "identities": [i.strip() for i in a.identity],
           "repos": {"include": a.include or [], "exclude": a.exclude or []},
           "since": a.since or None, "max_units_per_run": a.max_units}
    cfg.setdefault("sources", {}).setdefault("github", []).append(src)
    save_config(pool, cfg)
    print(json.dumps({"source": len(cfg["sources"]["github"]) - 1, "added": src}, ensure_ascii=False, indent=2))
    return 0


def cmd_status(a):
    pool = require_pool(a.pool)
    cfg = load_config(pool)
    out = []
    for i, s in enumerate(sources_of(cfg)):
        out.append({"source": i, "owners": s.get("owners"), "identities": s.get("identities"),
                    "repos": s.get("repos"), "since": s.get("since")})
    cursors = []
    d = gh_dir(pool)
    for f in sorted(d.glob("*.json")) if d.is_dir() else []:
        c = read_json(f, {}) or {}
        cursors.append({"repo": c.get("repo", f.stem), "last_date": c.get("last_date"),
                        "commits_recorded": len(c.get("seen_shas") or []), "runs": len(c.get("runs") or [])})
    runs = []
    for f in sorted((d / "runs").glob("*.json")) if (d / "runs").is_dir() else []:
        r = read_json(f, {}) or {}
        runs.append({"run": r.get("run"), "status": r.get("status"), "units": len(r.get("units") or []),
                     "remaining": r.get("remaining_units", 0)})
    print(json.dumps({"sources": out, "cursors": cursors, "runs": runs,
                      "gh_installed": bool(shutil.which("gh"))}, ensure_ascii=False, indent=2))
    return 0


def cmd_sync(a):
    pool = require_pool(a.pool)
    cfg = load_config(pool)
    srcs = sources_of(cfg)
    if not srcs:
        sys.exit("NO_GITHUB_SOURCE: add one first: pk github add --owner LOGIN --identity LOGIN")
    pending = [f.stem for f in sorted((gh_dir(pool) / "runs").glob("*.json"))
               if (read_json(f, {}) or {}).get("status") == "pending"] if (gh_dir(pool) / "runs").is_dir() else []
    fetcher = FixtureFetcher(a.fixture) if a.fixture else LiveFetcher()
    results = []
    for i, s in enumerate(srcs):
        if a.source is not None and i != a.source:
            continue
        run = sync(pool, i, s, fetcher, a.since, a.repo, a.full, a.branches, a.max_units)
        results.append({
            "run": run["run"], "file": (gh_dir(pool) / "runs" / f"{run['run']}.json").relative_to(pool).as_posix(),
            "source": i, "units": len(run["units"]),
            "already_recorded": sum(1 for u in run["units"] if u["already_recorded"]),
            "remaining_units": run["remaining_units"],
            "repos": {ro["repo"]: {"units": len(ro["units"]), "filtered": len(ro["filtered"]),
                                   "private": ro["private"]} for ro in run["repos"]},
            "errors": run["errors"]})
    print(json.dumps({"pending_before": pending, "runs": results}, ensure_ascii=False, indent=2))
    return 0


def cmd_commit_run(a):
    pool = require_pool(a.pool)
    print(json.dumps(commit_run(pool, a.run, a.discard), ensure_ascii=False, indent=2))
    return 0


def cmd_show(a):
    pool = require_pool(a.pool)
    run = read_json(gh_dir(pool) / "runs" / f"{a.run}.json")
    if not run:
        sys.exit(f"run {a.run} not found")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add"); add_pool_arg(p)
    p.add_argument("--owner", action="append", required=True, help="NAME[:user|org[:ACCOUNT]]")
    p.add_argument("--identity", action="append", required=True)
    p.add_argument("--include", action="append")
    p.add_argument("--exclude", action="append")
    p.add_argument("--since", default=None)
    p.add_argument("--max-units", type=int, default=25)
    p.set_defaults(fn=cmd_add)
    p = sub.add_parser("status"); add_pool_arg(p); p.set_defaults(fn=cmd_status)
    p = sub.add_parser("sync"); add_pool_arg(p)
    p.add_argument("--since", default=None, help="today | week | month | YYYY-MM-DD")
    p.add_argument("--repo", default=None)
    p.add_argument("--full", action="store_true", help="ignore the cursor; units already recorded are flagged")
    p.add_argument("--source", type=int, default=None)
    p.add_argument("--branches", action="store_true", help="also scan non-default branches (more API calls)")
    p.add_argument("--max-units", type=int, default=None)
    p.add_argument("--fixture", default=None, help=argparse.SUPPRESS)
    p.set_defaults(fn=cmd_sync)
    p = sub.add_parser("commit-run"); add_pool_arg(p); p.add_argument("run")
    p.add_argument("--discard", action="store_true")
    p.set_defaults(fn=cmd_commit_run)
    p = sub.add_parser("show"); add_pool_arg(p); p.add_argument("run"); p.set_defaults(fn=cmd_show)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
