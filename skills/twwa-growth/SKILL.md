---
name: twwa-growth
description: Use when a TWWA client site (Astro on Vercel) should rank first in Google, the map pack and AI answers and turn that into Anfragen, or when a prospect URL needs a free Sichtbarkeits-Check. Entry point for check, onboard, teardown, plan, run, weekly, report and status; also use when it is unclear which twwa skill applies.
---

# twwa-growth

One entry point that runs the whole programme and comes back with the final result. The centre is the SERP teardown: who wins each money query on each surface, why, and what closes the gap. Everything else serves it or measures it.

If `${CLAUDE_PLUGIN_ROOT}` is empty, the plugin root is two directories above this file. Scripts: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py"` (written below as `<name>.py`). Every script has `--help`; exit 3 = credentials missing (use the fallback it names), exit 4 = blocked by STOP, cap, approval, spend or scope (report it, never work around it).

## Pick the mode

| Situation | Mode |
|---|---|
| a URL that is not a TWWA repo (prospect) | `check <url>` |
| client repo without `.twwa-growth/` | `onboard` |
| client repo with state, no argument | `status`, then propose the most useful next mode |
| "why are competitors ahead", new trade or town | `teardown` |
| new cycle | `plan` |
| approved actions waiting | `run` (or `run --dry-run`) |
| scheduled | `weekly` |
| month end | `report [yyyy-mm]` |

Load `references/modes.md` for the exact phase sequence of the chosen mode and `references/phase-map.md` for which skill and script each phase uses. Shared rules: `../../references/safety.md` (load before any write).

## Always

1. `twwa_state.py status` (client) or nothing (prospect). If `STOP` exists, stop and say why.
2. Live data beats the state folder. Pull fresh snapshots when the last one is older than its window (GSC 7 days, GBP 7 days, teardown 35 days).
3. Run the mode. Each phase is a skill: invoke it (`twwa-check`, `twwa-onboard`, `twwa-serp-teardown`, `twwa-plan`, `twwa-ship`, `twwa-measure`, `twwa-weekly`, `twwa-report`, and the specialists `twwa-tech`, `twwa-gbp`, `twwa-reviews`, `twwa-pages`, `twwa-leads`, `twwa-ai-visibility`, `twwa-offsite`).
4. Finish with: the result file(s), a 5-line operator summary in the operator's language (what was found, what was decided, what waits for whom), and the one owner request in German if there is one.

## Never

- Ship, merge, post or send anything without the approvals the action's risk class needs (`twwa_actions.py verify`).
- Write a `- APPROVED:` line, touch Impressum/Datenschutz text, or write GBP name, address or pin.
- Estimate a number that was not measured: say "nicht geprüft".
- Produce link exchanges, review incentives, town-swap pages, page quotas, click or traffic bots.

## Optional integrations

If installed, prefer them for the step, otherwise the plugin's own scripts do it (mapping: `../../references/integrations.md`): a browser tool for manual SERP and AI observations, Vercel MCP for analytics and deployments, Exa for research, a humanizer for German copy review, claude-seo/searchfit skills for a second audit opinion.
