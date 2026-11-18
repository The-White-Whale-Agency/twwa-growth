# Claude Code routine: weekly twwa-growth loop

Schedule (e.g. `/schedule`): every Monday 06:00 Europe/Berlin, in the client repo.

Prompt:
> Run `/twwa-growth weekly` for this repo. Do not ship, merge, push, deploy, send messages or write to the Business Profile. Paid data calls only within `spend.monthly_cap_usd`. End with the weekly digest and the single German owner request.

Settings: no `--dangerously-skip-permissions`; allow `python3 *twwa-growth/scripts/*` and read-only git; deny `git push`, `vercel`, network writes.
