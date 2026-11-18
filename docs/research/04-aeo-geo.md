# 04 · AEO / GEO for local businesses

Confidence legend: [P] primary · [S] secondary · [V] vendor claim · [I] inference/recommendation.

## 1. How each engine selects sources (what is documented vs inferred)

| Engine | Retrieval layer (documented) | Local data layer | Evidence |
|---|---|---|---|
| **Google AI Overviews / AI Mode** | Google index; "query fan-out" issuing multiple related searches across subtopics and data sources. Eligibility = indexed + eligible for a snippet. "No additional requirements", "no special schema", "no AI text files" needed. Controls: robots for Googlebot, `nosnippet`/`data-nosnippet`/`max-snippet`/`noindex`; separate Search Console toggle (global since 2026-08-31) to opt out of generative AI features. | Business Profile + Maps data ("Checking that your Merchant Center and Business Profile information is up-to-date") | [P] Google Search Central "AI features and your website" (upd. 2025-12-10); [P] Search Console AI reports blog 2026-06/08 |
| **Gemini app / Ask Maps** | Google Search grounding; Google Maps grounding (also exposed in Gemini API) | Maps/GBP; Ask Maps answers from profile, reviews, photos, website, third-party sources; Europe rollout announced 2026-11-16 | [P] Google blog 2026-11-16; [S] BrightLocal 2026-04 |
| **ChatGPT search** | Rewrites prompt into one or more targeted queries sent to third-party search providers (Microsoft named in privacy links); uses approximate IP location; may share general location with "trusted third-party providers … such as nearby business listings". Crawler for inclusion: OAI-SearchBot (robots change effective ~24 h). | **Yelp** confirmed by Yelp (shareholder letters 2026-02 and 2026-08: Yelp ratings/reviews power ChatGPT local "in relevant categories"); Foursquare claim (60–70%) refuted in a 2,879-query test (0.00% of citations); Yelp data behind 95.83% of business cards in that test (US). | [P] OpenAI help center; [S] Yelp letters via askedabout/irongoo 2026; [S] Steady Demand test 2026-08 |
| **Microsoft Copilot / Bing** | Bing index; Bing Webmaster Tools "AI Performance" report (Copilot, Bing AI summaries, select partners) with grounding queries, cited pages, citation share (2026-02/06). IndexNow supported. | Bing Places | [P] Bing blog 2026-02-10, 2026-06-16 |
| **Perplexity** | Own index + web search; balanced source mix; Yelp/TripAdvisor data partnerships reported | Directories heavy for "best of" | [S] Yext 2025-10 |
| **Claude** | Web search tool; SOCi reports Claude appears to use Google Places API for local | Places/Maps, reviews/social (24% of food citations) | [S] SOCi 2026-11; Yext 2026-11 |
| **Apple Intelligence / Siri** | Apple Maps data | Apple Business (+ Das Örtliche as Apple data source in DE) | [S] soeners 2026-10 |

Key nuance: **citation ≠ recommendation**. A platform (Yelp, GBP) can supply data while the business gets the mention; licensed feeds produce no URL citation [S, askedabout 2026-10]. Measure *mentions of the business name* separately from *citations of its domain*.

## 2. What the data says about local AI visibility

- **AI is far more selective than the pack.** SOCi 2026 LVI (~350k locations of 2,751 US multi-location brands): ChatGPT recommended 1.2% of locations in its top 5, Perplexity 7.4%, Gemini 11.0%, vs 35.9% in Google's 3-pack [S/V]. SOCi's later update: average AI visibility rose to 36.1%, roughly matching traditional local platforms (methodology changed) [V, SEL 2026-11-10].
- **What gets cited for local queries**:
  - BrightLocal (200k prompts, 1,300 locations, US/UK/AU, 2026-09): GBP 28.6% of citations; Yelp 9.5%; Facebook 2.2%; business websites = 93% of unique cited domains and 42% of all citations; ChatGPT averages 4.1 businesses per answer, AI Mode 3.5, AIO 2.5; empty answers 10–11% [P].
  - Yext (6.8M citations, 2025-07/08): 86% of citations from sources brands own or manage (websites + listings); Gemini 52% from business websites; OpenAI 48.7% from listings; Perplexity 24% from industry directories on "best of" prompts [S]. Yext 2026-11 (17.2M citations, 4 engines): 90.6% to brand site or its profiles on maps/directories/apps [V].
  - Germany-specific small test (seorado, 40 ChatGPT answers): Das Örtliche in 21/40 search results, WerKenntDenBesten 20/40, Gelbe Seiten 17/40, Jameda cited in 7/10 for dentists/physio [S, n small].
