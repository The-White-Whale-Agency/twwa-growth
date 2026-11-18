# 05 · Content that converts for local service and professional businesses

Confidence legend: [P] primary · [S] secondary · [V] vendor claim · [I] inference/recommendation.

## 1. Page types ranked by lead value

Ranking basis: Grow and Convert conversion data (category > alternatives/vs > JTBD ≫ TOFU) [P], Whitespark (dedicated page per service is #1 local organic, #2 AI factor) [P], AIO trigger rates by query class (local-intent 4–15%, cost/hybrid 75–97%) [S], and lead-portal economics [I].

| # | Page type | Example (DE) | Why it converts | AIO exposure | Gate |
|---|---|---|---|---|---|
| 1 | **Core service page (home town)** | /fassadensanierung, "Fassadensanierung in Musterstadt" | Category intent; GBP landing page signals (#17, #20) | Low (pack-dominated) | Always, one per real service |
| 2 | **Emergency / urgent service** | "Rohrbruch Notdienst Musterstadt", "Schlüsseldienst" (only if truly offered 24/7) | Immediate call intent | Low | Only if staffed; hours must match GBP |
| 3 | **Service × town page** | "Dachdecker Nachbarstadt" | Local organic reach beyond pack | Low–medium | Evidence + demand gate (06) |
| 4 | **Cost / price page** | "Was kostet ein Fassadenanstrich? Preise pro m² 2026" | Hybrid intent; strongest pre-inquiry research; anchors price | **High (97%)** — must be citable and convert | Needs real price ranges from owner |
| 5 | **Case study / Referenz** | "Altbau-Fassade in Nachbarort: 280 m², 3 Wochen" | Proof; feeds service × town pages; AI evidence | Low | Needs real project data + consent |
| 6 | **Förderung page** (Handwerk energetisch) | "BAFA-Förderung Fassadendämmung 2026: 15 % und wann 20 %" | High-value projects; urgency on deadlines | High | Needs source URLs + verified-date; quarterly freshness check |
| 7 | **Problem/symptom page** | "Risse im Putz: harmlos oder Sanierungsfall?", "Schimmel an der Außenwand" | JTBD with buying intent; ends with "Begutachtung anfragen" | High | Must route to a service page + CTA |
| 8 | **Comparison page** | "WDVS vs. Einblasdämmung", "Mineralputz oder Silikonharzputz" | Decision stage | High | Only with first-hand expertise |
| 9 | **Process / "Ablauf"** | "So läuft eine Fassadensanierung ab" | Reduces anxiety, raises close rate | Medium | Can be part of service page |
| 10 | **FAQ (on page)** | FAQ block per service | Answers Ask Maps / AI follow-ups | — | No standalone FAQ hub needed; FAQ rich results are gone (2026-05-07) |
| 11 | **Team / Über uns / Meister** | Meisterbrief, years, photos | E-E-A-T, trust | — | Always |
| 12 | **Recruiting (Karriere)** | "Stuckateur Ausbildung Musterstadt" | Not leads but a top owner pain (Fachkräftemangel) | Low | Optional upsell |
| 13 | Generic DIY / Ratgeber | "Wasserhahn reparieren" | Lowest lead value; AIO-cannibalised | Very high | Avoid unless it is a problem page leading to service |

Vertical additions:
- **Steuerberater/Kanzlei**: niche × town ("Steuerberater für Ärzte/Handwerker/Gastronomie Musterstadt"), "Wechsel des Steuerberaters – so geht's", cost page ("Was kostet ein Steuerberater? StBVV erklärt"), deadline pages (Abgabefristen), "Existenzgründung Steuerberatung". Advertising must be factual (§57a StBerG) [I].
- **Finanzberatung/Versicherung**: needs pages per life event (Baufinanzierung, BU für Handwerker), Honorar vs Provision transparency, §34d/f disclosures; YMYL → named advisor with qualifications [I].
- **Ingenieure/Architekten**: project portfolio pages (Typ, Ort, BGF, Leistungsphasen, Jahr), HOAI cost explanations, Bauantrag process per Landesbauordnung, Energieberatung (iSFP) [I].
- **Hausverwaltung**: WEG vs Miet-/Sondereigentumsverwaltung, Verwalterwechsel page, cost per unit, area pages by Stadtteil, Eigentümer FAQ [I].
- **Spedition**: lane/relation pages only with real lanes ("Teilladung Stuttgart–Mailand"), equipment specs, ADR, Lager m² [I].
- **Fahrschule**: Klassen pages (B, B197, BE, A2), "Führerschein Kosten [Stadt] 2026" with real price list, Intensivkurs, Ferienkurs dates, Theorie times [I].
- **Restaurants**: menu as HTML (not PDF), events/catering, opening hours, reservations; Tripadvisor/Google dominate; the site mainly feeds GBP/Ask Maps facts [I].

## 2. Making pages non-thin with first-party data

Every money page must carry **at least 3 evidence items the competitor can't copy** [I, derived from Google's helpful-content questions and Sterling Sky local-signal advice]:
- Real project with town, date, scope (m², Stück, Etagen), duration, material/brand, before/after photos (own, EXIF-stripped, alt text descriptive) [P Sterling Sky: unique local visuals, testimonials].
- Price ranges actually charged (min–typical–max) with drivers ("Gerüst ab 10 m Höhe +X", "Altbau-Untergrund"), dated.
- Process + timeline (Besichtigung within N days, Angebot within N days, Ausführung typical weeks).
- Local regulation/conditions: Denkmalschutz in the Altstadt, Gestaltungssatzung, Bauantrag at the Landratsamt, typical soil/weather issues, Förderung programs incl. Landesprogramme (e.g., L-Bank in BW) — must be verified, with source link.
- Team/expert: who did it, Meister/Fachkraft, certifications (Sto-Fachbetrieb etc.).
- Review excerpts about that service/town (with §5b UWG notice; consent if shown with name).
- FAQ from real customer questions (owner provides 3–5 per service; mined from inquiries via `api/contact.js` messages).

**Owner data loop** [I; mirrors Handwerksratgeber's "jeden Monat Fotos und ein paar Sätze zu einem Auftrag" P]:
- Monthly "Projekt-Kurzbericht" (mobile form or WhatsApp to agency): photos (3–10), town (no street unless allowed), service, scope, duration, one challenge + solution, customer quote (with consent), price band (optional).
- The plugin turns each report into: a case study entry, GBP post, evidence blocks for the matching service and service × town pages, and a review request trigger.

## 3. E-E-A-T for small firms (practical)

- Named author/expert per page (Meister name, Steuerberater with Kammer), short bio with credentials and years, photo [I; QRG emphasis on experience].
- "Über uns" with founding year, Handwerksrolle/Kammer, Innung/Verband memberships (linked both ways), insurance (Betriebshaftpflicht), guarantees.
- Show real faces/vehicles/workshop; avoid stock photos (Whitespark: photo quality/not stock is a new factor) [P].
- Date stamps: "Stand: November 2026" on prices/Förderung; update log.
- Google generative-AI content guidance (updated 2026-10-01 per secondary source): AI may help research/structure, but "critical to manually factcheck and review all AI-generated content… before publishing", incl. titles, meta descriptions, structured data, alt text [S, searchmaxxed citing Google]. → Human approval of every published text is not just a trust feature; it is aligned with Google's guidance.
- "No AI slop" German style rules (for the writing subagent): concrete numbers over adjectives; no "In der heutigen Zeit", "Wir sind Ihr kompetenter Partner", "ganzheitlich", "maßgeschneidert"; short sentences; du/Sie per client voice in CLAUDE.md; regional vocabulary.

## 4. German keyword research specifics

- **Regional trade synonyms** (must be researched per region and used as page variants or H2s, not separate doorway pages) [I, common knowledge, verify per market with GSC + Keyword Planner]:
  - Stuckateur / Stukkateur / Gipser (Baden-Württemberg, CH "Gipser"), Verputzer.
  - Klempner (Nord) / Spengler (Süd, AT) / Flaschner (Württemberg) / Installateur / Sanitär / SHK.
  - Schreiner (Süd/West) / Tischler (Nord/Ost).
  - Maler / Malerbetrieb / Anstreicher / Lackierer.
  - Schlosserei / Metallbau / Schlosser / Schmied; "Geländer", "Treppe", "Tor".
  - Garten- und Landschaftsbau / GaLaBau / Landschaftsgärtner / Gärtner; "Pflasterarbeiten", "Gartengestaltung".
  - Dachdecker / Bedachung / Dachdeckerei; Spengler for Blech.
  - Elektriker / Elektroinstallateur / Elektrotechnik.
  - Steuerberater / Steuerbüro / Steuerkanzlei / Steuerberatung.
  - Hausverwaltung / Immobilienverwaltung / WEG-Verwaltung / Mietverwaltung.
- **Compounds and split forms**: Google usually maps "Fassadensanierung" ↔ "Fassade sanieren" ↔ "Sanierung Fassade" but SERPs can differ; check SERP overlap before creating separate pages (cluster by SERP similarity, not by string) [I].
- **Umlauts**: ä/ae etc. generally treated as equivalent; use correct umlauts on page; slugs with ae/oe/ue [I].
- **Local modifiers**: Germans mostly type "[Gewerk] [Stadt]" or "[Gewerk] in der Nähe"; Synup US data shows AIO only on 4–9% of such queries [S]. Town names with prefixes ("Nachbarstadt", "Bad …") and Ortsteile matter for small towns.
- **Volume data**: Keyword Planner shows ranges and buckets small local volumes (often "0–10"/"10–100"); DataForSEO Google Ads endpoint returns clickstream-free Ads volumes. For small towns, treat GSC impressions as the ground truth after 4–8 weeks, plus autosuggest and People-Also-Ask as demand evidence. Bing `GetRelatedKeywords` gives another free signal [I/P].
- **Autosuggest**: DataForSEO Google Autocomplete $0.0006/task [P] — legal, cheap path vs scraping Google (scraping Google for ranks/data violates Google ToS "machine-generated traffic") [P].

## 5. Seasonality (encode as a calendar per vertical) [I, verify with Google Trends DE per client]
- Dach: storm events (instant spikes), autumn pre-winter checks; Fassade/Maler außen: Feb–Jun planning peak, execution Apr–Oct; GaLaBau: Feb–May; Heizung/SHK: Sep–Jan (failures) + Förder news; Elektro/PV/Wallbox: driven by Förderung and prices.
- Steuerberater: Jan–May (Steuererklärung), Q4 (Jahresabschluss, Existenzgründung for Jan 1), deadline (31.7 / extended deadlines for advisors).
- Fahrschule: summer holidays and Jan; Hausverwaltung: Q4/Q1 (Verwalterwechsel at year end, Eigentümerversammlungen); Restaurants: Dec (Weihnachtsfeier), Mother's Day, terrace season.
- Publishing rule: publish/refresh seasonal pages 6–10 weeks before peak (indexing + ranking lag, see 11).

## 6. Förderung pages: high value, high freshness risk

Example of why freshness gates are needed: **BEG reform effective 2026-07-21** — envelope measures (Dämmung, Fenster) keep 15% base; the 5-point iSFP bonus now applies only above €30,000 eligible investment (single-unit building) and only on the amount above it; max effective rate ~17.5%; new caps per additional unit (€15k for units 2–6, €8k from unit 7 without iSFP); WPB bonus for worst-performing buildings planned from Q1 2027; heating subsidy (KfW 458) cap lowered to €28k and reduced every half-year by €750; income bonus restructured (40%/30%/10%) [P BMWSB 2026-08; S reduco 2026-07, PB Schilling 2026-07, VDPM 2026-08]. Any page written before July 2026 claiming "20% mit iSFP" is now wrong for typical Fassaden jobs under €30k.
Gate: every Förder claim stores `{claim, source_url, source_date, verified_on}`; the weekly loop re-fetches source pages monthly and flags changes; pages show "Stand: …".

## 7. Content production rules for the plugin [I]
- No page without: target query cluster (SERP-validated), owner-confirmed facts, ≥3 evidence items, CTA block, internal links (from parent service page + related case studies), schema, and human approval.
- Lead-value score to prioritise briefs: `intent_weight × local_demand × margin_weight × (1 − AIO_risk × 0.5) × evidence_availability`.
- Refresh > new: pages ranking 4–15 with impressions get updated before writing new ones (striking-distance queue, see 10).
