# twwa-growth: specification

Status: build spec, 2026-11-16. Factual basis: `docs/research/` (dossier). Tool landscape: `docs/inventory/`.
This file is the contract between components. Builders implement against it; where a builder needs to deviate, it records the deviation in its hand-back and the spec is updated.

## 1. What the plugin is

A Claude Code plugin that runs a measured local-growth programme on a client site TWWA controls (Astro static on Vercel, git repo), and a free read-only check on any public URL for prospects.

Goal: put the client first for its money queries on three surfaces, Google organic, the map pack and AI answers, and turn that visibility into qualified Anfragen. The centre of the plugin is the **SERP teardown** (section 10a): for each target query it observes who wins on each surface, works out why, scores the gap against the client and turns the gap into prioritised backlog items. Planning is driven by these teardowns. Tracking, GBP fundamentals, reviews and core citations are table stakes: they must be in place, but they are not the centre.

It is not an article generator. It ships few changes, each with a hypothesis, a metric, a measurement window and control pages, and it reports in qualified Anfragen.

The plugin contains no pricing and no packaging. It is a capability; what TWWA charges for it is decided outside the plugin. Website tier handling (scope file) stays.

Dependency order of work (dossier 00, 02 §6). Groups 1, 2, 4 and 5 are table stakes. Broken table stakes (P1) always come first; otherwise table-stakes items take at most 2 of the 5 slots of a cycle while teardown-driven actions exist:

1. tracking
2. GBP fundamentals
3. money-page fixes
4. review engine
5. core citations
6. evidence-backed new pages
7. off-site mentions
8. AI-specific refinements

## 2. Design rules

1. **Gates are scripts with exit codes.** Prose rules are explanations; the ship path calls scripts and stops on non-zero.
2. **Measure before you read.** Live data (HTTP, APIs, git) wins over anything in the state folder. Snapshots are dated; a finding older than its snapshot is stale.
3. **Evidence or "Hypothese".** Every finding carries a URL, file and line, or data point. Without one it is labelled a hypothesis and never leads a report.
4. **Drafts only for anything a customer, an owner or the public will read**, until an approval bound to the exact content exists.
5. **Idempotent.** Re-running a step updates in place (keyed by action id, slug, date); it never creates a second copy.
6. **Standalone.** Every phase works with no installed third-party skill, no MCP server and no credentials, in a reduced but honest form: missing data is reported as "nicht geprüft", never estimated.
7. **German for clients, English for the repo.** Reports, page copy, review texts, GBP posts, owner requests and proposals are German. Skill files, references, code comments and docs are English. Internal summaries to the operator follow the operator's language.
8. **No client data in this repo.** Examples use "Musterbetrieb", "Musterstadt", "Nachbarstadt", `musterbetrieb.example`.

## 3. Repository layout

```
.claude-plugin/plugin.json          manifest
.claude-plugin/marketplace.json     single-plugin marketplace so the repo installs directly
skills/twwa-*/SKILL.md              16 skills (section 6), each with its own references/
agents/twwa-*.md                    4 subagents (section 7)
scripts/*.py                        CLI tools, Python 3.9+ standard library only (section 8)
scripts/twwa_lib/                   shared library (section 8.1)
scripts/twwa_lib/providers/         provider-agnostic data adapters (section 9a)
templates/state/                    initial contents of a client state folder
templates/site/                     Astro, Vercel and API snippets copied into client repos by twwa-ship
templates/de/                       German text templates (report, owner request, review assets, outreach)
data/                               reference data as JSON (provider registry, citation sources DE, schema subtype map, seasonality, expected CTR curve)
references/                         shared references used by several skills
templates/monitors/                 scheduled monitor templates (GitHub Actions, Claude Code routine, launchd)
tests/                              unittest suites and fixtures
docs/                               research dossier, inventory, this spec
README.md LICENSE DECISIONS.md CHANGELOG.md
```

Scripts are invoked from skill text as `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py" ...`. Each SKILL.md states once: "If `${CLAUDE_PLUGIN_ROOT}` is empty, the plugin root is two directories above this file."

## 4. Per-client state folder: `.twwa-growth/`

Lives in the client repo root (default; switchable with `--state` or `TWWA_STATE_DIR`). Created by `twwa_state.py init`. Contains no personal data and no secrets.

```
.twwa-growth/
  config.json            owner and agency decisions, caps, connector switches (section 5)
  business.json          canonical business facts: the single source for NAP, schema, listings
  keywords.json          query clusters: id, queries[], intent, priority, target_page, town
  prompts.json           AI prompt panel
  competitors.json       competitor set (name, domain, maps place id if known, source)
  evidence/
    inbox/               raw monthly project reports as received (text file plus photo file names; photos themselves go to the site's asset folder or stay outside git)
    projects/<yyyy-mm>-<slug>.json    one "Projekt-Kurzbericht" per file, normalised by `evidence.py intake`
    facts.json           claims registry: claim, value, source_url, source_date, verified_on, confirmed_by
  teardowns/<yyyy-mm-dd>/<query-slug>.json   SERP teardown per target query, plus summary.json
  backlog.json           opportunities with status, priority and the reason they wait
  actions.jsonl          append-only action events
  approvals/<action_id>.json          approval records bound to a content hash
  drafts/<action_id>/    page drafts, GBP posts, replies, outreach, owner requests
  snapshots/<yyyy-mm-dd>/<source>.json  normalised data pulls (section 9)
  reports/<yyyy-mm>.md   monthly owner reports; reports/check-<yyyy-mm-dd>.md
  proposals/<yyyy-mm-dd>-<slug>.md    out-of-scope work written up as an offer
  leads.jsonl            lead records without personal data
  offsite.json           citations and mentions tracker
  reviews.json           velocity target, consent ledger references (no names), reply log
  spend.jsonl            paid-API ledger
  out/                   exports (HTML, SVG, PDF); git-ignored
  STOP                   circuit breaker: if this file exists, nothing ships and nothing spends
```

### 4.1 Compatibility with TWWA's tier guard

Client repos are checked by `check-tier.mjs`, which walks every folder including dot-folders, treats any `.html` file outside ignored folders as a page, treats `pages/**.md` as a route, and reads `- APPROVED: <name>` lines from every `.md` in the repo. Therefore:

- The state folder never contains `.html` files outside `out/` (a directory name the guard ignores).
- No directory inside the state folder is named `pages`, `app` or `routes`.
- **The plugin never writes a line that starts with `- APPROVED:` anywhere.** Scope exceptions are granted only by the agency owner, by hand, in the scope file. Our approvals are JSON in `approvals/`.
- `twwa_state.py doctor` verifies all three and exits 1 on a violation.

### 4.2 `business.json` (canonical facts)

```json
{
  "schema_version": 1,
  "name": "Musterbetrieb Stuck und Putz GmbH",
  "name_source": "impressum",
  "legal_form": "GmbH",
  "owner": "Max Mustermann",
  "vertical": "handwerk",
  "trade": "stuckateur",
  "schema_type": "HousePainter",
  "address": {"street": "Musterstraße 1", "zip": "12345", "city": "Musterstadt", "region": "Baden-Württemberg", "country": "DE"},
  "address_public": true,
  "customers_received_at_address": true,
  "geo": {"lat": 48.0, "lng": 8.0},
  "phone": "+49 7000 123456",
  "phone_display": "07000 / 12 34 56",
  "tracking_numbers": [],
  "email": "info@musterbetrieb.example",
  "url": "https://www.musterbetrieb.example",
  "hours": [{"days": ["Mo","Tu","We","Th","Fr"], "open": "07:30", "close": "17:00"}],
  "special_hours": [],
  "founded": 2001,
  "services": [
    {"id": "fassadensanierung", "name": "Fassadensanierung", "page": "/fassadensanierung", "price": {"unit": "m²", "min": null, "typical_min": null, "typical_max": null, "as_of": null, "confirmed_by": null}, "priority": 1, "margin": "high"}
  ],
  "service_area": [
    {"town": "Musterstadt", "zip": ["12345"], "population": 18000, "drive_minutes": 0, "owner_confirmed": "2026-11-01", "jobs_last_24_months": 14}
  ],
  "credentials": [{"type": "meisterbrief", "holder": "Max Mustermann", "issuer": "Handwerkskammer Musterregion", "verified": true}],
  "memberships": [],
  "gbp": {"place_id": null, "maps_url": null, "primary_category": null, "secondary_categories": [], "role_twwa": "manager"},
  "profiles": {"bing_places": null, "apple_business": null, "dasoertliche": null, "gelbeseiten": null, "elf880": null, "werkenntdenbesten": null},
  "legal": {"chamber": null, "register": null, "vat_id": null, "profession_rules": null},
  "voice": {"address": "Sie", "regional_terms": ["Gipser", "Stuckateur"]},
  "capacity": {"wanted_jobs_per_month": null, "avg_job_value_eur": null, "close_rate": null}
}
```

