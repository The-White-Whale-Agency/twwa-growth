# 01 · Benchmarks teardown

Research date: 2026-11-16. Confidence legend used across the dossier:
**[P]** primary/verified (official docs, the tool's own site, original study read directly) · **[S]** secondary (trade press, practitioner analysis) · **[V]** vendor/self-reported claim (unverified) · **[I]** inference or recommendation by the research lead.

The goal of this file: for each comparable product, what it actually does step by step, what is automated vs human, what data it must be using, what is hard to copy, what is risky under Google policy, and what TWWA should copy / improve / avoid.

---

## 1. Klano (klano.io), Germany

**What it is.** Self-serve SaaS for German SMBs ("Klartext für Suche und KI"). Founders Igor Wulf (GF) and Vincent Effertz [S, saashub]. The team says it runs its own businesses in Neuss, Darmstadt, Nürnberg and Erlangen and built Klano for them [V, klano.io 2026-11].

**Pricing** [P, klano.io + klano.io/pricing, 2026-11]: Starter €149/mo (10 new pages/mo, one-click fixes, lead inbox) · Pro €249 (30 pages/mo, "new website on request", "better visible in ChatGPT & Co.", 5 competitors) · Business €349 (100 pages/mo, team access). 3-day free trial, monthly cancellable, net prices. An older listing shows a €49 "Basic, 10 articles" plan, so pricing has moved upward [S, saashub]. Positioning line: "Agenturen nehmen oft 1.500–2.000 € im Monat" [P].

**Step-by-step workflow (as published)** [P]:
1. Enter URL → free "Sichtbarkeits-Check" (no login preview; full to-do list against email). Checks: HTTPS reachability, title/description, crawlability for search and AI, mobile; then "which queries you already appear for, where you're just off page 1, and whether Google/AI answers name you or competitors" ("live, without access to your accounts").
2. Connect site (WordPress plugin with one-click fixes; Wix direct; generic webhook; everything else gets copy-paste drafts) and Google Search Console.
3. Klano proposes pages ("Klano schreibt, du sagst Ja"); "ca. 5 Minuten im Monat" of owner time.
4. Every article/change goes through preview + approval; "Autopilot" lets the owner whitelist what may go live without asking, default = nothing. Every change revertible "because we keep the previous version".
5. Quality check before presenting a draft: structure, length, sources; sources attached to each article for faster review. Recommends expert review for Kanzleien/Praxen.
6. Measurement: GSC-based, "Klano misst jede Maßnahme nach und zeigt dir das Ergebnis, auch wenn es mal keins gibt". Published expectation: tech fixes 7–28 days, new articles 2–8 weeks. Daily rank-drop alerts when a GSC keyword loses >5 positions. "GEO score" per article (citability heuristic). AI-visibility checks run "in festen Abständen", not continuously ("jede Prüfung kostet Rechenzeit").
7. Lead inbox: calls, mails, forms in one place.
8. Competitor gaps: "Grundreinigung Kosten fehlt dir / Fensterreinigung Nürnberg fehlt dir / Büroreinigung Nürnberg hast du" — i.e. a keyword × competitor coverage matrix.
9. Explicitly NOT done by Klano (their "7 Schritte in ChatGPT" page): NAP consistency, GBP + reviews, earning real mentions (Verbände, Kammern, Presse) — "machst du" [P].

**Data sources it must use** [I]: GSC API (owner-connected), a SERP API for "where competitors rank" (public SERPs), crawler + PageSpeed for competitor site structure/speed, LLM APIs (ChatGPT/Perplexity/Gemini) for prompt checks, call tracking provider for "Anrufe" in the inbox (unspecified).

**Case data** [V]: a Nürnberg cleaning company: +133% inquiries, +61% Google visitors month 4 vs month 1; a Neuss gasket manufacturer: relaunch with product/material/industry pages, 37 datasheets, 8 technical articles, 58 old URLs redirected → "2× inquiries first week after relaunch", +68% Google visitors in 2-week comparison. Note the very short comparison windows (2 weeks) — not a valid measurement standard.

**What is genuinely good / hard to copy**
- Approval-first, default-nothing autopilot, one-click revert with stored previous version. This is the right trust model for SMB owners.
- "Measure every action, show it even if nothing happened." Honest expectation-setting (7–28 days / 2–8 weeks) in plain German.
- Plain-language ("Klartext") reports and German-language tone learning from the existing site.
- Owner-time budget framed as "5 minutes/month".

**What is risky**
- Volume model: 10/30/100 "new pages per month" as the plan differentiator. For a local SMB, 100 pages/month is almost certainly beyond the number of genuinely distinct, demand-backed topics → scaled-content-abuse / doorway exposure (see 06). The pricing ladder rewards page count, not outcome.
- Short-window case studies (2 weeks after relaunch) overstate causality.
- Generic AI articles ("Wie-geht-das" DIY topics) carry the lowest lead value and are the most AI-Overview-cannibalised query class (see 04/05).

**TWWA: copy / improve / avoid**
- COPY: approval gate with default-off autopilot; per-action measurement with fixed windows; free check as lead magnet; revert per change; German plain-language reporting.
- IMPROVE: TWWA controls the Astro repo, so "one-click fix" becomes a real git commit + Vercel preview URL + revert commit (stronger than a WP plugin). Add the off-site and GBP work Klano explicitly leaves to the owner (reviews, GBP, citations, Verbände) — that is where local-pack visibility comes from (Whitespark: GBP 32% + reviews 20% of pack weight).
- AVOID: page-count quotas as the product. Sell outcomes (Anfragen) with page creation gated by demand and evidence.

---

## 2. Distribb (distribb.io), US/international

**Pricing** [S, aisotools 2026-11; searchblueprint 2026-09]: Pro $97/mo; Accelerator $495/mo (listed as launch price vs $990 regular in one source). 3-day trial with card. No free plan. (The brief's "$97–495" matches.)

**Step-by-step workflow** [P, distribb.io 2026-11; docs]:
1. Connect CMS (WordPress plugin exposing `/wp-json/distribb/v1/`, Webflow, Shopify, Wix, Ghost, Notion, Framer, generic webhook with `publish_articles`/`update_articles` events, idempotency key, bearer token) and describe the business.
2. Keyword research → content calendar (volume/difficulty per keyword, e.g. "3 per week starting Monday"). FAQ says it publishes "every day".
3. Writes and auto-publishes 4,500+ word articles with images, internal links, FAQ schema; "original, cited research" tables built by scraping public data. Approve-each or auto-publish.
4. **Backlink exchange**: one toggle joins a network; "ABC cycles, niche-clustered, zero manual work"; dashboard shows "links earned" and DR.
5. **"Best of" list outreach**: finds roundups that rank and list competitors, finds author contact, drafts pitch (Pro); sends + 2 follow-ups + flags replies/asking price (Accelerator).
6. GSC connection; AI visibility tracker across ChatGPT, Gemini, Perplexity, AI Overview, AI Mode with "visibility score", "share of voice", prompts tracked.
7. Background optimisation: striking-distance keywords (avg rank ~11), "stuck on page 2", internal-link boosts, titles losing clicks → one-click fixes.
8. GBP: replies to new reviews in brand voice, publishes posts/offers on schedule.
9. Repurposing: articles → short video, carousel, posts published to YouTube/Instagram/Medium/Quora "on accounts we run" (Accelerator).
10. MCP/"skill" so the customer's own AI agent can call `keyword_research`, `set_article_plan`, etc.

**Independent evidence**: one 90-day tester: 47 articles, +38% impressions, 11 contextual referring domains, 7.8/10 [S]. Trustpilot 3.6–3.9 from 8–9 reviews, bimodal; one 1-star claims "backlink exchange got me banned by Google", "content is thin" (unverified) [S/V].

**Risk assessment** [P, Google spam policies]: Google's link-spam policy lists "Excessive link exchanges ('Link to me and I'll link to you') or partner pages exclusively for the sake of cross-linking" and "Using automated programs or services to create links to your site". An automated, network-wide ABC exchange matches both. Distribb's own blog concedes "Three-way or ABC: lower [risk], still a scheme if systematic" [P, distribb blog 2026-04]. Most likely outcome is devaluation (SpamBrain neutralising), worst case a manual action. Daily 4,500-word AI articles for a local business = textbook scaled content.

**Genuinely useful ideas**: striking-distance optimiser; "best of" list gap finder (which lists rank and name competitors but not you); webhook contract with idempotency key and stable article ID; per-prompt AI visibility with engine-level cited/not-cited.

**TWWA: copy / improve / avoid**
- COPY: striking-distance queue; best-of-list gap finder (but human-sent, honest pitches); idempotent publish contract; MCP-style tool surface.
- IMPROVE: "best of" outreach for local means German local roundups ("Die besten Stuckateure in X" on local portals/newspapers/Stadtmagazine) and branch directories, not SaaS listicles.
- AVOID completely: link exchange networks, auto-publishing daily long-form, publishing on "accounts we run" (also a site-reputation / authenticity risk), auto-replying to reviews without approval.

---

## 3. SEOLabs (seo-labs.de), Munich

**What it actually is.** A done-for-you SEO + GEO + website agency, not a tool. Founded 2023 (Exa company data), Munich (Englischer Garten / Ohmstraße), "16+ specialists in-house" on site, 13–20 staff per profile data; founder/GF Robin Koppelmann (site), sales calls with Tim Koppelmann [P/S]. Claims German Web Award 2026, "100+ regional clients, 20M+ visitors, 50K inquiries" [V].

**Offer mechanics** [P, seo-labs.de 2026-11]:
- Free 60-min "Potenzialanalyse": status quo in local pack and AI search vs strongest regional competitor → calculation of realistically achievable inquiries → roadmap; "Handlungsempfehlungen in 48 Stunden".
- 5 steps: Onboarding & Analyse (question catalogue on customer search behaviour) → Website-Optimierung first ("before we build visibility": conversion tracking, heatmaps) → Google-Sichtbarkeit → KI-Sichtbarkeit → ongoing optimisation.
- Handwerk landing page ("AI-Handwerker-Methode"): promise "20–40 qualifizierte Anfragen pro Monat", "most visible business in your niche within 50 km", "written guarantee that you reach the calculated results, otherwise money back", "Premium-Website zum Selbstkostenpreis for the first 3 new clients", **"Nur 1 Betrieb pro Region"** exclusivity [P].
- No annual contract, no ticket system, own reporting dashboard with calls, inquiries, new customers [P].
- Service tags per case: SEO (technical/structural/content), GEO, Webdesign (Figma relaunch), GMB-Optimierung, PR & Linkbuilding ("hochwertige Backlinks und Branchenportal-Präsenz", "Presseartikel").
- Pricing: not published. German market ranges for comparable agencies: €1,500–5,000/mo (Ahrefs DE), ongoing local care €800–2,500/mo (practitioner) [S]. Treat SEOLabs as the premium agency benchmark.

**Case data** [V]: Bamberg floor layer: #1 "Bodenleger Bamberg", 25+ leads/mo, 20+ calls, 35+ AI citations, 12 months. Marburg roofer: 20 → 1,267 visits/mo, Sistrix 0.0001 → 0.0249, ~15 calls + 10 forms/mo, 7 months. Hamburg PV installer: 1–2 → 30 inquiries/mo, conversion relaunch after 8 months. Note how the "hard KPI" is always calls + forms; traffic value (€) is used as a soft KPI.

**What is genuinely strong**: reports in leads, website-CRO before traffic, exclusivity per region as a sales lever, case-study density (40+), named contact person.
**Risky / questionable**: "guarantee" of inquiries (German practitioners warn guarantees are met by definition games — counting any form fill [S, W&P Consulting 2026-09]); "PR & Linkbuilding" unspecified (could include paid articles; unknown).
**TWWA**: COPY lead-based reporting, CRO-before-traffic order, exclusivity per Gewerk × Region (a natural fit for an agency that builds the sites), case-study format (Ausgangslage → Maßnahmen → Anfragen). AVOID unconditional lead guarantees; if any guarantee, define "qualifizierte Anfrage" precisely (e.g. call ≥60 s or form with project description, in service area).

---

## 4. Additional comparables (DACH-relevant first)

### 4a. Handwerksratgeber.de / Ostend Digital (Stuttgart region) — closest German productised analogue
[P, handwerksratgeber.de 2026-11] Packages: "Gefunden" €149/mo + €290 setup (GBP verification/full setup, 4 GBP posts/mo from customer photos, all reviews answered, QR review cards, NAP on Apple Maps/Bing/own portal + 1 platform, monthly report vs best-rated businesses of the same Gewerk in the city). "SEO für Handwerker" €349/mo + €490 setup, monthly cancellable after 3 months: GBP up to 15 services, holiday hours, up to 20 photos; reviews answered within 3 working days, critical ones after approval; 2 more branch/regional directories per month (e.g. Innung); pages and texts belong to the client; client remains GBP owner (agency = manager). Ads tier counts "only real inquiries: calls ≥60 seconds and submitted forms", reports cost per inquiry. Explicit exclusions: bought reviews, review incentives, legal review removal, bought links/PR, guarantees on rankings.
**Lessons**: a clean, honest German package language TWWA can match; "calls ≥60 s" is a sensible qualified-call definition; owner-input requirement "jeden Monat Fotos und ein paar Sätze zu einem Auftrag" is exactly the first-party data loop TWWA needs.

### 4b. Peec AI (Berlin) — AI visibility tracker
[P, peec.ai/pricing 2026-11] Starter $95/mo (50 prompts, 3 models, daily, 1 project) · Pro $245 (150 prompts, 2 projects) · Advanced $495 (350 prompts, 5 projects, multi-country, Looker Studio) · Enterprise (API, up to 26 models). Engines: ChatGPT, Perplexity, AI Overview, AI Mode, Gemini, Bing AI mode, etc. Metrics: visibility, position, sentiment, share of voice vs competitors; prompt suggestions, intent/brand classification, "Local GEO". **Lesson**: per-prompt × per-engine × daily = "monthly AI answers" (50 × 3 × 30 = 4,500). TWWA can self-build for 1–2 orders of magnitude less per client (see 10), but Peec is the reference UX.

### 4c. Otterly.AI (Austria) — AI visibility tracker
[P, otterly.ai/pricing 2026-11] Lite €29 (16 prompts), €189 (120 prompts), €489 tiers; credits = 1 prompt × 1 engine × 1 check; Claude costs 3 credits. **Most useful published method claim** [V]: "Plan for 50 to 100 prompts per topic or market… tracking 100 prompts daily for 30 days cut the variation in brand coverage by about 73% compared to tracking 10. From 50 prompts on, the numbers become stable enough to spot real trends." Also ran a 90-day llms.txt experiment: 84 of 62,100 AI bot hits touched /llms.txt [V/S].

### 4d. Profound — enterprise AI visibility
[P, tryprofound.com/pricing 2026-11] Retired its $399/$499 Starter/Growth plans in Sept 2026; enterprise-only now (custom). Trial: 50 prompts daily for 7 days on ChatGPT, Gemini, AIO. "Agent Analytics" (AI crawler/referral traffic via CDN log integrations incl. Vercel). **Lesson**: the market is moving from "tracking dashboard" to "AI marketer agent"; TWWA's plugin is that category for SMBs.

### 4e. Local Falcon — geo-grid rank tracking
[P, localfalcon.com/pricing 2026-11] Credit = one grid point; 5×5 = 25 credits. Packages $24.99–$199.99/mo for 7,500–63,000 credits; pay-as-you-go $0.05/credit; API from Starter; on-demand API $199/mo. Tracks Google and Apple; "Falcon AI" analysis at 25 credits/report. Also publishes local AI visibility research (83% of restaurants never appeared in ChatGPT for their category/area vs 14% missing from Google, Feb 2026 data) [S via Dekodi].

### 4f. BrightLocal — local SEO suite
[P, brightlocal.com/pricing 2026-11] 1 location: Track $41/mo (audits, 100 keywords + 4 competitors, geo-grid for 5 keywords, citation accuracy, **Local AI Visibility Tracker**), Manage $54 (listing sync), Grow $65 (reputation). Research arm is the best public source on local AI citations (200k prompts, 1.9M citations, 2026-09).

### 4g. Whitespark — local tools + services
[P, whitespark.ca/pricing 2026-11] Local Ranking Grids from $10/mo; Local Rank Tracker $14–200; Citation Finder $33–149; Reputation Builder $79/location; done-for-you SEO $499–1,999/mo; listings service $20–999 one-off. Publishes the Local Search Ranking Factors survey (2026 edition, 47 experts, 187 factors).

### 4h. Uberall (Berlin/Munich) and Partoo (Paris) — listing sync platforms
[S, 2026] Both: no public prices, demo-led, 12-month contracts with auto-renew; Partoo SMB entry reportedly ~€149/mo (third-party); Uberall GEO Studio add-on €99/€399 (DE). Uberall's own "not for" list starts with single-location small businesses. Listing data may revert after cancellation (sync-model risk) [S]. **Lesson**: for single-location Handwerker, a one-time manual citation build + annual audit beats a sync subscription.

### 4i. Localo (Poland, German UI) — GBP task tool
[S, rankzilla test 2026-03] €29/€49/€79 per month (1/3/10 locations): GBP audit, local rank tracking, weekly task lists, AI post planner, review monitoring; no citation management. **Lesson**: "weekly to-do list" UX for owners is cheap and liked.

### 4j. Other German SMB offers (price anchors)
- RocketSEO "Local SEO Booster" €99/mo (GBP, directories, monitoring, reputation) [P, 2026-02].
- LokalRang (1-person, 2026) from €199/mo [P].
- Lead portals: MyHammer pay per confirmed contact (reported €8 to >€70 + 5–12% commission in some models), Check24 Profis pay per confirmed interest (market observation €50–120/inquiry), Aroundhome fixed price per qualified inquiry (max 3 partners), Blauarbeit €99–149/mo [S, multiple 2026]. Inquiries are shared with 3–5 competitors. **This is the real competitor to SEO in the owner's head**: "€50–120 per shared lead". An owned-channel inquiry at €20–40 effective cost that is exclusive is the TWWA sales argument [I].
- Directory publishers (Gelbe Seiten / Das Örtliche / Das Telefonbuch via DTME): free basic entry, but "Starteintrag" converts after 3 months to a €358.80/year subscription [S, seorado 2026-10]. Plugin must warn clients and pick the free entry.
- Warning cases: German consumer-protection blogs document "Kooperationsvereinbarung with guaranteed contacts" schemes where leads were fake [S, renner-morbach 2025-04]; WebTando disputes over phone-sold "Unternehmensprofil" invoices [S, 2026-11]. These shape owner distrust: transparency and monthly cancellation are table stakes.

---

## 5. Synthesis: what the market does vs what TWWA can uniquely do

| Capability | Klano | Distribb | SEOLabs | Handwerksratgeber | Trackers (Peec/Otterly/BL/LF) | TWWA plugin (target) |
|---|---|---|---|---|---|---|
| Site edits with approval + revert | WP plugin | WP plugin/webhook | manual | manual | — | **git commit + Vercel preview + revert commit** |
| New pages | quota 10–100/mo | daily auto | strategic | 190 €/page add-on | — | **demand- and evidence-gated** |
| GBP management | no | replies/posts | yes | yes | partial | yes, approval-gated |
| Reviews generation | no | no | ? | QR cards | BL/WS yes | **UWG-safe flows** |
| Citations DE | no | no | "Branchenportale" | 2/mo | BL | one-time build + annual audit |
| AI visibility tracking | yes | yes | yes | no | core | prompt panel, multi-run, DE-localised |
| Lead attribution | inbox | GSC only | dashboard | calls ≥60 s | — | **forms via api/contact.js + call tracking + "Wie gefunden?"** |
| Per-action measurement | yes | partial | ? | monthly | — | **action log with windows + controls** |
| Risky tactics | page volume | link exchange, auto-publish | lead guarantee | none | — | **none, enforced by gates** |

**Biggest gap in the market [I]:** nobody combines (a) full code control of a fast static site, (b) honest German local SEO incl. GBP/reviews/citations, (c) first-party-data page creation from real projects, and (d) lead-level attribution per action. That is TWWA's wedge.
