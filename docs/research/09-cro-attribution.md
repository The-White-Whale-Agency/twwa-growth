# 09 · Conversion (CRO) and lead attribution without cookies (Germany)

Confidence legend: [P] primary · [S] secondary · [V] vendor claim · [I] inference/recommendation.

## 1. What converts on local service sites

### Conversion paths by vertical [I]
| Vertical | Primary | Secondary | Notes |
|---|---|---|---|
| Handwerk (Notfall: Dach, SHK, Elektro, Schlüssel) | Call | WhatsApp | Click-to-call above the fold on mobile; hours visible; "Rückruf in 30 Min" only if true |
| Handwerk (Projekt: Maler, Stuck, GaLaBau, Metallbau, Bau) | Form with photo upload | Call, WhatsApp | Form fields: PLZ/Ort, Leistung, Fläche/Umfang, Zeitraum, Fotos, Kontakt; promise "Angebot/Besichtigung innerhalb X Tagen" |
| Steuerberater, Finanz, Versicherung | Termin buchen / Rückruf | Form | Erstgespräch kostenlos/kostenpflichtig clarity; Mandatsgröße filter |
| Architekten/Ingenieure | Projektanfrage form | Call | Project type, Grundstück/Bestand, budget band |
| Hausverwaltung | Angebot anfordern (Einheiten, Ort, WEG/Miet) | Call | Price per unit anchors |
| Spedition | Quote form (Relation, Gewicht, Paletten, Termin) | Call | Needs structured fields |
| Fahrschule | Anmeldung/Beratung | WhatsApp | Price list + Kursstart dates |
| Restaurant | Reservierung | Call | Online booking tool; menu HTML |

### Page-level CRO checklist (enforced as template requirements) [I unless noted]
1. Above the fold (mobile): what + where ("Fassadensanierung in Musterstadt und Umgebung"), one primary CTA, phone tap target, trust line (★ rating + count with §5b notice, Meisterbetrieb, years).
2. Sticky bottom bar on mobile: Anrufen · WhatsApp · Anfrage.
3. **Price anchors**: "Fassadenanstrich EFH ab ca. € X / m²; typisch € Y–Z inkl. Gerüst" with drivers. German buyers research costs before contacting (cost/hybrid queries trigger AIO 97% per Whitespark → the page must give real numbers to be cited and trusted) [S].
4. Proof near CTA: 2–3 project photos with town, a review excerpt, certifications/partner logos (Sto, Innung).
5. Process & speed: "1. Anfrage → 2. Besichtigung in 5 Werktagen → 3. Festpreis-Angebot → 4. Ausführung". State response-time promise only if the business can keep it.
6. Form: ≤ 6 visible fields + optional photo upload; PLZ validation against service area (out-of-area → friendly message + still capture); honeypot + time-trap instead of reCAPTCHA (privacy); no mandatory phone unless needed.
7. Qualify gently: budget band / timeframe radio buttons improve lead quality reporting.
8. "Wie haben Sie uns gefunden?" (Google-Suche, Google Maps, ChatGPT/KI, Empfehlung, Fahrzeug/Bauschild, Portal, Sonstiges) — self-reported attribution, essential in a cookieless setup.
9. Thank-you state: what happens next + timeframe + phone; fire server-side event.
10. Accessibility basics (labels, contrast, focus) — also BFSG-relevant where in scope.

### Speed-to-lead
- Classic evidence: firms responding within 1 hour were ~7× more likely to qualify a lead than those responding later (HBR 2011, Oldroyd et al.) [S, older study]. German practitioner rule: "Rückruf innerhalb einer Stunde, sonst ruft der nächste Betrieb zuerst an" [S].
- Lead portals share each inquiry with 3–5 businesses; whoever calls first wins most often [S, ewerle/seodach 2026].
- Plugin action [I]: `api/contact.js` sends an instant owner notification (e-mail + optional SMS/WhatsApp via provider) with a one-tap "Anrufen" link; weekly report shows median response time if the owner marks "kontaktiert".

## 2. Attribution without cookies — architecture

Goal: count leads per channel and per landing page, and tie them to SEO actions, without consent banners.

