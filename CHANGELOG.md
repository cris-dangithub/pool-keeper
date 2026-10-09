# Changelog

## 0.1.0 — 2026-10-09

First public version: a generic, multi-person version of a person-specific knowledge-pool skill.

- **Setup** one question at a time: interface language, person, pool folder, pool language,
  optional domains (preferences & values, goals, availability, personal life), GitHub accounts,
  country (official sources for web research), question policy.
- **Pool layout in the pool's language** (`en`, `es`, `id` built in; any other language by
  passing a translated layout and headings). Scripts only use canonical keys.
- **Ingest**: archive with SHA-256 duplicate check, next IDs, text extraction from .docx
  (tables, headers, footers, links) with the standard library; every fact sourced, merged
  without duplicates and without deleting anything; conflicts, inferences, "do not use"
  history, time-dependent facts ("as of"), `🔒 private` marker.
- **Activity journal**: monthly files, global J#### IDs, tag vocabulary with aliases, light
  promotion to skills/achievements/experience, deterministic statistics (`pk journal stats`).
- **GitHub ingestion**: read-only `gh`, several accounts/identities, noise filter, work units
  (PR / branch / same-day series), Jira keys and tracker URLs, per-repo cursors advanced only
  after the pool is written (`commit-run`), batches for a first full-history sync.
- **Writing style**: observed patterns, active rules (G###), correction log (K###).
- **Delegation mode** for other skills (cv-tailor): packet archived verbatim, positives /
  corrections / negatives ("asked, never done") / rejected, structured return.
- **Readers**: a marked block in the pool's `CLAUDE.md` and `AGENTS.md` and a manager pointer
  `.pool-keeper/manager/SKILL.md` tell any agent how to read the pool and how to update it.
- `pk lint` (orphan tags, duplicate/out-of-order IDs, journal format, layout) and `pk status`.
- Pool discovery: `POOL_KEEPER_POOL` → parent folders → registry of pools
  (`~/.pool-keeper/pools.json`), asking whose pool when ambiguous.
