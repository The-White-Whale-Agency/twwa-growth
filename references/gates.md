# Page gates A to H

`page_gates.py run --page <file> --action <id>` runs A to G on a Markdown draft or a built HTML page and exits 1 when a gate fails. The output names the gate, the measured value, the threshold and a German backlog reason; with `--action` the result is logged and the reason lands in `backlog.json` as an owner data request. All numbers live in `config.thresholds.gates` and are internal heuristics; Google publishes none.

| Gate | Subcommand | Pass rule (default) | Data |
|---|---|---|---|
| A demand | `demand` | GSC impressions in 90 days at least 10 (towns under 20,000) or 30; or keyword volume above 0; or at least 2 jobs in 24 months and the town in the service area | latest `gsc.json`, `keywords.json` clusters, `keyword-volume.json`, `service_area.jobs_last_24_months`, projects |
| B service | `service` | town in `service_area` with `owner_confirmed` and `drive_minutes` at most 120 | `business.json` |
| C evidence | `evidence` | at least 3 items, at least 1 first-party | projects in the town; facts for the town or page (first-party kinds: travel time or fee, responsible person, review with consent); other facts count only with a source and `verified_on` |
| D swap | `swap` | at least 25% of non-boilerplate sentences town-bound; boilerplate under 60% of body words | see below |
| D similarity | `similarity` | 5-word shingle Jaccard at most 0.6 against every sibling page | non-boilerplate main text |
| D town list | `townlist` | no run of more than 8 towns | plain text runs and HTML lists |
| E usefulness | `thin` | what, where, price range, how fast, proof, contact, CTA, action on the page; under 250 own words is flagged thin (warning) | page text; drafts may declare `layout_contact: true` when the layout supplies phone and form |
| F facts and law | `sources` | no unsourced claim, no blocking legal wording, style gate passes | drafts: provenance markers; built pages: claims mapped against the registry |
| G ramp | `ramp`, `pilot` | new indexable pages per week at most max(2, 10% of indexed pages); at most 8 per month under 50 pages; a new template runs a pilot of 3 to 5 pages and continues only if 60% are indexed in 28 days and 50% have impressions in 56 days | `actions.jsonl`, GSC inspection |
| H prune | `prune` | pages older than 90 days with 0 clicks, under 20 impressions and no leads are proposed for consolidation (unless seasonal); a template with more than 40% "crawled, not indexed" stops | GSC snapshot, `leads.jsonl` |

## Swap test (rule based)

The page town and its Ortsteile are replaced with the nearest sibling town. A sentence counts as town-bound, and therefore false after the swap, when it contains an entity bound to the page town: a district, street, local authority or programme from `business.json.service_area` or from projects and facts in that town, a project or fact marker of that town, or a town-specific number with its unit (drive minutes, distance, project scope or duration). A sentence that only names the town is not town-bound. Boilerplate is text inside elements marked `data-twwa-shared`. The quality reviewer may add a judgement; it cannot turn a script failure into a pass.

## Provenance (spec 10b)

Drafts mark every factual sentence with `[[p:<project id>]]`, `[[f:<fact id>]]` or `[[b:<business.json path>]]` (lists resolve by `id` or `town`, e.g. `b:service_area.Nachbarstadt.drive_minutes`). `evidence.py provenance <draft>` fails when a factual sentence has no marker, a marker does not resolve, a resolved value is null, a number in the sentence is not in the record, a phone number differs, or a sourced fact was verified more than 90 days ago (31 days for subsidy claims). Factual means: digits, currency, units, percentages, years, durations, certifications and titles, place names other than the page town, programme or authority names, comparatives and superlatives. Markers are stripped when the page is built.

## Copy quality

`style_lint_de.py --gate` fails on stock phrases, empty superlatives and filler density above 2 per 100 words. In the ship path without `--gate` it only warns, and a reviewer acknowledges the warnings.