`null` means unknown, and unknown facts are never written into copy, schema or reports. `vertical` is one of `handwerk`, `steuerberater`, `finanzberatung`, `ingenieure`, `hausverwaltung`, `spedition`, `fahrschule`, `restaurant`, `other`.

### 4.3 Findings

Every audit script emits the same record:

```json
{"id": "tech.canonical.missing", "area": "tech", "severity": "P2", "title_de": "…", "detail_de": "…",
 "evidence": {"url": "https://…", "file": null, "line": null, "snippet": "…", "value": null},
 "status": "verified", "fix_hint": "…", "action_type": "tech_fix", "priority_group": 3}
```

- `area`: `tracking`, `gbp`, `tech`, `onpage`, `cro`, `legal`, `citations`, `reviews`, `ai`, `content`, `offsite`.
- `severity`: `P1` (leads are being lost now, or legal or indexing breakage), `P2` (clear loss of visibility or conversion), `P3` (improvement), `info`.
- `status`: `verified` (evidence attached), `hypothesis` (no direct evidence), `not_checked` (data source missing; `detail_de` says which).
- `priority_group`: 1 to 8, the work order in section 1.
- Finding ids are stable so that runs can be diffed; a finding fixed in a deploy must not reappear unless the live check fails again.

### 4.4 Actions

`actions.jsonl` is an event log. Each line: `{"ts", "action_id", "event", ...}`. The current state of an action is the fold of its events.

States: `proposed → approved → shipped → measured → kept | reverted`, plus `rejected`, `blocked` (waits on owner or scope) and `superseded`.

`proposed` event payload:

```json
{"action_id": "2026-11-a03", "type": "onpage_rewrite", "title_de": "…", "priority_group": 3, "risk": "R2",
 "hypothesis": "…", "primary_metric": "gsc.clicks", "secondary_metrics": ["gsc.position", "leads.count"],
 "window_days": 28, "pages_affected": ["/"], "queries_targeted": ["stuckateur musterstadt"],
 "control_pages": [], "owner_effort_minutes": 5, "source_findings": ["onpage.title.no_town"],
 "expected": "…", "scope": {"in_scope": true, "reason": "…"}, "baseline_snapshot": "2026-11-16"}
```

Action types, default windows (dossier 11 §3) and risk classes:

| type | group | window (days) | risk | notes |
|---|---|---|---|---|
| `tracking_fix` | 1 | 7 | R1 | form pipeline, click events, "Wie gefunden" field (visible field: R2) |
| `gbp_identity_edit` | 2 | 14 | R3 or R2+ | name, address, pin: R3, human only. Primary category, primary phone, website link: R2 with both approvals and pacing, max one identity-level edit per 48 h |
| `gbp_content_edit` | 2 | 14 | R2 | secondary categories, services, hours, attributes, description |
| `gbp_post` | 2 | 28 | R2 | conversion only; a ranking hypothesis is rejected by the linter |
| `tech_fix` | 3 | 28 | R1 | canonical, redirects, sitemap, schema and NAP sync, internal links, image weight |
| `robots_policy` | 3 | 7 | R1 | |
| `onpage_rewrite` | 3 | 28 | R2 | title, H1, meta, section copy on existing pages |
| `cro_change` | 3 | 28 | R2 | CTA, form, proof placement, price anchor |
| `review_engine` | 4 | 90 | R2 | assets and process; requests are sent by the owner |
| `review_reply` | 4 | 30 | R2 | draft, owner approves and posts |
| `citation` | 5 | 120 | R2 | Tier 1 and vertical listings |
| `new_page` | 6 | 90 | R2 | gates A to H; needs a multi-page tier |
| `page_refresh` | 6 | 28 | R2 | striking-distance update |
| `page_consolidate` | 6 | 28 | R2 | Gate H prune: redirect into parent |
| `offsite_mention` | 7 | 180 | R2 | press note, roundup pitch, membership listing: drafts only |
| `ai_refinement` | 8 | 28 | R2 | answer blocks, explicit facts; never special AI files as a lever |

Risk classes:

| class | meaning | approvals required | who executes |
|---|---|---|---|
| R0 | read-only | none | agent |
| R1 | technical, no visible claim changes | TWWA | agent on a branch; merge per autopilot level |
| R2 | visible content, claims, prices, photos, profile content | TWWA and owner | agent prepares; merge per autopilot level; GBP writes (review replies, posts, info edits) through the connector with `--execute` after `verify` passes; off-site entries by a human |
| R3 | identity or legal: GBP name, address, pin; Impressum, Datenschutz, consent wording | TWWA and owner, plus `legal.signoff` for legal text | always a human. No script performs R3 writes in any mode |

Caps enforced by `twwa_actions.py propose` (exit 4 on breach): at most 5 open proposals per cycle; at most one `gbp_identity_edit` per 48 h; page ramp per Gate G; spend caps; `STOP`.

### 4.5 Approvals

`twwa_actions.py approve <action_id> --role twwa|owner --by "<name>" --channel pr|email|whatsapp|call|in_person --evidence "<reference>"` computes

`content_hash = sha256( sorted lines of "<relative path>\t<sha256 of file bytes>" for every artifact of the action )`

where artifacts are the files listed in the action's `artifacts` (changed source files on the action branch and files under `drafts/<action_id>/`), and stores `{action_id, role, by, at, channel, evidence, content_hash, git_head, preview_url}`.

`twwa_actions.py verify <action_id>` recomputes the hash and exits 4 if any required role is missing or any artifact changed after approval. `twwa-ship` runs it immediately before merge and again before any connector write. A changed artifact invalidates the approval; there is no override flag.

Owner approvals are recorded by the TWWA operator with a reference to where the owner said yes (default channel: German summary with preview link by e-mail or WhatsApp). The plugin never fabricates an owner approval and never infers one from silence.

### 4.6 Autopilot

`config.autopilot.level`:

| level | behaviour |
|---|---|
| `off` (default) | The agent prepares branches, previews and approval packets. A human merges. Nothing is pushed, merged or posted by the agent |
| `technical` | After a verified TWWA approval the agent may merge R1 actions, then must run live verification |
| `approved` | The agent may merge any R1 or R2 action whose approvals verify |

In every level: no R3 execution, no sending of e-mails or messages, no review requests, no outreach, no production deploy without live verification afterwards, and `STOP` halts everything. Unattended runs (`weekly`) never merge and never write to GBP; a GBP write happens only when an operator asks for that action to be executed and its approvals verify.

Revert path for every shipped site action: `git revert <commit>` on a branch, preview, merge, live verification, `reverted` event with the reason.

## 5. Configuration and owner decisions

`config.json` is created from `templates/state/config.json`. Every default below is conservative, documented in `DECISIONS.md` as "default chosen by builder, owner to confirm", and switchable.

| # | Open question | Key | Default / decision |
|---|---|---|---|
| 1 | Packaging and price | none | **Owner decision 2026-11-16:** no pricing or packaging in the plugin. It is a capability included in TWWA's tariffs. Proposals describe scope and never print a price |
| 2 | Exclusivity | `exclusivity.offered` | `false`. `twwa_state.py conflicts` warns when two registered clients share trade and Landkreis |
| 3 | Guarantees | `guarantee.mode` | `"none"`. Linter rejects guarantee wording in proposals and reports |
| 4 | Approval channel | `approval.owner_channel`, `approval.twwa_channel` | owner: `"message"` (summary plus preview link by e-mail or WhatsApp, recorded by the operator); TWWA: `"branch_review"` |
| 5 | Call tracking | `call_tracking.mode` | `"none"`: click events, self-reported source and owner-reported call counts. `"static"` available. DNI is not implemented |
| 6 | Vercel plan | `vercel.custom_events`, `vercel.analytics_plus` | both `false` (works on Hobby). Leads are counted from tagged notification e-mails and manual entries until `custom_events` is `true` |
| 7 | GBP API | `gbp.mode`, `gbp.writes` | **Owner decision:** full integration for TWWA's own profile and every client profile where TWWA is owner or manager. `gbp.mode: "auto"` (API when credentials and access exist, else the manual fallback). `gbp.writes: "approved"`: review replies, posts and info edits go through the API only after `twwa_actions.py verify` passes. Name, address and pin are never written by a script |
| 8 | Data vendor | `providers.*`, `spend.monthly_cap_usd` | **Owner decision:** no hardcoded vendor. Provider registry with capability matrix; the best available provider is picked from the credentials present (section 9a). Cap `0` until the owner sets one, so paid calls are off by default; every paid call needs `--execute` and passes the ledger |
| 9 | Legal sign-off | `legal.signoff`, `legal.review_request_electronic`, `legal.referrer_capture` | all `false`: legal-relevant templates are marked "Entwurf, vor Einsatz rechtlich prüfen"; electronic review requests are disabled (in person and printed QR card remain); in-memory referrer capture is not installed |
| 10 | Monthly project report from the client | `owner_input.monthly_project_report` | **Owner decision:** `true`. Clients send photos plus a few sentences monthly. The intake format (`evidence.py intake`) is the evidence source for new pages; the weekly loop flags a missing report |
| 11 | Outreach sending | `outreach.send_mode` | `"draft_only"` (still unanswered by the owner; default kept) |
| 12 | AI training crawlers | `ai_bots.training` | `"no_change"`: the plugin does not alter training-bot rules. Search and answer bots must not be blocked (finding if they are) |
| 13 | Paid ads | `paid_ads.mode` | `"mention_only"`: the plan may note that the pack is unreachable and ads or LSA are worth evaluating. No campaign work |
| 14 | Where client data lives | `state_dir`, `data.pii` | state in the client's private repo, `data.pii: "never"`. Prospect checks are written outside client repos, to `./twwa-checks/<domain>/` |

