# 10 · Measurement and data stack the plugin can realistically use

Confidence legend: [P] primary · [S] secondary · [V] vendor claim · [I] inference/recommendation. Prices as of 2026-11; re-check before contracting.

## 1. First-party Google / Microsoft / Vercel APIs (free)

### Google Search Console API
- Auth: OAuth 2.0 (user who has access to the property) or service account added as a user to the property [I, standard].
- Quotas [P, developers.google.com/webmaster-tools/limits, upd. 2025-08-28]:
  - Search Analytics: 1,200 QPM per site and per user; 40,000 QPM and 30,000,000 QPD per project; plus load quotas (10-min and daily) — queries grouped by page AND query over long ranges are most expensive.
  - URL Inspection: **2,000 QPD and 600 QPM per site**; 10M QPD / 15,000 QPM per project.
  - Other resources: 20 QPS / 200 QPM per user.
- New (2026-11-16) in the Search Analytics API: `brandedClassification` (branded vs non-branded, eligible properties only), `type: webMultimodal` (Lens, Circle to Search), `filterLists` for multi-country/device in one request [P, Google blog].
- Generative AI performance report (AIO + AI Mode impressions by page/country/device/date; no clicks/queries) — global since 2026-08-31; API availability not documented [P/S]. Treat as UI-only for now; check periodically.
- 16 months of data retention → seasonality baselines need ≥13 months history [I].
- Plugin use: weekly pull (last 7/28/90 days, page×query for money pages), striking-distance queue (positions 4–15 with impressions), anomaly detection, per-action evaluation, index status via URL Inspection.

### Google Business Profile APIs
- **Access approval**: request via GBP API contact form ("Application for Basic API Access") per Google Cloud project; prerequisites: a GBP verified and active 60+ days (agency's own or a client's), a website for the business, applicant e-mail listed as owner/manager on that GBP, domain-matching e-mail recommended; reviewed within ~14 days; status visible as quota 0 QPM (not approved) vs 300 QPM (approved) [P, prereqs + FAQ upd. 2026-08-28]. Practitioner reports of long waits exist [S, Google dev forum 2026-07].
- APIs: Account Management, Business Information, Performance, Verifications, Notifications (Pub/Sub), Place Actions, Lodging, plus legacy My Business v4.9 for **Reviews, LocalPosts, Media, FoodMenus** [P].
- Quotas: 300 QPM default per API; Business Information: 300 QPD create, 10,000 QPD update, **10 edits per minute per profile (cannot be increased)** [P, limits].
- Key 2026 changes [P, change log]: review reply state + policy violation fields (2026-04/07: see why a reply was rejected), review media items (2026-04), `reviewReplyUrl` (2026-07), recurring LocalPosts (2026-04), **Q&A API discontinued 2025-11-03**.
- Performance API metrics: impressions (desktop/mobile × Maps/Search), CALL_CLICKS, WEBSITE_CLICKS, BUSINESS_DIRECTION_REQUESTS, MESSAGING_CLICKS, BUSINESS_BOOKINGS, food menu clicks; monthly search keyword impressions (values below a threshold returned as threshold) [P].
- Access to each client profile still requires the agency account to be manager on it (Organization account + location groups recommended) [P].
- Plugin use: read profile completeness, categories, services, hours; draft review replies and posts for approval and publish via API; monthly performance pull.

### Bing Webmaster Tools API
- REST/JSON (SOAP/POX retired 2026-08-31) [S]. Methods: `GetQueryStats`, `GetPageStats`, `GetQueryPageStats`, `GetRankAndTrafficStats`, `GetUrlInfo`, `GetCrawlIssues`, `GetLinkCounts`, `GetUrlLinks`, `SubmitUrl`, `SubmitUrlBatch` (≤500/batch), `GetUrlSubmissionQuota` (up to 10,000/day, actual quota varies), `SubmitFeed`, `GetRelatedKeywords` [S, gscmagic 2026-10; github api surface].
- **AI Performance report** (Copilot/Bing AI citations, grounding queries, page mapping, intents, citation share) — dashboard; API exposure not documented [P, Bing blog 2026-02/06].
- Setup: import sites from GSC in one click [I].

