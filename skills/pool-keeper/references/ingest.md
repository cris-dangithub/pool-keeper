# Ingest: archive, extract everything, merge, report

Goal: the most complete pool possible, so another agent can later produce anything about the
person (a tailored CV, a cover letter, an interview answer). **Completeness beats brevity** in
the pool files. Don't summarise until detail is lost; don't drop things as "not relevant".

Paths below are layout keys (`<sources>`, `<sources_index>`, `<experience>`...): resolve them
from `layout` in the config. Markers and headings: `pk strings`.

## 1. Read first

`README.md`, `<sources_index>`, `<open_questions>` and the category files you will touch. One or
many files can come in one message: process them all, then write **one** report.

## 2. Archive every file

For each attached file:

1. `pk hash <file>` → full SHA-256, 12-character prefix and `duplicate_of`. If it is a
   duplicate: say so, don't archive it again (but still check whether anything in it was missed).
2. `pk next-id S` → the new ID (S001, S002...). Several files: `pk next-id S --count N`.
3. Create `<sources>/<YYYY-MM-DD>_<file name without extension>/` and copy the original there
   (keep the file name). If the copy fails because the file is open in another program, retry
   once, then ask the user to close it.
4. Extract the text to `extracted.txt` in the same folder:
   - `.docx` → `pk extract <file> -o <folder>/extracted.txt` (body, tables, headers, footers,
     footnotes, hyperlinks).
   - `.pdf` → read it with your file reader (page ranges for long files) or a PDF skill;
     scanned PDF/photo → read the pages as images and transcribe.
   - `.pptx` / `.xlsx` → a pptx/xlsx skill; keep tables as tables.
   - images (certificates, screenshots, photos) → read the image; write a transcription plus a
     short description.
   - `.zip` → unzip into `<folder>/unzipped/` and treat each file as part of the same source
     (one ID), with a combined `extracted.txt` (one section per file).
   - text pasted in chat / spoken answers → `<sources>/<date>_chat-notes-<topic>/<source_notes>`
     with the content **verbatim** (question + answer), an ID like any file.
5. Add a row to the `<sources_index>` table: ID, date added, folder, kind, content summary,
   first 12 characters of the SHA-256 (`–` for chat notes / web research). Add a "notes per
   source" entry: where the file came from, what the document was made for, its date if known
   (inference allowed, labelled).

**Special kinds of source**
- **Work evidence** — documents the person made at work (schedules, SOPs, job descriptions,
  training material, reports, templates, code). Kind in the index: "Work evidence: …". In the
  related experience file add/fill the "work evidence" section pointing to the source folder,
  and extract measurable facts (people, units, shifts, positions, rules) as achievement points.
- **Sensitive data and third parties** — never copy into the pool or into `extracted.txt`
  anything listed in `sensitive.never_copy` (ID numbers, bank accounts, other people's names
  and contacts in work documents: keep only structure and counts). Note in the source notes that
  it was left out on purpose and exists only in the original file. Names and contacts of
  **references** that the person listed in their own CV may be kept in `<other>`.
- **Journal entries** (`J####`) are sources too, but live in `<journal>`, not in `<sources>`
  (`references/journal.md`).
- **GitHub syncs** → one source per repo per sync (`references/github.md`).
- **Delegated packets** → `references/delegation.md`.

## 3. Extract EVERYTHING

Read `extracted.txt` line by line. Record every fact, including small ones: organisation names
and descriptions, job titles, dates (month + year), locations, managers, team size, duties,
tools/software, numbers (counts, %, money, durations), results, awards, training names,
certificate issuers and numbers, grades, references, languages, hobbies, preferences, and
well-written phrases and sentences.

Non-CV documents are valuable too: an old job description → official duties; a reference letter
→ third-party quotes; a contract → exact dates and employment status; work evidence → real
numbers and scope; job offers the person applied to → career targets/preferences (to
`<other>` or `<goals>`/`<preferences_values>` if enabled — **never** as experience).

## 3b. Web research

When an organisation, school or certificate appears, or an official name is uncertain, follow
`references/web-research.md` (respecting `web_research` in the config).

## 4. Merge into the pool

Routing table and merge rules: `references/merge-rules.md`. In short: search first; same → add
the source tag; completes → enrich in place; new → add; contradicts → keep both + conflict.
Original sentences go verbatim into "Original text [S###]" sections of the matching file.
Every new gap → a question in `<open_questions>` written by `references/questions.md`, **not**
asked in chat.

## 5. Record and report

1. **`<changelog>`** (full detail): a new entry **above** the previous one:
   `## <date> — Ingest S0xx (<short kind>)`, then separate lists **New**, **Enriched** (write
   the point before → after), **Conflicts** (new / resolved / unclear).
2. **Snapshot**: regenerate `<snapshot>` from the other files (current role, location, top 5–8
   skills, languages with level, availability, goals; "updated" = today, "last sources" = the IDs
   just ingested). It is derived: no new facts there, keep it to one screen.
3. `pk lint` — fix every error you introduced (orphan tags, duplicate IDs...).
4. If `git` is true: `pk git-commit -m "Ingest S0xx: <short>"` (never push).
5. **Chat report — short, ~6 lines, in `ui_language`**, with this template. The before → after
   detail is NOT repeated in chat (it is in the changelog). **No list of questions.**

```
✅ Archived: S0xx (short kind)[, S0yy (kind)]
📊 Result: X new points · Y enriched · Z new conflicts
⭐ Highlights:
- <most important change, one line>
- <second — optional>
⚠ To check: <only for an important conflict / ambiguous answer — 1 question; drop the line otherwise>
✍ Extract writing patterns from this source? (yes/no) — <only if the source contains text the person wrote>
📁 Detail: CHANGELOG.md
🔎 Web sources: <URL, URL> — only if there was web research
```

Exception: if you took an important decision on the person's behalf (sensitive data not copied,
an old value marked "do not use"), say it in one extra line.

## 6. Answers written in the open questions file

When the user says "process my answers" (or you notice answers under questions):
1. Read `<open_questions>`; find the text written under questions that is not part of the
   original question list.
2. Save a verbatim copy as a new source `<sources>/<date>_answers-open-questions/<source_notes>`
   (next S ID, kind "Answers written in the open questions file").
3. Process it like any other information (steps 3–5): fill the category files, move each
   answered question to the "answered" section with its source tag, and remove the raw answer
   text from under the question.

Answers given in chat are archived the same way (`<date>_chat-notes-<topic>`), and also count
as the person's direct confirmation (they resolve conflicts).
