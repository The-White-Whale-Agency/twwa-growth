---
name: twwa-plan
description: Use when a new growth cycle for a TWWA client must be planned from the teardown backlog, audit findings and opportunities, or when the owner needs a German plan of at most five actions with hypotheses, metrics and measurement windows.
---

# twwa-plan

If `${CLAUDE_PLUGIN_ROOT}` is empty, the plugin root is two directories above this file. Scripts: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py"` (written below as `<name>.py`). Every script has `--help`; exit 3 = credentials missing (use the fallback it names), exit 4 = blocked by STOP, cap, approval, spend or scope (report it, never work around it).

## Steps

1. Preconditions: a check younger than 7 days and a teardown younger than 35 days (`twwa_state.py status`). Without a teardown only P1 and table-stakes items are planned.
2. `opportunities.py detect`, then `plan.py rank`.
3. For every item in the cycle, write a real hypothesis from the teardown evidence ("Wenn die Landingpage einen Abschnitt Fassadensanierung mit 3 belegten Projekten aus Musterstadt bekommt, steigen die Impressionen für 'fassadensanierung musterstadt', weil der Gewinner genau das hat und wir nicht"), pick control pages, then run the printed `twwa_actions.py propose ...` line. Exit 4 = cap, STOP, spend or scope: report, never bypass. Scope items run with `--as-proposal` and become a German offer in `proposals/` (no price).
4. `twwa_actions.py packet <id>` per action for the owner (German, preview link once built).
5. Present: the cycle (≤ 5), why each item (teardown numbers), owner effort in minutes, what waits and why. Approvals are recorded only when someone actually said yes: `twwa_actions.py approve <id> --role twwa|owner --by ... --channel ... --evidence ...`.
