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
- An existing folder with notes or an old pool → **adopting** existing content is planned for
  pool-keeper 0.2. For now: create the pool in a new folder and ingest the old files as sources
  (they are archived and merged like any other file). `pk init --allow-existing` only adds the
  missing structure without touching existing files; use it only if the user insists and say
  that old files are not yet indexed.

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
