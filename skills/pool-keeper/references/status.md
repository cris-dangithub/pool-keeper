# Guide mode and status

All in `ui_language`, short.

## "What can you do?"

Explain briefly:
- **Archive any file** (CV, certificate, work document, photo, ZIP) and extract every fact into
  the pool, without duplicates and without deleting anything.
- **Activity journal**: tell me what you did today (or any day) and I record it; later ask "how
  many times did I…?" or "what did I do last month?".
- **GitHub**: "analyze my changes this week" turns your commits and PRs into dated evidence.
- **Process answers**, in chat or written in the open questions file.
- **Web research** on employers, schools and certificates (public information only).
- **Writing patterns**: learn how you write "formally", from documents you wrote, so other
  skills (e.g. a CV generator) write like you, not like generic AI.
- **Learn from corrections**: paste an AI text + the version you wanted; the style rules update
  automatically.
- **Status**: "what is still missing?".
- Other skills (e.g. cv-tailor) can save what you confirm to them into this pool.

## "How do I use it?" / "What next?" / the user looks lost

Explain this flow, then offer the most useful next step:
1. **Add material** — attach any file (including documents you made at work: schedules, SOPs,
   job descriptions, code) or tell me something, and say "add to the pool". One or many files.
2. **Read the short report** — about 6 lines on what went in. **No question list** unless there
   is a conflict or an ambiguous answer (max. 1). Full detail in `CHANGELOG.md`.
3. **Questions only if you want them** — gaps are recorded silently in the open questions file.
   Ask "what is still missing?" any time; answer in chat, or write in that file and say
   "process my answers".
4. **Daily**: tell me what you did; it goes to the journal in seconds.
5. **No obligation to answer.** The pool is already usable; questions that matter for a
   specific job offer will be asked when that CV is made.
The pool is raw material; tailored CVs are made later by another skill (e.g. cv-tailor).

## "What is still missing?" (status)

1. `pk status --json` → sources, positions, achievements, journal entries (and last 30 days),
   open questions vs answered, open conflicts, asked-never-done, style rules/corrections,
   GitHub sources and pending runs, snapshot staleness.
2. Judge whether the pool is enough for the person's target field (from `profile` / `goals`):
   which positions lack numbers, dates or context; whether writing patterns exist.
3. Show **at most 3** of the highest-value questions from the open questions file, written by
   `references/questions.md`, and say that answering is optional.
4. If the snapshot is stale or `pk lint` reports errors, fix that first (silently).
