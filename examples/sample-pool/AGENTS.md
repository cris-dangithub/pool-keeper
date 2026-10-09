<!-- pool-keeper:start -->
# Knowledge pool — Maren Okafor

This folder is a **knowledge pool** about Maren Okafor, managed by the **pool-keeper** skill
(config: `.pool-keeper/config.json`).

- Talk to the user in **English**. Pool files are written in **English**;
  quoted original text stays in its own language.
- To add anything (files, facts, answers to open questions, daily activities, GitHub work,
  writing-style corrections) use the `pool-keeper` skill. Do not edit pool files by hand.
- **Other skills** (e.g. cv-tailor) may add or correct facts about Maren Okafor, but **only through
  pool-keeper's delegation mode**: they hand over a packet and pool-keeper writes it. Delegation
  allowed: **yes**. Things the person was asked about and has never done go to
  `90_open_questions.md` → "Asked, never done".
- Commits: no — this pool does not use git commits.

## Reading this pool (any agent)
1. Start with `00_snapshot.md`, then `01_profile.md`, then the file for the topic
   (layout below). For "what did they do lately / how often", read `55_journal/`
   (or run `pk journal stats`).
2. Every fact carries a source tag: `[S###]` (index: `sources/INDEX.md`) or `[J####]`
   (activity journal). Cite the tags in your answer.
3. Say how sure you are: a sourced fact > `(inference)` > `(needs confirmation)`. For
   `⚠ conflict` give both values and say it is unresolved.
4. Never claim anything listed under "Asked, never done". Never use values marked
   "do not use". Items marked `🔒` are for the person's own use only: never show them to
   third parties (CVs, public text).
5. Facts that change over time carry "as of <date>": use the most recent, the older ones
   are history.

## Layout
| key | path |
|---|---|
| readme | `README.md` |
| snapshot | `00_snapshot.md` |
| profile | `01_profile.md` |
| experience | `10_experience/` |
| education | `20_education.md` |
| skills | `30_skills.md` |
| certifications_languages | `40_certifications_languages.md` |
| achievements | `50_achievements.md` |
| journal | `55_journal/` |
| journal_readme | `55_journal/README.md` |
| narrative_positioning | `60_narrative_positioning.md` |
| stories | `62_stories.md` |
| writing_style | `65_writing_style/` |
| writing_style_readme | `65_writing_style/README.md` |
| writing_style_patterns | `65_writing_style/01_observed_patterns.md` |
| writing_style_rules | `65_writing_style/02_active_rules.md` |
| writing_style_corrections | `65_writing_style/03_correction_log.md` |
| other | `70_other.md` |
| goals | `76_goals.md` |
| keywords | `80_keywords.md` |
| open_questions | `90_open_questions.md` |
| changelog | `CHANGELOG.md` |
| sources | `sources/` |
| sources_index | `sources/INDEX.md` |
| source_notes | `notes.md` |

If the skill is not auto-loaded, install the `pool-keeper` plugin (`/plugin install pool-keeper@pool-keeper`).
<!-- pool-keeper:end -->
