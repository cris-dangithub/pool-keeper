# Learning from style corrections (6b, automatic)

Triggered when the person pastes a text produced by an AI/another skill **and** the version
they wanted (any labels: "input/output", "this is what it wrote / it should be", "before/after",
or simply two blocks in a row).

1. Next ID: `pk next-id K`. Log it at the **top** of `writing_style_corrections` (newest first):
   date, origin of the text (skill / document type / offer if mentioned), **the AI text
   literally**, **the expected text literally**. If it is unclear which is which → ask once.
2. Compare carefully: words/phrases replaced, removed or added; changes of structure, length,
   order, tone, numbers, punctuation, language.
3. For each meaningful difference (not an accidental typo):
   - a similar rule exists in `writing_style_rules` → **strengthen** it: Strength +1, add `K###`
     to Origin, add an example if clearer;
   - no rule yet → **create** `G###` (`pk next-id G`) with a DO example (from the expected text)
     and an AVOID example (from the AI text);
   - it **contradicts** an existing rule → ask the person once which one applies; the losing
     rule gets `Status: replaced by G###` (never deleted);
   - rules from corrections (`Origin: K###`) always beat rules from document patterns within the
     same scope.
4. In the log entry: the difference analysis + the list of rules created / strengthened /
   replaced. A short changelog entry.
5. Reply in chat in ≤3 lines, e.g.: "📝 K003 logged. Learned: G014 (new) — avoid
   'spearheaded'; G004 (strengthened, 3×) — numbers at the start of bullets."
6. Don't change facts in the pool because of a style correction, unless the person also
   corrected a fact (then process that part as normal information too).

A direct decision without a text pair ("use present tense for routine tasks, past for results")
is logged the same way, as `K### — <date> — direct decision`, with the person's words verbatim.

## Log entry format

Headings in the pool language (`pk strings` → `k_*`):

```
## K### — <YYYY-MM-DD> — <document type / originating skill / offer>
### AI text (literal)
> ...
### Expected text (literal)
> ...
### Difference analysis
- ...
### Rules
- New: G### — ...
- Strengthened: G### (Strength n → n+1)
- Replaced: G### → G###
```
