# Reading the gap score

- Reference = median of the `business` winners in the top 3 (portal-dominated: best business plus portals as listing targets).
- Each factor: 0 = client at or above reference, 1 = maximal gap. Unchecked factors are excluded and listed; `confidence` = share of weight checked.
- Weights (config `thresholds.teardown.weights`) follow the Whitespark 2026 factor order: organic (dedicated page 20, geo relevance 15, referring domains 15, title/H1 10, sub-questions 10, evidence 10, internal links 8, domain age 5, speed 4, schema 3); pack (primary category 20, proximity 20, review count 12, recency 10, rating 8, completeness 8, landing title/H1 8, landing links 8, NAP 6); AI (presence on cited domains 30, rating and volume 20, dedicated page with facts 20, third-party mentions 20, Bing index 10). Heuristics, not Google numbers.

Winnability (starting values, tunable with `learning.py suggest`):
- organic `now`: client at 4–15 and gap < 0.35; `with_work`: gap 0.35–0.65 or a business winner within 3× the client's referring domains (or ≤ 20); `long_term`: every winner > 10× and > 50 referring domains, or portal-dominated.
- pack `out_of_radius`: no address in town and farther than 15 km (5 km in towns ≥ 100,000); `with_work`: reviews < 50 % of the winner median (months = gap ÷ realistic monthly velocity); else `now`.
- AI `blocked_by_basics`: rating < 4.3, < 20 reviews or no dedicated page; else `with_work`.

Priority = query value × winnability factor (now 1, with_work 0.6, long_term 0.25, out_of_radius/blocked 0) × share of the gap the action closes ÷ effort (S 1, M 2, L 4).
