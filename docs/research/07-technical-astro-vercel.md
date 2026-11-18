# 07 · Technical SEO for Astro (static) on Vercel

Confidence legend: [P] primary · [S] secondary · [V] vendor claim · [I] inference/recommendation.

Static Astro on Vercel is already a strong baseline (HTML-first, fast, no CMS bloat). Most technical risk comes from configuration drift, preview leakage, URL inconsistency, and silent tracking breakage. The plugin should treat technical SEO as **tests in CI**, not as an audit PDF.

## 1. URL, canonical and trailing-slash consistency

- Astro: set `site: 'https://www.example.de'` (required for sitemap and absolute canonicals) and pick `trailingSlash: 'never'|'always'` with `build.format` to match (`'file'` for no slash, `'directory'` for slash) [P, Astro docs via Context7].
- Vercel: set the same in `vercel.json` (`"trailingSlash": false` → `/about/` 308 → `/about`; `true` the reverse) and `"cleanUrls": true` (`.html` → 308 to extensionless) [P, Vercel docs].
- Canonical: self-referencing absolute canonical on every indexable page generated from `new URL(Astro.url.pathname, Astro.site)`; normalise to the chosen slash policy; strip query strings (UTMs from GBP links must canonicalise to the clean URL) [I].
- One host: apex vs www redirect at Vercel Domains (domain redirect, 308) [P].
- CI test [I]: crawl built `dist/` → assert every HTML page has exactly one canonical, it equals its own normalised URL (or an intentional target), and every internal link already matches the slash policy (no internal 308 hops).

## 2. Redirects

- `vercel.json` `redirects` for patterns (`/leistungen/:slug` → `/:slug`), `permanent: true` = 308 (Google treats 308 like 301) [P].
- **Bulk redirects** for large migrations: `bulkRedirectsPath` pointing to CSV/JSON/JSONL (up to 100 files; no wildcards/header matching); REST API `PUT /v1/bulk-redirects` and CLI `vercel redirects list` [P, Vercel docs]. Use when a relaunch maps dozens/hundreds of old WordPress URLs.
- Relaunch rule [I]: export all old URLs (GSC pages with impressions in 16 months + old sitemap + backlinks from Bing/Ahrefs) → map 1:1 to closest new page → never mass-redirect to home → test with a script that every old URL returns 308 to a 200.
- Consolidation (Gate H, 06): 301/308 the retired page to its parent; update internal links; remove from sitemap.

## 3. Sitemaps, robots, indexing

- `@astrojs/sitemap` with `filter()` (exclude thank-you pages, intern pages, noindex pages) and `serialize()` to set accurate `lastmod` from content frontmatter/git date [P]. Google uses `lastmod` only if it's consistently accurate [S, common Google guidance]; don't stamp build time on every URL.
- `robots.txt` in `public/` with `Sitemap:` line. AI bot policy defaults (see 04): allow search/answer bots (Googlebot, Bingbot, OAI-SearchBot, ChatGPT-User, PerplexityBot, Claude-SearchBot); decide training bots per client. OpenAI: robots changes for OAI-SearchBot take effect in ~24 h [S, Klano citing OpenAI].
- **Preview leakage**: Vercel preview URLs on `*.vercel.app` are served with `x-robots-tag: noindex` (verify with `curl -I`); a custom domain assigned to a Git branch (e.g., `staging.example.de`) needs an explicit `X-Robots-Tag: noindex` header in `vercel.json` scoped with `has: [{type: "host", value: "staging.example.de"}]` [P, Vercel docs].
- Google indexing: sitemap + internal links + GSC; **URL Inspection API** = 2,000 inspections/day and 600/min per property (10M/day per project) — enough to check every page of an SMB site daily [P, GSC limits]. Google's Indexing API is only for JobPosting/BroadcastEvent — do not use for normal pages [I, long-standing Google rule].
- **IndexNow** (Bing, Yandex, Seznam, Naver; not Google): key file `public/<key>.txt` (8–128 chars [a-zA-Z0-9-]), POST changed URLs after each production deploy (GitHub Action or Vercel deploy webhook → small script). Notify on add/update/delete [P, indexnow.org]. Bing URL Submission API alternative: up to 10,000 URLs/day/domain (actual quota varies, read `GetUrlSubmissionQuota`), batch ≤500 [S]. Note Bing's SOAP/POX APIs retire 2026-08-31 → use JSON/REST [S].
- 404: real `404.astro` returning HTTP 404 (Vercel serves `404.html` with 404 status) [I]; monitor 404s from Vercel logs/Observability.

## 4. Structured data (JSON-LD), status 2026

Google position: structured data helps understanding and eligibility for some rich results; no special schema needed for AI features; markup must match visible content [P].

