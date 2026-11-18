# Safety rules

These rules are enforced by scripts (exit codes), not only stated. A skill that meets one of them stops and reports.

## Never produced or assisted

Rejected by `legal_lint.py` (and the off-site lint) when found in drafts:

- Review incentives of any kind (voucher, discount, raffle, gift), review gating or selective asking, fake or commissioned reviews, reviews by staff.
- Electronic review requests without recorded consent, reminders, steering to five stars.
- Link exchanges, paid links without `rel="sponsored"` or `rel="nofollow"`, automated link creation, keyword-anchor footer links across client sites, private blog networks.
- Keyword or town stuffing in the profile name, fake or virtual addresses, one profile per town.
- Pages made to a count, town lists, town-swap pages, self-published "best of" lists naming the client, pages or files made mainly to steer AI answers.
- Unverifiable superlatives and guarantees ("bester", "Nr. 1", "garantiert").
- Changes to Impressum, Datenschutz or consent texts without human legal sign-off.
- Sending any e-mail or message, posting to any profile, submitting any form on a site TWWA does not control.
- Writing scope exception lines. Only the agency owner adds those, by hand, in the scope file; the plugin's approvals are JSON in `approvals/`.
- Click bots, CTR manipulation, traffic bots or other fake engagement; scraping Google at scale against its terms. Rank, map and AI observations go through APIs and data providers, or a person looking at a result page.

## Operational guards

| Guard | Where | Exit |
|---|---|---|
| `STOP` file | every script that writes, spends or ships | 4 |
| proposal cap (5 open), page cooldown (14 days), one GBP identity edit per 48 h, page ramp (Gate G), spend cap | `twwa_actions.py propose` | 4 |
| scope | `twwa_state.py scope check`, `propose` | 4 (or a proposal with `--as-proposal`) |
| approvals bound to content | `twwa_actions.py verify` | 4 |
| paid calls | `spend.guard`, `--execute`, ledger | 4 |
| live verification after every production change | `regression_guard.py verify` | 1 |
| no private or loopback fetches | `http.fetch` | refused |
| tier-guard compatibility of the state folder | `twwa_state.py doctor` | 1 |

R3 actions (GBP name, address, pin; legal text) are never executed by a script in any mode. Unattended runs never merge and never write to GBP.

## Evidence rule

Every finding carries a URL, file and line, or a data point. Without one it is a hypothesis and never leads a report. Missing data is "nicht geprüft", never an estimate. Live data wins over anything in the state folder.

## No client data in the plugin

Examples use Musterbetrieb, Musterstadt, Nachbarstadt and `musterbetrieb.example`. Prospect checks are written to `./twwa-checks/<domain>/`, outside client repos. The learning log stays on the operator's machine.
