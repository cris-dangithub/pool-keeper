# Setup (first use, or a pool for another person)

Run when `pk find` says `NO_POOL`, or the user asks for a pool for someone new. Ask **one
question at a time** and wait for the answer. Keep anything the user already sent (files,
facts) and process it right after the setup.

## 0. Environment

`pk doctor`. Only Python 3.9+ is essential. `gh` is needed for GitHub ingestion, `git` only for
pools with commits. Nothing to install otherwise.

## 1. Interface language — ask in English, alone

> Which language do you want me to use when I talk to you? (for example: English, Español,
> Bahasa Indonesia)

From the answer on, **everything** is in that language (store an ISO 639-1 code: `en`, `es`,
`id`...).

## 2. Person

> Whose knowledge pool is this? Full name, as it should appear.

If it is the user themself, say so in the pool README later ("the person" = the user).

## 3. Pool folder

> Where should I keep it? A new empty folder (e.g. `Documents/Knowledge Pool <Name>`), or the
> current folder if it is empty.

- New/empty folder → continue.
- **An existing knowledge pool** (numbered Markdown files, a sources index, open questions —
  e.g. one kept by an older person-specific skill) → **adopt it** (section "Adopting an existing
  pool" below): every file and name is kept, nothing is moved or rewritten.
- A folder of loose notes/documents that is not a pool → create the pool in a new folder and
  ingest those files as sources (they are archived and merged like any other file).

## 4. Pool language

> In which language should the pool files be written? (Original quotes always stay in their
> own language.)

Built-in layouts and headings: `en`, `es`, `id` (`pk init --layout <code>`). **Other
languages:** translate the names yourself, keeping keys and numeric prefixes:
1. Copy `SKILL_DIR/templates/layout/en.json` → translate every value except the prefixes and
   `CHANGELOG.md`/`README.md` (e.g. pt: `10_experiencia/`, `90_perguntas_abertas.md`).
2. Copy `SKILL_DIR/templates/strings/en.json` → translate the values (headings, marker words,
   weekdays). Keep the 🔒 and ⚠ symbols.
3. Write both into the scratch/temp folder and pass `--layout-json` and `--strings-json` to init.
   The strings are stored in `.pool-keeper/strings.json`.

## 5. Optional domains

> Besides your career, do you want the pool to keep any of these? (any, several or none)
> (a) preferences & values (b) goals (c) availability (notice, relocation, permits)
> (d) personal life

Map to `preferences_values`, `goals`, `availability`, `personal_life`. See
`references/domains.md`. They can be enabled later (`pk config set domains.goals=true`).

## 5b. GitHub (optional)

> Do you want me to read your GitHub work into the pool? If yes: your GitHub user(s), the
> organisations you work in, and every name or e-mail you commit with.

- `gh auth status` lists the logged-in accounts; `account` is the gh login whose token reads
  that owner (personal and work accounts are common).
- Add after init: `pk github add --owner <user> --owner <org>:org:<account> --identity <login>
  --identity <email> [--exclude "*/dotfiles"] [--since YYYY-MM-DD]`. Can be done any time later.
- If `gh` is missing, say it is optional and how to install it (`https://cli.github.com`).

## 6. Country (for web research)

> Which country are your studies and employers mostly in? I use it to look facts up in official
> sources (school registries, certificate issuers).

Store the ISO code and propose 1–3 official sources for that country (see
`references/web-research.md` — e.g. Indonesia: referensi.data.kemendikdasmen.go.id; Colombia:
the Ministry of Education's SNIES and RUES; Spain: RUCT). Pass each as `--official-source`.

## 7. Questions policy

Tell, don't ask, unless the user objects:

> I won't fill your chat with questions: gaps are written silently to the open questions file.
> I'll ask at most one thing per report, only for a conflict on an important fact or an
> ambiguous answer. Ask "what is still missing?" whenever you want the list.

If they want more or fewer: `--max-questions N` (0 = never ask after an ingest).

## 8. Write the pool

```
pk init --root "<folder>" --name "<Full Name>" --ui-language <code> --pool-language <code> \
   [--layout en|es|id | --layout-json <file> --strings-json <file>] \
   [--domains goals,availability] [--country CO --official-source <url> ...] \
   [--default-context <experience-slug>] [--git]
```

`init` writes `.pool-keeper/config.json`, every template file in the pool language, a marked
block `<!-- pool-keeper:start --> … <!-- pool-keeper:end -->` in the pool's `CLAUDE.md` and
`AGENTS.md` (existing content preserved: the pool is managed by pool-keeper, other skills update
it only through delegation, how to read it, the layout map), a pointer
`.pool-keeper/manager/SKILL.md` (so tools like cv-tailor detect the managing skill and its
"asked, never done" section), and registers the pool in `~/.pool-keeper/pools.json` (several
people = several entries). `--git` initialises a repository and later commits after each ingest
(never pushes).

Then `pk lint` (must be clean) and offer the **first ingest**:

> Ready. Send me anything about you — old CVs, certificates, contracts, notes — or just tell me.
> I'll archive it and fill the pool.

---

## Adopting an existing pool

For a pool that already exists (built by hand or by an older, person-specific skill). The goal
is that, once adopted, it behaves exactly as before: same files, same names, same language,
same habits (question budget, web research, journal), now driven by pool-keeper.

1. **Read it first**: its `README.md`, `CLAUDE.md`/`AGENTS.md`, the old skill if there is one
   (often a `skill/` folder inside the pool), the changelog and the open questions file. From
   them — not by asking — take: the person's name, the pool language, the interface language
   the person is answered in, the question budget, whether web research runs on its own, the
   country of studies/employers, the current position (journal default context), and whether
   it uses git. Ask only what none of them says.
2. **Preview**: `pk adopt --root "<pool>" --name "<Full Name>" --ui-language <code>
   --pool-language <code> [--legacy-skill-dir <old skill folder>] --dry-run`. It maps every
   existing file to a layout key (exact name, or the same name with another numeric prefix:
   `00_profil.md` ↔ `profile`), lists what will be created (usually only the snapshot and the
   stories file), what is left as is (`unmapped_kept_as_is`: folders outside the layout, kept
   untouched) and whether the "asked, never done" section exists. Several candidates for one
   key → `AMBIGUOUS_LAYOUT`: pass `--map key=path` for each.
3. **Back up** the folder (a zip next to it) and record the SHA-256 of every file, so you can
   prove afterwards that nothing changed except what adopt is meant to touch.
4. **Adopt** with the same options without `--dry-run`, plus the config the old rules imply
   (`--max-questions`, `--web-research`, `--country`, `--official-source`, `--default-context`,
   `--domains`, `--git`). It writes `.pool-keeper/`, appends the marked block to `CLAUDE.md` /
   `AGENTS.md` (existing text kept), registers the pool and creates only missing files.
   `--legacy-skill-dir` moves the old skill into `.pool-keeper/legacy/<name>/` with its
   `SKILL.md` renamed `SKILL.legacy.md`, so tools that look for the pool's managing skill
   (cv-tailor) find only pool-keeper.
5. **Fill the new files** from existing content only: the snapshot (`references/ingest.md` §5)
   and, in the stories file, STAR stories built from situations already in the pool, every line
   with its source tags (no new facts, inferences labelled).
6. **Point everything at pool-keeper**: in the pool's own `CLAUDE.md`/`README.md`, replace lines
   that name the old skill (keep everything else: the session language rule, notes about the
   journal); uninstall the old skill from the user's skills folder by **moving** it to a backup
   folder (never delete); tell tools that read the pool to re-scan it (cv-tailor:
   `cvt workspace scan-pool --save` and its manager probe, in its workspace).
7. `pk lint` (0 errors; warnings inherited from the old pool are reported, not "fixed" by
   rewriting files) and `pk status`. Compare the hashes: only `CLAUDE.md` and `README.md` may
   differ; everything else is new (`.pool-keeper/`, `AGENTS.md`, snapshot, stories) or moved
   (the legacy skill).

## Changing the configuration

| Change | Command |
|---|---|
| interface language | `pk config set ui_language=es` (rewrites the instruction blocks) |
| enable a domain | `pk config set domains.goals=true` (creates its file) |
| commits on/off | `pk config set git=true` |
| question budget | `pk config set questions.max_per_report=0` |
| web research | `pk config set web_research=ask` (`auto` / `ask` / `off`) |
| default journal context | `pk config set journal.default_context=2025_acme` |
| add GitHub accounts | `pk github add ...` |
| delegation off | `pk config set delegation.allowed=false` |
| another person | run this setup again in another folder; `pk registry list` shows all pools |

Changing `pool_language` of an existing pool does not rename files: say so, and only change it
if the user accepts that existing files keep their names (new headings use the new language).
After an upgrade of pool-keeper, `pk refresh` adds new layout keys and missing files.
