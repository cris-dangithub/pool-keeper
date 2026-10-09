# Activity journal

Daily activities told by the person, one file per month (`YYYY-MM.md`). Every entry is a source in itself: `[J####]` is valid wherever `[S###]` is. Routine stays here; only new tools, measurable results, new responsibilities or role changes are promoted to the other files (with the `[J####]` tag).

## Entry format
```
## 2026-10-09 (Friday)
- **J0001** · <normalised description, in the pool language> · #tag1 #tag2 · @<experience file slug | personal | github:owner/repo> · qty: 3 <unit>
  - Original: "<verbatim sentence, in its original language>"
  - Promoted: <file key, only if promoted>
```
- IDs are global and incremental (`pk next-id J`, or `pk journal add` assigns it).
- Dates are absolute; an activity told days later carries `rec: YYYY-MM-DD` (the day it was recorded).
- `@context` is the slug of an experience file, `@personal`, or `@github:owner/repo`.
- The same action repeated = one entry with `qty:`.
- Third-party names are anonymised (role, not name).
- The fixed tokens `qty:`, `rec:`, `link:`, `Original:` and `Promoted:` are the same in every language (scripts read them).

## Tag vocabulary
Reuse a tag before creating a new one. Aliases are other words that mean the same tag (searches and statistics resolve them).

| Tag | Definition | Aliases |
|---|---|---|
| #feature | New functionality shipped or started | feat, funcionalidad, fitur |
| #bugfix | A defect found and fixed | fix, bug, error |
| #code-review | Reviewing someone else's pull request | review, revision |
| #mentoring | Helping or teaching a colleague | mentoria, pairing |
| #learning | Course, reading or practice to learn something | study, curso, belajar |
