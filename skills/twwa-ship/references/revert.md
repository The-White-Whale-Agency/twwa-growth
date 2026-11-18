# Revert path

Every shipped site action can be undone with one command and the normal verification.

1. `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/twwa_actions.py" rollback <id>`
   - creates `twwa/rollback-<id>` from the default branch in a temporary worktree, so the current checkout is untouched
   - reverts the action's commits newest first (from the `shipped` event, or commits whose message contains `[twwa:<id>]`; merge commits are reverted against their first parent)
   - with `--build "npm run build"` it builds the branch and runs `site_audit.py dist --fail-on P1`
   - prints the merge command; it never pushes
   - if a revert conflicts, the branch is removed again and the command exits 1; resolve by hand
2. With `--merge` the rollback is merged locally only when the autopilot level allows it for the action's risk and the checkout is a clean default branch. Otherwise merge by hand.
3. Push and deploy as a separate, explicit step.
4. Live verification: `regression_guard.py verify --action <id>`.
5. Log the outcome: `twwa_actions.py close <id> --outcome reverted --reason "<what went wrong, with numbers>"`.

When to revert without waiting for the window: a P1 regression on a money page, the form pipeline failing, a legal finding introduced by the change, or the owner withdrawing the approval. A `loss` verdict at window end is a revert candidate; the operator decides.

GBP changes are reverted by a new approved edit restoring the previous value from the last `gbp.json` snapshot, never by a script acting on its own.
