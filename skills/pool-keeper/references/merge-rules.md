# Merge rules

How a fact gets into the pool. Paths are layout keys; marker words come from `pk strings`
(shown here in English: `⚠ conflict`, `(needs confirmation)`, `(inference)`, `do not use`,
`🔒 private`, `as of`).

## 1. Where each kind of information goes

| Information | Key |
|---|---|
| Identity, contact, location, career targets, timeline | `profile` |
| A position (job, internship, freelance, own business) | `experience` → `<start-year>_<organisation-slug>.md` (new file from `pk template experience`; add a row to the timeline in `profile`) |
| Education, courses, training | `education` |
| Skills + evidence | `skills` |
| Certificates, languages | `certifications_languages` |
| Achievements and numbers | `achievements` (next `pk next-id A`) |
| Headlines, summaries, positioning, CV structure/strategy | `narrative_positioning` (keep every summary variant verbatim) |
| Concrete situations usable as STAR stories | `stories` |
| Writing patterns, style rules, style corrections | `writing_style` (`references/writing-style.md`, `references/corrections.md`) |
| Projects, organisations, volunteering, references, interests, anything else | `other` |
| Work preferences, values, deal-breakers | `preferences_values` if enabled, else `other` |
| Goals, target roles/countries, learning goals | `goals` if enabled, else `profile` → career targets |
| Availability, notice, relocation, permits, work mode | `availability` if enabled, else `other` |
| Personal context the person chose to share | `personal_life` if enabled, else **ask once** whether to enable it; don't store it elsewhere |
| New keywords | `keywords` (keyword → where the evidence is) |
| Daily activity | `journal` (`references/journal.md`) |
| Gaps, conflicts, asked-never-done | `open_questions` |

## 2. Search before adding

For every fact, search (Grep) the **whole pool** for a point about the same thing: same
organisation, same duty, same number or topic. Then exactly one of:

1. **Identical** → don't add a point; only add the second source tag (`[S001][S004]`).
2. **Completes / clarifies** an existing point (adds a number, duration, tool name, scope,
   result) → **edit the existing point in place**, don't create a new one. Example:
   `Filled several roles under a tight deadline [S001]` + info from S005 →
   `Filled 7 roles in 2 months [S001][S005]`. Remove `(needs confirmation)` once answered.
   Update the same point wherever it is repeated (achievements, skills, the profile timeline).
3. **Really new** → add a new point.

## 3. Contradictions

Dates differ, titles differ, numbers differ (not merely more detailed): **don't pick one**. Keep
both in the same point, mark `⚠ conflict`, and add it to `open_questions` → "Conflicts between
sources". Resolved only by the person: a direct answer in chat, or a confirmed correction
forwarded by another skill (delegation). The losing value stays recorded as history:
`(S004 wrote 3.51 — do not use)`.

Ambiguous answers: store them as they are (marked "meaning unclear"), **never guess**, and ask
one clarification question (`references/questions.md`).

## 4. Nothing is lost

- Editing a point to make it clearer is fine; the original sentences of every source stay intact
  in "Original text [S###]" sections (heading in the pool language — `pk strings` → `h_original`).
  Those sections are **append-only**: never edited, never deleted.
- Copy original sentences verbatim, in their language (don't translate them unless
  `keep_original_language` is false). Explanations are written in `pool_language`.
- Chat answers are kept verbatim too: as the source file, and as a short "Original text
  [S0xx] (chat answer)" section where the fact landed.

## 5. Honesty

- Don't invent or embellish. Write the role as it really was. Inferences are allowed only when
  labelled `(inference)`; turn important inferences into confirmation questions.
- Unconfirmed numbers or claims → `(needs confirmation)`. Numbers the person said they are not
  sure about → keep them, marked "<person> is not sure — do not use until confirmed".
- A detail that answers an open question → write it in its category file, move the question to
  "answered" with the source tag, remove `(needs confirmation)` where it applied.

## 6. Time-dependent facts

Facts that change (current role, location, availability, salary expectations, language level,
targets, relocation plans) are written with their date: `Location: Valencia (as of 2026-10)
[S012]`. A newer value does not erase the older one: the older one stays as history
(`previously: Madrid, until 2026-06 [S003]`). The snapshot always shows the latest.

## 7. Visibility

`🔒 private` marks what must never reach third parties: private repository names, personal
details the person flagged, anything they asked to keep out of CVs. Put it right after the
point. Readers respect it (`references/reader.md`).

## 8. Gaps

Every gap you notice becomes a question in `open_questions` → "Information gaps" (grouped by
position/topic), written by the rules in `references/questions.md` — **without asking it in
chat**. Never re-add something that was answered, skipped, or is listed under "asked, never
done".

## 9. Minimal edits

Edit the smallest span possible; keep the file's existing order, headings and format; never
rewrite a whole file; never reorder IDs. New achievements get the next A ID even if the table
is not in order.
