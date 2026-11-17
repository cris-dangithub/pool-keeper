# Questions: when to ask, and how to write them

## When to ask (important)

The person does not want to be asked things all the time. The default is: **don't ask.**

- After processing files or answers: **no questions** in chat. Every new gap is written
  silently to `<open_questions>`.
- **Exception — at most `questions.max_per_report` (default 1) per report:** (a) a conflict
  between sources on an important fact (job title, employment dates, achievement numbers, grade
  average, organisation name), or (b) an answer from the person so ambiguous it cannot be
  recorded correctly. Ordinary gaps (a missing number, a small detail) are NOT a reason to ask.
- **Writing-pattern question (always, outside the budget above):** for each new source that
  contains **text the person wrote themself** (CV, cover letter, SOP, job description, e-mail,
  report, a long message), add one line: "✍ Extract writing patterns from this source?
  (yes/no)". Not for certificates, diplomas, tables/schedules/spreadsheets of numbers, web
  research, short chat answers, or code, nor for a source whose text is identical to one whose
  patterns were already extracted (say "same text as S0xx" instead). If they say yes, run
  `references/writing-style.md` for that source.
- **Style corrections:** one question is allowed if it is unclear which text is the AI's and
  which is the expected one, or if a new rule contradicts an existing one.
- **The question list** is shown only when the person asks for status ("what is still
  missing?", "any questions?") — at most 3, and say that answering is optional.
- **Never repeat** a question that was answered or that the person skipped, including anything
  in "asked, never done" (don't turn it into a new gap; it must also never be claimed).
- **Journal and delegation modes ask nothing.**
- **Several pools, unclear whose:** asking "whose pool?" is always allowed (it is not a content
  question).

## How to write a question

Applies to every question to the person (when asking is allowed) and to every item written in
`<open_questions>`:

- **One thing per question.** Never merge 2–3 questions into one item.
- **State the unit and the answer format.** E.g. "On average, how many days from opening a
  vacancy to the candidate's first day? (answer in days, e.g. '30 days')".
- **Offer choices or examples when possible.** E.g. "The property on the island was: (a) a
  villa (b) a resort (c) a hotel (d) other?".
- **For lists, ask for pairs.** E.g. "One per line: position – number of people (e.g.
  'waiter – 5')".
- **Say that an estimate is fine.** E.g. "a rough estimate is enough, e.g. ±100".
- **Briefly say why it matters** when it is not obvious (≤1 sentence, e.g. "this number makes
  the recruitment point much stronger in a CV").
- **Prioritise** questions that yield numbers, results or scope.
- **If an answer is ambiguous:** store it as is, in the source and in the pool (marked "meaning
  unclear"), **don't guess**, and ask **one** clarification question that quotes the answer and
  offers the interpretations as options. E.g. "You wrote '104, 88, 6, 21, 16'. Is that (a) the
  days it took to fill 5 positions, (b) applicants per channel, or (c) something else? If (a)
  or (b), write the pairs, e.g. 'waiter – 104'."
- Write the question in `pool_language` in the file; ask it in `ui_language` in chat.
