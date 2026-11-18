# Capability map

For each phase: what installed tooling helps, what we distil, what nothing covers, and where sources disagree. Details and evidence are in `01` to `04`. "Dossier" is `../research/`.

| Phase | Optional integration (if installed) | Distilled into the plugin (restated, source credited) | Gap we build ourselves |
|---|---|---|---|
| P0 Onboard | none | NAP three-way check: page, schema, GBP (claude-seo `seo-local`); state-file pattern with verified non-problems (ai-builder-club `new-loop`) | `business.json`, scope and tier detection, Bing Webmaster and IndexNow setup |
| P1 Check | chrome-devtools `performance_*` for lab vitals; Vercel MCP `list_deployments`, `get_runtime_errors`; claude-seo `pagespeed_check.py` | Read metadata from raw server HTML, never from source; sitemap content-type check; redirect single hop; robots 5xx means disallow all; bot classes checked separately (claude-seo `seo-technical`, `seo-geo`; user skills `page-metadata`, `xml-sitemap`, `canonical-tag`) | Astro and Vercel checks, German legal surface, CRO and tracking surface, entity consistency |
| SERP teardown | Ahrefs or Similarweb connectors once authenticated; Exa search for mentions | Intent and page-type match idea (claude-seo `seo-sxo`, name and description only) | The whole method: winners per surface, data points, gap score, winnability, gap to action |
| P2 Plan | none | Screen queries before a CTR fix (fan-out, navigational, anonymised tail); one edit per page per cooldown window; link to an existing ranking page before building a new one (ai-builder-club `seo-growth`); hypothesis form "if X then Y because Z" (`conversion-optimization`) | Fixed dependency order, caps, scope proposals, teardown-driven ranking |
| P3 Ship | GitHub MCP `create_pull_request`; Vercel `web_fetch_vercel_url` for protected previews; gstack `canary` | Diff rules over title, meta, canonical, robots, headings, schema, status (claude-seo `seo-drift`) become the regression guard; gate = command plus expected token, empty ledger is failure (`unlazy`) | Approval hash, gate scripts, rollback, IndexNow step |
| P4 Pages | marketing-skills `cro`, `copy-editing`; humanizer; claude-blog `blog-factcheck`; `unslop` | Title swap test; answer in the first 40 to 60 words; information gain before writing; source logged per field and freshness rules (user skills `title-tag`, `featured-snippet`, `article-content`, `programmatic-seo` safe parts); anti-slop rules (`unslop`, CC-BY-4.0, credited) | German templates, evidence registry, provenance gate, gates A to H, German copy lint |
| P5 Reviews | small-business `review-reputation` for reply drafts | Velocity over 6 months, reply rate, signals of suspicious reviews (claude-seo `seo-maps`) | German review law, consent ledger, §5b notice, lawful request assets |
| P6 Off-site | Exa for press and roundup prospects; Gmail `create_draft` | none usable (installed link-building and directory skills are US or SaaS and partly banned for us) | German citation tiers, vertical catalogue, drafts, banned-tactic lint |
| P7 AI visibility | provider layer; claude-seo DataForSEO extension | Bot table; owner wording "we make facts readable, nobody can make an AI recommend you" (small-business `seo-ai-visibility`) | Multi-run German panel with intervals, cited-domain gaps |
| P8 Measure | Vercel MCP `aggregate_events`; claude-seo `gsc_query.py` | GSC caveats: end windows 3 days back, ignore rows under 50 impressions, merge host variants, one KPI and the rest diagnostics; canary rule on the best page (claude-seo references, `seo-growth`) | Action windows with control pages, verdicts, lead records, learning log |
| P9 Weekly loop and monitors | `schedule` routines; launchd plus `claude -p` | Loop roles: the scorecard never ships; reconcile with live data each run (`seo-growth`, `new-loop`) | Monitors: self-crawl, ranks and grid, AI panel, bot logs, competitor changes |
| P10 Report | Artifact or Docs connector as a delivery channel; `make-pdf` | Top findings first, rest in an appendix (small-business) | German Anfragen report, portal-cost comparison, bot and human split |
| P11 Prospect check | Exa, WebFetch | No score for AI visibility; observed answers only | German one-pager and call opener |

## Contradictions and which side we take

| Topic | Installed tools say | Dossier | Decision |
|---|---|---|---|
| llms.txt | medium-impact fix (small-business, claude-seo `seo-geo`) | no measurable effect (00 #18) | not a lever; never sold |
| Schema for AI citations | recommended by several | no citation lift (00 #18) | schema for entity clarity only |
| FAQ and HowTo rich results | offered by searchfit, marketing, user skills | removed (07 §4) | keep existing FAQ markup, promise nothing |
| GBP description keywords, photos, posts as ranking levers | scored as influential (claude-seo checklist, `local-seo`) | tested: no ranking effect (00 #3) | conversion features only |
| Uniqueness percentages for location pages | 40 to 70% thresholds | Google publishes none (06) | internal heuristics, labelled as such |
| Page volume | stop at 50, batches of 50 to 100, thousands of pages | ramp at most max(2, 10%) per week, pilot 3 to 5 (06) | Gate G |
| Disclosed review incentives | allowed (claude-seo schema, ecommerce) | unlawful in Germany (03 §5) | banned and linted |
| AI "position" from a single run | searchfit `ai-visibility` | noise (00 #16) | mention rate over many runs |
| Guest posts, directory links for equity, parasite SEO, self-published best-of lists | user skills | link spam, site reputation abuse (08, 06) | banned |
| GBP phone must equal website phone | claude-seo checklist | tracking number may be primary with the real number as additional (00 #25) | NAP lint allows registered tracking numbers |
| Indexing API | script does not block normal URLs | JobPosting and BroadcastEvent only (07 §3) | not used |
| Slug transliteration | ü to u | German convention ü to ue, ß to ss | ue, oe, ae, ss |

## Facts about the plugin format that shaped the build

From `04`, verified on Claude Code 2.1.325:

- Skills are found by bare name (`/twwa-check`) and by `/twwa-growth:twwa-check`. The `twwa-` prefix keeps bare names unique.
- `${CLAUDE_PLUGIN_ROOT}` works inside SKILL.md bodies and must be quoted.
- Scheduled tasks ask before running a skill that declares `allowed-tools` or hooks, so our skills declare neither, and the plugin ships no hooks. Hooks fail open anyway; enforcement lives in the scripts.
- Cloud routines cannot attach local MCP servers. Monitors therefore run as plain scripts with environment secrets.
- A single-plugin repo installs through `.claude-plugin/marketplace.json` with `"source": "./"`.
