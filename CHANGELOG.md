# Changelog

## 0.2.0 — 2026-11-17

Lessons from six weeks of a real pool kept by the person-specific skill that pool-keeper
generalises.

- **`pk adopt`**: bring an existing pool under pool-keeper without moving or renaming anything.
  Every file is mapped to a layout key (exact name, or the same name with another numeric
  prefix, e.g. `00_profil.md` → `profile`; `--map key=path` for the rest), the source-notes file
  name is detected (`catatan.md`), only missing files are created (usually the snapshot and the
  STAR stories), folders outside the layout are left as they are, and `--legacy-skill-dir`
  retires the old skill into `.pool-keeper/legacy/` (its `SKILL.md` renamed) so cv-tailor's
  manager probe finds a single manager. `--dry-run` previews the mapping. Documented in
  `references/setup.md` → "Adopting an existing pool".
- **ID reservation under a lock**: `pk next-id S --reserve <folder>` takes the number and writes
  a placeholder index row atomically; `pk journal add` takes the J number and writes the entry
  under the same lock (`.pool-keeper/ids.lock`). Two sessions ingesting into one pool at the same
  time used to get the same S number and had to renumber. `pk lint` warns about reservations
  never filled in; `references/ingest.md` §5b documents renumbering.
- **Forwarded sources**: an assistant in another session or project can forward what the person
  told it (delegation mode, "forwarded by" source kind; it does not resolve important conflicts
  without the person's own confirmation).
- **Journal tokens in the pool language** (`jumlah:` / `dicatat` / `Asli:` / `Dipromosikan:` in
  Indonesian, `cantidad:` / `registrado:` / `Promovido:` in Spanish); the scripts read the tokens
  of every built-in language. Unclear context `@?`, estimated dates, and one clarification
  question for a note that cannot be understood.
- **Pool-language labels** for source folders (`catatan-chat`, `riset-web`…), source kinds
  (`Bukti karya`…) and changelog sections (`Baru` / `Diperkaya` / `Konflik`…) in `pk strings`.

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
