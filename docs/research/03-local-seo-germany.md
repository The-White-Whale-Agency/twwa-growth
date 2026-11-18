# 03 · Local SEO in Germany (in depth)

Confidence legend: [P] primary · [S] secondary · [V] vendor claim · [I] inference/recommendation. Not legal advice; legal points are summarised from German case law and practitioner sources and should be checked by the agency's lawyer before being productised.

---

## 1. What ranks in the local pack (Whitespark LSRF 2026)

Survey of 47 experts, 187 factors, published 2025-11; scores are expert opinion, not Google confirmation [P, whitespark.ca].

**Group weights, local pack/Maps** [S, AdviceLocal/others citing report]: GBP signals 32% · Reviews 20% · On-page 15% · Behavioural 9% · Links 8% · Citations 6% · Personalisation 6% · Social 4%.

**Top 25 local pack/Maps factors (score)** [P]:
1 Primary GBP category (227) · 2 Proximity to searcher (225) · 3 Keywords in GBP business title (223) · 4 Physical address in city of search (213) · 5 Business open at time of search (189) · 6 High Google rating 4–5 (181) · 7 Address showing on GBP, not SAB (176) · 8 Additional categories (173) · 9 Quantity of native Google reviews with text (170) · 10 Proper map pin placement (165) · 11 Review recency (164) · 12 Proximity to centroid (157) · 13 CTR from pack/Maps (156) · 14 Sustained review influx vs bursts (154) · 15 HTML NAP = GBP NAP (153) · 16 GBP completeness (147) · 17 Keywords in GBP landing page title (146) · 18 Geographic relevance of content (142) · 19 Removal of spam listings (137) · 20 Keywords in landing page headings (135) · 21 Proper hours (134) · 22 GBP predefined services (134) · 23 Brand search volume (133) · 24 Dedicated page per service (132) · 25 Authority of links to GBP landing page (127).

**Top local organic factors**: 1 Dedicated page for each service (210) · 2 Geographic keyword relevance of content (190) · 3 Domain link authority (187) · 4 Keywords in GBP landing page title (179) · 5 Industry-relevant linking domains (175) · 6 Internal linking (174) · 7 Topical relevance across site (172) · 8 Keywords in GBP landing page headings (169) · 9 Niche focus (169) [P].

