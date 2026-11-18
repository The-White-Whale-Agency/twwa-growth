# 01 · SEO plugins

Inventory date 2026-11-16. Read-only. Dossier = `../research/`.

## 1. Scope

| Source | Version, path | Licence (file read) |
|---|---|---|
| claude-seo | 2.5.0, `~/.claude/plugins/cache/agricidaniel-claude-seo/claude-seo/2.5.0/` | MIT (root `LICENSE`, © 2026 agricidaniel); `seo-flow` prompts CC BY 4.0, attribution mandatory |
| searchfit-seo | 1.0.0, `synced/.../searchfit-seo/` | MIT (© 2026 SearchFit.ai) |
| marketing → `seo-audit` | 1.2.0 (Anthropic), `synced/.../marketing/` | Apache-2.0 |
| ai-builder-club `skills` | 0.1.0, `cache/ai-builder-club/skills/0.1.0/` | no LICENSE file; `plugin.json` says MIT |
| small-business → `seo-ai-visibility` | 1.35.2 (Anthropic), active in `synced/.../small-business~g2/` (old copies in `.trash`) | none found: do not quote |

MIT and Apache texts may be quoted with their notice; we copy nothing anyway. **Read in full:** claude-seo `seo`, `seo-local`, `seo-maps`, `seo-geo`, `seo-schema`, `seo-technical`, `seo-sitemap`, `seo-programmatic`, `seo-google`, `seo-drift` and the local, maps, quality-gate, schema-deprecation, AI-guide, GSC, cost and drift references; searchfit `ai-visibility`, `schema-markup`, `technical-seo`; marketing `seo-audit`; `seo-growth` with 4 references; `new-loop`; `seo-ai-visibility` + `ai_visibility.md`. **Partly read** (header, CLI, grep): the scripts in §4, `seo-dataforseo`, `seo-backlinks`, `seo-content`, `seo-flow`, hooks, the other searchfit files.

## 2. Per source

| Skill | Verified function | Phases | Use |
|---|---|---|---|
| claude-seo `seo` | Hub for 25 sub-skills; hard rules; adds a community promo footer to reports | P1 | distil the rules; strip the footer |
| `seo-local` | Website-side local audit: business type, NAP page vs schema vs GBP, reviews, citations (US), local schema | P1, P11 | distil the NAP 3-way check and type detection |
| `seo-maps` | DataForSEO geo-grid, GBP 25-field score, review velocity, fake-review signals, Overpass competitors | P1, P8 | distil the method; call if DataForSEO is set up |
| `seo-geo` | AI readiness: crawler table, citability heuristics, llms.txt reported with zero weight | P7 | distil the bot table and Google myth list |
| `seo-schema` | JSON-LD detect/validate/generate; deprecations to Oct 2026 | P1, P3 | distil the deprecation list |
| `seo-technical`, `seo-sitemap` | 9-category audit; sitemap validation and generation | P1, P3 | distil the rules (§3) |
| `seo-programmatic` | Template pages: uniqueness %, batch rollout, canonical | P4 | distil canonical rules; reject the numbers |
| `seo-google` | GSC, URL Inspection, PSI, CrUX/History, Indexing API, GA4 | P1, P8 | call the scripts; distil the GSC caveats |
| `seo-dataforseo` | DataForSEO MCP wrapper with a cost ledger (US/English defaults) | P1, P7, P8 | distil the cost guard |
| `seo-drift` | 17 diff rules over title, meta, canonical, robots, H1-H3, schema, OG, CWV, status | P3, P9 | distil into a post-deploy check |
| `seo-backlinks`, `seo-plan`, `seo-agentic`, `seo-audit`, `seo-page`, `seo-content(-brief)`, `seo-cluster`, `seo-sxo`, `seo-competitor-pages`, `seo-ecommerce`, `seo-hreflang`, `seo-images`, `seo-image-gen`, `seo-flow` | Links/disavow, US plan templates, agent readiness, generic audits, English readability, clustering, intent, vs pages, shops, i18n, images, prompt library | P1, P4, P6 | ignore: generic, English-only or off-scope |
| searchfit `ai-visibility` | Single-run prompt test scored on presence, **position**, sentiment (0-100) | P7 | ignore (§5) |
| searchfit (10 other skills, 3 agents, 6 commands) | Generic SaaS/blog SEO prompts, no local; each ends with a SearchFit promo line | P1, P4 | ignore |
| marketing `seo-audit` | Generic keyword/on-page/gap audit via Ahrefs/Similarweb | P1 | ignore (FID, FAQ/HowTo, no local) |
| ai-builder-club `seo-growth` | GSC method: breadwinner, query screening, canary, cooldowns, verify windows, loop roles | P2, P8, P9 | **distil**: B2B-derived, says local was never tested |
| `new-loop` | Scaffolds a loop: charter, backlog, timeline, LOG.md, one real run | P9 | distil the state-file pattern |
| ai-builder-club others | `agent-context-audit`, `crabbox-setup`, `dev-local-setup`, `e2e-setup`, `karaoke-captions`, `open-agent-teams`, `setup-codebase-harness`, `verifier-setup`, `visual-flow-gif` | none | ignore |
| small-business `seo-ai-visibility` | Owner crawl + AI check + fix files (robots, llms.txt, JSON-LD, copy); refuses gaming; no score | P1, P7, P11 | distil the stance; reject llms.txt and schema levers |