### Signals available
| Signal | How | Consent? | Notes |
|---|---|---|---|
| Form submissions | `api/contact.js` (Vercel function) → Resend; add server-side `track('lead_form', {service, page})` via `@vercel/analytics/server` | No device access → no §25 consent; Art. 6 DSGVO basis = contract/pre-contract | Custom events need Vercel Pro; 2 properties on Pro, 8 with Web Analytics Plus ($10/mo/team); UTMs only with Plus [P] |
| Page where form was submitted | Read `Referer` header in the function (same-origin page URL) or a hidden field filled from `location.pathname` at submit time | No storage → no consent | Gives landing/conversion page, not original entry page |
| Entry source of the session | `document.referrer` + URL params at load, kept only in memory and inserted into the form on submit | No storage if not persisted [I] | Lost if user navigates multiple pages; persisting in sessionStorage = device storage → consent needed [I, §25 TDDDG] — **get DSB confirmation** |
| Click-to-call / WhatsApp clicks | `track('call_click')`, `track('whatsapp_click')` client-side | Vercel WA cookieless | Click ≠ call; use as proxy |
| Real calls by channel | **Static** tracking numbers: one for GBP (primary, real number as "additional"), one for website, one for vehicle/print | None | Most robust; calls ≥60 s = qualified (Handwerksratgeber definition) [P] |
| GBP actions | Business Profile Performance API: `CALL_CLICKS`, `WEBSITE_CLICKS`, `BUSINESS_DIRECTION_REQUESTS`, `MESSAGING_CLICKS`, `BUSINESS_BOOKINGS`, impressions by Maps/Search × desktop/mobile; monthly search keywords with thresholds for low values [P] | — | Requires GBP API approval |
| GBP → site visits | UTM on GBP website link | — | Vercel UTMs need Web Analytics Plus; otherwise referrer hostname only |
| Organic clicks per page/query | GSC Search Analytics API (incl. new `brandedClassification`, 2026-11-16) [P] | — | 2–3 day lag |
| AI referrals | Referrer hostnames chatgpt.com, perplexity.ai, gemini.google.com, copilot.microsoft.com; plus "Wie gefunden: ChatGPT/KI" | — | Many AI clicks arrive without referrer; self-report fills the gap |
| Won/lost | Owner marks lead outcome (link in the lead e-mail: "Auftrag erhalten? Ja/Nein/Offen" + optional value) | — | Turns leads into revenue reporting |

### Lead record schema (store in repo-external DB or Vercel KV/Blob with retention; DSGVO minimal) [I]
`{id, ts, channel: form|call|whatsapp|email, page, entry_referrer_host, utm_source?, self_reported_source, service, town/PLZ, in_service_area, budget_band, timeframe, qualified: bool (rules), owner_status: new|contacted|quoted|won|lost, value_eur?, response_minutes?}`
- No message bodies or personal data in analytics; personal data stays in the mailbox/CRM; retention e.g. 12–24 months; listed in Datenschutzerklärung; AVV with TWWA [I].
- Qualified rules (configurable): form with service + PLZ in area + real contact; call ≥ 60 s; WhatsApp with project description; exclude spam/job applications/supplier pitches.

## 3. Tying SEO actions to leads

Approach [I] (inspired by Klano's per-action measurement [P] and Ethan Smith's control groups [S]):
1. **Action log** (`growth/actions.jsonl`): `{action_id, type, pages_affected[], queries_targeted[], shipped_at, commit_sha, hypothesis, primary_metric, window_days, control_set}`.
2. **Measurement windows by action type** (see 11): technical fix 7–28 d; title/meta 14–28 d; new page 28–90 d; GBP category 2–14 d; review velocity 30–90 d; citations/links 30–120 d.
3. **Metrics per action**: impressions/clicks/position on affected pages & queries (GSC), local grid coverage (geo-grid), leads on affected pages (lead records `page` field), GBP actions.
4. **Controls**: compare affected pages vs a control set of untouched pages on the same site (difference-in-differences on clicks/impressions); adjust for seasonality with prior-year GSC data where available (16 months retained).
5. **Verdicts**: `win` (primary metric +X% beyond control and CI excludes 0), `neutral`, `loss` (revert candidate), `inconclusive` (low data — common for small sites; say so).
6. **Attribution of leads to actions**: a lead is attributed to the most recent action that affected its landing page within the action's window ("assisted" if multiple). Report "Anfragen über Seiten, die wir in den letzten 90 Tagen gebaut/verbessert haben".

Small-data reality [I]: an SMB site may get 5–40 leads/month; per-action statistical significance is rarely achievable. Report direction + confidence honestly, aggregate actions into monthly "programmes", and prefer leading indicators (impressions, grid coverage) for early verdicts.

## 4. How to report "Anfragen" to SMB owners (German, one page)
Template [I, informed by Handwerksratgeber/SEOLabs/Klano P]:
- **Diesen Monat: 23 Anfragen** (Vormonat 17, Start 9) — davon 15 qualifiziert · 6 Aufträge gewonnen (≈ € 38.400, laut deiner Rückmeldung).
- Woher: Google Maps/Profil 9 · Google-Suche 7 · Empfehlung 4 · ChatGPT/KI 1 · Sonstige 2.
- Welche Leistungen: Fassade 11 · Innenputz 6 · Trockenbau 4 · Sonstiges 2.
- Was wir gemacht haben (3–5 bullets) und was es gebracht hat (per-action verdicts in plain language, incl. "noch zu früh").
- Sichtbarkeit: Google-Profil Anrufe/Website-Klicks; Karte (Grid-Bild); KI-Erwähnungen (x von y Fragen).
- Nächster Monat: geplante Maßnahmen + was wir von dir brauchen (Fotos von Projekt X, Freigabe Y).
- Vergleich: "Über Portale hätten 15 qualifizierte Anfragen ca. € 750–1.800 gekostet und wären an 3–5 Betriebe gegangen." (price anchor from 01) [I].

## 5. Implications for the plugin [I]
- Ship an `api/contact.js` upgrade pattern: validation, honeypot, PLZ check, server-side Vercel event, lead record write, owner notification with outcome links, self-reported source field.
- Default to static call tracking numbers; DNI only with consent manager (avoid by default).
- Every report starts with Anfragen; if call data is missing, the report says so and asks the owner for a call count.