Other keys: `tier` (detected: `basic`, `premium`, `scale`, `unknown`), `scope_file`, `tier_guard` (path to `check-tier.mjs` if present), `autopilot.level`, `language.client` (`de`), `language.internal` (`auto`), `caps` (`proposals_per_cycle: 5`, `table_stakes_slots: 2`, `target_queries: 15`, `ai_prompts: 40`, `ai_runs: 3`, `grid_size: 7`, `grid_keywords: 10`, `crawl_pages: 25`, `competitor_pages: 8`, `page_cooldown_days: 14`: one content edit per page per window), `gbp.pacing_hours` (48), `thresholds` (gate numbers from section 10 and teardown numbers from section 10a, overridable with a recorded reason), `providers` (section 9a), `connectors` (section 9).

Gate G always limits new pages.

### 5.1 Tier and scope

`twwa_state.py scope` finds the scope file (configured, or the first of `scope.md`, `SCOPE.md`, `TIER-SCOPE.md`, `TWWA-SCOPE.md`, or a root `.md` whose first heading names a tier), reads the tier and the owner's exception lines, and answers `scope check --type <action_type> [--adds-page] [--adds-dependency <name>] [--adds-api-route]`.

| tier | in scope for growth work | out of scope |
|---|---|---|
| basic | everything on the existing pages, GBP, reviews, citations, off-site, tracking that needs no new server route | new pages, new API routes, heavy visual work |
| premium | as basic, plus changes to the existing form handler | any new page beyond landing, legal and 404; databases, auth, CMS, i18n |
| scale | new pages through the gated pipeline, more server routes | what the scope file excludes |
| unknown | treated as premium, with a finding asking TWWA to set the tier | |

Out-of-scope work becomes a proposal: `twwa_actions.py propose --as-proposal` writes `proposals/<date>-<slug>.md` in German (what, why with the teardown evidence, what it needs, which website tier it belongs to; no price) and a `blocked` action with `reason: "scope"`. It is never implemented under the current tier, and the plugin never adds an exception line. On a one-page site, service and town demand is first served on the landing page itself (sections, anchors, explicit service-area facts), which is in scope.

If `tier_guard` is set, `twwa-ship` runs it and requires that it does not report a new FAIL compared with the base branch.

## 6. Skills

All are in `skills/<name>/SKILL.md`, with `name` equal to the folder name. The description states when to use it, in third person, and does not summarise the workflow. No skill declares `allowed-tools` or hooks (scheduled runs would stop to ask). Each SKILL.md is lean (target under 150 lines): purpose, inputs, the steps as a numbered list of script calls and decisions, outputs, stop conditions, optional integrations as one table, and links to its `references/*.md`, each loaded only at the step that needs it.

| Skill | Job | Inputs | Outputs | Loads |
|---|---|---|---|---|
| `twwa-growth` | Entry point. Detects context, picks the mode, runs the phases in order, returns the final result. Modes: `check`, `onboard`, `teardown`, `plan`, `run`, `weekly`, `report`, `status` | mode, optional URL or repo path | the mode's result plus a short operator summary | `references/modes.md`, `references/phase-map.md`, shared `references/safety.md` |
| `twwa-check` | Read-only audit. Client mode (repo plus live site) or prospect mode (any URL, no repo, no credentials). Never writes to the site, never posts forms on sites TWWA does not control | URL or repo | findings JSON, German check report, for prospects a one-page "Sichtbarkeits-Check" and a call opener | `references/check-areas.md`, `references/prospect-mode.md` |
| `twwa-onboard` | Creates the state folder, fills `business.json` from the repo and the live Impressum, marks unknowns, lists access to request, writes owner questions | repo | state folder, `clients-questions` additions, connector status | `references/onboarding.md`, shared `references/state-and-config.md` |
| `twwa-serp-teardown` | The central analysis. For each target query: who is first to third in organic, in the map pack and in AI answers, why they win, the gap against the client, winnability, and backlog items with priority and expected time | business.json, keywords.json, provider layer | `teardowns/<date>/`, backlog items | `references/method.md`, `references/data-points.md`, `references/gap-scoring.md`, `references/gap-to-action.md` |
| `twwa-plan` | Turns the teardown backlog, findings and opportunities into at most 5 proposed actions, each with hypothesis, metric, window, control pages, owner effort, risk; out-of-scope items become proposals. Refuses to plan growth actions without a teardown younger than 35 days (table-stakes and P1 fixes excepted) | teardowns, findings, backlog, config | proposed actions, German plan for the owner, proposals | `references/planning.md` |
| `twwa-ship` | Implements one approved action: branch, change, build, gate scripts, preview, approval verification, merge per autopilot, live verification, IndexNow, log | action id | branch, preview URL, approval packet, `shipped` event | `references/ship-path.md`, `references/revert.md` |
| `twwa-tech` | Astro and Vercel technical audit and fixers: canonical and slash policy, redirects, sitemap, robots and AI-bot policy, schema from `business.json`, internal links, images, preview noindex, IndexNow | repo or URL | findings, fix branches via `twwa-ship` | `references/astro-vercel.md`, `references/schema.md`, `references/indexing.md` |
| `twwa-gbp` | Google Business Profile connector and playbook: read everything (information, performance, reviews, posts, media, notifications) for TWWA's and clients' profiles, audit field by field against the pack winners, suspension-risk lint, edit pacing, and writes behind the approval gate (review replies, posts, info edits) | business.json, GBP API or manual snapshot | `snapshots/<date>/gbp.json`, findings, drafts, executed writes with log | `references/gbp-playbook.md`, `references/gbp-api-setup.md`, `references/suspension.md` |
| `twwa-reviews` | Review engine that is lawful in Germany by construction: velocity target, request assets, consent rules, §5b notice, reply drafts | business.json, reviews snapshot | assets, drafts, targets | `references/review-law-de.md`, `references/review-engine.md` |
| `twwa-pages` | Page pipeline: choose page type by lead value and by what the teardown shows the winners have, brief, evidence check against the monthly project reports, German draft, gates A to H, hand to ship. Also runs the project-report intake | backlog item or cluster, project reports | brief, draft, gate report, evidence records | `references/page-types.md`, `references/evidence.md`, `references/templates-de.md`, `references/verticals.md`, `references/style-de.md` |
| `twwa-leads` | Cookieless lead attribution: form handler pattern, click events, self-reported source, lead records, qualification rules, synthetic form test | repo | patch on a branch, `leads.jsonl`, probe result | `references/attribution.md`, `references/cro.md` |
| `twwa-ai-visibility` | Prompt panel: generate, run or import, parse, mention rate with Wilson intervals, cited-domain gaps | prompts.json, competitors.json | `snapshots/<date>/ai-panel.json`, gap list for off-site | `references/panel-protocol.md`, `references/ai-levers.md` |
| `twwa-offsite` | Citations (German tiers), membership and partner listings, local press, roundup pitches, NAP consistency. Drafts only | business.json, offsite.json, AI gaps | ranked opportunities, drafts, tracker updates | `references/citations-de.md`, `references/authority.md`, `references/banned.md` |
| `twwa-measure` | Pulls data into snapshots, evaluates actions whose window ended against baseline and control pages, raises alerts | state | snapshots, `measured` events, alerts | `references/windows-and-verdicts.md`, `references/connectors.md` |
| `twwa-weekly` | The scheduled loop: measure, health, evaluate, detect opportunities, at most 5 proposals, one owner request, snapshot | state | weekly digest, proposals, owner request draft | `references/weekly-loop.md`, `references/scheduling.md` |
| `twwa-report` | One-page German monthly report led by qualified Anfragen and the portal-cost comparison | state, month | `reports/<yyyy-mm>.md`, optional HTML in `out/` | `references/report.md` |