**Factors that do NOT move pack rankings (tested)**:
- GBP posts: no measurable ranking effect over 9 weeks, 441 keywords × 3 listings (Sterling Sky 2021) [P]; Whitespark 2026 ranks post frequency #148 [S]. Posts are a conversion/CTR tool (Sterling Sky: offer posts 0.6% CTR, updates 0.3%) [S].
- GBP photos: no measurable ranking effect (Sterling Sky, 4 profiles) [S]; geotagging photos dead last (#187) [S].
- Business description keywords: no ranking effect (widely repeated, Google-confirmed per practitioners) [S].
- Category "dilution" myth: adding relevant secondary categories did not hurt existing category rankings (GMB Everywhere test, 2 businesses) [V].

**Plugin rule [I]:** spend GBP effort on category, name accuracy, address/pin, hours, services, reviews; treat posts/photos as conversion features (do them, but don't promise rankings).

## 2. Google Business Profile — field-by-field playbook

| Field | Rule | Evidence |
|---|---|---|
| Business name | Exactly the real-world name (signage, Impressum, stationery). No keywords/cities. Keywords in name is #3 factor, which is why spammers do it; for clients it is a suspension trigger. If the legal/brand name genuinely contains the trade ("Malerbetrieb Müller"), fine. | [P] GBP guidelines via [S] NYXR 2026-11; Whitespark |
| Primary category | Most specific category matching the core money service. Compare top-3 pack competitors (Pleper/GMB Everywhere). Change rarely; a primary change can trigger re-verification; judge effect at ≥48 h, re-evaluate at 1–2 weeks. Never stack edits. | [S] Sterling Sky 2025-12; LSF threads |
| Secondary categories | Add all that genuinely describe services (typically up to 9). | [V] GMB Everywhere; [S] |
| Address vs SAB | Google requires SABs that don't serve customers at the address to hide it. Sterling Sky (8,186 businesses, 200 cities, 2025-11) found SAB status negatively correlated with "near me" rankings and an A/B on a client: hiding the address tanked rankings, re-adding restored them. **Compliance trumps ranking**: only show the address if customers are genuinely received there during posted hours (office/showroom/Werkstatt with signage). | [P] Sterling Sky 2025-11 |
| Service area | Cities/PLZ/regions, not radius; up to 20; ≲2 h drive from base; one profile per business, not per city. | [S] gbpreinstatement 2026-02 citing Google help |
| Hours | Accurate incl. holidays and special hours; "open at time of search" is #5. Consider genuine extended phone hours if staffed (e.g., Notdienst). | [P] Whitespark |
| Services | Fill predefined services (#22) and custom services with keyword-relevant titles (#30). Mirror website service pages. | [P] Whitespark |
| Products | Use for productised services ("Fassadenanstrich EFH ab …") with photo, price range, link to page. | [I] |
| Photos/video | Real, recent, relevant, high quality (factors #45, #79, #90 in new-factors table); conversion effect large in correlational data (BrightLocal: 100+ images → far more actions; correlation only). | [P]/[S] |
| Posts | Weekly/biweekly "Projekt der Woche", offers, seasonal. Conversion, not ranking. API supports scheduling incl. recurrence (2026-04). | [P] change log |
| Q&A | **Removed.** Q&A API discontinued 2025-11-03; front-end section phased out Dec 2025–early 2026; replaced by Gemini "Ask Maps" that answers from profile, reviews, photos, website and third-party sources. Ask Maps launched US/India 2026-03; **announced for 30+ European countries on 2026-11-16** (verify DE availability on device). Owners can still answer existing/aggregated questions in the backend. | [P] change log, Google blog 2026-11-16; [S] SER 2025-12 |
| Messaging | GBP chat was discontinued 2024-07-31; WhatsApp-type messaging clicks still measured in Performance API (`MESSAGING_CLICKS`). | [S] ppc.land; [P] API ref |
| Website link | Link to the most relevant page (homepage for single-location, or main service page); add UTM `?utm_source=gbp&utm_medium=organic&utm_campaign=website` for attribution. UTMs don't affect ranking. | [S] multiple |
| Phone | Real local number. If call tracking: tracking number as primary, real number as "additional phone"; keep the real number on site/citations. | [S] Google forum answer, Whitespark |
| Attributes | Fill all truthful ones (e.g., "Online-Termine", payment, accessibility). Ask Maps reads them. | [S] |

**Implication of Ask Maps [I]:** GBP description, services, attributes, reviews and the website's FAQ/service content become the answer corpus for conversational questions ("Macht ihr auch Altbau-Fassaden mit Denkmalschutz?"). The website must state such facts explicitly; reviews that mention services help (Joy Hawkins: reviews with text have stronger impact [S]).

### Suspension avoidance checklist (encode as hard gate)
Triggers [S, NYXR 2026-11, gbpreinstatement 2026-02, Splinternet 2026-07]: keyword/city in name; ineligible address (virtual office, coworking desk without signage/staff, PO box); visible home address for SABs; service area too large / >20 areas; duplicate profiles (one per city or specialty); call-center or non-local phone; lead-gen/agent models; fake engagement (bought reviews, staff reviews, discounts for 5 stars); big edits stacked (name + category + address in one session).
Video verification for SABs: ≥30 s, unedited, recorded/uploaded from phone via the profile; show location identifiers (street signs at base), proof the business exists (tools, branded vehicle), proof of management (unlock van, documents). Review up to 5 business days. Appeal once with complete evidence [S].
Ownership: add a second trusted owner (client-side); agency stays manager.

## 3. Proximity and growing beyond the home town

- Proximity is #2 pack factor and only partly controllable [P]. The pack is hyper-local; ranking radius depends on competitor density (rural Handwerk: often 10–30 km; city: 1–3 km) [I, consistent with geo-grid practice].
- **What works beyond the town** (evidence-based order):
  1. Local *organic* results, which are much less proximity-bound than the pack: Sterling Sky's Toronto study found 5 law firms filled the top-3 localised organic results across 72 postal codes; one appeared 100% of the time [P, 2020]. Service × city pages target exactly this layer.
  2. Prominence: reviews volume/recency, links from local-relevant domains (#26–27), brand searches (#23).
  3. A second real location (Werkstatt/Büro with signage and staff) → second GBP. Never fake.
  4. Ads/LSA where pack is unreachable (outside scope but mention in plan).
- **Service-area/city pages**: work when they carry location-specific substance; fail or become doorways when only the name changes. Conflicting evidence: Sterling Sky showed 35 SAB pages with ~84% similarity still ranked and drove sales (2023/2024) [P], while 2026 spam updates (March, June, August 18–21, Sept 24–Oct 8) are widely reported to hit swap-the-city-name matrices [S]. Google policy names "multiple … pages targeted at specific regions or cities that funnel users to one page" as doorway abuse [P]. Plugin stance: shared boilerplate is acceptable *if* each page also has real local evidence and real demand; see 06 for the gate.

## 4. German citation sources (prioritised)

Data flow: Apple Maps lists Das Örtliche (DE), Herold (AT), local.ch (CH), Foursquare, Localeze as data sources; Google uses licensed third-party data among sources [S, soeners 2026-10]. Bing can import from GBP [S].

**Tier 1 (do for every client)** [S, seorado 2026-10 tested 50 portals; seoforge 2026-11; dtile 2026-07]:
| Source | Notes |
|---|---|
| Google Business Profile | core |
| Bing Places (now bing.com/forbusiness since 2025-10) | import from GBP; address can be hidden with ≤20 service areas; feeds Copilot/Bing |
| Apple Business (renamed from Business Connect 2026-04-14) | street address mandatory (no SAB without address); ~33% iOS share in DE; feeds Siri/Apple Maps/Apple Intelligence |
| Das Örtliche / Gelbe Seiten / Das Telefonbuch (DTME) | one entry via DTME covers the trio; **choose free Grundeintrag, not "Starteintrag" (→ €358.80/yr after 3 months)**; Das Örtliche link dofollow; ChatGPT pulled Das Örtliche in 21/40 test answers, Gelbe Seiten 17/40 |
| 11880.com | dofollow; same form populates WerKenntDenBesten |
| WerKenntDenBesten | aggregates reviews from 52 portals; most visibly cited in the ChatGPT test (7/40); appeared in 20/40 search results; no website link |
| OpenStreetMap | only for visible locations with signage |

**Tier 2 (by vertical)**:
- Handwerk: Handwerkskammer "Handwerkerradar"/Betriebsbörse (via own Kammer), Innung member search, manufacturer partner finders (Sto Fachhandwerkersuche — self-activation via Sto service platform, live within 2 days [P]; Caparol "Qualifizierte Handwerkspartner"; Brillux, Knauf Fachunternehmer-Suche; Viessmann/Buderus/Vaillant installer finders for SHK; Velux/Roto for Dach; Schüco/Hörmann for Metallbau), "TOP Malermeister/Stuckateurmeister", MyHammer/Check24 Profis profiles (profile even without buying leads), ProvenExpert (free plan: 10 visible reviews), golocal, KennstDuEinen.
- Steuerberater: **DATEV/Kammer "Steuerberater-Suchdienst" was discontinued 2025-12-31**; successor is the Bundessteuerberaterkammer's amtliches Steuerberaterverzeichnis with PLZ/Ort search; plus DStV's steuerberater.de (7,100+ entries in one regional verband's count) [P, StBK Hessen; DStV]. Also ProvenExpert, kanzlei profiles on anwalt.de only for lawyers.
- Finanzberatung/Versicherung: IHK Vermittlerregister (mandatory, links to legal compliance), WhoFinance, ProvenExpert.
- Ingenieure/Architekten: Kammer member directories (Architektenkammer "Architektensuche", Ingenieurkammer lists), BauNetz, competitions.
- Hausverwaltung: VDIV/regional verband member search, Immobilienscout24 Verwalter-Suche.
- Spedition: wer liefert was (wlw), DSLV member lists, regional logistics clusters.
- Fahrschule: Fahrschulverband listings, fahrschulen.de-type portals, Google is dominant.
- Restaurants: Tripadvisor (most important after Google), TheFork, OpenTable, Falstaff/Guide Michelin where applicable, Yelp (weak in DE but cited by ChatGPT globally).
- Healthcare (if ever): Jameda basic profile (exists anyway; BGH 2021).

**Tier 3 / avoid**: mass submissions to unknown "SEO directories" (no ranking value; only 9/50 portals even link dofollow) [S]. Link value is not the point; data consistency and AI-retrievable mentions are.

**NAP rule [I]:** one canonical spelling (as in Impressum) stored in the repo (`growth/business.json`), used for site footer, schema, and every listing; quarterly audit by searching name + city and comparing.

## 5. Reviews: legal in Germany, effective for ranking and AI

### What works
- Recency and steady velocity matter (#11, #14 pack factors). Joy Hawkins (8,186 businesses, 2025): reviews received *this month* mattered more than lifetime count; a client that stopped getting reviews for 18 days saw rankings drop while competitors getting 15–45/month held steady; text reviews outweigh star-only [S, LinkedIn 2025-11 summarising study].
- Consumers (BrightLocal LCRS 2026, US n=1,002): 47% won't use a business with <20 reviews; 74% only care about reviews from last 3 months; 31% require ≥4.5★ (up from 17%), 68% ≥4★; 89% expect owner responses; 19% same day, 81% within a week; 50% put off by templated replies [P, US data — directionally applicable].
- AI: SOCi 2026 — recommended locations average ~4.2–4.3★; ChatGPT recommended only 1.2% of locations vs 35.9% in the 3-pack; more review volume can offset a slightly lower rating (4% more reviews offsets −0.2★ on ChatGPT, 14% on Claude, 64% on Gemini) [S/V, SOCi via SEL 2026-11].

### What is legal (UWG/DSGVO) — encode as hard rules
1. **No incentives for reviews.** Gutschein, Rabatt, Gewinnspiel, cash for a review make the review "unfrei"; advertising with them is misleading unless disclosed at each review — and courts treat even the *request* for a paid review as unlawful (LG Hildesheim 2024: €50 voucher for Google review; Wettbewerbszentrale 2025: Gewinnspiel for 5★; OLG Frankfurt 2020 6 U 270/19; OLG Hamm 2010 4 U 136/10) [P/S]. Abmahnung cost from Wettbewerbszentrale ~€374.50 + Unterlassungserklärung + removal of reviews [S]. **Never incentivise customers.** (Sterling Sky's US example of a staff lottery tied to customers mentioning staff is *not* transferable as a customer incentive; incentivising your own staff to ask is a different question — have counsel confirm.)
2. **Fake or commissioned reviews**: always unlawful (UWG Anhang Nr. 23c); claiming reviews are from real customers without verification is always unlawful (Nr. 23b); OLG Köln 2024-12-20 (6 U 59/24): a banner "Kundenbewertungen" requires that customer status was checked; disclaimer behind a click doesn't cure it [S, racoonmedia 2026-10].
3. **§5b Abs. 3 UWG transparency**: any site that displays consumer reviews (own stars, embedded Google reviews, widgets) must state near the reviews whether and how authenticity is verified. Template: "Diese Bewertungen stammen von Google. Wir haben keinen Einfluss auf Auswahl und Inhalt und prüfen nicht, ob die Verfasser Kunden sind." Use the label "Bewertungen" not "Kundenbewertungen" unless verified [S].
4. **No review gating / selective solicitation**: asking only happy customers distorts the overall picture (UWG Irreführung) and violates Google policy ("Don't discourage negative reviews or selectively solicit positive reviews") [S/P].
5. **Review requests by e-mail/SMS/WhatsApp are advertising.** BGH VI ZR 225/17 (2018-07-10): satisfaction survey in the invoice e-mail = advertising; without consent unlawful. Whether §7 Abs. 3 UWG (existing-customer exception) covers review requests is **disputed**: IT-Recht Kanzlei and Wettbewerbszentrale (2024-10 enforcement) say no; other practitioners say yes if all four conditions incl. objection notice at collection are met [P/S — conflicting]. **Safe default**: obtain explicit consent (checkbox at inquiry/Auftrag: "Ich bin einverstanden, nach Abschluss per E-Mail/WhatsApp um eine Bewertung gebeten zu werden", separately from newsletter), or ask in person/by handing a printed card with QR code (not electronic advertising). One request per job, no reminders without consent, neutral wording ("Wir freuen uns über Ihre ehrliche Bewertung"), no "5 Sterne" steering.
6. Sharing customer data with a review platform needs a legal basis + AVV (Wettbewerbszentrale 2024 case) [P].
7. Showing reviews with name/photo on own site needs consent [S].
8. Removing defamatory/fake reviews: platforms must run a check procedure when the business disputes customer contact (BGH line; LG Hamburg 2025, KG 2025); review removal *as a service by an agency* is legal services (Rechtsdienstleistung) — only lawyers may offer it (OLG Hamburg 2023, OLG Frankfurt 2024) [S]. Plugin may draft a factual flag/report for the owner, not represent them.

### Review engine design [I]
- Trigger: job marked done (owner taps a link / form on `/intern/auftrag-fertig` or a weekly list) → owner hands over card or sends pre-written WhatsApp from own phone *only if consented*.
- Assets: GBP review short link (from GBP "Get more reviews"), QR card print file, A6 Baustellenschild/Rechnungsfußzeile text.
- Target velocity: match median of top-3 pack competitors' last-90-day review count (computed weekly from Maps SERP API data) +10%.
- Replies: draft within 24 h, owner approves; never templated; mention service + town naturally (no stuffing); respond to negatives factually, offer offline contact, no personal data.

## 6. DSGVO / TDDDG constraints on tracking

- **§25 TDDDG** (formerly TTDSG, renamed 2024-05): storing or reading information on the end device (cookies, localStorage, pixels, fingerprinting) requires prior consent unless strictly necessary [P via S, HmbBfDI 2025-04; worconiq 2026-08]. Art. 6 DSGVO legal basis is a separate second step.
- **Vercel Web Analytics**: cookieless by design (no cookie, hashed daily identifier) — commonly treated as not triggering §25 (no device access) but still processing personal data (IP) under Art. 6(1)(f) → list in Datenschutzerklärung [I/S; confirm with DSB].
- **Dynamic number insertion (DNI)** call tracking uses JS + storage to swap numbers by source → consent required; **static tracking numbers** per channel (one for GBP, one for website, one for print/vehicle) need no device access → workable without banner [S, LeadRaum 2026-06; matelso 2025-09].
- Call recording without prior announcement is a criminal offence (§201 StGB); AVV needed with call-tracking provider [S].
- Google Ads forwarding numbers only with consent (Consent Mode v2) [S].
- Embedded Google Maps iframes transmit IP → load only after click/consent (two-click solution) [S; common German practice].
- WhatsApp: a plain `https://wa.me/49…` link is fine; embedded WhatsApp widgets that load third-party scripts need consent [I].

## 7. Impressum and branch-specific legal pages

- Legal basis is now **§5 DDG** (Digitale-Dienste-Gesetz, replaced §5 TMG in 2024-05) [I — verify wording].
- Required for all: full name/legal form, address (no PO box), fast electronic contact (e-mail + phone or form), register entry (HRB/HRA), USt-IdNr if any, responsible person for content (§18 MStV) for journalistic content.
- Handwerk: zuständige Handwerkskammer, Eintrag in die Handwerksrolle, Berufsbezeichnung + Staat der Verleihung for reglementierte Berufe [I].
- Steuerberater: Kammer, Berufsbezeichnung, berufsrechtliche Regelungen (StBerG, BOStB) with link; advertising must be "sachlich" (§57a StBerG) — impacts superlatives on "bester Steuerberater" pages [I].
- Architekten/Ingenieure: Kammer, Berufsbezeichnung, Berufsordnung, Berufshaftpflicht details in some states [I].
- Versicherungs-/Finanzvermittler: Vermittlerregister number (§34d/§34f GewO), Schlichtungsstellen, IHK [I].
- Barrierefreiheitsstärkungsgesetz (in force 2025-06-28): applies to B2C services concluding contracts electronically; microenterprises (<10 staff and ≤€2M) exempt for services. Most brochure sites with contact forms are not in scope; online booking/contract flows may be [I — verify].
- Plugin rule: an Impressum/Datenschutz check is part of every audit; legal text changes require human (lawyer/owner) approval — never auto-generated.

## 8. Implications for the plugin (summary) [I]
1. GBP module with field-level checks, competitor category comparison, edit pacing (one identity edit per 48 h, API max 10 edits/min/profile [P]), suspension-risk linter.
2. Review module that is UWG-safe by construction (no incentives, no gating, consent-aware channels, §5b notice component on the site).
3. Citation module: canonical NAP in repo; Tier-1 checklist; vertical Tier-2 list; warn on DTME Starteintrag; annual audit.
4. Location strategy that uses local organic pages for reach beyond the pack, gated by evidence (06).
5. Privacy-safe tracking defaults: cookieless analytics, static call-tracking numbers, two-click maps.
