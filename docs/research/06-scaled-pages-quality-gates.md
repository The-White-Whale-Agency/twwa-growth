# 06 · Programmatic / scaled pages and the quality gates the tool must enforce

Confidence legend: [P] primary · [S] secondary · [V] vendor claim · [I] inference/recommendation.

## 1. Google's own definitions (quote-level)

From "Spam policies for Google web search" [P, developers.google.com, read 2026-11-16]:
- Spam now explicitly includes "attempting to manipulate generative AI responses in Google Search".
- **Doorway abuse**: "sites or pages are created to rank for specific, similar search queries. They lead users to intermediate pages that aren't as useful as the final destination." Examples: "Having multiple domain names or pages targeted at specific regions or cities that funnel users to one page"; "Generating pages to funnel visitors into the actual usable or relevant portion of a site"; "Creating substantially similar pages that are closer to search results than a clearly defined, browseable hierarchy".
- **Scaled content abuse**: "many pages are generated for the primary purpose of manipulating search rankings and not helping users… no matter how it's created." Examples: "Using generative AI tools or other similar tools to generate many pages without adding value for users"; "Scraping feeds, search results… (including through automated transformations like synonymizing, translating…)"; "Stitching or combining content from different web pages without adding value"; "Creating many pages where the content makes little or no sense to a reader but contains search keywords".
- **Keyword stuffing** includes "Blocks of text that list cities and regions that a web page is trying to rank for" (the classic footer town list).
- **Policy circumvention**: continuing actions intended to bypass spam policies (e.g., inflating 300 thin pages into 300 slightly longer thin pages) [P heading; S interpretation newreward 2026-08].
- Detection: automated systems (SpamBrain) and human review → manual actions; "Sites that violate our policies may rank lower… or not appear… at all" (site-level wording) [P].
- Google's generative AI guidance: AI use is fine; generating many pages without adding value may violate scaled content abuse; manual fact-check of all AI content incl. metadata/structured data/alt text is "critical" (updated 2026-10-01 per secondary) [S].
- Google's AI features guide (2026-05): no special files/markup needed; making pages mainly to manipulate AI responses breaks the scaled content policy [S, townsmith log].

**There is no numeric uniqueness threshold in any Google document.** Agency figures like "40% / 60% unique" are folklore [S, localbiz 2026-10]. The test is purpose and usefulness.

## 2. Enforcement timeline 2024–2026 (relevant to location pages)
[S, townsmith log 2026-11; skrol 2026-09; SEL]
- 2024-03: March core + spam update; new policies: scaled content abuse, site reputation abuse, expired domain abuse.
- 2024–2025: multiple core and spam updates; Aug 2025 spam update; site reputation abuse enforcement.
- 2026-03: March 2026 spam update, then core update (Mar 27–Apr 8).
- 2026-04-13: back-button hijacking added (enforced from 2026-06-15).
- 2026-05: Google AI features guide; 2026-05-07 FAQ rich results removed.
- 2026-06: June spam update.
- 2026-08-18→21: August 2026 spam update (no new policies).
- 2026-09-24→10-08: September 2026 spam update (longest of 2026).
Between 2024-03 and 2026-10: nine confirmed core updates and eight spam updates; none officially named location pages, but practitioner audits consistently find templated town pages concentrated among losers [S]. Recovery from spam-update hits "can take months" after fixing [S citing Google].

## 3. Where scaled pages DO work for local SMBs (and the conflicting evidence)

- Works: service × town pages for genuinely served towns with distinct local evidence; case-study libraries (each project is unique data); price pages per service; Klassen pages (Fahrschule); lane pages with real lanes (Spedition); niche pages for Kanzleien (each niche has different law/practice). These are "a clearly defined, browseable hierarchy" with unique value [I].
- Evidence they can work even with heavy boilerplate: Sterling Sky — 35 service-area pages averaging 84% similarity (Siteliner) still ranked and generated sales; "80/20 rule: customise 10–20% per city" (2023, reiterated 2024) [P].
- Evidence they fail: Sterling Sky also deleted dozens of boilerplate city pages without links/traffic and local pack rankings *improved* within weeks (2021) [P]; 2026 spam updates reportedly hit swap-name matrices [S].
- **Resolution [I]**: similarity alone is not the trigger; the risky combination is *many* pages × *little unique value* × *no real demand/links/engagement* × *rapid creation*. The plugin should allow shared boilerplate (process, guarantees, company facts) but require local substance and demand per page, ramp slowly, and kill pages that don't earn impressions.

## 4. Quality gates (hard rules the plugin enforces before any page can be proposed for approval)

