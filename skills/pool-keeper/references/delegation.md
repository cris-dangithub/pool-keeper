# Delegation mode (another skill or session hands over a packet)

Used when another skill (usually through a subagent) sends a **packet** of questions it asked
the person and their answers, or fact corrections, to be written into the pool. There is no
conversation with the person: the calling skill reports to them.

**Forwarded by another agent or session** (not a skill): the person told something to an
assistant working elsewhere (another project folder, another chat) and that assistant passes it
on ("save this in her knowledge pool"). Same steps, with these differences: the source folder
is `<date>_<src_forwarded>-<topic>`, the kind is "`kind_forwarded` <session or assistant name>
(<what the person told>)", the packet is stored verbatim **as received** (say in the source
notes that it is the assistant's wording of what the person said, not the person's own words),
and its facts count like chat notes from the person — except that they do **not** resolve a
conflict on an important fact unless the packet quotes the person's own confirmation. The
return block goes to that assistant.

The pool advertises this in its `CLAUDE.md`/`AGENTS.md` block and in
`.pool-keeper/manager/SKILL.md`, so a manager probe (e.g. cv-tailor's) answers:

```json
{"skill": "pool-keeper", "can_update": true, "has_not_done_section": true,
 "not_done_location": "<open_questions> → <h_not_done heading>", "commits": <config git>}
```

If `delegation.allowed` is false: write nothing and return `rejected: delegation disabled`.

## Steps

1. **POOL**: use the path the caller gives; otherwise Step 0 of `SKILL.md`. Read the same files
   as for an ingest before writing.
2. **No interaction**: ask nothing (no ✍ question, no conflict question), no chat report
   template, skip writing-style steps. Unresolved conflicts → `⚠ conflict` + "Conflicts between
   sources", as usual.
3. **Source**: store the packet **verbatim** (its language, no translation) in
   `<sources>/<YYYY-MM-DD>_answers-<caller>-<application id>/<source_notes>`, S ID reserved with `pk next-id S --reserve`, kind
   "Answers via <caller> (application <id>, <company – role>)" in the index.
4. **Classify each answer** (the caller usually pre-labels them; check anyway):
   - **Positive** (a new fact) → normal merge (`references/merge-rules.md`): search first,
     then same / enriched / new.
   - **Correction** ("before A, now B, confirmed <date>") → counts as the person's direct answer:
     apply B; A stays recorded as history "do not use"; related conflicts move to "answered".
   - **Negative** ("has not / never done X") → **only** to `<open_questions>` → "asked, never
     done", format: `- [x] <thing> → never [S###] (asked via <caller>, application <id>)` (in
     the pool language — `pk strings` → `not_done_format`). Infer nothing else from it and
     change no other file.
   - **Reject (don't write)**: decisions about one application ("apply anyway", "don't mention it
     here"), CV format/content preferences, trivial answers ("yes, go on"), unanswered or pending
     questions. General career preferences (targets, relocation, salary) may go to `other` or
     the enabled domain file.
5. Questions in `<open_questions>` answered along the way → "answered" with the source tag.
6. **Write only inside POOL**, with minimal edits (no whole-file rewrites, no reordering).
   Never touch the skill folder. Commit only if `git` is true (`pk git-commit`), never push.
7. **Changelog**: a normal entry (New / Enriched / Conflicts) plus "Negatives recorded" and
   "Rejected" lines, with the application ID in the title. Regenerate the snapshot if affected;
   `pk lint`.
8. **Return to the caller** (not to the person), in the language the caller asked for (default:
   the packet's language):

```
source: S0xx — <sources>/<folder>/<source_notes>
files_touched: [<relative path>, …]
new: [<point> → <file>]
enriched: [<before> → <after> (<file>)]
corrections_applied: [<A> → <B> (<file>)]
negatives_recorded: [<thing>]
conflicts_open: [<thing>]
rejected: [<answer> — <reason>]
per_item: [<item> — written | already known | rejected (<reason>)]
```

`per_item` matches what cv-tailor's write-back expects ("written / already known / rejected
with the reason, and the files you changed").