- **Whitespark 2026 "AI search visibility" top factors (expert opinion)** [P]: 1 Presence on expert-curated "best of" lists (179) · 2 Dedicated page per service (170) · 3 Prominence on key industry-relevant domains (167) · 4 Authority of unstructured citations: newspapers, blogs, gov, associations (160) · 5 Authority of third-party review sites (156) · 6 Geographic relevance of content (153) · 7 Quantity of unstructured citations (147) · 8 High Google rating (146) · 9 Niche focus (138) · 10 Scannable content structure (137) · 11 Diversity of review sites (136) · 12 Unlinked brand mentions (135).
- **Reviews**: recommended locations ~4.2–4.3★ average across ChatGPT/Claude/Gemini; review volume offsets rating deficit [S/V, SOCi].
- **Query class matters for Google AIO**: Whitespark (540 US queries, 2025-05): pure local-intent queries showed AIO 15% (pack 93%); informational 92% (pack 6%); hybrid ("average cost of dental implants in Phoenix") 97% (pack 17%) [S]. Synup (53,900 SERPs, 2026-09): AIO on 4% of "near me", 8.6% of "[category] [city]", 27% of "best [category] in [city]", 75% of "[category] for [specific need]" [S]. Conflicting small sample (GeoParrot 6/6 local queries with AIO) [S, n=6].
- **Click impact of AIO**: Ahrefs (300k keywords, 2025-12 vs 2023-12): position-1 CTR −58% when an AIO is present; Seer −61% organic CTR on AIO queries; Amsive −15.5% [S]. Indig/Clickstream (846k sessions, 2026-02/03): in AI Mode 88% accept the AI shortlist, 74% pick the first item, 64% click nothing; in AIO SERPs users compare and re-scroll more [S].
- **Implication [I]**: service+town pages are protected by the pack (low AIO rate); cost/how-to/"best X for Y" pages are where AIO/AI Mode answer the user — so those pages must be built to be *cited and named*, and must convert the fewer clicks they get.

## 3. Variance and how to measure share of voice reproducibly

- SparkToro × Gumshoe (2,961 runs, 12 prompts, ChatGPT/Claude/Google AI, 2025-11/12): <1 in 100 chance of the same brand list twice; ~1 in 1,000 for same order; list length varies 2–10+. **Visibility % (how often a brand appears across many runs) is stable enough to track; rank position is not.** Smaller markets (regional services) are more stable [S, SEL/SEJ 2026-01].
- BrightLocal local repeat runs: 20–33% overlap of result sets between repeats; a business seen once reappears ~50% (ChatGPT, AI Mode) to 58% (AIO) of later attempts; 71–80% of businesses appear in ≤ half the attempts [P].
- Otterly (vendor): 50–100 prompts per market; 100 daily prompts cut coverage variance ~73% vs 10 [V].
- **API ≠ UI**: NUS paper (arXiv 2610.15382, 2026-10): Responses API + Google results together recover only ~25% of URLs ChatGPT Web cites; hostname/entity level matches better (~50% of sites) [P]. Malte Landwehr (555 prompts × 47 runs each path): brand visibility differed 41% on average; API fan-out ≤7 queries vs UI ≤20; API cites far fewer listicles (4% vs 25%) [S]. Genezio (3,645 conversations): zero overlap in fan-out queries API vs UI [V].
- **OpenAI API location default**: `user_location` defaults to the **United States** if omitted; pass `{type:"approximate", country:"DE", city:"Musterstadt", region:"<Bundesland>", timezone:"Europe/Berlin"}` [P, OpenAI API reference].
- Gemini: Google Search grounding and Google Maps grounding for Gemini 3+ models: 5,000 free requests/month (shared), then $14 per 1,000 [P, AI Studio pricing 2026-11].
- Perplexity: Search API $5/1k requests; Agent API web_search tool $0.0025/call + model tokens [P].
- DataForSEO: LLM Scraper (UI-parity scraping of ChatGPT & Gemini) $0.0012/result standard queue, $0.004 live; Google AI Mode SERP $0.0012 standard; LLM Mentions database (ChatGPT + AIO, 280M prompts, 60-day refresh) $0.10/task + $0.001/row [P, dataforseo.com pricing 2026-11].
- Bing Webmaster AI Performance: free first-party citation data for Copilot/Bing incl. grounding-query→page mapping and citation share [P].
- Google Search Console Generative AI report: AIO + AI Mode **impressions** by page/country/device/date; no clicks, no queries; global since 2026-08-31 [P].

