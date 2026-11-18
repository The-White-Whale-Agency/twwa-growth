# Modes: exact phase sequence

`check <url or .>`
1. Prospect (URL, no repo): `check_report.py prospect <url> --owner "<Name aus Impressum>"`. Output goes to `./twwa-checks/<domain>/` (never a client repo). Done: hand over `sichtbarkeits-check.md` and `gespraechseinstieg.md`.
2. Client: skill `twwa-check` (site_audit dist + live, schema, legal, gbp audit/lint, entity, psi, alerts), then `check_report.py client`.

`onboard`: skill `twwa-onboard`, then `check`. Unknown facts become owner questions; work continues with them marked unknown.

`teardown [query...]`: skill `twwa-serp-teardown`. Read-only. Paid observations only with a spend cap and `--execute`.

`plan`: `check` if the last is older than 7 days; `teardown` if older than 35 days; `opportunities.py detect`; skill `twwa-plan`. Present the German plan; the operator records approvals.

`run`: `twwa_state.py status`; for each approved action skill `twwa-ship`; then `twwa-measure` for due windows. `run --dry-run` prints each step and which gate or approval would block it.

`weekly`: skill `twwa-weekly`. Never ships, never writes to GBP.

`report [yyyy-mm]`: `twwa-measure` if stale, then skill `twwa-report`.

`status`: `twwa_state.py status`, `twwa_actions.py list`, `twwa_actions.py due`.
