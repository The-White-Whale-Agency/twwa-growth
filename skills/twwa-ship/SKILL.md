---
name: twwa-ship
description: Use when one approved twwa-growth action is to be implemented on a client site, or when a shipped action has to be rolled back. Applies to site changes on a branch with preview, gate scripts and approval verification, and to logging changes a human made by hand.
---

# twwa-ship

Implements exactly one action. Every gate is a script; a non-zero exit stops the run. Nothing is pushed, merged or posted unless the autopilot level and verified approvals allow it.

If `${CLAUDE_PLUGIN_ROOT}` is empty, the plugin root is two directories above this file.

## Inputs

- An action id in state `proposed` or `approved` (`twwa_actions.py show <id>`).
- The client repo with `.twwa-growth/`, a clean working tree, and the default branch up to date.

## Steps

1. Check the kill switch and the action:
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/twwa_actions.py" show <id> --json`. Stop if `STOP` exists, if the risk is R3 (a human executes; only log it, see step 12), or if the action is blocked by scope.
2. Branch: `git checkout -b twwa/<id>` from the default branch. Commit messages end with `[twwa:<id>]` so rollback finds them.
3. Make the change. Site templates come from `templates/site/`. Copy drafts from `.twwa-growth/drafts/<id>/` into the site, stripping provenance markers (`[[p:…]]`, `[[f:…]]`, `[[b:…]]`). Facts come only from `business.json` and `evidence/`; unknown values are left out, never guessed.
4. Build: `npm run build` (or `config.site.build_command`).
5. Run the gates; stop on the first non-zero exit. Load `references/ship-path.md` for the exact order and what each failure means:
   - `site_audit.py dist dist --fail-on P1`
   - `schema_gen.py validate dist`
   - `legal_lint.py site dist` and `legal_lint.py text <changed copy>`
   - `style_lint_de.py <changed copy>` (warnings do not block; record that a reviewer read them)
   - `page_gates.py run --page <file> --action <id>` for every new or rewritten page
   - `site_audit.py redirects --repo .`
   - the tier guard, if `config.tier_guard` is set: `node "<tier_guard>" --tier <tier>` must not report a new FAIL compared with the base branch
6. Preview: push of the branch is a separate, explicit operator step; the Vercel preview URL comes from the PR or the Vercel MCP. Without a preview, stop at the approval packet with "Vorschau-Link folgt".
7. Approval packet: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/twwa_actions.py" packet <id>` writes the German summary to `out/packets/<id>.md`. The operator sends it; the plugin sends nothing.
8. Record approvals as they arrive (operator only, with a reference to where the yes was given):
   `twwa_actions.py approve <id> --role twwa --by "<name>" --channel pr --evidence "<PR URL>" --preview-url <url>`
   `twwa_actions.py approve <id> --role owner --by "<name>" --channel whatsapp --evidence "<message reference>"`
   Never infer an owner approval from silence.
9. Immediately before merge: `twwa_actions.py verify <id>`. Exit 4 means a role is missing or an artifact changed after approval; there is no override. Ask again with a new packet.
10. Merge per `config.autopilot.level` (`off`: a human merges; `technical`: agent may merge R1; `approved`: agent may merge R1 and R2). Then log: `twwa_actions.py ship <id> --commit <sha> [--merged-by agent] --preview-url <url>`.
11. After the production deploy, verify live; the deploy log is not evidence:
    `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/regression_guard.py" verify --action <id>`. Exit 1 (a P1 regression on a money page) means roll back now (step 13).
    Then `indexnow.py submit --action <id>` (dry run) and `--execute`.
12. Changes a human made by hand (R3, GBP identity, legal text): `twwa_actions.py ship <id> --by-human "<name>"` after verify passes.
13. Rollback: `twwa_actions.py rollback <id> [--build "npm run build"]` creates `twwa/rollback-<id>` and reverts the action's commits. Load `references/revert.md`. Pushing stays a separate step; after the deploy run `regression_guard.py verify --action <id>` and `twwa_actions.py close <id> --outcome reverted --reason "<text>"`.

## Outputs

Branch `twwa/<id>`, gate results in `actions.jsonl` (`gates`, `approval`, `approved`, `shipped`, `live_verified`, `indexnow_submitted` events), approval records in `approvals/<id>.json`, the packet in `out/packets/<id>.md`.

## Stop conditions

`STOP`; a failing gate; `verify` exit 4; R3 execution; the tier guard reports a new FAIL; any request to send a message, post to a profile or submit a form on a site TWWA does not control. See `../../references/safety.md`.

## Optional integrations

| If available | Use it for | Otherwise |
|---|---|---|
| GitHub MCP `create_pull_request` | PR as the TWWA approval channel | the operator opens the PR |
| Vercel MCP `web_fetch_vercel_url` | fetch a protected preview | operator shares the preview |
| gstack `canary` | extra post-deploy watch | `regression_guard.py verify` |

## References

- `references/ship-path.md`: gate order, failure meaning, autopilot table (step 5 and 10).
- `references/revert.md`: rollback and the revert path (step 13).
- Shared: `../../references/gates.md`, `../../references/safety.md`, `../../references/legal-de.md`, `../../references/state-and-config.md`.