## 3. Rules worth distilling (restated)

| Rule | Source |
|---|---|
| Grid: centre on the pin; spacing = 2·radius/(n−1); lat offset = km/111.32, lng offset ÷ cos(lat); default 7×7; radius 2-5 km urban, 5-10 suburban, 10-25 rural; one POST for all points (≤100 tasks); save each grid as JSON (row-major from NW, `null` = not found) | `maps-geo-grid`, `seo-maps` |
| Grid metrics: SoLV = top-3 points ÷ all points, plus mean rank, a weighted score (top 3 = 3, 4-10 = 1) and the weakest quadrant; cost estimate and confirmation before each scan | `maps-geo-grid` |
| Reviews: monthly velocity over 6 months, gaps, star distribution, owner reply rate (≥80%). Possible fake if 2+ hit: same-day cluster, one-review accounts, far-away reviewers, 5-star spike, near-duplicate text, spike with no campaign | `seo-maps` |
| GBP: most specific primary category; real name; local number, not a hotline; holiday hours; services with descriptions; SAB areas as towns/postcodes only, ≤20; Q&A = N/A. The SAB area setting does not rank; the verification address does | `maps-gbp-checklist`, `local-schema-types`, `local-service` |
| Schema: never mark up first-party reviews; `geo` ≥5 decimals; `priceRange` <100 chars; most specific subtype; unique `@id` per location. Never generate HowTo, SpecialAnnouncement, CourseInfo, EstimatedSalary, LearningVideo, ClaimReview, VehicleListing, Practice Problem; keep existing FAQPage, add none | `seo-maps`, `seo-local`, `seo-schema` |
| Sitemap: ≤50k URLs and ≤50 MB; only canonical, indexable, 200, HTTPS URLs; `lastmod` = last real content change (warn if uniform or newer than the content); `priority`/`changefreq` ignored | `seo-sitemap` |
| Technical: Googlebot reads only the first 2 MB of HTML; canonical and robots identical in raw and rendered HTML; no rendering on non-200 pages; a canonical fix can take ~2 weeks; ≤1 redirect hop; robots.txt returning 5xx = disallow all; INP only | `seo-technical` |
| Bots: check each separately. Search: Googlebot, OAI-SearchBot, Claude-SearchBot, PerplexityBot, Applebot. Training: GPTBot, ClaudeBot, Google-Extended (no effect on Search or AIO), Applebot-Extended, CCBot. Google user-triggered fetchers ignore robots.txt | `seo-geo`, `seo-technical` |
| GSC: impressions/CTR/position unreliable 2025-05-13 to 2026-04-27 (clicks fine); totals from a query with no dimensions; country `DEU`; end windows 3 days back; ignore rows <50 impressions; merge apex and www; one KPI, the rest labelled diagnostics | `search-console-api`, `seo-growth/measurement` |
| Before "fixing" low CTR, screen out AI fan-out, competitor-navigational, brand-navigational and anonymised-tail queries (visible <10% of impressions) | `seo-growth` |
| Snippet-limited (human queries, position ≤15, title misses the query): rewrite title/H1/meta. Position-limited (CTR fine, position 5-7): one internal link per cycle from a high-impression page | `seo-growth/with-data` |
| Canary: the best page loses ≥3 positions or >30% of clicks → stop. Cooldowns 14 d (best page) / 7 d (others), one edit per page per window. Verify at +14 d (7 days after vs 7 before); >30% drop = revert candidate | `seo-growth/with-data` |
| If one of our pages already ranks <15 for a term, link to it instead of building a new page | `seo-growth/emerging-terms` |
| Loops by role (scout, engine, enrichment, scorecard); the scorecard never ships; PRs, human merge; reconcile with live data each run; the state file lists verified non-problems | `operationalize`, `new-loop` |
| Cost guard: estimate → check per-call threshold and daily cap → ask → log to a locked ledger; some endpoints always ask; unknown endpoints need approval | `dataforseo_costs.py` |
| Owner wording: we make the site readable and the facts right, nobody can make an AI recommend you. Report observed answers, no score; top 5 findings, the rest in an appendix; DNS changes go back to the owner; never invent claims | `seo-ai-visibility` |

