# 02 · User-level skills (`~/.claude/skills/`)

Inventory date 2026-11-16. Dossier = `../research/`; "F#" = finding in `00-summary.md`.

## 1. Scope

| Item | Value |
|---|---|
| Location | `~/.claude/skills/`, 1,111 entries; most are symlinks into `~/.agents/skills/`; installs tracked in `~/.agents/.skill-lock.json` (v3) |
| Main pack | `kostja94/marketing-skills` (GitHub, MIT per repo metadata; 167 skills here). **71 of the 167 are "moved" stubs** with no rules, pointing to the author's other repos `pagina`, `bricks`, `open-analytics` (not installed, not read) |
| Other packs read | `Leonxlnx/unlazy` (MIT, LICENSE file); `unslop` (local install, CC-BY-4.0, author Damir Sokolovsky, attribution required if adapted); `vercel-labs/agent-skills` (`writing-guidelines`; licence not checked); `heygen-com/hyperframes` v0.9.34 (`style-sampling`; licence not checked) |
| Read in depth | 58 skills (SKILL.md; no marketing skill has reference files) |
| Skimmed (frontmatter) | 62 `*-generator` + 45 others (36 marketing, 8 vercel-labs, `context7-mcp`) |
| Skipped by pattern | 946 (818 from `mukul975/Anthropic-Cybersecurity-Skills`), see `skipped.md` |
| Not read | rules that `writing-guidelines` fetches at runtime from GitHub; `unslop` references other than the copy section of `signs.md`, and its scripts; `unlazy` scripts, tests and references except headings and opening of `gates.md`; `style-sampling/references/remix.md` |

## 2. Per source

`D` distil · `C` call · `I` ignore.

| Skill | What it actually does | Phases | Use |
|---|---|---|---|
| local-seo | NAP exact-match rules, GBP field list, US citation priority list | P0 P1 P6 | D: NAP exact match, fix before adding. I: citation list (US: Yelp, BBB, Foursquare, Nextdoor), description-keyword tip |
| seo-audit | Audit order technical → on-page → content → off-page, with checklists | P1 | D: order and P0/P1/P2 labels |
| seo-strategy | Workflow order, P0–P3 roadmap ladder, paid/organic alignment | P2 | D: priority ladder. I: routing to parasite/pSEO |
| generative-engine-optimization | AI platform and crawler overview, answer-first patterns | P7 P4 | D: crawler classes, push = IndexNow only. I: schema-as-lever, parasite distribution |
| entity-seo | Organization/Person `@id` graph, cross-platform consistency | P0 P4 | D: `@id`, sameAs, consistency |
| eeat-signals | Author bio, citations, experience signals, AI-content review | P4 | D |
| schema-markup | Type choice, placement, validation, Article dates | P3 P4 | D: match-visible, required props, validation. I: FAQ, sitelinks, AI claims |
| indexing | GSC issue → fix, noindex matrix, 301/410/404 decision | P1 P3 | D |
| indexnow | Key file, submit on deploy, shared URL source | P3 | D |
| xml-sitemap | Protocol limits, accurate `lastmod`, sitemap-returns-HTML diagnosis | P1 P3 | D |
| robots-txt | Directive syntax, crawl vs index, AI bot table | P1 | D |
| canonical-tag | 301 vs canonical, no chains, HTTPS | P1 | D |
| site-crawlability | Redirect chains, orphans, depth, AI crawler 404/redirect waste | P1 | D |
| rendering-strategies | SSG/SSR/CSR choice; content in initial HTML | P1 | D (Astro SSG passes by default; check tabs, accordions) |
| core-web-vitals | p75 thresholds and fix tables | P1 | D |
| image-optimization | `<img>` not CSS bg, alt, lazy only below fold, sizes | P1 P4 | D |
| mobile-friendly | Viewport, 16 px text, 48 px tap targets, parity | P1 | D checklist; I: tool references (see §5) |
| url-structure, url-slug-generator | Lowercase, hyphens, short, 301 on change, ASCII transliteration | P4 | D, but adapt umlauts (§5) |
| website-structure | SaaS page-priority template | P4 | I, except "max 4 clicks" |
| internal-links | Depth, hub-spoke, descriptive anchors | P4 | D |
| heading-structure | One clear H1, semantic levels | P4 | D |
| title-tag, meta-description | Writing rules with swap test, length as warning | P4 | D |
| page-metadata | Metadata lifecycle with raw-HTML and production verification | P3 | D |
| open-graph | Four core tags, absolute URLs | P4 | D (minor) |
| serp-features | SERP feature catalogue, zero-click notes | P2 | I (outdated rich-result list) |
| featured-snippet | Answer-first block formats | P4 P7 | D: format rules. I: schema claim |
| keyword-research | Discovery methods, intent modifiers, autocomplete | P0 P2 | D: intent and autocomplete. I: volume floor |
| competitor-research | Keyword, content, backlink gap methods | P1 P2 | D: gap method. I: word-count targets |
| content-optimization | Word count, H2 keywords, density | P4 | I, except "word count is not a ranking factor" |
| content-strategy, content-marketing | Pillar/cluster, repurposing matrix | P4 | D: repurposing only |
| article-content | Information gain, Q→A→evidence pattern | P4 | D: information gain, answer-first. I: word counts, hook stats |
| copywriting | PAS/AIDA/BAB, CTA copy, ad-to-page match | P4 | D: CTA, promise match |
| conversion-optimization | Hypothesis, PIE scoring, A/B rules | P2 P8 | D: hypothesis format, PIE |
| programmatic-seo | Template + data pages with AI per-URL copy | P4 | D safe parts only (§3, §6) |
| parasite-seo | Rank content on third-party platforms | none | I, banned (§6) |
| link-building | List of link tactics and outreach norms | P6 | D: mentions, journalist requests, real partnerships |
| backlink-analysis | Profile metrics, toxic links, disavow caution | P1 | D: disavow only when necessary |
| directory-submission | SaaS/AI-tool directory and launch-site submission | P6 | I (wrong directory type) |
| directory-listing-ads | Paid placements on Taaft, G2, Capterra, Shopify | none | I |
| brand-monitoring | Impersonation and brand-abuse monitoring | P9 | D: Google Alerts for brand and owner name |
| public-relations | Press release structure | P6 | D (local press drafts) |
| google-ads, paid-ads-strategy | Campaign structure, bidding thresholds, incrementality | P2 | C only if Ads enter scope (open question 13); no Local Services Ads coverage |
| localization-strategy, translation | Locale launch and translation lifecycle | none | I (German-only sites) |
| unslop | De-AI-ifies UI in nine passes; has a copy pass | P4 | D: copy rules (credit author) |
| unlazy | Gate ledger with CHECK/EXPECT, approval binding, fail-closed checker | P3 P9 | D: gate semantics; C: optional for long agent runs |
| writing-guidelines | Wrapper that fetches remote rules | none | I (no local rules) |
| style-sampling | HyperFrames Pro video episode templates | none | I |
| research-sources | Source categories for content ideas | none | I |
| seo-monitoring, ai-traffic-tracking, google-search-console, analytics-tracking, traffic-analysis | Moved stubs, no rules | none | I |

