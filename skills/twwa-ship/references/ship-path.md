# Ship path

## Gate order

| # | Command | Blocks on | Meaning of a failure |
|---|---|---|---|
| 1 | `twwa_actions.py show <id>` | STOP, R3, blocked | nothing to implement yet |
| 2 | `npm run build` | build error | fix the code, not the gate |
| 3 | `site_audit.py dist dist --fail-on P1` | exit 1 | a P1 on the built site: noindex on a money page, broken form handler, unreachable Impressum, robots block |
| 4 | `schema_gen.py validate dist` | exit 1 | JSON-LD broken or NAP differs from `business.json` |
| 5 | `legal_lint.py site dist`, `legal_lint.py text <copy>` | exit 1 | §5b notice missing, incentive or gating wording, superlative or guarantee |
| 6 | `style_lint_de.py <copy>` | never | warnings; a reviewer reads and acknowledges them |
| 7 | `page_gates.py run --page <file> --action <id>` | exit 1 | gates A to G; the failure becomes a backlog reason and an owner data request |
| 8 | `site_audit.py redirects --repo .` | exit 1 | chain, loop, missing target, old URL without redirect |
| 9 | tier guard | new FAIL against base | the change is outside the website tier |
| 10 | `twwa_actions.py verify <id>` | exit 4 | approval missing or content changed since approval |
| 11 | `regression_guard.py verify --action <id>` (after deploy) | exit 1 | P1 regression live; roll back |

For the tier guard, run it on the base branch and on the action branch and compare the FAIL lines; only new FAIL lines block.

## Approval hash

`content_hash = sha256` of the sorted lines `"<relative path>\t<sha256 of file bytes>"` for every artifact: files under `drafts/<id>/`, the action's listed artifacts, and every file changed on `twwa/<id>` against the default branch (content read from the branch). Any edit after approval changes the hash; `verify` then exits 4. An empty artifact list cannot be approved.

## Who approves

| Risk | Required | Executes |
|---|---|---|
| R1 | TWWA | agent on a branch; merge per autopilot |
| R2 | TWWA and owner | agent prepares; merge per autopilot; GBP writes only after verify with `--execute` |
| R3 | TWWA and owner, plus `legal.signoff` for legal text | a human, always |

## Autopilot

| `autopilot.level` | Agent may merge |
|---|---|
| `off` (default) | nothing |
| `technical` | R1 after a verified TWWA approval |
| `approved` | R1 and R2 whose approvals verify |

In every level: no R3, no sending of e-mails or messages, no review requests, no outreach, no production deploy without live verification afterwards. Unattended runs never merge.

## After shipping

Baseline for measurement is the last full window before the ship date (`baseline_snapshot` in the action). `twwa_actions.py due` lists actions whose window has ended; `twwa-measure` evaluates them.