### 6.1 Entry skill modes

| Mode | Runs | Stops for a human |
|---|---|---|
| `check <url or .>` | twwa-check | never (read-only) |
| `onboard` | twwa-onboard, then check | when facts are unknown: writes questions, continues with unknowns marked |
| `teardown [query...]` | twwa-serp-teardown for the target queries (or the given ones) | never (read-only; paid observations need a spend cap and `--execute`) |
| `plan` | check if the last one is older than 7 days, teardown if the last one is older than 35 days, then twwa-plan | presents the plan; approval is recorded by the operator |
| `run` | status, then for each approved action twwa-ship; then twwa-measure for due windows | before every merge unless autopilot allows it; always before R3 |
| `run --dry-run` | as `run`, but only prints what each step would do and which gate or approval would block it | never |
| `weekly` | twwa-weekly | never ships; produces proposals and one owner request |
| `report [yyyy-mm]` | twwa-measure (if stale), twwa-report | if no Anfragen number exists: asks, or marks the number as missing |
| `status` | `twwa_state.py status` | never |

With no mode: in a repo with a state folder, `status` then the most useful next mode is proposed; in a repo without one, `onboard`; with a URL, `check`.

## 7. Subagents

| Agent | Tools | Purpose |
|---|---|---|
| `twwa-writer-de` | Read, Grep, Glob, Write | German copy drafts from a brief and the evidence registry. Writes only under `drafts/<action_id>/`. Every factual sentence carries a provenance marker (section 10b) |
| `twwa-quality-reviewer` | Read, Grep, Glob, Bash | Fresh-context reviewer. Receives only paths. Runs the gate and lint scripts, reads the draft cold, reports pass or fail with reasons. Cannot edit, so it cannot quietly fix what it found |

Audit and measurement run as scripts, not as agents.

## 8. Scripts

Rules for every script:

- Python 3.9+, standard library only. No `match` statements. `from __future__ import annotations` at the top.
- `--help` documents purpose, inputs, outputs, exit codes and one example. `--json` prints machine output on stdout; human text goes to stderr when `--json` is set.
- Exit codes: `0` ok or pass, `1` gate failed or findings at or above `--fail-on`, `2` usage or config error, `3` credentials or connector not configured (the message names the exact variable or file and the no-credentials fallback), `4` blocked by safety (STOP, cap, approval, spend, scope), `5` network or remote error.
- Anything that writes to a remote system or costs money is dry-run by default and acts only with `--execute`. Paid calls print the estimated cost first and append to `spend.jsonl`.
- Network scripts accept `--fixture <file>` to run from a saved response, so tests and demos never need the network.
- Fetching uses `twwa_lib.http.fetch`: timeout, size cap, identifying User-Agent, respects robots.txt for crawling, refuses private and loopback addresses unless `--allow-private`.
- No script prints secrets. Tokens come from the environment or from files outside the repo.

### 8.1 Shared library `scripts/twwa_lib/`

| Module | Provides |
|---|---|
| `cli.py` | `base_parser(description)`, exit code constants `EXIT_OK, EXIT_FAIL, EXIT_USAGE, EXIT_NOCREDS, EXIT_BLOCKED, EXIT_REMOTE`, `emit(obj, args)`, `die(code, msg)`, `finding(...)` constructor that validates the section 4.3 schema |
| `state.py` | `find_state(start=".")`, `require_state(args)`, `load_json`, `save_json` (atomic), `append_jsonl`, `read_jsonl`, `load_config(state)` with defaults merged, `stop_requested(state)`, `snapshot_dir(state, date=None)`, `latest_snapshot(state, source, before=None)` |
| `http.py` | `fetch(url, method="GET", headers=None, data=None, timeout=20, max_bytes=3_000_000, allow_private=False) -> Response(status, headers, text, url, history)`, `robots_allows(url, agent)`, `post_json` |
| `htmlx.py` | `parse(html, base_url) -> Page` with `title`, `metas`, `canonical`, `robots`, `lang`, `headings`, `links`, `images`, `jsonld` (parsed objects plus parse errors), `forms`, `text` (main content, with nav, header, footer and script excluded), `text_blocks`, `tel_links`, `wa_links`, `mailto_links` |
| `textde.py` | `sentences(text)`, `tokens(text)`, `shingles(text, n=5)`, `jaccard(a, b)`, `norm_phone(s)`, `norm_address(s)`, `norm_name(s)`, `town_variants(town)`, `fold_umlauts(s)` |
| `stats.py` | `wilson(successes, n, z=1.96)`, `pct_change(a, b)`, `median(xs)`, `diff_in_diff(treat_before, treat_after, ctrl_before, ctrl_after)` |
| `google_auth.py` | `access_token(scopes) -> str`: `GOOGLE_ACCESS_TOKEN`, else `GOOGLE_APPLICATION_CREDENTIALS` (authorized-user refresh token, or service account signed with the `openssl` binary), else `gcloud auth print-access-token` if present; raises `NoCredentials` with setup text |
| `spend.py` | `estimate(provider, endpoint, units)`, `guard(state, usd)` (exit 4 over cap or when `STOP` exists), `record(state, provider, endpoint, units, usd, note)` |

### 8.2 CLI tools