Skimmed: all 60 page and block generators named in the brief (services, landing, homepage, contact, about, FAQ, testimonials, trust badges, CTA, hero, pricing, customer stories, careers, legal, privacy, cookie policy, footer, breadcrumb, how-to, comparison table, 404, and the rest) are **moved stubs with no rules** → I. Only `brand-visual-generator` (visual identity tokens) and `favicon-generator` (icon sizes) have content; both are I for growth work.

## 3. Rules worth distilling

| Area | Rule (restated) | Source |
|---|---|---|
| Title | Page-specific; main concept early; about 60 chars for the body is a warning, not a gate; brand suffix separate and never doubled; claims must be on the page; **swap test**: if the title fits a sibling page, add a verified page fact | title-tag |
| Meta | No fixed length; lead with what sets the page apart from siblings; body must back the promise; same swap test | meta-description |
| Title vs H1 | Same intent and promise, wording may differ; one clear H1; heading levels by structure, not visual size | title-tag, heading-structure |
| Metadata release | Never infer production metadata from source; check raw server HTML of samples before and after deploy: one title, one description, absolute canonical/OG, no placeholders, no double suffix | page-metadata |
| Internal links | Money pages ≤3 clicks from home; every page has ≥1 contextual inbound link; descriptive, varied anchors; links in body, not only footer | internal-links, site-crawlability |
| Crawl | Single-hop redirects; no loops; fix 4xx links; prefer pagination over infinite scroll; all tab/accordion content in the DOM | site-crawlability, rendering-strategies |
| Index | noindex,follow for thank-you, 404, filter URLs; never robots-block a noindex page; removal: 301 if a replacement exists, 410 if gone, never mass-redirect to home; then fix internal links and sitemap | indexing, robots-txt |
| Sitemap | Indexable canonical URLs only; real `lastmod`, never build time; `curl -I` must show XML content type (HTML-at-200 fails silently) | xml-sitemap |
| IndexNow | Key file at root holding the key; one batch per deploy for new/changed pages; build the URL list from the same source as the sitemap; Google does not use it | indexnow, xml-sitemap |
| Canonical | 301 for protocol, www, slash variants; canonical for params/UTMs; absolute; no chains; sitemap URLs = canonicals | canonical-tag |
| CWV | p75: LCP ≤2.5 s, INP ≤200 ms, CLS ≤0.1; never lazy-load the LCP image; width/height on all images | core-web-vitals, image-optimization |
| Mobile | Viewport meta; body text ≥16 px; tap targets ≥48 px; no interstitials covering content | mobile-friendly |
| Images | Content images as `<img>` (CSS backgrounds are not indexed); descriptive alt ≤~125 chars, `alt=""` for decoration; descriptive filenames | image-optimization |
| Schema | Mark up only visible content; stable `@id` linking Organization ↔ WebSite ↔ page; one Organization instance site-wide; BreadcrumbList must equal visible crumbs | schema-markup, entity-seo |
| Answer blocks | Direct answer in the first 40–60 words under an H2; real `<ol>/<ul>/<table>`; each block readable alone | featured-snippet, article-content |
| Information gain | Before writing, list what the top results already say; lead with what is new: own data, practitioner view, newer facts, counter-case | article-content |
| E-E-A-T | Named author with real credentials, photo, verifiable links; Person data must match the page; cite sources for every figure; human review and fact check of AI-assisted text | eeat-signals |
| Local NAP | Character-identical NAP everywhere; fix inconsistencies before adding listings | local-seo |
| CRO | Hypothesis "if X then Y because Z"; score ideas by Potential, Importance, Ease; full-week test cycles; size samples first; test mobile separately | conversion-optimization |
| CTA copy | Verb plus concrete outcome, no "Absenden"; ad or GBP promise must appear on the landing page | copywriting |
| Anti-slop copy | No exclamation marks; no hype words; changes state their baseline ("+12 % vs. Vormonat"); unverifiable claims are made specific if confirmed, else removed; no fake-looking numbers; no emoji labels | unslop |
| Scaled pages, safe parts | Evidence block per page from first-party data; log the source of every field; freshness rules (e.g. prices 30 d, ratings 90 d); launch in small batches; noindex or prune weak pages; n-gram overlap check before publish; flag sentence tails shared by >30 % of sibling pages | programmatic-seo |
| Gates | Each gate: one observable outcome, a command, an expected token; pass needs exit 0 and a match; empty or malformed ledger = failure; an abandoned gate is a handoff, never success; re-measure every number before reporting | unlazy |

