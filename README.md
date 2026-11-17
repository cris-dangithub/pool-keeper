# pool-keeper

*[Leer en español](README.es.md)*

An agent skill (Claude Code and Codex) that builds and maintains a **knowledge pool about a
person**: every document archived, every fact extracted with its source, no duplicates, nothing
ever deleted. Any agent can read the pool and know almost everything relevant about the person —
to write a CV, prepare an interview, or just answer "what did I do last month?". It never
invents a fact.

```
you:    [attach an old CV, a certificate and a contract]  add to my pool
agent:  ✅ Archived: S014 (CV), S015 (certificate), S016 (contract)
        📊 Result: 23 new points · 6 enriched · 1 new conflict
        ⚠ To check: the contract says you started in March 2024, your CV says February. Which one?

you:    today I interviewed 3 candidates and fixed the roster
agent:  📓 J0107–J0108 recorded (#interview ×3, #roster).

you:    analyze my GitHub changes this week
agent:  GitHub: 4 work units in acme/api and acme/web (2 PRs merged, PAY-12, PAY-15);
        7 noise commits skipped. New skill evidence: Redis. Details in CHANGELOG.md.
```

## What it does

- **Archives every source** (CV, certificate, contract, SOP, schedule, screenshot, ZIP, chat
  answers) with a SHA-256 duplicate check, and **extracts all facts** into topic files:
  profile, experience (one file per position), education, skills with evidence, certifications
  and languages, an achievements bank, narrative and positioning, a STAR story bank, keywords.
- **Merges without duplicates and without deleting**: same fact → one more source tag; more
  detail → the point is enriched in place; contradiction → both values kept and flagged. The
  original sentences are always kept verbatim.
- **Keeps track of what is unknown**: gaps, conflicts between sources, things the person was
  asked about and has never done. It asks at most one question per report, never a list.
- **Activity journal**: tell it what you did, any day, in any language; ask later "how many
  times did I…?" and get an exact, sourced count.
- **GitHub history**: your commits and PRs (several accounts and identities), minus noise,
  grouped into work units with Jira keys, recorded once — a second pass never duplicates.
- **Learns how you write** (patterns from your own documents) and **learns from your
  corrections** (paste the AI's text and the version you wanted).
- **Optional domains**: preferences & values, goals, availability, personal life.
- **Works with other skills**: cv-tailor (and any skill that follows the same contract) can
  save what you confirm to it into your pool, through pool-keeper.
- **Speaks your language**: the conversation, the pool's file names and headings can be in
  different languages (English, Spanish and Indonesian built in; any other by translation).

## Install

Requirements: Python 3.9+ (standard library only — nothing to install). Optional: `gh` (GitHub
ingestion), `git` (pools that commit after each change).

**Claude Code, as a plugin**

```
/plugin marketplace add cris-dangithub/pool-keeper
/plugin install pool-keeper@pool-keeper
```

**Codex and/or Claude Code, from a clone**

```bash
git clone https://github.com/cris-dangithub/pool-keeper
cd pool-keeper
./install.sh            # Windows: .\install.ps1
```

It links `skills/pool-keeper` into `~/.codex/skills` and `~/.claude/skills` and runs
`pk doctor`. You can also copy `skills/pool-keeper` into a project's `.claude/skills/`.

## First use

Say "set up pool-keeper" (or just attach your CV). The setup asks, one at a time:

1. the language to talk to you in (asked in English);
2. whose pool it is;
3. where to keep it (a new folder);
4. the language of the pool's files;
5. optional domains (preferences, goals, availability, personal life) and, optionally, your
   GitHub accounts and the identities you commit with;
6. your country (to look facts up in official sources);
7. how many questions you want (default: at most one per report).

Then it writes the pool and offers the first ingest. From then on: attach files, tell things,
dictate your day, or ask "what is still missing?".

### Adopting an existing pool

Already have a knowledge pool (built by hand, or by an older skill written for one person)?
Say "adopt my pool" in its folder. pool-keeper reads its rules, previews how each file maps to
its layout (`pk adopt --dry-run`), backs it up, and takes it over **without moving or renaming
anything**: same files, same language, same habits. It only adds what is missing (a one-page
snapshot, a STAR story bank) and retires the old skill into `.pool-keeper/legacy/`.

## Your data

- **The pool is a plain folder of Markdown files that you own**, wherever you choose. Nothing is
  stored in this repository or sent anywhere. Several people = several pools; a small registry
  (`~/.pool-keeper/pools.json`) remembers where they are.
- Sensitive data (ID numbers, bank details, passwords, other people's names in your work
  documents) is never copied into the pool; it stays only in your original files.
- Anything marked `🔒 private` (e.g. private repositories) is for your own agents only and is
  never put in text for third parties.
- GitHub access is read-only and uses the accounts already logged into `gh`.

```
my-pool/
  .pool-keeper/config.json        # languages, layout, domains, GitHub sources
  CLAUDE.md, AGENTS.md            # how any agent should read and update the pool
  README.md  CHANGELOG.md
  00_snapshot.md  01_profile.md
  10_experience/2024_acme.md
  20_education.md  30_skills.md  40_certifications_languages.md  50_achievements.md
  55_journal/2026-10.md  55_journal/README.md
  60_narrative_positioning.md  62_stories.md  65_writing_style/  70_other.md
  75_… 78_… (optional domains)  80_keywords.md  90_open_questions.md
  sources/INDEX.md  sources/2026-10-09_cv/{original file, extracted.txt}
```

(File names follow the pool's language: `10_experiencia/`, `55_diario/`,
`90_preguntas_abiertas.md` in Spanish; `10_pengalaman/`, `55_jurnal_aktivitas/`,
`90_pertanyaan_terbuka.md` in Indonesian.)

## Repository layout

```
.claude-plugin/            plugin + marketplace manifests
skills/pool-keeper/        the skill (this is what agents load)
  SKILL.md                 entry point and the rules that are never broken
  references/              step-by-step guides loaded on demand (setup, ingest, merge rules,
                           questions, journal, github, delegation, reader, writing style...)
  scripts/                 pool, ids, extract, journal, github, lint, status, doctor
  templates/layout/        file names per language (en, es, id)
  templates/strings/       headings and marker words per language
  templates/pool/          the pool's file templates
  templates/instructions/  the CLAUDE.md / AGENTS.md block and the manager pointer
  pk.py                    launcher: `python pk.py <command>`
examples/sample-pool/      a small fictional pool (journal, GitHub source, conflict, not-done item)
tests/                     pytest suite (offline; GitHub through a JSON fixture)
```

## Development

```bash
python -m pip install pytest
python -m pytest tests -q
python skills/pool-keeper/pk.py doctor
python skills/pool-keeper/pk.py lint --pool examples/sample-pool
```

## License

MIT.
