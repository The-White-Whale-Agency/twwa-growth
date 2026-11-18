# Changelog

## 0.1.0 (2026-11-17)

First version.

- Entry skill `/twwa-growth` with modes check, onboard, teardown, plan, run, weekly, report and status, and 15 focused `/twwa-*` skills.
- SERP teardown: winners per target query in organic results, the map pack and AI answers, gap score, winnability, backlog.
- Provider-agnostic data layer with a registry and capability matrix.
- Google Business Profile connector with reads across all accessible profiles and writes behind the approval gate.
- Page pipeline with gates A to H, claim provenance and a German copy-quality gate.
- Action log with hypotheses, measurement windows, control pages and verdicts; approvals bound to a content hash; kill switch and one-command rollback.
- Regression guard, internal link graph, cannibalisation check, entity consistency check.
- Scheduled monitors: self-crawl, ranks and grid, AI panel, bot logs, competitor changes.
- German monthly report led by qualified Anfragen; free check for prospects.
- Agency-level learning log outside client repositories.
- Connectors: Search Console, Bing Webmaster, PageSpeed/CrUX, Vercel, Google Business Profile (OAuth, reads, gated writes, manual template fallback).
- Provider adapters implemented from documentation (not yet live-verified): DataForSEO (organic, maps, volumes, backlinks), OpenAI, Perplexity and Gemini (AI answers), Wayback (domain age), manual and agent-search imports.
- 53 unit tests on a fixture site, including an end-to-end teardown from a manual observation.
