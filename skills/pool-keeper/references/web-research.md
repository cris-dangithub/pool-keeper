# Web research (public information only)

Controlled by `web_research` in the config: `auto` (do it without asking when useful — the
default), `ask` (propose it in one line of the report and wait), `off` (only when the user asks
explicitly).

## When

- A new organisation, school or certificate appears.
- An official name is uncertain (spelling conflict between sources, popular vs official name).
- The "organisation context" section of an experience file is still empty.
- The user says "search Google/the web for…".

## How

1. Web search, then fetch the best page. Prefer **official sources**: the organisation's own
   site, government registries (`official_sources` in the config, chosen at setup for
   `country`), the issuer's certificate-verification site. Public pages only — never log in.
2. Save it as a source: `<sources>/<date>_web-research-<topic>/<source_notes>` (next S ID; kind
   "Web research by the agent (public)"), with the URL next to every fact.
3. Merge with `[S###]` tags as usual. Facts about the organisation go to the experience file's
   organisation context / the school profile. **Conclusions about the person** drawn from the
   research (e.g. "joined during the pre-opening phase") are labelled `(inference)` and become a
   confirmation question in `<open_questions>`.
4. List the URLs in the report line "🔎 Web sources".

## Examples of official sources by country

| Country | Useful official sources |
|---|---|
| Indonesia | referensi.data.kemendikdasmen.go.id (schools, NPSN), PDDikti (universities and study programmes), BNSP (professional certification) |
| Colombia | SNIES (higher-education programmes), RUES (company registry), Ministerio de Educación |
| Spain | RUCT (universities and degrees), Registro Mercantil / BORME (companies) |
| Anywhere | issuer verification pages (Certiport, Credly, Coursera, Microsoft Learn), the organisation's own site, LinkedIn company pages (public) |

These are suggestions for setup; the config's `official_sources` list is what counts.

## Limits

- Only public information about **organisations, schools, certificates, products or terms**.
- **Never** search for personal information about the person, their references, colleagues or
  anyone else (no people search, no social profiles of individuals, no address lookups).
- Don't treat a web fact as a fact about the person: it describes the organisation.
- Trackers and private systems (Jira, Confluence, intranets): only through a connector the user
  already connected; never enter credentials (`references/github.md` §6).