### PageSpeed Insights / CrUX
- PSI v5: API key recommended; widely reported quota 25,000/day [S — not stated on the getting-started page].
- CrUX API: 150 QPM per project, free; 28-day rolling, daily updates; most SMB URLs have no data [P].

### Vercel
- Web Analytics: cookieless; Pro: $0.03 per 1k events, 12-month window, custom events with 2 properties; Web Analytics Plus $10/mo/team: 8 properties, UTM parameters, 24-month window; Hobby: 50k events/mo, no custom events [P].
- Query API: `GET /v1/query/web-analytics/events/aggregate` (group by eventName, requestPath, referrerHostname, utm*, country, device; filter; since/until) [P]; server-side `track()` from `@vercel/analytics/server` for form submissions [P].
- Speed Insights (RUM CWV) for field data [I].
- Deployments/logs/redirects via REST API or Vercel MCP (available in this environment) [P].

## 2. Paid data APIs (with real prices)

### DataForSEO (pay-as-you-go, $50 minimum top-up, balance never expires) [P, dataforseo.com 2026-11]
| Endpoint | Price | Use |
|---|---|---|
| Google Organic SERP | $0.0006/SERP (10 results) standard queue; next pages $0.00045; priority $0.0012; live $0.002 | rank tracking, competitor discovery, AIO presence |
| Google Maps SERP | $0.0006 per request (up to 100 listings) standard; live $0.002; `location_coordinate` for grid points | **geo-grid rank tracking**, competitor review counts/ratings |
| Google Local Finder | $0.0006/SERP standard | pack beyond top 3 |
| Google AI Mode SERP | $0.0012 standard; $0.004 live | AI Mode answers + citations |
| LLM Scraper (ChatGPT, Gemini UI-parity) | $0.0012/result standard; $0.0024 priority; $0.004 live | prompt panel (UI-like) |
| LLM Mentions (DB of 280M ChatGPT/AIO prompts, 60-day cycle) | $0.10/task + $0.001/row | market-level mention discovery (US-heavy; check DE coverage) |
| Google Autocomplete | from $0.0006/task | demand discovery |
| Keywords Data (Google Ads volumes), Business Data (reviews), Backlinks, On-Page | see pricing pages (multiple billing models) | volumes, review monitoring, link data |

### Other suites (if TWWA already pays for one)
- **SE Ranking**: API+MCP included in every plan — Core $129/mo (25k credits), Growth $279 (100k); PAYG $50 = 250k credits; standalone API $179/mo [S, SE Ranking 2026-06; seotoolledger 2026-11].
- **Ahrefs**: API v3 from Lite $129/mo (200k units/mo), Standard $249 (800k), Advanced $449 (2M), Enterprise $1,499/mo (annual); min 50 units/request; 1–10 units per row by field [P help.ahrefs 2026-09; S].
- **Semrush**: direct Standard API requires Business-tier subscription (~$499.95/mo historically) plus separately purchased unit packages (2M/5M/10M/20M, prices not public); 10 units/line domain organic, 40–45 units/line backlinks; MCP units included on newer "Semrush One" plans [S, multiple 2026].
- **Sistrix** (German visibility index): useful for DE sales decks; API credits per plan [I — not verified this round].
- Verdict [I]: for SMB local work DataForSEO + first-party APIs covers ~95% of needs at a fraction of the cost; add Ahrefs/SE Ranking only for backlink research on competitors.

