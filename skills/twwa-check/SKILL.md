---
name: twwa-check
description: Use for a read-only audit of a TWWA client site (repo plus live site) or of any prospect URL without repo access, for example a free Sichtbarkeits-Check as a door opener for a prospective client. Never writes to the site and never posts forms.
---

# twwa-check

If `${CLAUDE_PLUGIN_ROOT}` is empty, the plugin root is two directories above this file. Scripts: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py"` (written below as `<name>.py`). Every script has `--help`; exit 3 = credentials missing (use the fallback it names), exit 4 = blocked by STOP, cap, approval, spend or scope (report it, never work around it).

## Prospect (URL only)

1. `check_report.py prospect <url> --owner "<Inhaber aus dem Impressum>"`. Output: `./twwa-checks/<domain>/` (findings.json, sichtbarkeits-check.md, gespraechseinstieg.md). Never into a client repo.
2. If a browser tool is available, add one manual observation of "<Gewerk> <Stadt>" (who is in the map pack, where the prospect is) and mention it in the opener. Label it "Stichprobe".
3. Load `references/prospect-mode.md` for what to say and what not to promise.

## Client

1. `twwa_state.py doctor`; build if needed (`npm run build`).
2. `site_audit.py dist dist --write-snapshot` and `site_audit.py live <url> --write-snapshot --with-graph`.
3. `schema_gen.py validate dist`, `legal_lint.py site dist`, `entity_check.py run --dist dist`.
4. GBP: `gbp.py snapshot` (or the manual template), `gbp.py audit`, `gbp.py lint`.
5. Speed for money pages: `psi.py snapshot <urls>`. Tracking: `leads.py probe <form endpoint>` (dry run unless the operator says so).
6. `measure.py alerts`, then `check_report.py client`. Hand over `reports/check-<date>.md` and the P1 list.
