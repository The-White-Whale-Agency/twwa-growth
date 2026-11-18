# Decisions

Two kinds of entries: decisions the agency owner has made, and defaults the builders chose where the owner has not decided yet. Every default is conservative, lives in the per-client `config.json`, and can be changed there. Nothing in this file contains client data.

## Decided by the owner (2026-11-16)

| Topic | Decision | Where it shows |
|---|---|---|
| Goal | First place for the client's money queries in Google organic, the map pack and AI answers. Reviews and profile basics are table stakes, not the centre | SERP teardown drives planning (`/twwa-serp-teardown`, `/twwa-plan`) |
| Pricing and packaging | None in the plugin. It is a capability TWWA includes in its tariffs | No price keys in config, no prices in proposals or reports |
| Google Business Profile | Full integration for TWWA's own profile and every client profile where TWWA is owner or manager: read everything, write behind the approval gate | `gbp.py`, `config.gbp.mode: "auto"`, `config.gbp.writes: "approved"` |
| Data vendors | No hardcoded vendor. A provider registry with a capability matrix; the best available provider is picked from the credentials present; a refresh step re-checks the market | `data/providers.json`, `providers.py` |
| Monthly project report | Clients send photos and a few sentences every month. It is the evidence source for new pages | `evidence.py intake`, `config.owner_input.monthly_project_report: true` |
| Monitoring | The legitimate parts of agency monitoring run as scheduled scripts without an own server | `monitor.py`, `templates/monitors/` |
| Banned | Click and CTR bots, traffic bots, fake engagement, private blog networks, scraping Google at scale against its terms, link exchanges, review incentives and gating, fake reviews, mass doorway pages | `references/safety.md`, the linters |
| Commits | Authored by the owner only, no co-author trailers | repository history |

## Defaults chosen by the builders, owner to confirm

| # | Question | Default | Key | To switch |
|---|---|---|---|---|
| 2 | Exclusivity per trade and district | Not offered. The plugin only warns when two registered clients share trade and Landkreis | `exclusivity.offered: false` | set to `true` and define `exclusivity.region` |
| 3 | Guarantees | None. Guarantee wording is rejected by the linter | `guarantee.mode: "none"` | `"exit_clause"` enables a neutral exit-clause sentence in proposals |
| 4 | Approval channel | TWWA approves on the branch. The owner approves by replying to a German summary with a preview link (e-mail or WhatsApp); the operator records it with a reference | `approval.owner_channel: "message"`, `approval.twwa_channel: "branch_review"` | other channels can be recorded; there is no owner-facing web app |
| 5 | Call tracking | None. Click events, the "Wie haben Sie uns gefunden?" field and owner-reported call counts | `call_tracking.mode: "none"` | `"static"` with one number per channel. Dynamic number insertion is not implemented because it needs consent |
| 6 | Vercel plan | Works on Hobby: no custom events, no UTM reporting. Leads are counted from tagged notification e-mails and manual entries | `vercel.custom_events: false`, `vercel.analytics_plus: false` | set to `true` on Pro, and with Web Analytics Plus |
| 7b | GBP identity fields | Name, address and pin are never written by a script. Primary category, primary phone and website link can be written with both approvals, at most one identity-level edit per 48 hours | `gbp.pacing_hours: 48` | not switchable for name, address and pin |
| 8b | Spend | Paid data calls are off until a monthly cap is set | `spend.monthly_cap_usd: 0` | set a cap per client; every paid call still needs `--execute` |
| 9 | Legal sign-off | Not assumed. Legal-relevant templates are marked as drafts to be checked by a lawyer; electronic review requests are disabled; in-memory referrer capture is not installed | `legal.signoff: false`, `legal.review_request_electronic: false`, `legal.referrer_capture: false` | set each to `true` after sign-off |
| 11 | Outreach | **Owner decision 2026-11-18:** both the client and TWWA may send. The plugin drafts and checks; a person sends. TWWA sends only with a recorded written mandate. `offsite.py send-check` enforces the German channel rules (no promotional e-mail without consent or relationship; cold contacts by letter or phone) | `outreach.send_mode: "draft_only"`, `outreach.mandate` | `"client_sends"`, `"twwa_sends"`; no automated sending exists |
| 12 | AI training crawlers | Unchanged. The plugin does not add or remove rules for training bots; search and answer bots must not be blocked | `ai_bots.training: "no_change"` | `"allow"` or `"block"` |
| 13 | Paid ads | Mention only: the plan may note that the pack is out of reach for a query and that ads are worth evaluating | `paid_ads.mode: "mention_only"` | `"off"` |
| 14 | Where client data lives | In the client's private repository under `.twwa-growth/`, with no personal data. Prospect checks go to `./twwa-checks/<domain>/`. The learning log stays on the operator's machine | `state_dir`, `data.pii: "never"` | `TWWA_STATE_DIR`, `TWWA_AGENCY_DIR` |
| - | Autopilot | Off. The agent prepares, a human merges | `autopilot.level: "off"` | `"technical"` or `"approved"` |
| - | Footer credit on client sites | Left as it is. A brand-anchor credit is not a link scheme; `rel="nofollow"` is recommended in the check but never changed by the plugin | none | agency decision |
| - | Internal language | Summaries to the operator follow the operator's language; everything for clients is German | `language.internal: "auto"` | `"en"`, `"de"`, `"ru"` |

## Engineering decisions

- **Gates are scripts.** Skills explain; scripts decide with exit codes.
- **No hooks, no `allowed-tools` in skills.** Scheduled runs stop to ask when a skill declares either, and hooks fail open. Enforcement lives in the scripts.
- **Python standard library only.** No install step; Google service-account signing uses the `openssl` binary.
- **Thresholds are heuristics.** Gate and teardown numbers come from the research dossier, are stored in `config.thresholds`, and are meant to be tuned from the learning log. Google publishes no numeric thresholds for page similarity or uniqueness.
- **Adapters built from documentation are marked.** A provider adapter counts as live-verified only after its first successful real call.