### Prompt panel protocol (proposed for the plugin) [I]
1. **Panel size per client**: 30–60 prompts (local SMB markets are small and stable; scale to 100 for multi-service/multi-town clients). Composition: 40% "best/empfehlenswert [Gewerk] in [Stadt]" variants, 25% need-specific ("[Gewerk] für Altbau/Denkmalschutz in [Stadt]", "Steuerberater für Handwerker Musterstadt"), 20% cost/process questions with locality ("Was kostet Fassadenanstrich in [Region]"), 15% brand prompts ("Erfahrungen mit [Firma]", "Ist [Firma] seriös").
2. **Locales**: German language; for each prompt set approximate location = client town (OpenAI `user_location`; Perplexity/Gemini via prompt + parameters; DataForSEO location codes for AI Mode).
3. **Engines**: ChatGPT (UI-parity via DataForSEO LLM Scraper, plus optional API), Google AI Mode (SERP API), Google AIO (from organic SERP API result), Gemini, Perplexity; Copilot via Bing AI Performance report (first-party).
4. **Runs**: 3 runs per prompt per engine per measurement; weekly cadence (monthly for small clients). Report **mention rate** = runs mentioning client / total runs, with Wilson 95% interval; competitor mention rates; cited domains frequency; client-domain citation rate.
5. **Change significance**: only claim movement if intervals don't overlap or if ≥4 consecutive weekly points trend the same direction (practical rule).
6. **Parse**: extract business names via fuzzy match against a competitor list built from Maps SERP top-20 for the client's categories + towns; store raw answers for audit.
7. **Cost**: 40 prompts × 4 engines × 3 runs × 4.3 weeks ≈ 2,064 calls/month ≈ $3–25/month depending on path (scraper ≈ $0.0012–0.004/call; OpenAI API ≈ $0.01 + tokens) — see 10.

## 4. What measurably increases citation and mention for a local business

