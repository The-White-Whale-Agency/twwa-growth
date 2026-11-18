# Optional integrations

The plugin works alone. When one of these is installed, it does a step better; otherwise the plugin's own script does it. Derived from `docs/inventory/capability-map.md`; third-party text is not copied.

| Step | If available | Otherwise |
|---|---|---|
| Manual SERP, map-pack and AI observations | a browser tool (chrome-devtools MCP, Claude in Chrome) with geolocation set to the town | the operator's browser, procedure in `skills/twwa-serp-teardown/references/method.md` |
| Lab vitals | chrome-devtools `performance_*` / `lighthouse_audit` | `psi.py` (keyless at low volume) |
| Vercel analytics and deployments | Vercel MCP `aggregate_pageviews`, `count_events`, `list_deployments`, `get_runtime_errors` | `vercel_analytics.py` (deployments via token; analytics imported) |
| Pull requests | GitHub MCP `create_pull_request` | `gh pr create` printed for the operator |
| Research: press, roundups, memberships | Exa search | WebSearch / WebFetch |
| Backlinks and keyword volumes | Ahrefs or Similarweb connectors once authenticated; any provider in `data/providers.json` | `bing_wmt.py links` (own site), GSC impressions as demand |
| Second audit opinion | claude-seo (`seo-technical`, `seo-local`, `seo-geo`), searchfit-seo `seo-audit` | `site_audit.py`, `gbp.py audit`, `entity_check.py` |
| German copy review | a humanizer or unslop-style skill | `style_lint_de.py --gate` |
| Report delivery | Artifact or Docs connector, `make-pdf` | Markdown in `reports/` |
| Scheduling | `/schedule` routines | `templates/monitors/` (GitHub Actions, launchd) |

Contradictions between installed tools and the research are resolved in the capability map; the plugin follows the research (no llms.txt lever, no FAQ rich-result promises, no review incentives, no page quotas).
