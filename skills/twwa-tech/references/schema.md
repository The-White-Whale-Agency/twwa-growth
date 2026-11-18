# Structured data for local businesses

Purpose: entity clarity. Markup helps search engines and AI systems tie the site to one business. It does not create rich results for FAQ or HowTo any more, and it is not a ranking lever by itself.

## Source of truth

`business.json` is the only source. Generate, never hand-edit:

- `schema_gen.py localbusiness` (home page graph: WebSite plus the business node)
- `schema_gen.py service --id <service> [--town <town>]` (service pages)
- `schema_gen.py breadcrumb --path /a/b --names "Start,A,B"`

The Astro components in `templates/site/components/` produce the same output at build time. `null` values are never emitted; prices only when `price.confirmed_by` is set.

## Subtype

The most specific schema.org type from `data/schema-types.json` (`trades`), else the vertical default. Examples: Stuckateur and Maler `HousePainter` (or `GeneralContractor` when Stuck, Putz and Fassade dominate), Dachdecker `RoofingContractor`, Elektro `Electrician`, Steuerberater `AccountingService`, Fahrschule `DrivingSchool`. `Locksmith` only for a Schlüsseldienst, `MovingCompany` only for Umzüge.

## Required and checked by `schema_gen.py validate`

- JSON parses.
- The home page has a LocalBusiness node.
- Name, street, postcode, town and telephone equal `business.json` (a registered tracking number counts as equal).
- URL host equals `business.json.url`.
- Name and phone are visible on the page (no markup of invisible content).
- Every confirmed profile URL is in `sameAs` (entity check, separate script).

## Never

- `AggregateRating` or `Review` about the business itself (self-serving; no stars since 2019). If reviews are shown on the page, they need the §5b notice next to them.
- Markup for content that is not on the page.
- Retired types as a promise: FAQPage (rich results removed 2026-05-07), HowTo, SpecialAnnouncement, ClaimReview. Existing FAQ markup may stay; promise nothing.
- Keyword stuffing in `name` or `description`.

## Service pages

`Service` with `serviceType`, `areaServed` (City), `provider` pointing to the business `@id`, optional `offers.priceSpecification` with a confirmed range. One Service node per page.
