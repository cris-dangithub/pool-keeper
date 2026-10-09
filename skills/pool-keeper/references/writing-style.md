# Writing patterns (6a) and the style rule format

Goal: texts that other skills write later (CVs, cover letters, e-mails) sound like **the
person's own "formal"**, not like generic AI formality. Everything lives in `<writing_style>`:

| Key | Contents |
|---|---|
| `writing_style_readme` | instructions for skills that use the rules (don't change unless the structure changes) |
| `writing_style_patterns` | patterns observed in documents the person wrote, per document type and dimension, with literal examples and `[S###]` tags |
| `writing_style_rules` | rules ready to follow (`G###`) |
| `writing_style_corrections` | every correction (`K###`) with its literal texts and the rules born from it (`references/corrections.md`) |

## 6a. Extract writing patterns

Only when the person answered "yes" to the ✍ question for a source, or asked for it.

1. Make sure the text was really written by the person (not a template, a certificate, or
   someone else's document). If unsure, record it as "maybe a template" with low weight.
2. Analyse by dimension:
   - document structure and order/titles of sections
   - opening verbs and tense
   - bullet length and shape (sentence pattern)
   - placement and format of numbers (%, counts, durations)
   - favourite vocabulary/phrases and recurring formulas
   - tone and level of formality
   - bilingual conventions (which language where, mixing)
   - punctuation and formatting (capitals, bold, separators, date dashes)
   - recurring mistakes/habits — **recorded, but never turned into rules to imitate** unless the
     person asks
3. Merge into `writing_style_patterns` with "search first": a known pattern → add the source tag
   and an example (and its strength); a new pattern → add it. Newer sources weigh more (write
   the weighting order of the sources at the top of the file).
4. Derive or strengthen rules in `writing_style_rules` (format below). Rules from patterns have
   `Origin: pattern [S###]`. Next ID: `pk next-id G`.
5. Changelog entry; in the chat report one line: "✍ Writing patterns: X new patterns, Y rules
   new/strengthened".

## Rule format (`writing_style_rules`)

Field names in the pool language (`pk strings` → `g_*`):

```
### G### — <short title>
- Scope: <CV-EN | Cover-letter-ES | SOP | Email | all>
- Rule: <clear imperative sentence>
- DO: "<literal example>"
- AVOID: "<literal example>"
- Origin: <pattern [S###][S###] | correction K###>
- Strength: <n> (number of sources/corrections supporting it)
- Status: active | replaced by G###
```

Priority when rules clash (written in the folder README for other skills): rules from
corrections (`Origin: K###`) > higher Strength > rules from patterns > examples in the patterns
file. Rules are never deleted: a losing rule gets `Status: replaced by G###`.
