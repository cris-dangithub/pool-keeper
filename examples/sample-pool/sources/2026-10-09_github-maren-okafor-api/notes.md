# GitHub — maren-okafor/api

- Sync date: 2026-10-09
- Identities: maren-okafor, maren.okafor@example.com
- Window: since 2026-10-01

## 2026-10-05 — Refresh tokens (PAY-12) (pr, u-0000000001)
- PR #7 (merged 2026-10-06): https://github.com/maren-okafor/api/pull/7
- Branch: `feat/refresh`
- 2026-10-05 `c100000` feat(auth): add refresh tokens PAY-12
- 2026-10-05 `c200000` fix(auth): handle expired token
- Jira / tracker keys: PAY-12 — not read (no access)
- Key files: `src/auth/tokens.py`, `tests/test_tokens.py`
- WHAT: added refresh-token issuing and rotation to the auth API, with tests; expired tokens now return 401 with a clear error.
- WHY: users of the mobile apps were logged out every hour (PR body); PAY-12 not readable.
- Result: merged.
- Technologies: Python, FastAPI, JWT, pytest.