| Script | Subcommands | Purpose |
|---|---|---|
| `twwa_state.py` | `init`, `status`, `doctor`, `scope`, `detect`, `conflicts`, `validate` | State folder lifecycle; repo detection (Astro config, Vercel config, form handler path, scope file, tier guard); config and business validation |
| `twwa_actions.py` | `propose`, `list`, `show`, `approve`, `verify`, `ship`, `measure`, `close`, `due`, `packet`, `stop`, `resume`, `rollback` | Action log, caps, approvals, approval packet (German summary for the owner), kill switch, one-command rollback |
| `site_audit.py` | `dist <dir>`, `live <url>`, `page <url or file>`, `linkgraph`, `redirects` | Technical, on-page, CRO, legal-surface and tracking-surface findings from built output or a polite live crawl (default 25 pages); internal link graph (inlinks, orphans, depth, anchors); redirect integrity (chains, loops, missing anchors, old URLs that 404) |
| `regression_guard.py` | `baseline`, `run`, `verify` | Post-deploy and weekly regression guard (section 12a) |
| `indexnow.py` | `key`, `check`, `submit` | Key file management and URL submission (dry-run by default) |
| `schema_gen.py` | `localbusiness`, `service`, `breadcrumb`, `validate` | JSON-LD from `business.json`; validation of built pages against it |
| `page_gates.py` | `run`, `demand`, `service`, `evidence`, `swap`, `similarity`, `townlist`, `thin`, `sources`, `ramp`, `pilot`, `prune` | Gates A to H (section 10) |
| `legal_lint.py` | `text <file>`, `site <dir or url>`, `impressum <file or url>` | German legal surface lint: review incentives and gating wording, review label and §5b notice, superlatives and guarantee wording, banned off-site tactics, Impressum fields by profession. Always "Hinweis, keine Rechtsberatung" |
| `style_lint_de.py` | `<file...>` | German AI-slop and filler lint with line numbers |
| `evidence.py` | `intake`, `add-project`, `add-fact`, `list`, `for-page`, `coverage`, `recheck` | Monthly project-report intake (text plus photos to a normalised record), evidence registry, which pages each record can support, and Förder or regulation source re-check (fetch, hash, flag change) |
| `gbp.py` | `auth`, `accounts`, `locations`, `get`, `performance`, `reviews`, `posts`, `media`, `notifications`, `snapshot`, `template`, `audit`, `lint`, `pacing`, `reply`, `post`, `update` | Full GBP connector (section 9b): OAuth, reads across all accessible profiles, writes behind the approval gate, manual snapshot fallback, field audit, suspension-risk lint, pacing ledger |
| `reviews.py` | `target`, `assets`, `consent`, `reply-lint` | Velocity target from pack-winner data, request assets (card and notice texts; the QR image is made with the profile's own review link in any QR tool and verified by scanning), consent ledger, reply lint |
| `gsc.py` | `sites`, `query`, `inspect`, `sitemaps`, `snapshot` | Search Console: search analytics, URL inspection, sitemap status |
| `bing_wmt.py` | `sites`, `query`, `pages`, `urlinfo`, `links`, `sitemap`, `submit`, `snapshot` | Bing Webmaster JSON API. Bing is a first-class step because ChatGPT search and Copilot draw on Bing's index: verify the site, submit the sitemap, check money pages are indexed, read backlinks to the own site |
| `psi.py` | `run`, `crux`, `snapshot` | PageSpeed Insights and CrUX (works without a key at low volume) |
| `vercel_analytics.py` | `events`, `pageviews`, `deployments`, `snapshot` | Vercel Web Analytics query API and deployment status |
| `providers.py` | `list`, `status`, `pick`, `cost`, `call`, `refresh` | Provider layer CLI (section 9a): registry, credentials present, best provider per capability, cost preview, a uniform call for each capability, registry refresh procedure |
| `serp_teardown.py` | `queries`, `observe`, `import`, `collect`, `score`, `backlog`, `run`, `summary` | SERP teardown (section 10a) |
| `geogrid.py` | `points`, `run`, `score`, `render` | Grid coordinates, observation through the provider layer, ARP, ATRP, SoLV, SVG rendering |
| `ai_panel.py` | `generate`, `run`, `import`, `score`, `compare`, `gaps` | Prompt panel (section 11) |
| `leads.py` | `add`, `import-events`, `qualify`, `summary`, `outcome`, `probe` | Lead records without personal data; `probe` is the synthetic form test through the honeypot path and refuses any host that is not the configured client domain |
| `offsite.py` | `catalog`, `plan`, `track`, `lint` | Off-site tracker, vertical catalogue, outreach lint |
| `entity_check.py` | `run` | Entity consistency matrix (section 12a): the same facts in `business.json`, site HTML, JSON-LD including `sameAs`, GBP and citations |
| `learning.py` | `record`, `summary`, `suggest` | Agency-level learning log outside client repos (section 12a) |
| `monitor.py` | `crawl`, `ranks`, `ai`, `bots`, `competitors`, `all` | Scheduled monitors (section 12b) |
| `measure.py` | `baseline`, `evaluate`, `alerts` | Action verdicts and alerts (section 12) |
| `opportunities.py` | `detect`, `cannibalisation` | Striking distance, CTR outliers, uncovered clusters, prune candidates, cannibalisation, review velocity gap, seasonal triggers, source changes, missing monthly project report |
| `plan.py` | `rank` | Builds the cycle from the teardown backlog, audit findings and opportunities: P1 first, table-stakes slots, then teardown-driven actions ordered by query value times winnability times gap closed over effort; applies caps and scope |
| `check_report.py` | `client`, `prospect` | Assembles findings into the German check report, the prospect one-pager and the call opener |
| `report.py` | `build`, `owner-request` | Monthly report and the single German owner request |

## 9. Data connectors

| Connector | Auth | Cost | Without credentials |
|---|---|---|---|
| Google Search Console | OAuth user or service account added to the property (`google_auth`) | free; 1,200 QPM per site, URL Inspection 2,000 per day per site | "nicht geprüft"; operator may export CSV from the UI and `gsc.py snapshot --from-csv` |
| Bing Webmaster | `BING_WEBMASTER_API_KEY` | free | skipped with a note; setup = import from GSC |
| Google Business Profile | OAuth user (owner or manager of the profiles) on a Cloud project with approved Basic API Access (verified profile 60+ days, website, about 14 days review; quota 0 QPM until approved, 300 QPM after) | free; 300 QPM, 10 edits per minute per profile | `gbp.py template` produces a snapshot file the operator fills from the profile in a few minutes; public values of competitors come from the provider layer or a browser tool |
| PageSpeed Insights, CrUX | optional `PSI_API_KEY` | free | keyless PSI at low volume; CrUX usually has no data for SMB sites and that is reported as such |
| Vercel Web Analytics | `VERCEL_TOKEN`, project and team id | Hobby: no custom events; Pro: custom events; Plus $10 per team for UTMs | Vercel MCP tools if available; else manual counts |
| Keyword, SERP, maps, backlink and AI-answer data | any provider in the registry whose credentials are present (section 9a) | per provider; shown before every call | free and manual providers: observations imported by hand or collected with the agent's own search or browser tools, labelled "Stichprobe"; surfaces not observed are "nicht geprüft" |
| IndexNow | key file in `public/` | free | not applicable |

Normalised snapshot files (`snapshots/<date>/<source>.json`), each with `{"source", "pulled_at", "range": {"start", "end"}, "origin": "api|csv|manual|fixture", ...}`:

- `gsc.json`: `rows: [{"page", "query", "clicks", "impressions", "ctr", "position", "branded": true|false|null}]`, `pages: [...]` aggregated by page, `inspection: [{"url", "verdict", "coverage_state", "google_canonical", "user_canonical", "last_crawl"}]`.
- `bing.json`: `rows` as above without `branded`.
- `gbp.json`: `profile: {name, primary_category, secondary_categories, address_shown, service_areas, hours, services, attributes, description, website_url, phone, photos_count, latest_photo_date}`, `reviews: {count, rating, last_30, last_90, reply_rate, latest_date}`, `performance: {calls, website_clicks, directions, messages, impressions_maps, impressions_search}`, `competitors: [{name, primary_category, review_count, rating, last_90}]`.
- `psi.json`: `pages: [{"url", "strategy", "performance", "lcp_ms", "cls", "inp_ms", "tbt_ms", "field": {...}|null}]`.
- `vercel.json`: `pageviews: [{"path", "views", "visitors"}]`, `referrers: [{"host", "views"}]`, `events: [{"name", "count", "props": {...}}]`.
- `gbp.json` additionally, in API mode: `locations: [...]` when a snapshot covers several profiles, `posts: [...]`, `media: {count, latest}`, `notifications: {topic, types}`.
- `grid.json`: `center`, `spacing_km`, `size`, `keywords: [{"keyword", "points": [{"lat","lng","rank"}], "arp", "atrp", "solv", "competitors": [{"name","solv"}]}]`.
- `ai-panel.json`: section 11.
- `site.json`: findings from `site_audit.py` plus `pages: [{"url","title","h1","canonical","indexable","words"}]`.
- `leads.json`: monthly aggregates from `leads.jsonl`.

## 9a. Provider layer (keyword, SERP, maps, backlink and AI-answer data)

Vendors change fast, so no script names a vendor. `data/providers.json` is a registry; `scripts/twwa_lib/providers/` holds one adapter per implemented provider; `providers.py` is the CLI.

Capabilities: `serp_organic`, `serp_maps`, `keyword_volume`, `autocomplete`, `backlinks`, `ai_answers`, `business_reviews`, `domain_age`.

Registry entry:

```json
{"id": "dataforseo", "name": "DataForSEO", "homepage": "https://dataforseo.com", "billing": "payg",
 "auth": {"env": ["DATAFORSEO_LOGIN", "DATAFORSEO_PASSWORD"]},
 "capabilities": {"serp_maps": {"cost_usd": 0.0006, "unit": "request", "freshness": "live", "localised": true, "ui_parity": null}},
 "adapter": "dataforseo", "status": "implemented", "live_verified_on": null,
 "verified_on": "2026-11-16", "source_url": "https://dataforseo.com/pricing"}
```

`status` is `implemented` (adapter plus fixture test exist) or `registry_only` (known, no adapter). `live_verified_on` is set by the first successful real call; until then the adapter is built from documentation and says so.

Entries at release: DataForSEO, SE Ranking, Ahrefs, Semrush, OpenAI, Gemini and Perplexity (direct `ai_answers`, `ui_parity: false`), and free entries: `wayback` (`domain_age`), `bing_wmt` (own-site `backlinks`, related keywords), `gsc` (own-site demand), `agent_search` (organic results the agent collected with its own search tool: `localised: false`, labelled "Stichprobe"), `manual` (any capability from a file the operator filled).

Interface (`twwa_lib.providers`):

```python
status(state=None) -> list[dict]                      # every entry with creds_present, capabilities, cost
pick(capability, state=None, engine=None) -> Provider  # raises NoProvider(capability, how_to_enable)
call(capability, params, state=None, execute=False, fixture=None) -> dict   # normalised result, see below
```

Selection: providers with credentials present and `status: implemented` for the capability; `config.providers.prefer[capability]` wins; otherwise localised and UI-parity first, then freshness, then cost. `call` is dry-run unless `execute=True`, passes `twwa_lib.spend.guard`, and records to `spend.jsonl`.

Normalised results (every result also carries `provider`, `origin`, `observed_at`, `cost_usd`):

- `serp_organic` (params `query`, `location: {town, lat, lng, country, language}`, `depth`): `{"localised": bool, "results": [{"rank", "url", "domain", "title", "snippet"}], "local_pack": [{"rank", "name", "place_id", "rating", "reviews", "category", "address"}], "ai_overview": {"present": bool, "cited_domains": []} | null}`
- `serp_maps` (params `query`, `lat`, `lng`, `depth`): `{"results": [{"rank", "name", "place_id", "rating", "reviews", "category", "additional_categories", "address", "lat", "lng", "website", "phone"}]}`
- `keyword_volume` (params `keywords`, `country`): `{"items": [{"keyword", "volume", "volume_range", "cpc"}]}`
- `autocomplete` (params `query`, `country`, `language`): `{"suggestions": []}`
- `backlinks` (params `target`): `{"referring_domains", "backlinks", "authority", "authority_scale", "top_referring": [{"domain"}]}`
- `ai_answers` (params `prompt`, `engine`, `location`): `{"engine", "answer_text", "citations": [{"url", "domain"}], "ui_parity": bool}`
- `business_reviews` (params `place_id` or `name` plus `address`): `{"count", "rating", "recent": [{"date", "rating", "has_text"}]}`
- `domain_age` (params `domain`): `{"first_seen": "yyyy-mm-dd" | null}`

`providers.py refresh` lists entries whose `verified_on` is older than 90 days and prints, per entry, what to re-check (pricing page, API documentation, capability changes) and a scouting brief per capability ("is there a newer or better provider for German local data?"). The agent researches with its web tools and applies dated updates with `providers.py refresh --apply <file>`. New providers enter as `registry_only` with a source URL; they become `implemented` only with an adapter and a fixture test.

## 9b. Google Business Profile connector (`gbp.py`)

Covers TWWA's own profile and every client profile where the authenticated Google user is owner or manager.

- **Auth**: `gbp.py auth --client-secrets <file>` runs the OAuth installed-app flow on a loopback port with scope `https://www.googleapis.com/auth/business.manage`, and stores the refresh token outside every repo (`~/.config/twwa-growth/google-token.json`, mode 600). `GOOGLE_ACCESS_TOKEN` is honoured for one-off runs.
- **Reads**: accounts and location groups (Account Management), locations with full read mask, attributes and categories (Business Information), daily metrics and monthly search keywords (Performance), reviews, local posts and media (v4.9), notification settings (Notifications). `gbp.py snapshot` writes `snapshots/<date>/gbp.json`; `--all` iterates every accessible location and matches each to a client by `business.json.gbp.location`.
- **Writes, behind the approval gate**: `reply` (review reply), `post` (local post create, update, delete), `update` (info edits through `locations.patch` with an explicit update mask: hours, special hours, services, description, attributes, additional categories, website link; primary category and primary phone as identity-level edits). Every write requires `--action <id>`, calls `twwa_actions.py verify`, is dry-run unless `--execute`, respects 10 edits per minute per profile and the 48-hour identity pacing ledger, logs request and response, and re-reads the profile afterwards to confirm the change. Name, address and pin are refused by the script in every mode.
- **Access**: `references/gbp-api-setup.md` documents the Basic API Access application step by step (Cloud project, prerequisites, form, how to see approval as quota 0 versus 300 QPM, enabling each API, OAuth consent screen, adding TWWA as manager through an organisation account and location groups).
- **Without credentials**: `gbp.py template` writes a snapshot file the operator fills from the profile; `audit` and `lint` work on it identically; drafts are produced for manual entry.

## 10. Quality gates for pages (`page_gates.py`)

All thresholds are internal heuristics from dossier 06 (Google publishes no numeric threshold). They live in `config.thresholds` and may be changed only with a recorded reason.

| Gate | Check | Pass rule |
|---|---|---|
| A demand | cluster in `keywords.json` against GSC snapshot, keyword data, project evidence | GSC impressions in 90 days at least 10 for towns under 20,000 inhabitants, else 30; or keyword volume above 0; or at least 2 jobs in the town in 24 months and the town is in the service area |
| B service relationship | town in `business.json.service_area` with `owner_confirmed` date and `drive_minutes` at most 120 | all true |
| C local evidence | evidence items attached to the page from `evidence/` | at least 3 distinct items, at least 1 first-party (own project in that town, review from that town with consent, named responsible person, real travel time or fee) |
| D distinctness: swap | replace town and Ortsteile with the nearest sibling town; rule-based detection of sentences that become false (they mention town-bound entities from the evidence registry: project ids, street or district names, local authority, distances, local programme names) | at least 25% of non-boilerplate sentences are town-bound; boilerplate (blocks marked `data-twwa-shared`) under 60% of body words |
| D distinctness: similarity | 5-word shingle Jaccard against every sibling page | at most 0.6 |
| D town list | plain-text runs of town names | no list of more than 8 towns |
| E usefulness | page answers what, where, price range, how fast, proof, contact; CTA present; action possible on the page | all present; under 250 non-boilerplate words is flagged thin |
| F facts and law | every factual claim maps to `facts.json` or a project; `legal_lint` clean | no unsourced claim, no blocked wording |
| G ramp | new indexable pages against the action log | per week at most max(2, 10% of indexed pages); at most 8 per month for sites under 50 pages; new template: pilot of 3 to 5 pages, continue only if at least 60% indexed in 28 days and at least 50% with impressions in 56 days |
| H prune | published pages older than 90 days | 0 clicks and under 20 impressions and no leads: propose consolidation (unless marked seasonal); template with more than 40% "crawled, not indexed": stop the template |

`page_gates.py run --page <file> --action <id>` runs A to G and exits 1 on the first failure with the gate, the measured value, the threshold and the German backlog reason ("wartet auf erstes Projekt mit Fotos in Nachbarstadt"). A failing page cannot reach the approval queue; the failure becomes an owner data request instead of a dead end. The swap test's rule-based result is the gate; the quality reviewer agent adds a judgement on top but cannot turn a script failure into a pass.

Other gates in the ship path: `site_audit.py dist --fail-on P1`, `schema_gen.py validate`, `legal_lint.py`, `style_lint_de.py` (warnings do not block; a reviewer must acknowledge them), `site_audit.py redirects`, the tier guard, and `twwa_actions.py verify`.

## 10a. SERP teardown (`serp_teardown.py`)

A method the plugin runs at use time on the real client, in its own trade and town. Nothing about any real business or SERP is stored in the plugin; findings go to `.twwa-growth/teardowns/`. All numbers below are starting values derived from the dossier (03 §1 and §3, 04 §2, 06, 11 §3), stored in `config.thresholds.teardown`, and marked tunable once `learning.py` has enough observations.

**Step 1, target queries (`queries`).** Built from `business.json` services and service area, in five classes:

| class | pattern | main surface |
|---|---|---|
| `service_town` | "{Leistung} {Stadt}", "{Gewerk} {Stadt}", regional synonyms from `voice.regional_terms` | pack and organic |
| `near_me` | "{Gewerk} in der Nähe" | pack only, observed at the client's address and the town centre |
| `cost` | "{Leistung} Kosten", "was kostet {Leistung}" | organic and AI overview |
| `need` | "{Gewerk} für {Bedarf} {Stadt}" from each service's `needs` | organic and AI |
| `best` | "bester {Gewerk} {Stadt}", "{Gewerk} {Stadt} Empfehlung" | AI answers and organic |

Value of a query = service priority weight × margin weight × demand, where demand is provider volume, else GSC impressions, else unknown (counted as 1 and flagged). The set is capped at `caps.target_queries` (15), with at least one `service_town` query per priority-1 service and the home town before other towns. Stored in `keywords.json` with `target: true`.

**Step 2, observe (`observe`, `import`).** Per query, through the provider layer: organic top 10 localised to the town; maps top 20 at the town centre (and at the client's address when it differs); AI answers from the latest panel or 1 to 3 runs per available engine. Fallbacks, in order: `import` of a manual observation (the reference file gives the operator a 5-minute procedure in a clean browser with the location set), then `agent_search` for organic only, flagged `localised: false`. Maps and AI surfaces are never guessed: without an observation they are `not_checked`.

**Step 3, winners.** Top 3 per surface. Each organic winner gets a `domain_type`: `business`, `directory` (branch books, review portals), `lead_portal`, `publisher`, `association`, `client`. If at least 2 of the top 3 are not `business`, the SERP class is `portal_dominated`.

**Step 4, collect (`collect`).** Polite fetches that respect robots.txt, at most `caps.competitor_pages` (8) pages per winner domain. Review data is stored as counts and dates only.

| Surface | Data points per winner |
|---|---|
| organic | page type (home, service, service and town, cost, case study, listing, article); title and H1 contain service and town; main-content word count; sub-questions covered (price, process, duration, area, proof, FAQ, contact); evidence items (captioned own photos, numbers with units, named people, review excerpts, prices, dated facts); internal links pointing to the page from the sampled pages and from navigation; schema types; NAP on page; call to action in the first screen; lab performance if a key or tool is available; referring domains and authority (`backlinks`); first seen (`domain_age`); HTTPS |
| pack | primary and additional categories; rating; review count; reviews in the last 90 days (`business_reviews`); distance from the town centre in km; address inside the searched town; trade or town in the business name (recorded as a risk signal, never copied); landing-page title and H1 match; hours listed |
| AI | businesses named per engine with mention rate; cited domains with domain type; whether the client is named; whether the client's domain is cited |

**Step 5, gap score (`score`).** Reference = median of the `business` winners in the top 3 (for portal-dominated SERPs: the best-ranked business plus the portals as listing targets). Each factor yields a gap between 0 (client at or above reference) and 1; factors that could not be checked are excluded and listed. Composite gap = weighted mean over checked factors; confidence = share of weight checked.

| Organic factor | Weight | | Pack factor | Weight | | AI factor | Weight |
|---|---|---|---|---|---|---|---|
| dedicated page for the service | 20 | | primary category match | 20 | | present on the cited data-layer domains | 30 |
| geographic relevance with local evidence | 15 | | proximity and address in town | 20 | | rating at least 4.3 and review volume | 20 |
| referring domains and authority | 15 | | review count | 12 | | dedicated service page with explicit facts | 20 |
| title and H1 match | 10 | | review recency and velocity | 10 | | third-party mentions on cited domains | 20 |
| sub-question coverage | 10 | | rating | 8 | | indexed in Bing | 10 |
| evidence depth | 10 | | profile completeness | 8 | | | |
| internal links to the page | 8 | | landing-page title and H1 | 8 | | | |
| domain age and brand | 5 | | links to the landing page | 8 | | | |
| page experience | 4 | | NAP site equals GBP | 6 | | | |
| schema and entity clarity | 3 | | | | | | |

Weights follow the Whitespark 2026 factor order (dossier 03 §1, 04 §2); they are heuristics, not Google numbers.

**Step 6, winnability.**

| Surface | Class | Rule (starting values) |
|---|---|---|
| organic | `now` | client already at position 4 to 15 and composite gap under 0.35 |
| organic | `with_work` | composite gap 0.35 to 0.65, or not ranking but at least one business winner has referring domains at most 3 times the client's or at most 20 absolute |
| organic | `long_term` | every business winner has more than 10 times the client's referring domains and more than 50 absolute; or portal-dominated: get listed and strong on those portals, target the first business slot |
| pack | `now` | client inside the town or within `pack_max_km`, category mismatch or incomplete profile is the main gap |
| pack | `with_work` | review count under 50% of the winner median: months needed = (median minus client) divided by a realistic monthly velocity |
| pack | `out_of_radius` | no address in the searched town, all top 3 have one, and distance above `pack_max_km` (15 km, or 5 km for towns of 100,000 or more): the pack is not the target for this query; target organic, and note ads or LSA under `paid_ads.mention_only` |
| AI | `with_work` | rating at least 4.3 and missing on some cited domains |
| AI | `blocked_by_basics` | rating under 4.3, or fewer than 20 reviews, or no dedicated page: fix those first |

**Step 7, gap to action to expected time (`backlog`).**

| Largest gap | Action type | First signal | Evaluate after |
|---|---|---|---|
| no dedicated page | `new_page` through gates A to H; on a one-page tier: strengthen the landing-page section and write a scope proposal | 2 to 8 weeks | 28 to 90 days |
| title or H1 mismatch | `onpage_rewrite` | after recrawl | 14 to 28 days |
| sub-questions, evidence depth | `page_refresh` plus a project-report request to the owner | 2 to 4 weeks | 28 days |
| internal links, schema, speed | `tech_fix` | 1 to 3 weeks | 7 to 28 days |
| referring domains, third-party mentions | `citation`, `offsite_mention` (memberships, partner finders, local press) | weeks to months | 60 to 180 days |
| category, profile completeness | `gbp_identity_edit`, `gbp_content_edit` | 2 to 14 days | 14 days |
| review count, recency | `review_engine` | weeks | 30 to 90 days |
| NAP mismatch | `tech_fix` plus `citation` corrections | weeks | 60 to 120 days |
| not on AI-cited domains | `citation`, `offsite_mention` | weeks | 60 to 120 days, at least 4 panel measurements |
| facts not explicit on the page | `ai_refinement` | 2 to 4 weeks | 28 days |
| not indexed in Bing | IndexNow and Bing sitemap as `tech_fix` | days | 7 days |

Backlog priority = query value × winnability factor (`now` 1.0, `with_work` 0.6, `long_term` 0.25, `out_of_radius` and `blocked_by_basics` 0 for that surface) × share of the composite gap the action closes ÷ effort (S 1, M 2, L 4). One backlog item per action, listing every query it serves.

Teardown file: `{"query", "class", "town", "value", "observed_at", "surfaces": {"organic": {"origin", "localised", "serp_class", "client_rank", "winners": [{"rank", "url", "domain", "domain_type", "data": {}, "not_checked": []}], "gap": {"factors": [{"id", "weight", "client", "reference", "gap", "status"}], "composite", "confidence"}, "winnability": {"class", "reasons": []}}, "pack": {}, "ai": {}}, "backlog_items": []}`. `summary.json` aggregates across queries. A teardown is valid for planning for 35 days.

## 10b. Claim provenance and copy quality

- Drafts are Markdown under `drafts/<action_id>/`. A sentence that states a fact carries a marker at its end: `[[p:<project-id>]]`, `[[f:<fact-id>]]` or `[[b:<business.json path>]]`. Markers are stripped when the page is built.
- `evidence.py provenance <draft>` finds factual sentences by rule (digits, currency, units, percentages, years, durations, certifications and titles, place names beyond the page's own town, programme and authority names, comparatives and superlatives) and fails when one has no marker, when a marker does not resolve to a record, or when a number in the sentence does not appear in the referenced record. Facts with `source_url` must have `verified_on` within the freshness window (90 days; 31 days for subsidy claims).
- `style_lint_de.py --gate` fails on stock phrases and filler typical of machine-written German, on empty superlatives, and above a density threshold; it prints line numbers. Its rules are restated from the dossier (05 §3) and the inventory, in our words.
- Both run inside Gate F. A page reaches the approval queue only with full provenance.

## 11. AI prompt panel (`ai_panel.py`)

Protocol from dossier 04 §3:

- `generate`: builds `prompts.json` from business, keywords and service area. Composition 40% recommendation ("bester", "empfehlenswert"), 25% need-specific, 20% cost and process with locality, 15% brand. German, natural phrasing, location set per prompt.
- `run`: asks the provider layer for capability `ai_answers` per engine (`chatgpt`, `gemini`, `ai_mode`, `perplexity`); UI-parity providers are preferred over direct model APIs, and the result records which was used. Location is always set explicitly; a direct OpenAI call refuses to run without `user_location` because the API default is the United States. Default 3 runs per prompt per engine. Dry-run prints the call count and cost.
- `import`: scores answers collected by hand or with a browser tool from a simple JSON or folder of text files. Output is labelled `origin: "manual"` and reports show it as "Stichprobe".
- `score`: fuzzy business-name match against client and competitor names; mention rate per engine with Wilson 95% interval; domain citation rate separately from name mentions; cited domains ranked; raw answers stored.
- `compare`: movement is claimed only when intervals do not overlap or at least 4 consecutive measurements trend the same way. Otherwise "keine belastbare Veränderung".
- `gaps`: cited domains where competitors appear and the client does not, handed to `twwa-offsite`.

Never reported: an "AI ranking position".

## 12. Measurement and verdicts (`measure.py`)

- Baseline at `shipped`: the last full window before the ship date for affected pages and queries, plus the control set (untouched pages of the same site with similar baseline impressions; when the site has a single page, control is the non-targeted query set and the verdict confidence is capped at "low").
- At window end: difference in differences on clicks and impressions, position change on targeted queries, leads on affected pages, grid and GBP metrics for local actions.
- GSC handling: windows end 3 days before today; rows under 50 impressions are not used for a verdict; host variants are merged; one primary metric per action, the rest are diagnostics.
- Verdicts: `win`, `neutral`, `loss` (revert candidate), `inconclusive`. Small-data rule: if the affected pages have fewer than 100 impressions in the window, or the control moved by more than the treatment, the verdict is `inconclusive` and the German text says "noch zu früh" or "zu wenig Daten" with the numbers.
- Alerts (dossier 07 §7): form pipeline failure (P1), noindex or robots block on a money page (P1), production deploy failed (P1), GBP suspended or disabled (P1), money query average position worse by 3 or more against the 28-day baseline, "crawled, not indexed" share above 20%, search or answer bot blocked.

## 12a. Guards and cross-cutting checks

- **Regression guard (`regression_guard.py`).** `baseline` records, per URL in the sitemap and for every money page: status, final URL, canonical, indexability (meta and header), title, H1, schema types and a hash of the NAP fields, presence of the primary call to action and phone link, sitemap membership, plus every redirect in `vercel.json` and its target. `run` compares the live site with the baseline and adds, when available: index status from the latest GSC inspection, Bing index status, lab performance against the budget (performance at least 90, CLS at most 0.05, LCP at most 2.5 s), and the form pipeline through `leads.py probe`. A regression on a money page is P1 and exits 1. `verify --action <id>` is the post-deploy form of the same check and is the last step of every ship. `run` is step 2 of the weekly loop.
- **Internal link graph (`site_audit.py linkgraph`).** Inlinks per page, orphans, click depth from the home page, anchor texts; findings for money pages with fewer than 3 internal inlinks and for links that pass through a redirect.
- **Cannibalisation (`opportunities.py cannibalisation`).** Two own pages that each take at least 20% of a query's impressions over 28 days with average positions within 10 of each other, or two pages with the same normalised title or H1 target. Output: which page should own the query and whether to consolidate, differentiate or link.
- **Entity consistency (`entity_check.py`).** A matrix of field (name, street, postcode, town, phone, URL, hours, primary category) by source (`business.json`, site HTML, JSON-LD, GBP snapshot, each known listing URL): match, mismatch with the differing value, missing, or not checked. Every confirmed profile URL must appear in `sameAs`; no `sameAs` entry may point to a dead URL.
- **Bing and IndexNow.** Onboarding verifies the site in Bing Webmaster, submits the sitemap and installs the IndexNow key file. Every ship pings IndexNow for changed URLs after live verification. The weekly loop checks that money pages are in Bing's index.
- **Kill switch.** `twwa_actions.py stop --reason "..."` creates `STOP`; every script that writes, spends or ships checks it first and exits 4. `resume` removes it and logs who and why.
- **One-command rollback.** `twwa_actions.py rollback <action_id>` creates `twwa/rollback-<action_id>` from the default branch, reverts the action's commits, runs the gates, and prints the merge command; with `--merge` it merges locally when the autopilot level allows it. Pushing is always a separate, explicit step. After the deploy, `regression_guard.py verify` runs and a `reverted` event is logged with the reason.
- **Learning log (`learning.py`).** Lives outside client repos (`~/.twwa-growth/learning.jsonl`, or `TWWA_AGENCY_DIR`). On every `measured` event it records client alias, vertical, trade, town-size bucket, action type, gap factor addressed, window, verdict, effect size against control and confidence. `summary` shows win rate and median effect by action type and vertical once there are at least 5 observations. `suggest` proposes changes to windows and teardown thresholds; nothing is applied automatically.

## 12b. Scheduled monitors (`monitor.py`)

What agencies run on their own bots and servers, reduced to the legitimate parts and run as scheduled scripts: a GitHub Actions workflow, a Claude Code routine or launchd. No own server. Each monitor writes a dated snapshot, compares with the previous one, and emits findings and alerts for the weekly loop.

| Monitor | What it does | Data path | Without the data |
|---|---|---|---|
| `crawl` | Weekly self-crawl of the client site: status codes, canonicals, titles, broken internal and external links, orphan pages, redirect hops. Reuses `site_audit.py live`, `linkgraph` and `regression_guard.py run` | plain HTTP | always available |
| `ranks` | Positions of the target queries in organic results and the local grid | provider layer (`serp_organic`, `serp_maps`), GSC average position as a free cross-check | GSC only; pack and grid "nicht geprüft" |
| `ai` | Runs the prompt panel on schedule and appends the measurement | provider layer (`ai_answers`) | skipped; last manual sample is kept and labelled |
| `bots` | Crawl and bot-log monitoring: hits per URL by Googlebot, Bingbot, OAI-SearchBot, ChatGPT-User, GPTBot, PerplexityBot, ClaudeBot and Claude-SearchBot; 4xx and 5xx served to bots; time to first crawl of each new page (first verified bot hit after the `shipped` event) | Vercel log drain export or log file in NDJSON; bots are identified by user agent and marked `verified` only when the address matches the operator's published ranges or reverse DNS | "nicht geprüft"; GSC and Bing crawl data where readable |
| `competitors` | Change detection on the winners recorded by the teardown: new URLs in their sitemaps, title and H1 changes on the winning pages, profile changes (category, review count, rating) | polite fetches of public pages, provider layer for profile data | page changes only |

The bot and human split: reports count human traffic only. Vercel Web Analytics already excludes known bots; any figure derived from logs passes the same user-agent classification first, and bot hits are reported separately as crawl activity.

Templates in `templates/monitors/`: `github-actions-weekly.yml` (runs the scripts with repository secrets, uploads snapshots as artifacts, opens an issue for a P1 alert, never deploys), `claude-routine.md` (prompt and settings for a scheduled `/twwa-weekly`), `launchd.plist` (local weekly run with a budget cap). Monitors never merge, never write to GBP and never spend above the cap.

## 13. Safety rules (linted, not just stated)

Never produced or assisted by the plugin, and rejected by `legal_lint.py` or `offsite.py lint` when found in drafts:

- review incentives of any kind (voucher, discount, raffle, gift), review gating or selective solicitation, fake or commissioned reviews, staff reviews;
- electronic review requests without recorded consent, reminders, star steering ("5 Sterne");
- link exchanges, paid links without `rel="sponsored"` or `rel="nofollow"`, automated link creation, keyword-anchor footer links across client sites, private blog networks;
- keyword or town stuffing in the GBP name, fake or virtual addresses, one profile per town;
- pages produced to a count, town lists, town-swap pages, self-published "best of" lists naming the client, pages or files made mainly to steer AI answers;
- unverifiable superlatives and guarantees ("bester", "Nr. 1", "garantiert");
- changes to Impressum, Datenschutz or consent texts without human legal sign-off;
- sending any e-mail or message, posting to any profile, or submitting any form on a site TWWA does not control;
- writing scope exception lines;
- click bots, CTR manipulation, traffic bots or any other fake engagement; private blog networks; scraping Google at scale against its terms. Rank, map and AI observations go through APIs and data providers, and a manual observation is a person looking at a result page.

Operational guards: `STOP` file; spend cap and ledger; step, page and proposal caps; GBP pacing; idempotent keys; live verification after every production change ("the deploy log is not evidence"); fresh-context reviewer for content; no secrets in the repo.

## 14. Optional integrations

The plugin works alone. Where an installed skill, plugin or MCP tool does a step better, the skill text says "if available, use X for Y; otherwise Z". The mapping is maintained in `references/integrations.md` and derived from `docs/inventory/capability-map.md`. Third-party text is not copied; rules are restated and sources credited in the README.

## 15. Build components

| ID | Component | Owns |
|---|---|---|
| B1 | Core | `scripts/twwa_lib/` (all modules except `providers/`), `twwa_state.py`, `twwa_actions.py`, `site_audit.py`, `regression_guard.py`, `schema_gen.py`, `indexnow.py`, `page_gates.py`, `evidence.py`, `legal_lint.py`, `style_lint_de.py`, `templates/state/`, `templates/site/` (SEO head, schema, robots, sitemap), `data/schema-types.json`, manifests, fixture Astro site and state under `tests/fixtures/musterbetrieb/`, tests, `skills/twwa-tech/`, `skills/twwa-ship/`, `references/state-and-config.md`, `references/safety.md`, `references/gates.md`, `references/legal-de.md` |
| B2 | Data | `scripts/twwa_lib/providers/`, `providers.py`, `data/providers.json`, `geogrid.py`, `gsc.py`, `bing_wmt.py`, `psi.py`, `vercel_analytics.py`, `gbp.py`, `skills/twwa-gbp/`, `references/connectors.md` |
| B3 | Teardown and planning | `serp_teardown.py`, `ai_panel.py`, `opportunities.py`, `plan.py`, `data/ctr-curve.json`, `data/seasonality.json`, `skills/twwa-serp-teardown/`, `skills/twwa-plan/`, `skills/twwa-ai-visibility/` |
| B5 | Measure, monitors, leads, report | `measure.py`, `monitor.py`, `learning.py`, `leads.py`, `report.py`, `templates/site/api/`, `templates/monitors/`, report and owner-request templates, `skills/twwa-measure/`, `skills/twwa-weekly/`, `skills/twwa-report/`, `skills/twwa-leads/` |
| B4 | Content, local, off-site, entry | `reviews.py`, `offsite.py`, `entity_check.py`, `check_report.py`, `data/citations-de.json`, `templates/de/` (page types, project-report intake, review assets, outreach), `skills/twwa-growth/`, `skills/twwa-check/`, `skills/twwa-onboard/`, `skills/twwa-pages/`, `skills/twwa-reviews/`, `skills/twwa-offsite/`, `agents/`, `references/integrations.md` |

Order: B1 first; B2, B3, B4 and B5 in parallel against the interfaces in this file; then one cold review.
