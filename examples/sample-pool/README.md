# Knowledge pool — Maren Okafor

Complete knowledge base about this person: identity, work history, concrete duties, achievements, skills, education, certifications, daily activity, writing style and narrative material. It is **not a CV**: it is raw material, as complete as possible, that any agent can read to know almost everything relevant about the person.

## Ground rules
1. **Every fact has a source.** `[S001]` points to the sources index; `[J0001]` points to an entry of the activity journal.
2. **No duplicates, nothing lost.** Same information → only a new source tag. Information that completes an existing point → that point is enriched in place (the original sentences stay in the "Original text" sections). Contradicting information → both values are kept, marked as a conflict and listed in the open questions file until the person confirms.
3. **Original wording is kept.** Sentences from source documents are copied verbatim, in their language, into "Original text [S###]" sections, which are never edited or deleted.
4. **Facts vs. claims.** Unconfirmed numbers or results are marked; inferences are labelled; values that must not be used again stay as history.

## Markers
| Marker | Meaning |
|---|---|
| `⚠ conflict` | two sources disagree; both values kept; listed in the open questions file |
| `(needs confirmation)` | not confirmed yet |
| `(inference)` | deduced, not stated by a source |
| `do not use` | historical value or claim the person rejected; kept only as history |
| `🔒 private` | visible to the person's own agents only; never shown to third parties (private repos, private details) |
| `as of <YYYY-MM-DD>` | fact that changes over time; the date says when it was true (history is kept) |

## Structure
| File / folder | Contents |
|---|---|
| `00_snapshot.md` | One-page card (derived, regenerated after every ingest): current role, location, top skills, languages, availability, goals |
| `01_profile.md` | Identity, contact, location, career targets, timeline |
| `10_experience/` | One file per position (job, internship, freelance, own business): context, duties, results, tools, original text |
| `20_education.md` | Formal education, courses and training |
| `30_skills.md` | Skills, grouped, with evidence (where each was used) |
| `40_certifications_languages.md` | Certificates and languages |
| `50_achievements.md` | Achievement and numbers bank (A## IDs), across positions |
| `55_journal/` | Daily activity journal: one file per month, J#### entries, tag vocabulary in its README |
| `60_narrative_positioning.md` | Headlines, summaries and positioning used so far (every variant kept) |
| `62_stories.md` | STAR story bank (Situation, Task, Action, Result) for interviews and cover letters |
| `65_writing_style/` | How the person writes: observed patterns, active style rules (G###), correction log (K###) |
| `70_other.md` | Projects, organisations, volunteering, references, interests, anything else |
| `76_goals.md` | Short- and long-term goals, targets, learning goals (optional domain) |
| `80_keywords.md` | Keyword → evidence index (to match job offers) |
| `90_open_questions.md` | Information gaps, conflicts between sources, things asked and never done, answered questions |
| `CHANGELOG.md` | History of every change to the pool |
| `sources/` | Archive of every source + index: original files with extracted text, chat notes, web research, delegated answers, GitHub notes |

## How to add
Attach any file (CV, certificate, contract, reference letter, schedule, SOP, report, screenshot...) or tell the agent something, and say *"add to the knowledge pool"*. For daily activity, just tell what you did ("today I..."). For GitHub work: *"analyze my changes this week"*. The `pool-keeper` skill archives, extracts everything and merges it; the chat report is short, the full detail is in `CHANGELOG.md`.
