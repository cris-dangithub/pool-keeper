# Optional domains

The career core is always on. Four domains are opt-in (chosen at setup, or later with
`pk config set domains.<key>=true`, which creates the file):

| Key | File (en) | What goes in | Typical sources |
|---|---|---|---|
| `preferences_values` | `75_preferences_values.md` | work preferences (team size, industry, schedule, culture), values, deal-breakers | chat, offers the person applied to or rejected, feedback |
| `goals` | `76_goals.md` | short- and long-term goals, target roles/sectors/countries, learning goals | chat, delegated packets (career targets), journal promotions |
| `availability` | `77_availability.md` | current availability, notice period, relocation, permits/visas, documents (passport: yes/no — never numbers), remote/hybrid, travel | chat, contracts, delegated packets |
| `personal_life` | `78_personal_life.md` | personal context the person chose to share: hobbies, family situation if they want it used, routines | chat only, unless they attach something |

## Rules

- Everything follows the same merge rules: sources, no duplicates, nothing deleted, verbatim
  originals.
- **Time-dependent**: goals and availability change — write "as of <date>" and keep the
  history (`references/merge-rules.md` §6). The snapshot shows the latest.
- **Sensitive by nature**: `personal_life` items are 🔒 unless the person says they can be used
  (e.g. a hobby for a CV's interests line). Health, religion, politics, sexual orientation,
  family details: store only if the person explicitly asks, always 🔒.
- **The person decides what not to keep**: if they say "don't record that", don't (and if it was
  already written, remove it and note in the changelog that something was removed at their
  request — `SKILL.md` rule 2). Record in `<open_questions>` → answered "<topic> — do not ask
  again".
- **Disabled domain, relevant info arrives**: preferences → `other`; goals → `profile` →
  career targets; availability → `other`; personal life → ask once whether to enable the
  domain, and don't store it until they answer.
- Journal activities with `@personal` stay in the journal; promote to `personal_life` only
  if enabled and the activity says something lasting (a new hobby, a sports result).
