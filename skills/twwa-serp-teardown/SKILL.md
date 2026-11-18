---
name: twwa-serp-teardown
description: Use when deciding how a client gets to first place for its money queries, when competitors outrank it in Google, the map pack or AI answers, before planning a growth cycle, or when a teardown in .twwa-growth/teardowns is missing or older than 35 days.
---

# twwa-serp-teardown

Reverse-engineers the winners for the client's own queries, in its own trade and town, at use time. Nothing about real businesses is stored in the plugin; results go to `.twwa-growth/teardowns/<date>/`.

If `${CLAUDE_PLUGIN_ROOT}` is empty, the plugin root is two directories above this file. Scripts: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py"` (written below as `<name>.py`). Every script has `--help`; exit 3 = credentials missing (use the fallback it names), exit 4 = blocked by STOP, cap, approval, spend or scope (report it, never work around it).

## Steps

1. Queries: `serp_teardown.py queries` (review), then `serp_teardown.py queries --write`. Check the list with the operator if a service or town looks wrong; fix `business.json` rather than the list. Load `references/method.md` for the query classes and value.
2. Data: `providers.py list`. If a provider with `serp_organic`/`serp_maps` has credentials: `serp_teardown.py observe` (dry run, prints cost) then `observe --execute` when the spend cap allows.
   Without a provider, or for the AI surface: observe by hand (method.md, "Manual observation", about 5 minutes per query with a browser tool if available) and `serp_teardown.py import <file>`. Never guess a surface: unobserved = `not_checked`.
3. AI surface: latest `ai-panel` snapshot younger than 35 days, else run skill `twwa-ai-visibility` first.
4. Collect winners and the client page: `serp_teardown.py collect` (robots.txt respected, ≤ 8 pages per winner; add `--execute` to allow paid backlink and age lookups).
5. Score and decide: `serp_teardown.py score`, `backlog`, `summary`. Load `references/gap-scoring.md` to read factors, confidence and winnability.
6. Optional local grid for pack queries: `geogrid.py run` (dry run, cost = size² × keywords) → `--execute` → `geogrid.py render`.
7. Report to the operator, per query: who wins each surface and why (top 3 factors with values), winnability class, the 3 highest-priority backlog items with first signal and evaluation window, and what was not checked.

## Rules

- Confidence under 0.5 means the gap is mostly unmeasured: say so and name the data that would fix it.
- Portal-dominated SERPs: the target is being listed and strong on those portals plus the first business slot, not beating the portal.
- `out_of_radius` pack queries: attack organically; ads only as a note (`paid_ads.mode = mention_only`).
- A name with trade or town keywords at a winner is a risk signal, never something to copy.