## 4. Scripts and data access

| Skill | Interface | Credentials / cost |
|---|---|---|
| marketing pack (all) | Prose only; no scripts; optional `contextus.md` project file | none |
| unlazy | `node scripts/gate-check.mjs --status/--approve`, `gate-lint.mjs`, optional Stop hook via `install-hooks.mjs` | local Node, none; hook only with user consent |
| unslop | `scripts/snapshot.mjs <url>`, `story.mjs` (not read) | local; image tool optional |
| writing-guidelines | Fetches rules from raw.githubusercontent.com each run | network |
| style-sampling | `npx hyperframes` CLI, sends a usage beacon, needs HyperFrames Pro | paid plan |

## 5. Contradictions with the dossier

| Claim in skill | Dossier | Supported side |
|---|---|---|
| Schema improves AI citation; "SEO + structured data" is the best AIO path; "3.2× AI visibility" (schema-markup, generative-engine-optimization, entity-seo, featured-snippet, programmatic-seo) | Schema is not an AI lever; no citation lift (F18, 04, 07 §4) | Dossier |
| FAQ rich results "limited"; FAQ schema "triggers PAA" (schema-markup, serp-features) | FAQ rich results removed 2026-05-07 (07 §4) | Dossier |
| serp-features lists "HowTo (desktop)" as high impact | HowTo deprecated (07 §4); schema-markup itself agrees | Dossier |
| Sitelinks search box via WebSite + SearchAction (schema-markup, serp-features, entity-seo) | Not covered; Google retired the feature in 2024 [outside dossier, verify] | Against skill |
| AggregateRating/Review markup → stars (serp-features) | Self-serving LocalBusiness reviews not eligible (07 §4) | Dossier |
| GBP description: keywords in first 100 chars (local-seo) | Description keywords have no ranking effect (F3, 03) | Dossier |
| Citation priority Yelp, BBB, Foursquare, Nextdoor; "40+ sites → ~19 % more visibility", unsourced (local-seo) | German tiers; few portals matter; Foursquare refuted for ChatGPT (F8, F11) | Dossier |
| "300+ words per page", ">30 % shared tails", cycle 8–15 phrasing variants (programmatic-seo); "<300 words thin" (article-content) | No numeric threshold exists in Google docs (F7, 06); dossier gates are inference | Neither is primary; keep as heuristics, reject variant cycling |
| Hundreds to thousands of pages, "Plumber in [city]" (programmatic-seo) | Ramp ≤ max(2, 10 %)/week, pilot 3–5, prune at 90 d (summary Step 4) | Dossier |
| Volume floor ~100 searches/month (keyword-research) | Demand gate uses GSC impressions or real jobs (Step 4) | Dossier for local |
| AIO on ~47 % of US searches, 83 % zero-click (serp-features, featured-snippet) | AIO on 4–8.6 % of local service queries, 75 % of need queries (F15) | Dossier (query-class data) |
| Guest posts with bio link; directory listings for link equity, DA 50+, bulk/outsourced submission (link-building, directory-submission) | Guest-post ranking links and low-quality directory links are link spam (08 §2, F29) | Dossier |
| "Top 10 / Best X" list posts rated high-fit, no caveat (content-strategy, content-marketing, article-content) | No self-published best-of list naming the client (F20) | Dossier |
| Parasite SEO suits "local businesses needing quick leads" (parasite-seo) | Site reputation abuse; avoid publishing on accounts we run (06, 01) | Dossier |
| Slug transliteration ü → u (url-slug-generator) | Not covered; German convention is ü → ue, ß → ss [I] | Adapt |
| Mobile-Friendly Test and GSC Mobile Usability report as tools (mobile-friendly) | Not covered; both were retired by Google in 2023 [outside dossier, verify] | Against skill |

