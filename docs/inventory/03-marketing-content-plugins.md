# 03 · Marketing, content, conversion and small-business plugins

Inventory date 2026-11-17. **Reduced scope:** the builder for this group ran out of budget before writing. This file is compiled by the orchestrator from plugin manifests, LICENSE files and skill frontmatter only. Skill bodies were not read, so nothing here is distilled from them; the plugin's CRO, attribution, review and copy rules come from the research dossier (03, 05, 09) instead.

| Plugin | Version, licence | Relevant skills (from frontmatter) | Phases | Use |
|---|---|---|---|---|
| marketing-skills (Corey Haines) | 2.13.0, MIT | `cro`, `copywriting`, `copy-editing`, `conversion-tracking`, `attribution`, `analytics`, `ai-seo`, `seo-audit`, `schema`, `site-architecture`, `customer-research`, `public-relations` | P1, P4, P8 | call: `cro` and `copy-editing` as a second opinion on a page draft. `conversion-tracking` targets GTM, pixels and ad platforms, which conflicts with the cookieless default (dossier 09): do not follow it for client sites |
| marketing-skills | same | `programmatic-seo`, `directory-submissions`, `link-building` | P4, P6 | ignore. Descriptions target pages at scale, SaaS directories for backlinks and link acquisition; our gates and off-site rules replace them |
| claude-blog (AgriciDaniel) | 2.3.1, MIT | `blog-factcheck`, `blog-cannibalization`, `blog-decay`, `blog-seo-check`, `blog-geo` | P4, P8 | call: `blog-factcheck` on a draft if installed; our provenance gate remains the gate |
| humanizer (Siqi Chen) | 3.1.0, MIT | `humanizer` | P4, P5, P6, P10 | call on German drafts as a final pass if installed. No German-specific file was found by grep; `style_lint_de.py` stays the gate |
| claude-ads (AgriciDaniel) | 2.1.0, MIT | `ads-google`, `ads-landing`, `ads-server-side-tracking` | P2 | call only when the owner enables paid ads beyond `mention_only` |
| small-business (Anthropic) | 1.35.2, no licence file found | `review-reputation` (drafts replies, owner approves each), `speed-to-lead`, `lead-triage`, `report-builder` | P5, P8, P10 | call: reply drafting follows the same approve-each rule as ours. Its sources are Google, Yelp, Facebook; German review law is not covered |
| social-media-skills (Charlie Hills), linkedin-agent (Jake Schincariol) | 1.1.0 and 1.0.0, MIT | post writers and scorers | P5 | ignore; GBP posts are written from project reports with our own template |
| marketing, sales (Anthropic, synced) | Apache-2.0 | `draft-content`, `performance-report`, `draft-outreach` | P6, P10 | ignore; generic B2B |

## Positions to hold regardless of what these skills say

Taken from the dossier, because the bodies were not checked for contradictions:

- No review incentives, no gating, no electronic review request without consent (03 §5).
- Cookieless attribution by default; no pixels, no dynamic number insertion (09 §2).
- No link exchanges, no paid followed links, no directory submissions for link equity (08 §2).
- No page-count targets; pages pass gates A to H (06).

## Not read

All skill bodies and reference files in this group.
