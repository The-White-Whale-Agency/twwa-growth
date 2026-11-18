# Phase map

| Work order group | Phase | Skill | Scripts |
|---|---|---|---|
| 1 tracking | form pipeline, click events, source field | twwa-leads | leads.py, site_audit.py (tracking findings) |
| 2 GBP fundamentals | category, services, hours, photos, suspension risk | twwa-gbp | gbp.py audit/lint/snapshot |
| 3 money-page fixes | title/H1, sections, CTA, schema, links, speed | twwa-tech, twwa-pages | site_audit.py, schema_gen.py, psi.py |
| 4 review engine | velocity target, card, §5b notice, replies | twwa-reviews | reviews.py, gbp.py reply |
| 5 core citations | tier-1 listings, NAP | twwa-offsite | offsite.py, entity_check.py |
| 6 evidence-backed pages | gated pages, refresh, prune | twwa-pages | evidence.py, page_gates.py |
| 7 off-site mentions | memberships, partners, press, roundups (drafts) | twwa-offsite | offsite.py |
| 8 AI refinements | answer blocks, explicit facts, Bing | twwa-ai-visibility | ai_panel.py, bing_wmt.py, indexnow.py |
| centre | SERP teardown | twwa-serp-teardown | serp_teardown.py, geogrid.py |
| plan | cycle of ≤ 5 | twwa-plan | opportunities.py, plan.py, twwa_actions.py |
| ship | branch → gates → approval → merge → verify | twwa-ship | twwa_actions.py, regression_guard.py |
| measure | verdicts, alerts, learning | twwa-measure | measure.py, learning.py |
| loop | weekly digest | twwa-weekly | monitor.py |
| report | German one-pager | twwa-report | report.py, leads.py |

Broken table stakes (P1) always come first; otherwise table-stakes groups take at most 2 of the 5 slots while teardown-driven work exists.