| Type | Status / use | Notes |
|---|---|---|
| **LocalBusiness** (+ most specific subtype) | Supported (local business rich data, knowledge panel signals) | Required: name, address. Recommended: geo, telephone, url, openingHoursSpecification, priceRange, image, sameAs (GBP/Maps URL, Das Örtliche, Kammer listing). Use same NAP as `business.json`. |
| Subtype mapping | schema.org | Elektro → `Electrician`; SHK → `Plumber`/`HVACBusiness`; Dach → `RoofingContractor`; Maler/Stuckateur → `HousePainter` (or `GeneralContractor` for Stuck/Putz/Fassade); Bau → `GeneralContractor`; Schlosserei → `Locksmith` only for Schlüsseldienst, else `HomeAndConstructionBusiness`; GaLaBau → `HomeAndConstructionBusiness` (no specific type); Steuerberater → `AccountingService`; Finanzberatung → `FinancialService`; Versicherung → `InsuranceAgency`; Architekt/Ingenieur → `ProfessionalService`; Hausverwaltung → `RealEstateAgent` or `ProfessionalService`; Spedition → `MovingCompany` only for Umzüge, else `LocalBusiness`; Fahrschule → `DrivingSchool`; Restaurant → `Restaurant` (+ `servesCuisine`, `menu`, `acceptsReservations`). [I, schema.org types] |
| **Service** | Valid schema.org; no Google rich result | Use on service pages: `serviceType`, `areaServed` (City/AdministrativeArea), `provider` → LocalBusiness `@id`, `offers` with `priceSpecification` ranges. Entity clarity only. |
| **Review / AggregateRating** | Self-serving reviews on LocalBusiness/Organization are **not eligible** for review rich results (since 2019) | Don't mark up your own Google reviews as AggregateRating expecting stars. If shown visibly, keep §5b UWG notice. [I/P long-standing] |
| **FAQPage** | **FAQ rich results removed 2026-05-07**; Search Console report removed June 2026; API support removed Aug 2026; markup may stay, other engines may use it | [P via S, SEL/SER 2026-05] |
| HowTo | Deprecated (rich results gone) | [S] |
| **BreadcrumbList** | Supported; still useful for structure | [I] |
| Organization | Supported; logo, sameAs | Use on home. |
| Person | For Meister/Steuerberater author pages | E-E-A-T clarity. |
| Article/BlogPosting | For case studies/ratgeber | `datePublished`, `dateModified`, `author`. |
| Event | Restaurants/Fahrschule course dates | Supported rich result. |
- Retired by Google in 2025 (don't build): Course Info, Claim Review, Estimated Salary, Learning Video, Special Announcement, Vehicle Listing; Practice Problem (2026) [P, Google blog 2025-06/11; S].
- Validation in CI: JSON parse, required fields present, NAP equals `business.json`, no markup of invisible content; Rich Results Test manual spot check for new templates.

## 5. Core Web Vitals and images

- Thresholds (p75 field data): LCP ≤ 2.5 s, INP ≤ 200 ms (replaced FID 2024-03), CLS ≤ 0.1 [P, web.dev — long-standing].
- Field data reality: most SMB sites have **no CrUX data** (insufficient traffic); CrUX API returns 404 for them. CrUX API: 150 queries/min/project, free, 28-day rolling, updated daily ~04:00 UTC [P]. Use **Vercel Speed Insights** (RUM) for field data on low-traffic sites, PageSpeed Insights/Lighthouse for lab data in CI [I].
- Astro images: `astro:assets` `<Picture formats={['avif','webp']}>` with mandatory `alt`; `priority` on the LCP hero (`loading="eager"`, `fetchpriority="high"`) and lazy for the rest; always width/height to prevent CLS [P, Astro docs]. Project photos: resize at build, strip EXIF GPS (privacy; also geotagging has no ranking value [S]).
- Fonts: self-host (also avoids Google Fonts IP-transfer issue in DE), `font-display: swap`, preload the 1–2 used weights [I].
- Third-party scripts: none by default; maps via click-to-load; review widgets as static HTML built at deploy time, not client-side embeds [I].
- CI budget [I]: Lighthouse mobile on 3 templates (home, service, service×town): Performance ≥ 90, CLS ≤ 0.05, total JS ≤ 50 KB, LCP image ≤ 200 KB.

## 6. On-page template requirements (per page type)

- Title: `{Leistung} in {Ort} | {Firma}` (≤ ~60 chars); H1 with Leistung + Ort on GBP landing page (Whitespark #17, #20) [P].
- NAP block in HTML on every page (footer) matching GBP (#15 factor) [P].
- Phone as `tel:` link, click-tracked; WhatsApp `wa.me` link; form above the fold on mobile or sticky CTA bar (see 09).
- Internal links: service ↔ case studies ↔ towns; breadcrumb; no orphan pages (CI check).
- Hreflang: only if the site has true language versions (e.g., an EN page set for international Kanzlei clients); `de-DE` + `en` + `x-default`; reciprocal; otherwise none [I].

## 7. Monitoring (what the weekly loop checks automatically)

| Check | Source | Alert threshold [I] |
|---|---|---|
| Production deploy health | Vercel API/MCP deployments + runtime errors | any failed prod deploy; 5xx on `api/contact` |
| Form pipeline | synthetic POST to `api/contact` in preview + Resend delivery status | any failure → P1 |
| Indexing | GSC URL Inspection for all sitemap URLs (≤2,000/day) | money page not indexed; canonical chosen by Google ≠ declared |
| Coverage | GSC Page indexing (UI) / sitemap status | "Crawled – not indexed" share > 20% |
| Rankings/CTR | GSC Search Analytics (1,200 QPM/site) | money query avg position −3 vs 28-day baseline; Klano uses ">5 positions" daily alert [P] |
| Robots/noindex regressions | fetch live robots.txt + `x-robots-tag` on prod | any noindex on prod money page |
| CWV | Speed Insights / Lighthouse CI | template regresses below budget |
| Schema/NAP drift | CI on build | mismatch with `business.json` |
| Redirect integrity | old-URL list test | any 404 among mapped URLs |
| AI bot access | server logs (Vercel Observability) or CDN | OAI-SearchBot/Bingbot 4xx/blocked |

## 8. Implications for the plugin [I]
- Ship a `seo-checks` script (Node) run in CI and by `/twwa-check`: canonical, slash policy, sitemap, robots, schema/NAP, internal links, image budgets, headers on preview vs prod.
- Deploy hook script: IndexNow ping + optional Bing batch submit + GSC sitemap resubmit for changed sitemaps.
- Every site change = branch → Vercel preview URL (noindexed) → approval → merge → production → post-deploy verification (fetch live page, check 200, canonical, title, CTA, schema). "The deploy log is not evidence" — verify the live page [S, practitioner lesson].