No contradiction: INP replaced FID (core-web-vitals is correct); Indexing API only for JobPosting/BroadcastEvent (indexing, generative-engine-optimization agree). Not claimed by any skill read: llms.txt as a lever, GBP posts or photos as ranking factors, GBP Q&A, review incentives or gating, link exchanges.

## 6. Harmful or banned for our use

| Skill | Unusable parts |
|---|---|
| parasite-seo | Entire skill: ranking content on Medium/Reddit/LinkedIn/Quora for lead capture, tier-2 backlinks to that content, cross-platform link networks, keyword layering |
| programmatic-seo | City × service matrices at scale; AI per-URL narrative as the source of difference; cycling 8–15 phrasing variants so neighbouring pages differ (spinning); "best [service] in [city]" pages; 300-word floor as a quality bar; Zapier-scale volume as a model |
| link-building | Guest posting for followed bio links; directory and best-of submission framed as link building; "earn links at scale" via press releases with ranking links |
| directory-submission | DA 50+ link-equity rationale; bulk or outsourced submission; "submit small directories too"; paid newsletter or featured placements as SEO; SaaS directory set (Taaft, Product Hunt, G2) is irrelevant |
| directory-listing-ads | All of it (SaaS marketplaces) |
| content-strategy, content-marketing, article-content | Self-published "Top 10 / Best X" lists for local services |
| generative-engine-optimization | Reddit/YouTube/forum seeding to gain AI mentions; any page made mainly for AI mentions (F20) |

No skill read promotes fake reviews, review gating or incentives; none covers German review law at all.

## 7. Gaps

- German law: §5b UWG review notice, review-request consent (BGH VI ZR 225/17), Impressum, TDDDG consent for tracking; nothing in this group.
- German citation tiers (GBP, Bing Places, Apple Business, DTME, 11880/WerKenntDenBesten, Kammer/Innung, manufacturer finders).
- GBP operations: categories, Ask Maps answer corpus, suspension triggers, API edit limits.
- Reviews: velocity targets, reply drafting, compliant request flow.
- Location pages: demand, local-evidence, town-swap and similarity gates, ramp, pruning.
- AI visibility measurement: multi-run prompt panel, mention rate with intervals, German locale, UI parity (the measurement stubs moved out, nothing replaces them).
- Astro specifics (`@astrojs/sitemap` filter/serialize, `astro:assets`), Vercel preview noindex, `vercel.json` redirects.
- Cookieless attribution (server events, call tracking, "Wie gefunden?"), per-action measurement windows, control pages.
- German keyword grammar (compounds, "in/bei {Ort}"), umlaut slugs, German anti-slop phrase list.
- Lead-portal cost comparison and German monthly owner report.