### Gate A — Demand
Pass if at least one is true:
- GSC shows ≥ N impressions in the last 90 days for queries matching the page's cluster (N=10 for towns <20k inhabitants, 30 otherwise) — OR
- Keyword data shows non-zero volume for the cluster (Ads range > 0) — OR
- The client has completed ≥2 jobs in that town in the last 24 months (real service relationship) AND the town is within the GBP service area.
Fail → no page; add town to the parent service page's service-area section instead.

### Gate B — Real service relationship
- Town must be in `business.json.service_area` (≤ ~2 h drive; the same towns as GBP).
- Owner confirms "we actively take jobs there" (checkbox stored with date).

### Gate C — Local evidence (minimum 3 distinct items, at least 1 from group 1)
Group 1 (first-party, strongest): completed project in that town with own photos; review from a customer in that town (with consent if quoted); named team member responsible for that area; real travel time / Anfahrtspauschale for that town.
Group 2 (local facts, must be verified with source): local regulation (Denkmalschutz, Satzung, Bauamt/Landratsamt process), local Förderprogramm, local building stock characteristics (Baujahre, typical issues), local partners (Baustoffhändler, Innung).
Fail → hold page in backlog ("wartet auf Projekt").

### Gate D — Distinctness ("swap test") [I; adapted from localbiz.ai 2026-10]
- Automated: replace the town name (and Ortsteile) with the nearest sibling town; ask an LLM judge and a rule-based check which sentences become false. **Pass if ≥ 25% of body sentences (excluding shared boilerplate blocks explicitly marked as such) would become false**, i.e. are town-specific. Shared boilerplate blocks are allowed but must be < 60% of body words.
- Automated similarity: 5-word shingle Jaccard similarity of main content vs every sibling page; **fail if > 0.6** with any sibling (internal heuristic, not a Google number; calibrated so 80%-boilerplate pages with substantive local sections pass while name-swaps fail).
- No town lists in footers/body ("Wir sind tätig in A, B, C, D…" blocks of >8 towns as plain text) — use a map/region page with grouped, linked towns instead.

### Gate E — Usefulness / UX
- Page answers: what, where, price range, how fast, proof, how to contact. CTA above the fold on mobile.
- No intermediate funnel: the page itself must allow the action (call/form), not just link to "the real page".
- Word count is not a gate; substance is. But flag pages with < 250 words of non-boilerplate content as thin.

### Gate F — Factual and legal
- All claims trace to owner-confirmed facts or cited sources (stored in page frontmatter `sources:`).
- No superlatives that violate Berufsrecht/UWG ("bester", "Nr. 1") unless provable and allowed.
- §5b UWG notice where reviews are shown.

### Gate G — Velocity / ramp (anti-scale)
- New indexable pages per site per week ≤ max(2, 10% of current indexed pages), and ≤ 8 per month for sites under 50 pages [I].
- Template batches: release a new template (e.g., service × town) in a pilot of 3–5 pages; continue only if ≥ 60% of pilot pages are indexed within 28 days and ≥ 50% receive impressions within 56 days.

### Gate H — Post-launch kill/consolidate rules
- 90 days after publish: page with 0 clicks and < 20 impressions, no links, no conversions → consolidate into parent (301) or noindex, unless seasonal.
- If GSC Page Indexing shows "Crawled – currently not indexed" for > 40% of a template's pages → stop the template, improve or consolidate.
- After any confirmed spam update, compare template groups 2–4 weeks after vs before; if a template group drops > 30% while others hold → consolidate that template.

## 5. Recovery playbook (if a client is hit)
[S, townsmith 2026-06; skrol 2026-09; Google via secondary]
1. Check Manual Actions report; if present, fix named issue on all affected pages; reconsideration with examples of removed bad and added good content.
2. If algorithmic: wait until rollout completes; compare 2–4 weeks before/after per template group in GSC; separate deindexed (Page indexing) from demoted (Performance).
3. Triage each page: keep / rewrite / retire; consolidate near-duplicates first (301 to stronger page); rewrite keepers with real local substance; hold back pages without substance.
4. Don't inflate; don't delete strong pages in panic; recovery may take months / until next core update.

## 6. Implications for the plugin [I]
- Page creation is a pipeline with gates A→H; a page that fails any gate cannot reach the approval queue.
- The plan shows the *backlog with reasons* ("Nachbarort: wartet auf erstes Projekt mit Fotos"), which turns gating into an owner data request rather than a dead end.
- The weekly loop runs Gate H automatically and proposes consolidations.
- Sell "evidence-backed pages", never page counts.
