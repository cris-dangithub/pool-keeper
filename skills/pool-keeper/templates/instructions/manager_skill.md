---
name: pool-keeper
description: >
  Manager of the knowledge pool about {{name}} (pointer file written by the pool-keeper plugin;
  the full skill is installed separately). Other agents and skills may add or correct facts
  about {{name}} only through pool-keeper's delegation mode, never by editing pool files.
  The pool has an explicit section for things the person was asked about and has never done.
---

# pool-keeper — manager of this knowledge pool

This file only describes the rules; the full skill is the `pool-keeper` plugin
(`references/delegation.md`).{{skill_line}}

## Updates by other agents or skills — {{delegation_word}}
- Updates allowed: **{{delegation_allowed}}**. Send a packet (new facts, corrections, things
  not done) to the pool-keeper skill in delegation mode; it writes it, without asking the
  person anything, and returns what it wrote.
- How facts are stored: every fact in the file of its topic (layout in `CLAUDE.md` /
  `AGENTS.md`), with a source tag `[S###]`; the packet itself is archived verbatim as a new
  source in `{{layout.sources}}`. Search first: same fact → only a new source tag; more
  detail → the existing point is enriched in place; contradiction → both values kept and
  marked `{{m.conflict}}`. Nothing is ever deleted; original sentences are kept verbatim.
- Corrections confirmed by the person replace the old value, which stays as history marked
  "{{m.do_not_use}}".
- Things asked about and never done: **only** in `{{layout.open_questions}}` →
  "{{t.h_not_done}}". {{t.not_done_format}}
- Commits: {{git_line}}