### Local rank grid: buy vs build
- Local Falcon: 1 credit per grid point; packages $24.99–199.99/mo for 7.5k–63k credits; PAYG $0.05/credit; API from Starter [P].
- BrightLocal Track: geo-grid for 5 keywords + Local AI Visibility Tracker, $41/mo per location [P]. Whitespark grids from $10/mo [P].
- **Self-build with DataForSEO Maps**: 7×7 grid (49 points) at ~1.5–2 km spacing (rural) or 0.5–1 km (urban) × 10 keywords × weekly ≈ 2,100 requests/month ≈ **$1.30/month** in standard queue [P price; I calc]. Metrics: ARP (average rank position), ATRP (average total rank incl. not-found = 21), SoLV (share of points in top 3). Compute competitor SoLV from the same responses at no extra cost.
- Caveat: Maps results reflect "search this area" behaviour; pack (Search) and Maps app rankings differ; validate with occasional manual checks [P DataForSEO note; I].
- Legal/ToS: Google's spam policy calls scraping results for rank-checking "machine-generated traffic" against ToS; using a third-party data provider keeps automated queries off the client's and TWWA's infrastructure; it does not affect the client site's rankings [P/I].

### AI visibility APIs (direct)
- OpenAI Responses API web_search tool: $10 per 1k calls + search content tokens at model rates (or $25/1k "preview" for non-reasoning models with free content tokens); set `user_location` (defaults to US if omitted!) [P].
- Gemini API grounding with Google Search / Google Maps (Gemini 3+): 5,000 free requests/month shared, then $14/1k [P].
- Perplexity: Search API $5/1k; Agent API `web_search` $0.0025/call + tokens; fast search $0.001 [P].
- Anthropic web search tool (if used): check current pricing page [I].
- API ≠ consumer UI (see 04) → prefer UI-parity scraping (DataForSEO LLM Scraper) for ChatGPT/Gemini share-of-voice; use APIs for cheap exploration and for grounding-source analysis.

## 3. Free demand sources
- Google Keyword Planner (needs Ads account; ranges for low-spend accounts) [I].
- Google Trends DE (seasonality per Bundesland) [I].
- GSC queries (best source after a page exists).
- Bing `GetRelatedKeywords` [S].
- People Also Ask / autosuggest: via SERP/Autocomplete APIs (cheap) rather than scraping (ToS) [P/I].
- Customer inquiries text from `api/contact.js` (best qualitative source of real questions) [I].

## 4. Per-client monthly data cost estimate (typical single-location SMB) [I]
| Item | Volume | Cost |
|---|---|---|
| GSC, GBP, Bing, PSI/CrUX, Vercel Query API | — | $0 |
| Vercel Web Analytics events | ~10–30k events | $0.30–0.90 (Pro) |
| Vercel Web Analytics Plus (UTMs) | per team, shared across all clients | $10 total |
| Geo-grid (DataForSEO Maps) | 7×7 × 10 kw × 4.3/mo | ~$1.30 |
| Organic rank tracking (top 30) | 60 kw × weekly | ~$0.50 |
| AI Mode + AIO checks | 40 prompts × 3 runs × 4.3 | ~$0.60–0.80 |
| ChatGPT + Gemini UI-parity (LLM Scraper) | 40 × 3 × 2 engines × 4.3 | ~$1.25 |
| Perplexity API | 40 × 3 × 4.3 | ~$1.50–3 |
| Optional OpenAI API exploration | 500 calls | ~$5–10 |
| **Total** | | **≈ $5–20 per client per month** |
LLM tokens for the agent itself (Claude Code runs) are the larger cost line; budget per weekly run and cap (see 11).

## 5. Data model the plugin should persist (per client repo, `growth/`) [I]
- `business.json` (canonical NAP, categories, services, service area, hours, price ranges, USPs, legal identifiers)
- `keywords.yml` (clusters, intent, priority, target page)
- `prompts.yml` (AI prompt panel, locale)
- `competitors.yml` (auto-maintained from Maps top-20)
- `actions.jsonl` (action log with windows/verdicts)
- `snapshots/YYYY-WW/*.json` (GSC, GBP, grid, AI panel raw + parsed)
- `leads/` (pointer only; personal data stays out of git)
- `offsite.yml`, `reviews.yml` (velocity targets), `reports/YYYY-MM.md`
Secrets (API keys, OAuth tokens) never in git: use environment/keychain/Vercel env [I].
