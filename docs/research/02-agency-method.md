# 02 · How strong SEO / local SEO / AEO agencies run engagements

Confidence legend: [P] primary · [S] secondary · [V] vendor claim · [I] inference/recommendation.

## 1. What separates agencies that get results from those that don't

Distilled from Grow and Convert, Sterling Sky/Joy Hawkins, Whitespark/Darren Shaw, Graphite/Ethan Smith, Kevin Indig, SEOLabs, Handwerksratgeber and churn surveys.

1. **They pick the money queries first ("bottom-up").** Grow and Convert's Pain Point SEO starts with customer research, then targets (1) category keywords ("what you sell"), (2) comparison/alternatives, (3) jobs-to-be-done keywords with buying intent, and only later top-of-funnel [P, growandconvert 2025-09]. Their 95-article study: main category keywords converted 4.85%, alternatives 8.43%, "vs" 5.45%, JTBD 2.44% [P, 2023-09]; a 64-article client: BOFU 4.78% vs TOFU 0.19% conversion (25×), BOFU produced 77% of conversions from 12% of traffic [P, 2022-04]. Local translation: "Stuckateur Musterstadt", "Fassade streichen Kosten", "Steuerberater für Handwerker Musterstadt" before any "Ratgeber".
2. **They measure conversions per page, not traffic.** Grow and Convert reports conversions per article (last/first click). Sterling Sky's case studies start with "identifying & assigning conversion actions that drive real-world business" before content [P, sterlingsky LawnSavers]. SEOLabs fixes the website and tracking *before* building visibility [P].
3. **They test, they don't follow listicles.** Sterling Sky publishes controlled tests (posts don't move rankings; hiding SAB address hurt rankings; reviews stopping → drop; 80%-similar service-area pages still ranked). Ethan Smith: "Never trust best practices — validate every tactic with your own reproducible experiment": 200 questions, 100 control / 100 treatment, compare before/after [S, Lenny's/podplaybooks].
4. **They own the GBP fundamentals obsessively** (primary category, real address/pin, hours, services, reviews velocity) because GBP signals ≈32% and reviews ≈20% of local pack weight (Whitespark 2026) [P].
5. **They prune.** Sterling Sky deleted dozens of boilerplate city pages with no links/traffic, redirected to the core page, and local pack rankings rose within weeks [P, SEL 2021-04]. Results-driven agencies remove cruft; volume agencies add it.
6. **They communicate in leads and money, with a named person.** Churn surveys: top reasons for leaving an SEO provider are dissatisfaction with business results (82%) and cost (81%); 34% poor responsiveness; 27% find SEO confusing, 25% "not sure what I'm paying for" [S, SEL/Increv, US SMB survey]. vcita (500 US SMBs, 2025-04): 40% switch agencies; 56% of churn happens within 6–12 months; 60% cite lack of ROI [S]. A practitioner survey: 68% "no results after 12 months", 54% poor communication, 47% confusing reports, 31% locked out of own accounts [S/V].
7. **They set honest timelines and baselines.** Document starting point, show movement against it, celebrate milestones, explain dips proactively [S, multiple].
8. **Ownership hygiene.** Client owns domain, GBP (agency = manager), content stays after cancellation (Handwerksratgeber, Klano both promise this) [P]. "Locked out of own accounts" is a top-5 churn reason.

## 2. Engagement blueprint (synthesised, adapted to TWWA)

### Phase 0 — Onboarding (week 0–1)
Inputs to collect (store in repo `growth/` folder, see 11):
- **Business truth**: legal name exactly as on signage/Impressum, address, phone(s), opening hours incl. holidays, service area (towns/PLZ, ≤20 areas, ≤ ~2 h drive per Google SAB rules [S]), services with price ranges, minimum order value, response-time promise, capacity (how many new jobs/month are wanted, which are high-margin), seasonality.
- **Access**: GSC (owner or full user), GBP manager access (never ownership transfer), Bing Webmaster (import from GSC), Vercel project, call tracking (if any), Resend/inbox for forms, existing directory logins.
- **Proof assets**: last 12–24 months of projects (town, service, date, photos, m², material, duration, price band if shareable), certificates (Meisterbrief, Innung, Kammer, manufacturer partner), team bios, reviews on all platforms.
- **Goals in owner language**: "X qualified inquiries/month for Y service in Z area", average job value, close rate → revenue goal.
- **Legal**: AVV (Art. 28 DSGVO) with TWWA for processing GSC/GBP/lead data [P, Klano does this], consent for review-request emails (see 03), permission to publish project photos/addresses (street-level anonymised).

### Phase 1 — Audit (week 1–2) — "Check"
Order matters: tracking → GBP → site → competitors → AI.
1. Tracking baseline: are form submissions and tel:/WhatsApp clicks counted (Vercel custom events need Pro plan [P])? Current monthly leads by channel (ask owner if no data).
2. GBP audit: primary/secondary categories vs top-3 competitors, NAP match, pin, hours, services (predefined + custom), photos (own, recent), review count/rating/recency/response rate vs competitors, duplicates, suspension risk (keyword-stuffed name, virtual office).
3. Local pack geo-grid baseline for 5–10 money keywords (7×7 grid around the business; see 10).
4. Site: indexation (GSC page indexing, URL inspection), CWV, title/H1 per service, one page per service, location relevance, internal links, schema, NAP in HTML, conversion elements per page (call button, form, trust, price anchor).
5. Competitor gap: which service × town pages do the top-3 local organic results have that the client lacks; their review velocity; their directory/Verband presence.
6. AI baseline: prompt panel (see 04) — mentioned yes/no per engine, who is named instead, which sources are cited.

### Phase 2 — Plan (week 2) — "Plan"
Rank actions by **expected leads per effort** with confidence; group into:
- Quick wins (days): GBP category/services/hours fixes, missing tracking, title/H1 rewrites on money pages, call CTA on mobile, NAP mismatches, broken redirects.
- Foundations (weeks): one page per core service, review engine, Bing/Apple listings, core citations, schema.
- Growth bets (months): service × town pages with real evidence, cost pages, Förder pages, case-study library, Verband/manufacturer listings, local PR.
Present as a one-page German plan with "Was wir tun / warum / was du lieferst / wann wir messen".

### Phase 3 — First 90 days
| Window | Typical work | What should move |
|---|---|---|
| Days 1–14 | Tracking, GBP fixes, technical fixes, money-page rewrites, Bing Places/Apple Business | GBP category/hours effects visible in 2–7 days; recrawl of edited pages in days |
| Days 15–45 | Review engine live, 3–6 new/rebuilt service pages, citations core set | GSC impressions on new pages; first review velocity gains |
| Days 46–90 | Location pages with evidence (only where demand), cost page(s), first case studies, outreach to 3–5 local/branch sources | Local-pack grid coverage, non-brand clicks, first attributable inquiries |
(Timelines: see 11 for evidence.)

### Phase 4 — Monthly cadence (steady state)
- Weekly (automated): data pull, anomaly detection, action-window evaluations, approval queue of next actions, review replies drafted for approval.
- Monthly (human): 1 report + optional 15-min call; 2–6 shipped actions; 1 owner input request ("3 photos + 3 sentences about a recent job").
- Quarterly: re-plan; AI prompt panel refresh; prune/consolidate underperforming pages; competitor review.

## 3. Reporting in revenue/lead terms

What strong local agencies report (Sterling Sky, Handwerksratgeber, SEOLabs, Whitespark advice):
- **Primary**: qualified inquiries by channel (form, call ≥60 s, WhatsApp, GBP call clicks), by service, by town; estimated pipeline value = inquiries × close rate × avg job value (owner-supplied).
- **Secondary**: GBP actions (calls, website clicks, direction requests, messaging clicks — Performance API [P]), local-pack grid coverage, non-brand organic clicks (GSC branded filter now available in API, 2026-11-16 [P]), AI mention rate.
- **Context**: what was shipped, what is next, what we need from you.
Format: one page, German, numbers vs last month and vs baseline, 3 bullets of interpretation, no jargon. Portal cost comparison ("Eine Anfrage über Portale kostet €50–120 und geht an 3–5 Betriebe") gives owners a value anchor [I].

## 4. AEO-specific agency method (Graphite / Ethan Smith)
[S, Lenny's 2025-09 + Graphite 2026-03]
- LLM answers = model + retrieval summarising many citations → "being mentioned most often beats ranking first".
- Split work: on-site (answer every follow-up question: features, use cases, prices, areas, integrations) and off-site (show up in the citations: video, UGC like Reddit/Quora, affiliates/editorial lists, blogs).
- Question research: convert keywords to questions; mine sales calls, support, forums.
- Long tail is larger in chat (≈25-word prompts vs ≈6-word queries) [V/S].
- Reddit: one real account, name + employer disclosed, genuinely helpful comment; "five good comments can transform visibility"; spam accounts get banned [S].
- Experiment design with control group of questions.
- LLM traffic converted 6× better than Google search at Webflow [V].
Local German translation [I]: off-site citation groups are GBP, Das Örtliche / WerKenntDenBesten / Gelbe Seiten, branch portals (MyHammer profiles, ProvenExpert, Jameda, anwalt.de, steuerberater.de), local news, Verbände/Kammern, manufacturer partner finders, gutefrage.net / local Facebook groups / nebenan.de (authentic participation only).

## 5. German-market specifics observed
- German owners distrust guarantees and long contracts after bad experiences with phone-sold "Unternehmensprofile" and fake-lead cooperations [S]. Monthly cancellable after a short minimum (3 months) is common [P, Handwerksratgeber].
- Exclusivity per region/Gewerk is used as a sales lever (SEOLabs) [P].
- Price anchors: €99–349/mo productised; €800–2,500/mo managed local SEO; €1,500–5,000/mo full agency [S].

## 6. Implications for the plugin [I]
- The entry skill must enforce the order **tracking → GBP → money pages → reviews → evidence-backed expansion → off-site**, because that is the order in which leads appear.
- Every proposed action must carry: hypothesis, expected metric, measurement window, owner effort, risk class.
- Reports must be lead-first and German; never ship a report without an "inquiries" number (if unknown, ask the owner for a count and record it as self-reported).
- Build a prune/consolidate routine into the quarterly loop.
