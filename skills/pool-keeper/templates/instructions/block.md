# Knowledge pool — {{name}}

This folder is a **knowledge pool** about {{name}}, managed by the **pool-keeper** skill
(config: `.pool-keeper/config.json`).

- Talk to the user in **{{ui_language}}**. Pool files are written in **{{pool_language}}**;
  quoted original text stays in its own language.
- To add anything (files, facts, answers to open questions, daily activities, GitHub work,
  writing-style corrections) use the `pool-keeper` skill. Do not edit pool files by hand.
- **Other skills** (e.g. cv-tailor) may add or correct facts about {{name}}, but **only through
  pool-keeper's delegation mode**: they hand over a packet and pool-keeper writes it. Delegation
  allowed: **{{delegation_allowed}}**. Things the person was asked about and has never done go to
  `{{layout.open_questions}}` → "{{t.h_not_done}}".
- Commits: {{git_line}}

## Reading this pool (any agent)
1. Start with `{{layout.snapshot}}`, then `{{layout.profile}}`, then the file for the topic
   (layout below). For "what did they do lately / how often", read `{{layout.journal}}`
   (or run `pk journal stats`).
2. Every fact carries a source tag: `[S###]` (index: `{{layout.sources_index}}`) or `[J####]`
   (activity journal). Cite the tags in your answer.
3. Say how sure you are: a sourced fact > `{{m.inference}}` > `{{m.confirm}}`. For
   `{{m.conflict}}` give both values and say it is unresolved.
4. Never claim anything listed under "{{t.h_not_done}}". Never use values marked
   "{{m.do_not_use}}". Items marked `🔒` are for the person's own use only: never show them to
   third parties (CVs, public text).
5. Facts that change over time carry "{{m.as_of}} <date>": use the most recent, the older ones
   are history.

## Layout
| key | path |
|---|---|
{{layout_table}}
{{skill_line}}
