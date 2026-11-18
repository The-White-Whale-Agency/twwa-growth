# Teardown method

## Query classes (step 1)

| class | pattern | main surface |
|---|---|---|
| service_town | "{Leistung} {Stadt}", "{Gewerk} {Stadt}", regional synonyms (`voice.regional_terms`) | pack and organic |
| near_me | "{Gewerk} in der Nähe" | pack only (observe at the address and the town centre) |
| cost | "{Leistung} Kosten", "was kostet {Leistung}" | organic and AI overview |
| need | "{Gewerk} {Bedarf} {Stadt}" from `services[].needs` | organic and AI |
| best | "bester {Gewerk} {Stadt}" | AI answers and organic |

Value = service priority weight × margin weight × demand (provider volume, else GSC impressions, else 1 and flagged). Cap 15; every priority-1 service gets its home-town query first.

## Manual observation (no provider, or AI surface)

1. Clean browser profile (private window), logged out, Google set to German. Set the location to the searched town (search tools > location, or a browser tool's geolocation override). Note the method.
2. Search the query on google.de. Record organic ranks 1–10 (URL, title) and the 3 map-pack entries (name, rating, review count, category if shown). Note whether an AI Overview appears and which domains it cites.
3. Save as JSON (`serp_teardown.py import --help` shows the shape): `{"query","surface":"organic","town","observed_at","how","results":[{"rank","url","title"}],"local_pack":[{"rank","name","rating","reviews","category","lat","lng"}]}`.
4. AI answers: ask ChatGPT, Perplexity and Gemini the panel prompts in a clean session; save each answer as `<prompt_id>__<engine>__<n>.txt`; `ai_panel.py import <folder>`.
Manual observations are labelled "Stichprobe" in every report. One person looking at a result page is fine; automated scraping of Google is not.

## Data points per winner (step 4)

Organic: page type; title and H1 contain service and town; main-content words; sub-questions covered (price, process, duration, area, proof, FAQ, contact); evidence items (numbers with units, captioned own photos); internal inlinks from sampled pages; schema types; referring domains (provider `backlinks`); first seen (`domain_age`); speed when PSI is available.
Pack: primary category; rating; review count; distance from the town centre; address in the searched town; landing-page title/H1; NAP equality.
AI: businesses named per engine with mention rate; cited domains by type; whether the client is named or its domain cited.

## Gap → action → time (step 7)

| largest gap | action | first signal | evaluate after |
|---|---|---|---|
| no dedicated page | new_page (Scale) or landing section + scope proposal (Premium) | 2–8 weeks | 28–90 days |
| title/H1 | onpage_rewrite | after recrawl | 14–28 days |
| sub-questions, evidence | page_refresh + project report request | 2–4 weeks | 28 days |
| internal links, schema, speed | tech_fix | 1–3 weeks | 7–28 days |
| referring domains, mentions | citation, offsite_mention | weeks–months | 60–180 days |
| category, completeness | gbp_identity_edit / gbp_content_edit | 2–14 days | 14 days |
| review count, recency | review_engine | weeks | 30–90 days |
| not on AI-cited domains | citation, offsite_mention | weeks | 60–120 days, ≥ 4 panel runs |
| not in Bing | IndexNow + Bing sitemap | days | 7 days |