## 4. Scripts and data access (claude-seo)

Launcher `scripts/claude-seo run <script>`, Python 3.11-3.14 in an isolated venv (`/seo setup`). Dependencies are **not stdlib** (requests, bs4, lxml, Playwright, Google client libs, weasyprint). Auth: `~/.config/claude-seo/google-api.json` or env vars (`GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_API_KEY`, `GSC_PROPERTY`), gcloud ADC, or OAuth with PKCE. Private hosts are blocked unless listed in `CLAUDE_SEO_LOCAL_TARGETS`.

| Script | CLI | Auth | Without credentials |
|---|---|---|---|
| `gsc_query.py` | `--property --days --start-date --end-date --type --limit --country --json`; `sitemaps`, `sites` | OAuth/SA, read-only | error. Quick wins = position 4-10, >50 impressions |
| `gsc_inspect.py` | `url` / `--batch`, `--site-url` | OAuth/SA | error; caps 2,000/day, 600/min |
| `pagespeed_check.py` | `url --strategy --crux-only --psi-only` | key optional | PSI runs at a low quota; CrUX needs the key |
| `crux_history.py` | `url --form-factor PHONE --origin` | key | none |
| `bing_webmaster.py` | `links / counts / compare` | Bing key | error. **Links only**: no queries, no AI Performance |
| `indexnow_submit.py` | `--host --key --key-location --urls / --urls-file --verify-only` | hosted key file | works |
| `indexing_notify.py` | `url --action --batch --status` | OAuth/SA | warns about JobPosting-only use but **does not block** other URLs |
| `dataforseo_costs.py` | `estimate / check / log / summary / today / config / reset` | none, stdlib | works; $0.50 per-call threshold, $10/day; no Maps SERP or LLM Scraper prices |
| `gbp_deprecation_lint.py` | `source --file --json`, exit 1 on a finding | none | works (GBP chat CTAs, `business.site` links) |
| `drift_*.py` | `url --skip-cwv --baseline-id` | key only for CWV | works; SQLite in `~/.cache`, outside the repo |
| `schema_generate.py` | `reservation / order / discussion / profile` | none | no LocalBusiness/Service, so not useful |
| hook `validate-schema.py` | PostToolUse on every Edit/Write | none | checks .html/.jsx/.tsx/.vue/.svelte/.php/.ejs, **not `.astro`** |

DataForSEO (refs): Maps SERP $0.0006 standard / $0.002 live, `location_coordinate` = "lat,lng,zoom"; My Business Info $0.0015; reviews by `place_id` cost ¼ of a keyword lookup. The MCP defaults to US/English, so set the German location and language on every call.

## 5. Contradictions with the dossier

