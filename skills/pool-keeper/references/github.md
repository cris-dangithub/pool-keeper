# GitHub → pool

Turns the person's GitHub history into sources, journal entries and promoted facts. Triggers:
"analyze my changes today / this week / since <date>", "update the pool from GitHub", "what did
I ship this month?" (the last one is analysis: `pk journal stats --context github:`).

**Read-only, always:** GET requests through `gh api`; never clone, push, comment, label or
change anything. Each account's token is used through `GH_TOKEN` (`gh auth token --user
<account>`), so the user's active gh account is never switched. If `gh` is missing, the
command exits 5 with install instructions: relay them and stop.

## 0. Configure (once; more accounts any time)

```
pk github add --owner octocat --owner acme-inc:org:octo-work \
  --identity octocat --identity octo@acme.com [--include "acme-inc/*"] [--exclude "*/dotfiles"] \
  [--since 2024-01-01] [--max-units 25]
```

- `owners`: where to look (`user` or `org`), and `account` = the gh login whose token can read
  it (`gh auth status` lists them). Several people/accounts are fine: one source per person.
- `identities`: **every** login, name and e-mail the person commits with. Only work authored by
  an identity counts; colleagues' commits in the same repo never do.
- `repos.include/exclude`: globs on `owner/repo` or `repo`.
- `pk github status` shows sources, per-repo cursors and runs.

## 1. Sync

```
pk github sync [--since today|week|month|YYYY-MM-DD] [--repo owner/repo] [--full] [--branches]
```

It lists the person's new commits and PRs, drops **noise** (merges, bots, lockfile-only,
version bumps, formatting-only, typo fixes — each with its reason in `filtered`), groups the
rest into **work units** (a PR; else a non-default branch; else a same-day same-topic series
— topic = Jira key, conventional-commit scope, or main folder), extracts **Jira keys**
(`[A-Z][A-Z0-9]+-\d+`, minus UTF-8/ISO-8601-style false positives) and **tracker URLs**, and
writes:

- `.pool-keeper/github/runs/<run>.json` — every unit: repo, `private`, kind, title, dates,
  commits (SHA, date, subject, full message, URL), PR (number, state, merged, body, URL),
  branch, Jira keys, tracker URLs, key files with +/− lines, stats, `already_recorded`;
- `.pool-keeper/github/runs/<run>/<owner>__<repo>.notes.md` — a draft of the source notes
  with every deterministic fact filled in.

Without `--since`, each repo continues from its cursor (`.pool-keeper/github/<owner>__<repo>.json`).
The cursor **does not move** until step 4: an interrupted run is simply offered again, and
units already recorded never come back (`--full` re-lists them flagged `already_recorded`; skip
those). `pr-update` units = a PR recorded earlier whose state changed (e.g. merged): just
update the existing journal entry/source (no new entry for the same work).

**First full-history sync**: units are processed oldest first, at most `max_units_per_run` per
run (`remaining_units` says how many are left). Loop: sync → write → commit-run → report
progress in one line ("GitHub: 25/140 units recorded (up to 2025-03)") → next batch. Ask before
starting a long loop only if it is more than ~5 batches.

## 2. Per unit, the agent works out

- **WHAT** — summary of the change from the diff/files (open `gh api repos/<o>/<r>/commits/<sha>`
  for the patch when the message is not enough). Name key files; **never copy code**.
- **WHY** — from the commit messages, PR body, linked issues and tracker tickets. If only
  deduced: `(inference)`.
- **Result** — merged / closed / open / pushed directly.
- **Technologies** — languages, frameworks, services visible in files and messages.

## 3. Record

1. **One source per repo per sync**: `<sources>/<date>_github-<owner>-<repo>/<source_notes>`
   (S ID reserved with `pk next-id S --reserve`; index kind "GitHub sync (<n> units)"; SHA column `–`). Start from the run's notes
   draft and complete WHAT/WHY/result/technologies. It holds the date, user/identity, SHAs,
   commit/PR URLs, Jira keys, what/why. Private repos: `🔒 private` in the title and in every
   pool line that names the repo.
2. **One journal entry per unit**, dated with the **commit date** (the last commit of the unit;
   for a PR, the merge date if merged that day), `@github:<owner>/<repo>`, tags (reuse the
   vocabulary: e.g. `#feature`, `#bugfix`, `#refactor`, `#docs`, `#tests`, `#review`), `link:`
   the PR or commit URL, `Original:` the PR title or commit subject(s) verbatim. Description:
   one normalised line in the pool language that includes the source tag, e.g. "Added refresh
   tokens to the auth API (PR #7, PAY-12) [S041]".
3. **Light promotion** (tag `[J####]`/`[S###]`):
   - technologies → `skills` (evidence: repo + J IDs);
   - the repository → a project in `other` (what it is, the person's role, period, stack;
     `🔒 private` when private);
   - notable features or measurable improvements ("build time −40%", "p95 latency 800→200 ms"
     — only when stated in the PR/commit/issue) → `achievements` + the experience file of the
     employer that owns the repo.
4. `pk github commit-run <run>` — only after the pool is written. (`--discard` drops a run
   without recording it.)
5. Changelog entry (one per sync), snapshot if skills changed, `pk lint`, `pk git-commit` if
   enabled. Report in 2–4 lines: units recorded per repo, noise dropped, promotions.

## 4. Natural-language windows

| User says | `--since` |
|---|---|
| "today" | `today` |
| "this week" | `week` (last 7 days) |
| "this month" | `month` |
| "since March 3" | `2026-03-03` |
| "update from GitHub" | (none: continue from the cursors) |

## 5. Scheduling (only if the user asks)

If the user wants it automatic ("every evening analyse my changes"), offer a scheduled task or
a loop (`/schedule` or `/loop`) that runs this flow with no `--since`. Never set one up
unasked.

## 6. Jira and other trackers

- Public tracker pages → fetch them (web fetch) and use title/description for WHY.
- Private trackers → only through a connector/MCP the user has already connected (e.g. an
  Atlassian connector). Never enter credentials, never ask for tokens.
- No access → store the key and URL in the source notes as "not read (no access)" and move on.
