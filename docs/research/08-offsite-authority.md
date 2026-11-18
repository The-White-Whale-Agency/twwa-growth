# 08 · Off-site and authority for SMBs without link schemes

Confidence legend: [P] primary · [S] secondary · [V] vendor claim · [I] inference/recommendation.

## 1. Why off-site matters more now
- Local pack: links ≈ 8% of weight, but links to the GBP landing page from locally relevant domains rank #25–27 [P, Whitespark 2026].
- Local organic: domain link authority #3, industry-relevant linking domains #5 [P].
- AI visibility: top expert-rated factors are off-site — "best of" lists (#1), prominence on industry domains (#3), authority of unstructured citations (news, associations, gov) (#4), quantity of unstructured citations (#7), unlinked brand mentions (#12) [P]. Ethan Smith: "being mentioned most often beats ranking first" [S].
- Therefore: **mentions count even without a followed link** (AI reads text), which makes nofollow/sponsored-qualified placements and pure mentions valuable and safe [I].

## 2. What Google penalises (hard "never" list for the plugin)
From the link-spam policy [P]: buying/selling links that pass ranking credit (money, goods, services, free product for a review with link); **excessive link exchanges** and partner pages exclusively for cross-linking; **automated programs or services to create links**; requiring links in ToS/contracts without allowing qualification; advertorials/guest posts/press releases with ranking-passing or keyword-anchor links; low-quality directory/bookmark links; widget/footer/template links across sites; forum signature links; low-value content made mainly to place links.
Allowed: paid/sponsored relationships qualified with `rel="sponsored"` or `rel="nofollow"` [P].
- **Distribb-style ABC exchange networks** = automated + exchange → avoid (see 01) [P/S].
- "Website by Agency" footer links on all client sites with keyword anchors → widely distributed template links. TWWA footer credit on client sites: brand anchor ("Website: The White Whale Agency"), `rel="nofollow"` or omit [I].
- Interlinking between TWWA client sites (e.g., the painter links to the roofer "Partner") only when it is a real, disclosed cooperation and not a network pattern [I].
- PBNs/expired domains: expired domain abuse policy [P].

## 3. Safe authority sources for German SMBs (prioritised by effort/value)

### Tier A — membership and partner listings (high trust, low effort, often unique to the business)
- Handwerkskammer (Betriebsbörse/Handwerkerradar), Innung and Kreishandwerkerschaft member pages, Landesinnungsverband [S].
- Manufacturer partner finders: Sto Fachhandwerkersuche (self-activate, live within 2 days) [P], Caparol Handwerkspartner, Brillux, Knauf Fachunternehmer, Keim; SHK: Viessmann, Buderus, Vaillant installer search; Dach: Velux, Braas; Metallbau: Schüco, Hörmann; Elektro: SMA/Fronius installer finders for PV, Wallbox partner lists [I/S].
- Quality seals/associations with real criteria: "TOP Malermeister/Stuckateurmeister" [S], Meisterbetrieb directories, Energie-Effizienz-Experten-Liste (dena) for Energieberater/Architekten [I].
- Professions: Steuerberaterkammer/BStBK amtliches Verzeichnis, DStV steuerberater.de; Architekten-/Ingenieurkammer directories; VDIV for Hausverwalter; IHK Vermittlerregister [P/S].
- Local business networks: IHK/HWK regional pages, Wirtschaftsförderung (Gewerbegebiet directories), BNI chapters, Werbegemeinschaften, Gewerbevereine [I].

### Tier B — local editorial (high value for AI and organic)
- Lokalzeitung/regional news (the regional daily and its online edition), Stadtmagazine, Gemeindeblatt/Amtsblatt (many are online), local radio sites [I].
- Story angles that get published in German local media [I]: Ausbildung/Azubi-Erfolg (Gesellenprüfung bester des Kammerbezirks), Firmenjubiläum, Generationswechsel/Nachfolge, Restaurierung eines bekannten Gebäudes (Kirche, Rathaus, Denkmal), Hochwasser-/Sturmhilfe, Förder-Explainer with local numbers ("So viele Hausbesitzer im Kreis könnten…"), Fachkräftemangel-Initiativen, Spenden/Ehrenamt, Meisterpreis/Wettbewerbe.
- Process: monthly "Nachrichtenwert-Check" of the project log → draft press note (facts, photo with rights, quote, contact) → owner approval → send to the local editor (named contact, phone first). Presseportal distribution only as nofollow supplement [I].

### Tier C — "best of" lists and roundups (top AI factor)
- German local roundups: "Die besten Stuckateure in X" on city portals, regional blogs, "Top-Handwerker"-type award sites, Stadtmagazin rankings, Gastro guides; for Kanzleien: Focus/Handelsblatt-style lists (research-based, apply where criteria fit), regional business awards [I].
- Method (honest version of Distribb's gap finder): query engine (DataForSEO SERP + AI Mode) for "beste {Gewerk} {Stadt}" / "empfehlenswerte …" → collect roundup URLs that list ≥2 competitors but not the client → assess legitimacy (editorial criteria, not pay-to-play) → human-sent pitch with facts (rating, reviews count, years, specialisation, project examples) → never pay for a followed placement [I].
- Pay-to-play "award" sites that sell badges: avoid or treat as ads (no SEO claim) [I].

### Tier D — community & sponsorship
- Sponsoring local clubs (Sportverein trikot, Musikverein), school projects, charity runs: value = local brand + mention; Google requires paid links to be `sponsored`/`nofollow`, so don't make a followed link a condition [P/I].
- Expert contributions: answer journalist/editor queries, give talks at Innung/IHK events, write a guest column in the Innung newsletter (link qualified if exchanged for anything) [I].
- UGC: authentic answers on gutefrage.net / Reddit / local Facebook groups with disclosed identity; no fake accounts (Reddit kingmaker effect, Ethan Smith) [S].

### Tier E — citations and portals (see 03 for list)
- Value is consistency and AI retrieval, not link equity (only 9/50 tested German portals link dofollow) [S].

## 4. Cadence and targets [I]
- Month 1: all Tier A that apply (typically 3–8 listings) + Tier 1 citations.
- Months 2–6: 1 local editorial attempt per month; 1–2 roundup pitches per month; 1 community/sponsorship mention per quarter.
- Track in `growth/offsite.yml`: source, type, status, URL, link attribute, anchor, date, cited-by-AI flag (from prompt panel cited-domain analysis).
- KPI: count of distinct authoritative domains mentioning the business (linked or unlinked); share of panel-cited domains where the client is present.

## 5. Discovery data for off-site work
- Competitor backlinks/mentions: Bing Webmaster `GetUrlLinks`/`GetLinkCounts` (own site), Ahrefs/Semrush/DataForSEO Backlinks for competitors (paid), Common Crawl (free, coarse) [P/S].
- Unlinked mentions: search engine queries for `"Firmenname" -site:own-domain` via SERP API weekly; news via SERP News endpoint [I].
- AI-cited domains: from prompt panel raw citations (04) — the most actionable list ("these domains are cited for 'Stuckateur Musterstadt' prompts").

## 6. Implications for the plugin [I]
- `/twwa-offsite` produces a ranked opportunity list (Tier A first), drafts pitches/press notes for approval, never sends automatically, never buys/exchanges links, enforces rel-qualification on any paid relationship.
- A hard linter blocks: link-exchange networks, footer keyword links across client sites, paid followed links, automated comment/forum posting.
