---
name: pool-keeper
description: >
  Builds and maintains a knowledge pool about one person (or several, one pool each): archives
  every source file, extracts ALL facts and merges them without duplicates and without ever
  deleting anything, tracks conflicts and open questions, learns the person's writing style and
  style corrections, keeps a daily activity journal and ingests GitHub history, so any agent can
  read the pool and know almost everything relevant about the person. Use it whenever the user
  attaches any file about their career or life (CV, certificate, diploma, contract, payslip,
  reference letter, job description, schedule, SOP, report, notes, screenshot, photo, PDF, docx,
  xlsx, pptx, zip) or tells new facts about their work, studies, achievements, preferences or
  goals; says "add to my knowledge pool / knowledge base", "añade a la base de conocimiento",
  "tambahkan ke knowledge pool"; answers open questions (in chat or by writing in the open
  questions file: "process my answers", "procesa mis respuestas", "proses jawaban saya");
  tells what they did today or on a past day for the journal ("today I...", "yesterday I...",
  "hoy hice...", "ayer...", "nota del día", "hari ini aku...", "kemarin aku...", "catatan hari
  ini", "journal"); asks about recorded activity ("how many times did I...", "what did I do last
  week/month", "weekly summary", "evidence for skill X", "¿cuántas veces...?", "resumen de la
  semana", "berapa kali aku...", "ringkasan minggu ini"); asks to analyse GitHub work ("analyze
  my changes today / this week / since <date>", "update the pool from GitHub", "analiza mis
  cambios", "analisis perubahanku"); asks to search the web about an employer, school or
  certificate; asks to extract writing patterns or pastes a style correction (AI text + the
  version they wanted: "it should be like this", "debería ser así", "harusnya begini"); asks
  "what can you do?", "what next?", "what is still missing?", "¿qué sigue?", "apa yang masih
  kurang?"; wants to set up a new pool ("set up pool-keeper", "create my knowledge pool").
  Also when another skill (e.g. cv-tailor) hands over a packet of facts, corrections or "not
  done" answers to write into the pool (delegation mode, no interaction). Never invents facts.
  Not a CV generator.
version: 0.1.0
---

# pool-keeper

A **pool** is a folder of Markdown files about one person, with an archive of every source and
a config at `<pool>/.pool-keeper/config.json`. Completeness matters more than brevity **in the
pool files** (never in chat reports): never summarise until detail is lost, never filter for
"relevance" — relevance is decided later, by whoever reads the pool.

`SKILL_DIR` is the folder containing this file. Every helper is run through the launcher
(standard library only, nothing to install):

```
python "<SKILL_DIR>/pk.py" <command> [args]       # python3 on macOS/Linux if python is missing
```

Written below as `pk <command>`. Add `--pool <name|path>` when several pools exist.

## Step 0 — every time

1. `pk find`
   - `NO_POOL` → run the **setup** (`references/setup.md`) before anything else; keep whatever
     the user sent and process it right after.
   - `AMBIGUOUS` → several people have pools: ask **whose** pool this is (one question, list the
     names), then use `--pool <name>` for the whole session.
   - a path → that is POOL. Read `.pool-keeper/config.json`.
2. **Speak `ui_language`** for the whole session, whatever language the user writes in, unless
   they explicitly ask for another language in that message (and only as far as they ask).
   Pool files are written in `pool_language`; original quotes stay in their own language
   (`keep_original_language`).
3. Never use fixed file names: every path comes from `layout` in the config (canonical keys:
   profile, experience, journal, open_questions, sources_index...). `pk strings` prints the
   marker words and section headings to use in the pool language.
4. Before writing, read `README.md`, the sources index, the open questions file and the files you
   are about to change.

## Step 1 — what does the user want?

| The user... | Do | Read |
|---|---|---|
| attaches files, pastes text, tells facts, "add to my pool" | archive → extract everything → merge → report | `references/ingest.md`, `references/merge-rules.md` |
| answers open questions (chat, or written in the open questions file) | store the answer as a source, merge, move questions to "answered" | `references/ingest.md` §6 |
| tells what they did (today / a past day) | journal entries, light promotion, 1–2 line report | `references/journal.md` |
| asks how often / when / what they did, a weekly or monthly summary, evidence for a skill | `pk journal stats`, cite J IDs | `references/journal.md` §5 |
| "analyze my changes today / this week", "update from GitHub" | GitHub sync → sources + journal + promotion | `references/github.md` |
| asks to search the web about an employer, school, certificate | public research, stored as a source | `references/web-research.md` |
| says "yes" to extracting writing patterns, or asks for it | pattern extraction (6a) | `references/writing-style.md` |
| pastes AI text + the version they wanted | style correction (6b) | `references/corrections.md` |
| another skill hands over a packet (cv-tailor...) | delegation mode, no questions | `references/delegation.md` |
| "what can you do?", "what next?", "what is missing?", status | guide / status | `references/status.md` |
| any agent asks how to read the pool, or a question about the person | reader rules | `references/reader.md` |
| wants to enable preferences, goals, availability or personal life | optional domains | `references/domains.md` |
| first time, no pool yet, or a second person | setup | `references/setup.md` |
| wants to change settings (language, domains, git, GitHub accounts) | `pk config set ...` / `pk github add` | `references/setup.md` ("Changing the configuration") |

When to ask questions, and how to write them: `references/questions.md` (default: **don't ask**).

## Rules that are never broken

1. **No invented facts.** Write roles as they really were ("welcomed and guided the
   influencers", not "managed the influencer campaign"). Inferences only with the inference
   marker. Never "improve" a number.
2. **Nothing is ever deleted.** Enrich points in place; contradicting values are both kept and
   marked as a conflict; superseded values stay as history marked "do not use"; "Original text
   [S###]" sections are append-only. The one exception: the person explicitly asks to remove
   something (then remove it, and record in the changelog *that* something was removed at their
   request, without repeating it).
3. **Original wording is kept verbatim**, in its language, in the original-text sections and in
   the archived source (`extracted.txt` / notes).
4. **Every fact has a source tag**: `[S###]` (sources index) or `[J####]` (journal entry).
5. **Search before adding** (Grep across the whole pool): same → only a new tag; more detail →
   edit the existing point; truly new → new point (`references/merge-rules.md`).
6. **Sensitive data** (`sensitive.never_copy` in the config: ID numbers, bank data, passwords,
   third parties' names and contacts in work documents...) is never copied into the pool or into
   `extracted.txt`; say in the source notes that it was left out on purpose. Third-party names
   in the journal are anonymised (role, not name).
7. **Questions are minimal**: after an ingest, no question list; gaps go silently to the open
   questions file; at most `questions.max_per_report` question (only a conflict on an important
   fact or an ambiguous answer). Never ask again what was answered, skipped, or listed under
   "asked, never done".
8. **Write only inside POOL, only through this skill**, with the smallest possible edits (never
   rewrite a whole file, never reorder). Never touch `SKILL_DIR`. Other skills update the pool
   only through delegation mode.
9. **Private stays private**: anything marked 🔒 (private repositories, personal details the
   person flagged) is never shown to third parties or written into public-facing text.
10. **Web research only about public organisations, schools, certificates and terms**, never
    personal information about the person or anyone else.
11. **GitHub is read-only** (GET requests); never clone, push, comment. Never enter credentials
    anywhere (trackers, Jira, websites).
12. After every ingest: changelog entry, regenerate the snapshot (`references/ingest.md` §5),
    `pk lint`, and `pk git-commit` if `git` is true (never push).
