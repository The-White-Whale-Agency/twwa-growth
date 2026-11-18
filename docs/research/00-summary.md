# 00 · Summary: the 30 findings that shape `twwa-growth`

Research date: 2026-11-16. Scope: German SMB local search + AI answers → leads. Detailed evidence in files 01–12, all URLs in `sources.md`.
Confidence: **[P]** primary/verified · **[S]** secondary · **[V]** vendor claim · **[I]** inference/recommendation.

## A. What actually drives local visibility

1. **GBP is the biggest lever in the local pack**: expert weights ≈ GBP 32%, reviews 20%, on-page 15%, behaviour 9%, links 8%, citations 6% (Whitespark LSRF 2026, 47 experts). Top single factors: primary category, proximity, keywords in the business name (don't fake it), physical address in the search city, open at time of search, 4–5★ rating. [P/S]
2. **Hiding the address hurts**: Sterling Sky (8,186 businesses) found SAB status negatively correlated with "near me" rankings and reproduced a drop when hiding a client's address. Only show an address that genuinely receives customers — compliance first. [P]
3. **Posts, photos, description keywords don't move pack rankings** (controlled tests); they matter for conversion. Don't sell them as ranking work. [P/S]
4. **Review recency and steady velocity matter**: a client that stopped getting reviews for ~18 days dropped while competitors with 15–45/month held; text reviews outweigh star-only. Consumers: 74% only care about the last 3 months; 47% avoid businesses with <20 reviews; 31% require ≥4.5★. [S/P, US]
5. **German review law is stricter than Google policy**: no incentives of any kind (vouchers, raffles: LG Hildesheim 2024, OLG Frankfurt 2020, Wettbewerbszentrale 2025), no gating, §5b UWG notice wherever reviews are shown, "Kundenbewertungen" label only if verified (OLG Köln 2024). Review requests by e-mail/WhatsApp are advertising (BGH VI ZR 225/17); whether the existing-customer exception applies is disputed → get explicit consent or ask in person / by QR card. [P/S]
6. **Proximity caps the pack, not the organic layer**: local organic results are much less proximity-bound (5 firms held the top-3 organic across 72 Toronto postcodes). Growth beyond the home town = service × town pages with real local substance + prominence (reviews, local links), or a real second location. [P]
7. **City pages: evidence conflicts** — 84%-similar service-area pages still ranked for Sterling Sky (2023/24), while 2026 spam updates (Mar, Jun, Aug 18–21, Sep 24–Oct 8) reportedly hit swap-the-town-name matrices, and Google's doorway policy names "pages targeted at specific regions or cities that funnel users to one page". There is no numeric threshold in Google's docs. Resolution: allow shared boilerplate but require demand + local evidence + slow ramp + pruning. [P/S]
8. **German citations: few matter, and they matter mostly for consistency and AI**: GBP, Bing Places (now bing.com/forbusiness), Apple Business (renamed 2026-04; needs street address), DTME trio (Das Örtliche/Gelbe Seiten/Telefonbuch — use the free entry; the "Starteintrag" becomes €358.80/yr), 11880 → WerKenntDenBesten, plus vertical sources (Kammer/Innung, manufacturer partner finders like Sto, steuerberater.de / BStBK register — the DATEV Suchdienst closed 2025-12-31). Only 9/50 German portals even link dofollow. [S/P]
9. **GBP Q&A is gone; Ask Maps answers from your data**: Q&A API discontinued 2025-11-03; Gemini-powered Ask Maps answers questions from profile, reviews, photos, website, third-party sites; **announced for 30+ European countries on 2026-11-16**. Website and GBP must state facts explicitly (services, areas, prices, attributes). [P]

## B. AI answers (AEO/GEO)

10. **Google says there is nothing special to do for AI Overviews/AI Mode** beyond SEO fundamentals: indexed + snippet-eligible; no AI text files, no special schema; keep Business Profile current. Query fan-out means breadth of answered sub-questions matters. [P]
11. **ChatGPT search** rewrites prompts into queries sent to third-party providers (Microsoft named), uses approximate IP location, and draws local data from partners; **Yelp is the only confirmed local data partner** (2026 shareholder letters); the "60–70% Foursquare" claim was refuted (0.00% of citations in 2,879 queries). OAI-SearchBot must be allowed (robots change ~24 h). [P/S]
12. **AI is far more selective than the pack**: SOCi 2026 — ChatGPT recommended 1.2% of locations, Perplexity 7.4%, Gemini 11% vs 35.9% in the 3-pack; recommended businesses sit at ~4.2–4.3★; extra review volume offsets small rating gaps. [S/V]
13. **What gets cited for local prompts is mostly brand-controlled**: BrightLocal (200k prompts): GBP 28.6% of citations, Yelp 9.5%; business websites = 93% of cited domains and 42% of citations; Yext: 86% of citations from sites/listings brands control. German mini-test: Das Örtliche, WerKenntDenBesten, Gelbe Seiten appear in about half of ChatGPT's search results. [P/S/V]
14. **Expert-rated AI factors are off-site**: #1 presence on curated "best of" lists, #3 prominence on industry domains, #4 authority of unstructured citations (press, associations, gov), #12 unlinked brand mentions; #2 is a dedicated page per service. Mentions count even without followed links. [P]
15. **Query class decides AIO exposure**: AIO on 4% of "near me", 8.6% of "[Gewerk] [Stadt]", 27% of "best [Gewerk] in [Stadt]", 75% of need-specific queries (Synup, 53.9k SERPs); Whitespark: hybrid cost queries 97%. Ahrefs: AIO present → −58% CTR for position 1. Service+town pages are protected by the pack; cost/problem pages must be built to be cited and to convert the fewer clicks. [S]
16. **AI rankings are noise; mention rate is signal**: <1% chance of the same brand list twice (SparkToro, 2,961 runs); repeat-run overlap 20–33% for local; a business seen once reappears ~50% of the time (BrightLocal). Smaller (regional) markets are more stable. Measure visibility % over many runs, never "AI position". [S/P]
17. **API ≠ UI**: OpenAI API + Google results recover only ~25% of the URLs ChatGPT Web cites (NUS preprint 2026-10); brand visibility differed 41% API vs UI in a 52k-chat test. OpenAI's `user_location` **defaults to the US** if omitted. Use UI-parity scraping (DataForSEO LLM Scraper, $0.0012/result) for share-of-voice; set German locale everywhere. [P/S]
18. **llms.txt and schema are not AI levers**: 97% of llms.txt files got zero requests (Ahrefs, 137k domains); no citation correlation (SE Ranking 300k, Trakkr p=0.85); JSON-LD additions showed no clear citation lift (Ahrefs, 1,885 pages). FAQ rich results were removed 2026-05-07. Keep correct LocalBusiness/Service/Breadcrumb markup for entity clarity only. [P/S]
19. **Free first-party AI data now exists**: Bing Webmaster "AI Performance" (Copilot citations, grounding queries, page mapping, citation share) and Search Console's Generative AI report (AIO + AI Mode impressions by page; no clicks/queries; global since 2026-08-31). [P]
20. **Google treats manipulating AI answers as spam**: spam definition now includes "attempting to manipulate generative AI responses"; pages made mainly for AI mentions fall under scaled content abuse. No self-published "Top 10 [Gewerk] in [Stadt]" with the client at #1. [P/S]

## C. Content and conversion

21. **Bottom-of-funnel first**: Grow and Convert — category keywords 4.85% conversion, alternatives 8.43%, JTBD 2.44%, top-of-funnel 0.19% (25× gap). For local: core service pages → urgent services → evidence-backed service × town → cost pages → case studies → Förder → problem pages; generic DIY content last. [P]
22. **First-party data is the moat**: every money page needs ≥3 evidence items competitors can't copy (own project with town/scope/photos, real price ranges, process/timeline, local regulation/Förderung with source, named expert, local review). A monthly "Projekt-Kurzbericht" from the owner (photos + 3 sentences) feeds case studies, GBP posts, evidence blocks and review requests. [I, consistent with P sources]
23. **Förder content goes stale fast**: BEG reform effective 2026-07-21 — envelope base stays 15%, but the 5-point iSFP bonus now only applies above €30k (single unit) and only to the excess; heating cap €28k falling €750 per half-year. Pages claiming "20% mit iSFP" for typical Fassaden jobs are now wrong. Store source + verified date per claim; recheck monthly. [P/S]
24. **The real competitor in the owner's head is the lead portal**: Check24 Profis ~€50–120 per inquiry (market observation), MyHammer per contact (+ commission in some models), inquiries shared with 3–5 firms. Owned, exclusive inquiries are the value proposition. [S]
25. **Cookieless attribution is workable**: forms via `api/contact.js` with server-side Vercel events (custom events need Pro; UTMs need Web Analytics Plus, $10/mo/team), static call-tracking numbers per channel (GBP primary + real number as additional), GBP Performance API (calls, website clicks, directions, messaging), GSC (now with branded/non-branded in the API, 2026-11-16), and a mandatory "Wie haben Sie uns gefunden?" field. DNI call tracking needs consent (§25 TDDDG); avoid by default. [P/S]

## D. Operating model, data and economics

26. **Measure every action in fixed windows**: tech fixes 7–28 days, new pages 2–8 weeks to first impressions (28–90 d evaluation), GBP category 2–14 days, reviews 30–90 days, citations/links 60–180 days (Klano publishes 7–28 d / 2–8 w; Sterling Sky/Whitespark tests). Small sites rarely reach significance → use control pages, leading indicators, and honest "inconclusive". [V/P/I]
27. **Gates must be code, not prose**: practitioner failure logs show documented sign-off gates bypassed, non-idempotent publishers creating duplicates, agents trusting their own stale notes, self-reviews agreeing with themselves. Use exit-code scripts in the ship path, idempotent publishing, live-data-first, fresh-process reviewers, step/time/spend caps and a STOP file. [S]
28. **Data is cheap; labour is the cost**: GSC/GBP/Bing/CrUX/Vercel APIs are free (GBP needs approval: verified GBP 60+ days, website, ~14-day review, 300 QPM, 10 edits/min/profile). DataForSEO: Maps SERP $0.0006 (7×7 grid × 10 keywords weekly ≈ $1.30/mo), AI Mode $0.0012, LLM scraper $0.0012. Total ≈ $5–20 per client per month vs Local Falcon/BrightLocal/Peec subscriptions. [P/I]
29. **Benchmarks show what to copy and avoid**: copy Klano's default-off autopilot, per-change revert, per-action measurement and plain-German reports; copy Handwerksratgeber's honest packages ("calls ≥60 s count as inquiries", client owns GBP/content); copy SEOLabs' lead-first reporting, CRO-before-traffic and exclusivity per region. Avoid Klano's page-count quotas, Distribb's automated link exchange (Google: "excessive link exchanges" and "automated programs… to create links" are link spam) and daily auto-published long-form, and unconditional lead guarantees. [P/S]
30. **SMB churn is about results and clarity**: 82% leave over results, 81% cost, 34% responsiveness; 25–27% don't understand what they pay for; 56% of agency churn happens in months 6–12. German owners distrust lock-in after phone-sold "Unternehmensprofil" schemes. → 3-month minimum then monthly, written scope, client owns assets, one-page monthly "Anfragen" report. [S]

---

## What the plugin must do — in this order, with thresholds [I]

**Step 0 · Onboard (once).** Create `growth/business.json` (canonical NAP exactly as in the Impressum; categories; services with price ranges; service area ≤20 towns within ~2 h; hours incl. holidays; capacity/margin preferences), `keywords.yml`, `prompts.yml`, `competitors.yml`. Get GSC, GBP manager, Bing (import from GSC), Vercel access. AVV in place.

**Step 1 · Check (`/twwa-check`, read-only).**
1. Tracking: form → server event works; tel/WhatsApp click events; "Wie gefunden?" field; P1 if the form pipeline fails.
2. GBP: primary category vs top-3 pack competitors; name = real name; address/pin eligibility; hours; predefined + custom services; photos recency; review count, 90-day velocity, rating, reply rate vs competitor median; suspension-risk lint.
3. Geo-grid baseline: 7×7 for 5–10 money keywords (ARP, ATRP, SoLV).
4. Site: canonical/slash consistency, sitemap/robots, preview noindex, index status via URL Inspection (≤2,000/day/site), one page per service, title/H1 = Leistung + Ort, NAP in HTML = GBP, schema = `business.json`, CWV budget, CTA above the fold, §5b notice where reviews show, Impressum basics.
5. Citations: Tier-1 presence and NAP match.
6. AI panel baseline: 30–60 German prompts × 4–5 engines × 3 runs, client location set; mention rate with 95% interval; cited domains where the client is absent.

**Step 2 · Plan (`/twwa-plan`).** ≤5 actions per cycle, each with hypothesis, metric, window, owner effort, risk class. Fixed priority order: tracking → GBP fundamentals → money-page fixes → review engine → Tier-1/vertical citations → evidence-backed new pages → off-site mentions → AI-specific refinements.

**Step 3 · Implement approved items (`/twwa-ship`).** Branch → Vercel preview (noindex) → gates (seo-checks, page gates A–H, legal lint, approval hash) → merge → production → live verification → IndexNow ping → log action. GBP edits via API: max 1 identity-level edit per 48 h. Default autopilot = none; only non-visible technical fixes may skip owner approval (still TWWA-approved).

**Step 4 · Page gates (hard).** Demand (GSC ≥10/30 impressions in 90 d, or volume >0, or ≥2 jobs in the town), real service relationship, ≥3 local evidence items (≥1 first-party), swap test (≥25% of non-boilerplate sentences become false when the town is swapped; boilerplate <60% of words), shingle similarity ≤0.6 vs any sibling, no town lists, factual sources stored, ramp ≤ max(2, 10% of indexed pages) per week and ≤8/month for sites <50 pages, pilot 3–5 pages per new template (continue only if ≥60% indexed in 28 d and ≥50% with impressions in 56 d), 90-day prune rule (0 clicks and <20 impressions → consolidate).

**Step 5 · Measure (`/twwa-measure`).** Weekly pulls; action verdicts at window end vs control pages; alerts: money query −3 positions vs 28-day baseline, any noindex/robots regression, form failure, GBP suspension, "Crawled – not indexed" >20%.

**Step 6 · Weekly loop (`/twwa-weekly`, scheduled).** Measure first → health → evaluate actions → detect opportunities (striking distance pos 4–15; CTR <50% of expected; new query clusters; review velocity below competitor median +10%; AI-cited domains missing the client; seasonal triggers 6–10 weeks ahead; Förder source changes) → ≤5 proposals → one short German owner request → snapshot.

**Step 7 · Report (`/twwa-report`, monthly).** One page, German: Anfragen (qualified, by source/service), won jobs/value (owner-reported), what we did and what it brought (incl. "noch zu früh"), GBP actions, grid image, AI mention rate, next steps, what we need. Portal cost comparison as value anchor.

**Never (linted):** review incentives or gating; fake/bought reviews; keyword-stuffed GBP names; fake addresses or per-city GBPs; link exchanges, paid followed links, footer keyword links across client sites; auto-publishing without approval; town lists; self-published "best of" lists naming the client; unverifiable superlatives; legal text changes without human sign-off.

---

## Open questions

Owner decisions are recorded in `DECISIONS.md`.

## File list
- `00-summary.md` (this file)
- `01-benchmarks-teardown.md` — Klano, Distribb, SEOLabs + Handwerksratgeber, Peec, Otterly, Profound, Local Falcon, BrightLocal, Whitespark, Uberall/Partoo, Localo, German SMB offers, lead portals
- `02-agency-method.md` — onboarding, audit, 90 days, cadence, reporting, AEO method
- `03-local-seo-germany.md` — ranking factors, GBP field playbook, suspensions, proximity, citations DE, reviews law, DSGVO/TDDDG, Impressum
- `04-aeo-geo.md` — engine source selection, local AI data, variance, prompt panel protocol, levers vs myths
- `05-content-page-types.md` — page types by lead value, first-party data, E-E-A-T, German keyword specifics, seasonality, Förder freshness
- `06-scaled-pages-quality-gates.md` — Google definitions, enforcement 2024–2026, gates A–H, recovery
- `07-technical-astro-vercel.md` — URLs, redirects, sitemaps, indexing, IndexNow, schema 2026, CWV, monitoring
- `08-offsite-authority.md` — safe vs penalised, German authority sources, local PR, best-of lists
- `09-cro-attribution.md` — CRO per vertical, cookieless attribution architecture, action→lead tying, owner reports
- `10-data-stack-apis.md` — GSC/GBP/Bing/Vercel APIs and quotas, DataForSEO and suite prices, grid self-build, cost per client
- `11-automation-kpis-timelines.md` — agent architecture, approval states, failure modes, timelines, weekly loop
- `sources.md` — all sources with date, type, confidence
