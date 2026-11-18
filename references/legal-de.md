# German legal surface (Hinweis, keine Rechtsberatung)

The plugin checks wording and visible surfaces. It does not give legal advice and never writes or changes legal text; Impressum, Datenschutz and consent texts are R3 and need human sign-off (`legal.signoff`).

## Reviews

- No incentive for reviews, not even for asking (voucher, discount, raffle, gift, cash). Courts treat the request for a rewarded review as unlawful.
- Fake, bought or commissioned reviews, and reviews by staff, are always unlawful.
- No gating: never ask only happy customers, never intercept unhappy ones before they review.
- §5b Abs. 3 UWG: wherever reviews are shown (own stars, embedded Google reviews, widgets), say next to them whether and how authenticity is checked. Default text: „Diese Bewertungen stammen von Google. Wir haben keinen Einfluss auf Auswahl und Inhalt und prüfen nicht, ob die Verfasser Kunden sind.“ Use „Bewertungen“, not „Kundenbewertungen“, unless customer status is verified.
- Review requests by e-mail, SMS or WhatsApp are advertising and need recorded consent (`legal.review_request_electronic` is off by default). Safe channels: in person, a printed card with QR code. One request per job, no reminders, neutral wording („Wir freuen uns über Ihre ehrliche Bewertung“), no steering to five stars.
- Showing reviews with name or photo on the site needs consent. Review removal as a service is legal services; the plugin only drafts a factual report for the owner.

## Advertising claims

Unverifiable superlatives („bester“, „Nr. 1“, „führend“) and guarantees („garantiert“, „Geld zurück“) are linted out. Gewährleistung is a legal duty, not a guarantee. Steuerberater must advertise „sachlich“ (§ 57a StBerG); other chambers have similar rules.

## Tracking and embeds

- § 25 TDDDG: storing or reading information on the device needs prior consent unless strictly necessary. Vercel Web Analytics is cookieless; list it in the Datenschutzerklärung.
- Static call-tracking numbers need no device access; dynamic number insertion needs consent and is not implemented.
- Map iframes and remote Google Fonts transmit the visitor's IP on page load: maps behind a click, fonts self-hosted.
- A plain `wa.me` link is fine; embedded WhatsApp widgets that load third-party scripts need consent.

## Impressum (§ 5 DDG) checked by `legal_lint.py impressum`

All: full name and legal form, address (no PO box), e-mail plus a fast second channel (usually phone), register court and number for registered forms, representative for GmbH, UG and AG, USt-IdNr. if one exists. Outdated references: § 5 TMG (since 14 May 2024 § 5 DDG), TTDSG (now TDDDG), the EU online dispute resolution platform (closed 20 July 2025).

| Vertical | Additional fields |
|---|---|
| handwerk | Handwerkskammer, entry in the Handwerksrolle, professional title and state that granted it for regulated trades |
| steuerberater | Steuerberaterkammer, title „Steuerberater“ and granting state, professional rules (StBerG, BOStB, DVStB, StBVV) and where to read them, professional liability insurance |
| ingenieure | chamber, professional title, professional rules, liability insurance where the state requires it |
| finanzberatung | Vermittlerregister number, permit (§ 34d, § 34f, § 34h or § 34i GewO), IHK, arbitration bodies |
| hausverwaltung | permit under § 34c GewO, supervisory authority |
| fahrschule | permit or supervisory authority |

Every audit includes an Impressum and Datenschutz check; findings are hints for the owner and their lawyer.
