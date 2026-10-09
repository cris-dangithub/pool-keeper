# Reading the pool (for any agent)

The same rules are written into the pool's `CLAUDE.md` / `AGENTS.md` block, so agents that never
load this skill still follow them.

## Reading order

1. `<snapshot>` — one page: current role, location, top skills, languages, availability, goals.
2. `<profile>` — identity, targets, timeline (which experience file covers which period).
3. The file for the topic (layout map in `CLAUDE.md` / `AGENTS.md`, or `pk config get layout`):
   experience files for a role, `achievements` for numbers, `skills` for evidence, `stories` for
   interview answers, `writing_style` before writing anything in the person's name,
   `keywords` to match an offer.
4. `<journal>` for recent or repeated activity (`pk journal stats` gives exact counts).
5. `<open_questions>` before claiming anything uncertain: conflicts, gaps and "asked, never done".
6. `<sources_index>` and the source folders only to verify or quote originals.

## Answering

- **Cite** the source tags of every fact you use (`[S012]`, `[J0107]`).
- **State confidence**: sourced fact > `(inference)` > `(needs confirmation)`. For `⚠ conflict`,
  give both values and say it is unresolved — never pick one silently.
- **Never claim** anything listed under "asked, never done".
- **Never use** values marked "do not use" (they are history).
- **`🔒 private`**: for the person's own use only. Never put it in a CV, a cover letter, a public
  profile or any text for third parties; don't name private repositories — describe the work
  generically if needed.
- **Time**: facts with "as of <date>" — use the most recent; mention the date when it matters.
- **Journal counts** are lower bounds: "at least N recorded".
- **Writing on the person's behalf**: facts from the pool, voice from `writing_style`
  (rules from corrections first).
- If the pool does not know: say so, and suggest adding it (the open questions file may
  already list it). Don't fill gaps from general knowledge.

## Writing

Readers never write. To add or correct something, use the pool-keeper skill (or its
delegation mode from another skill).
