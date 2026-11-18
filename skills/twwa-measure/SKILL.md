---
name: twwa-measure
description: Use when shipped TWWA actions have reached the end of their measurement window, when fresh data snapshots are needed, or when alerts (form failure, deindexing, ranking drops, GBP suspension) must be checked.
---

# twwa-measure

If `${CLAUDE_PLUGIN_ROOT}` is empty, the plugin root is two directories above this file. Scripts: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py"` (written below as `<name>.py`). Every script has `--help`; exit 3 = credentials missing (use the fallback it names), exit 4 = blocked by STOP, cap, approval, spend or scope (report it, never work around it).

1. Snapshots: `gsc.py snapshot`, `gbp.py snapshot`, `bing_wmt.py snapshot`, `leads.py summary`; optional `psi.py snapshot`, `geogrid.py run --execute`.
2. `twwa_actions.py due` then `measure.py evaluate --write` (difference in differences against control pages; small data = "noch zu früh" / "zu wenig Daten"). Each verdict also goes to the agency learning log.
3. Loss verdicts are revert candidates: propose `twwa_actions.py rollback <id>` to the operator, do not run it unattended.
4. `measure.py alerts`: any P1 goes to the operator immediately.
5. Monthly: `learning.py summary` and `learning.py suggest` (suggestions are never applied automatically).
