---
name: twwa-weekly
description: Use for the scheduled weekly loop of a TWWA client (GitHub Actions, Claude Code routine or launchd), or when asked for the weekly digest. Never ships, never merges, never writes to the Business Profile.
---

# twwa-weekly

If `${CLAUDE_PLUGIN_ROOT}` is empty, the plugin root is two directories above this file. Scripts: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py"` (written below as `<name>.py`). Every script has `--help`; exit 3 = credentials missing (use the fallback it names), exit 4 = blocked by STOP, cap, approval, spend or scope (report it, never work around it).

1. `twwa_state.py status`; STOP present = digest only.
2. Measure: skill `twwa-measure` steps 1–4.
3. Health: `monitor.py crawl` (self-crawl + regression guard; P1 exits 1), `monitor.py bots --log <drain export>` if available, `monitor.py competitors`.
4. Opportunities: `opportunities.py detect`; teardown older than 35 days → flag "teardown fällig" (do not run paid observations unattended unless the cap allows and config says so).
5. At most 5 proposals (`plan.py rank` and `twwa_actions.py propose`), exactly one German owner request (`report.py owner-request`).
6. Digest to the operator: alerts, verdicts, new proposals, what waits for whom. Scheduling templates: `templates/monitors/`.