Ordered by evidence strength for *local* prompts [synthesis I, with sources]:
1. **Be present and strong on the data layers the engines read**: GBP (largest single cited source), Bing Places, Apple Business, Das Örtliche/Gelbe Seiten/11880/WerKenntDenBesten, vertical portals; consistent NAP; high rating + recent volume (≥4.3★ appears to be the inclusion bar; reviews mentioning services) [P/S BrightLocal, SOCi, Yext].
2. **Own website with one page per service and explicit local facts** (service area towns, prices/ranges, process, guarantees, certifications, response times) — business sites are 42% of local citations and 93% of cited domains [P BrightLocal]; Whitespark #2 AI factor [P].
3. **Third-party editorial mentions**: local press, Verbände/Innungen/Kammern pages, manufacturer partner pages, "best of" roundups — Whitespark AI factors #1, #3, #4, #7, #12 [P]. Klano also points to "Einträge bei Verbänden, Kammern und Partnern oder ein Bericht in der lokalen Presse" [P].
4. **Answer-ready content blocks**: short factual answers near the top (definition/price range/time frame), tables (price by m², material comparison), named author with credentials, dated updates. Scannable structure is Whitespark AI factor #10 [P]. This is SEO hygiene, not a special format.
5. **Authentic UGC presence** where locals ask (gutefrage.net, Reddit r/de / city subs, local Facebook groups, nebenan.de): only real, disclosed participation (Ethan Smith's Reddit rule) [S]. For Handwerk/Kanzlei this is low-volume but can surface in AI Mode "Discussions" blocks (Synup: forum blocks on 39% of service-qualified local queries in the US) [S].
6. **Bing hygiene**: verify in Bing Webmaster Tools, submit sitemap, IndexNow on deploy — Copilot and ChatGPT's search partner rely on Bing's index [P/S].

What does **not** have evidence:
- **llms.txt**: Ahrefs (137k domains, 2026-05 logs): 97% of llms.txt files received zero requests; AI bots never request it if absent [P]. SE Ranking (300k domains): no relationship with citations [S/V]. Trakkr (37.9k domains): 6.8 vs 6.7 citations, p=0.85 [S/V]. 66-day log test: zero verified AI-crawler requests for /llms.txt, while crawlers did fetch robots.txt, sitemaps and Markdown copies of pages [S]. Google: no AI text files needed [P]. → Optional, near-zero cost, never sold as a lever. Serving clean HTML matters more.
- **Schema for AI citation**: Ahrefs (1,885 pages that added JSON-LD vs matched controls): AI Mode +2.4%, ChatGPT +2.2% (not significant), AIO −4.6% (significant, not attributed) [S, SEJ 2026-05]. Google: "no special schema.org structured data that you need to add" [P]. → Keep LocalBusiness/Service/Breadcrumb schema for entity clarity and correctness, not as an AI lever.
- **Wikipedia/Wikidata**: SMBs rarely meet notability; creating self-promotional entries violates Wikipedia rules and gets deleted [I]. Wikidata entries for clearly notable firms (e.g., long-established Kanzlei with press coverage) are possible but low priority.
- **Manipulating AI answers**: Google's spam policy now defines spam as including "attempting to manipulate generative AI responses in Google Search"; and Google's AI-features guide (2026-05) states that making pages mainly to manipulate AI responses violates the scaled content abuse policy [P/S]. No fake listicles, no self-published "Top 10 Stuckateure in X" with the client at #1 on the client's own site.

## 5. Example: "bester Stuckateur in Musterstadt" / "Steuerberater für Handwerker Musterstadt" [I]
What an engine needs to name the client:
- Entity facts: name, town, Gewerk/Kanzlei type, services list, service area, contact — consistent across GBP, Bing, Apple, Das Örtliche, website.
- Quality evidence: ≥4.3★ with recent text reviews mentioning "Fassade", "Altbau", "Putz" / "Handwerksbetriebe", "Lohnbuchhaltung Bau".
- Niche proof on the website: "Steuerberatung für Handwerksbetriebe" page with specifics (Bauabzugsteuer §48 EStG, Soka-Bau, Baulohn, Kalkulation, typical client sizes, Innung cooperation), case examples, author/team credentials.
- Third-party confirmation: Innung/Kreishandwerkerschaft partner listing, local press piece, manufacturer partner finder (Sto/Caparol), steuerberater.de profile with "Branchen: Handwerk".
- For "bester": rating, review count, awards/certifications that are real (e.g., "TOP Stuckateurmeister" membership), explicit years in business.

## 6. Implications for the plugin [I]
- `/twwa-ai-visibility` = reproducible prompt panel, multi-run, German-localised, mention rate with confidence intervals, cited-source analysis that feeds the off-site queue ("these 6 domains are cited for your prompts; you're absent on 4").
- AI work is mostly *local SEO + entity consistency + third-party mentions + answerable service pages*; the plugin must not sell or produce special AI files/schema as levers.
- Pull Bing AI Performance and GSC Generative AI impressions as free first-party AI KPIs.
- Robots policy default: allow Googlebot, Bingbot, OAI-SearchBot, PerplexityBot, ChatGPT-User, Claude-SearchBot/Claude-User; decide training bots (GPTBot, Google-Extended, CCBot, ClaudeBot) per client preference (training opt-out does not affect search inclusion for Google per docs) [P/I].