| # | Claim (source) | Dossier | Evidence supports |
|---|---|---|---|
| 1 | llms.txt is a "medium impact" fix (`seo-ai-visibility`), or a medium-effort item (`seo-geo`) | 00 #18, 04 | dossier |
| 2 | FAQPage/HowTo offered for rich results (searchfit schema, content, audit; marketing `seo-audit`) | 07: FAQ gone 2026-05-07 | dossier; claude-seo agrees |
| 3 | Schema as an AI lever: "schema for AI discoverability" (`seo-geo`), ProfilePage "for AI citation" (`schema_generate.py`), FAQ/Product schema for AI (searchfit, small-business) | 00 #18 | dossier |
| 4 | GBP description keywords, 10+ photos, uploads every 30 d and weekly posts scored as "significant influence" (`maps-gbp-checklist`) | 00 #3 | dossier; claude-seo's signals file agrees |
| 5 | Location pages need 60-70% / 40-60% unique; <40% = thin (`quality-gates`, `seo-local`, `seo-programmatic`) | 06: no Google number | dossier |
| 6 | Warn at 30 location pages, stop at 50; batches of 50-100 (`seo`, `seo-programmatic`) | 06 Gate G: ≤max(2, 10%)/week, ≤8/month under 50 pages, pilot 3-5 | dossier |
| 7 | "FID/INP" (marketing `seo-audit`) | 07 | dossier |
| 8 | Disclosed incentivised reviews allowed (`seo-schema`, `seo-ecommerce`); gating framed as Google/FTC only | 00 #5 | dossier (German law) |
| 9 | ChatGPT uses Bing, Yelp, TripAdvisor, BBB, Reddit; Foursquare and Bing Places "power ChatGPT" (`local-search-behavior`, `local-seo-signals`) | 00 #11: only Yelp confirmed, Foursquare refuted | dossier |
| 10 | AI "position" and a single-run score (searchfit `ai-visibility`) | 00 #16 | dossier |
| 11 | Blocked GPTBot/ClaudeBot is the top AI blocker (`seo-ai-visibility`) | 04: training bots, per-client choice | dossier; claude-seo agrees |
| 12 | AggregateRating on own reviews page (`seo-plan`), `aggregateRating` recommended (`seo-local`) | 07: self-serving reviews not eligible | dossier; `seo-maps` agrees |
| 13 | Don't point the GBP link at the strongest page (`seo-local`, "Diversity Update") | 03: homepage or main service page + UTM | open; keep the dossier, test it |
| 14 | GBP phone must match the website (`maps-gbp-checklist`) | 00 #25: tracking number as primary | dossier; our NAP lint must allow it |
| 15 | "5-10 local links/month", "magic 10 reviews", "cliff after 18 days" stated as rules (`seo-local`, `local-seo-signals`) | 00 #4, 08: case examples | dossier |
| 16 | Pagination with rel next/prev (searchfit `technical-seo`) | (claude-seo: unused since 2019) | claude-seo |

Q&A: every source marks the API as discontinued on 2025-11-03, so no conflict. Indexing API: correct in the text, not enforced in the script.

## 6. Harmful or banned for our use

- Disclosed review incentives (#8): illegal in Germany. The linter must block them.
- The `/locations/city/service-city` tree with a stop only at 50 pages (`seo-plan`, `seo`): a doorway matrix.
- searchfit "influence AI training data" and "write for the prompts you want to rank for": close to manipulating AI answers (00 #20).
- Vendor promo footers (claude-seo, SearchFit) must never reach client reports.
- No source recommends link exchanges, paid followed links or fake reviews.

## 7. Gaps

None of these sources covers:

- **German law:** §5b UWG, consent for review requests, the "verified" review label.
- **German citation tiers:** DTME, 11880/WerKenntDenBesten, Kammer/Innung, manufacturer partner finders.
- **Google and Bing first-party data:** Ask Maps; the official GBP APIs (Performance, edit limits, 48-hour identity-edit rule); Bing query stats and AI Performance; the GSC Generative AI report and branded/non-branded API data.
- **Grid and AI panel metrics:** ATRP and competitor SoLV; a multi-run German-locale AI panel with confidence intervals.
- **Astro and Vercel specifics:** sitemap `lastmod`, `.astro` schema validation, preview noindex, IndexNow deploy hook.
- **Measurement and attribution:** cookieless attribution and lead records; action windows by action type with control pages (`seo-growth` covers only 14-day page edits).
- **Content:** German copy and readability, Förder freshness.
- **Reporting:** the lead-portal cost anchor.
- **Ship path:** an approval hash and gate scripts.
