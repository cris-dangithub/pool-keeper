# Activity journal

The person tells what they did ("today I…", "yesterday…", "on Monday…", "hoy hice…", "hari ini
aku…"); every activity becomes a journal entry. Over time the journal answers "how many times
did I…", "what did I do in March", and gives dated evidence for skills. GitHub work lands here
too (`references/github.md`).

## 1. Files

- `<journal>/YYYY-MM.md` — one file per month, day headings in date order.
- `<journal>/README.md` (`journal_readme`) — the format and the **tag vocabulary** table:
  `| #tag | definition | aliases |`. Aliases are other words for the same tag (any language);
  scripts resolve them.

## 2. Entry format

```
## 2026-10-09 (Friday)
- **J0001** · <normalised description in the pool language> · #tag1 #tag2 · @<context> · qty: 3 <unit>
  - Original: "<verbatim text, in the language it was told>"
  - Promoted: <file key> (only if promoted)
```

- **IDs** are global and incremental: J0001, J0002… across all months. `pk journal add` takes
  the number and writes the entry under a pool lock (two sessions never share a J number).
- **Dates are absolute.** Resolve "today", "yesterday", "last Monday" against today's date.
  When the activity is told on a later day, add `rec: <date it was told>` (`--recorded`). A date
  that cannot be worked out at all → today's date and "(estimated date)" in the description.
- **`@context`**: the slug of the experience file (`2025_acme`), `@personal`, or
  `@github:<owner>/<repo>`. Default: the current position, or `journal.default_context`. When
  the context is really unclear → `@?` plus "(context unclear)"; don't ask.
- **`qty:`** for countable things (`qty: 3 interviews`, `qty: 2 h`) — only when the person gave
  the number; never guess one.
- The weekday in the heading and the tokens are in the pool language (`pk strings` →
  `journal_tokens`: e.g. Indonesian `jumlah:`, `dicatat`, `Asli:`, `Dipromosikan:`; Spanish
  `cantidad:`, `registrado:`, `Promovido:`). `pk journal add` writes them; scripts read the tokens
  of every built-in language, so a pool that changes language keeps parsing.
- **Third-party names are anonymised**: "interviewed a candidate for the waiter role", not the
  candidate's name; "met the operations manager", not their name.

Write entries with the helper — it assigns the ID, creates the month file and day heading, keeps
days ordered, and resolves tag aliases:

```
pk journal add --date 2026-10-09 --desc "Interviewed candidates for the waiter role" \
  --original "hoy entrevisté a 3 candidatos para mesero" --tag interview --context 2025_acme \
  --qty 3 --unit interviews [--recorded 2026-10-11] [--link URL] [--promoted achievements]
```

It reports `unknown_tags`: add them to the vocabulary (`pk journal tags --add <tag>
--definition "<one line>" --aliases a,b`) or use the existing tag instead.

## 3. Rules

1. **Split into atomic activities.** "I interviewed 3 people, fixed the roster and went to the
   gym" = 3 entries. The **same action repeated** = one entry with `qty:`.
2. **Reuse tags before creating new ones** (`pk journal tags` lists them with usage counts).
   Tags are short, lowercase, in the pool language or English; one concept = one tag; synonyms
   go into aliases.
3. **Original text is kept verbatim** (`Original:`), whatever language it was told in. The
   description is normalised, in `pool_language`, without embellishment.
4. **Light promotion** — only when the activity is new information for the rest of the pool;
   tag the promoted point with `[J####]` and add `Promoted: <key>` to the entry:
   - a new tool or skill → `skills` (evidence: "used in <context> [J0042]") and the experience
     file's "tools" section;
   - a measurable result, an award, praise/feedback → `achievements` (+ the experience file);
   - a new responsibility → the experience file's duties;
   - a job or role change → this is a normal ingest (`references/ingest.md`): archive the
     message as a chat-notes source too, update profile/experience/timeline.
   Routine (meetings, usual tasks) **stays in the journal only**.
5. **No questions** — never the ✍ writing-pattern question either. Gaps (e.g. which position an
   activity belongs to, a missing number) go silently to `<open_questions>`. Single exception: a
   note that truly cannot be understood → store it as it is, marked "meaning unclear", and ask
   **one** clarification question.
6. **Changelog only when something was promoted** (short entry: `## <date> — <cl_journal_promotion>
   J0004–J0006`). Pure journal writes don't touch the changelog or the snapshot (unless a
   promotion changes what the snapshot shows).
7. **Sources index**: the journal is not archived per note; the index carries one standing note
   that J#### entries are sources (written at init).
8. **Report: 1–2 lines** in `ui_language`, e.g. `📓 J0107–J0109 recorded (#interview ×3,
   #roster). Promoted: Excel pivot tables → skills.`

## 4. Corrections to the journal

If the person corrects an entry ("it was 4 interviews, not 3"), edit the entry's description/qty
in place and keep the original line; append the correction as a second original:
`  - Original: "<correction text, verbatim>" (correction <date>)`. Never delete entries; an
entry that was entirely wrong gets `do not use` in its description.

## 5. Analysis mode (questions about recorded activity)

Always deterministic, always citing IDs. Use `pk journal stats`:

| Question | Command |
|---|---|
| "How many interviews did I do this year?" | `pk journal stats --tag interview --from 2026-01-01` |
| "What did I do last week?" | `pk journal stats --from <mon> --to <sun> --list` |
| "Monthly summary of October" | `pk journal stats --from 2026-10-01 --to 2026-10-31 --group-by tag` (+ `--list`) |
| "Weekly breakdown" | `... --group-by week` |
| "Everything at Acme" / "all GitHub work" | `--context 2025_acme` / `--context github:` |
| "Evidence that I know Excel" | `pk journal stats --text excel --list` and `--tag excel` |

- Phrase counts as **"at least N recorded"** — the journal only knows what was told.
- Quantities are summed per unit (`qty_by_unit`); entries without `qty` count as one each.
- Always list the J IDs you counted (or the first/last ones for long lists).
- Read the entries themselves before summarising content; don't infer beyond them.

**On request only** (never automatically):
- a derived monthly summary: a `## Summary` section at the end of `<journal>/YYYY-MM.md`
  ("derived from J0101–J0140, generated <date>"), regenerated when asked again;
- skill evidence lines: in `skills`, add "— journal: at least N times (J…, J…) as of <date>"
  to the matching skill.
