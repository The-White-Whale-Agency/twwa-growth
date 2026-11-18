# State folder and configuration

The per-client state lives in `.twwa-growth/` in the client repo root (override with `--state` or `TWWA_STATE_DIR`). It holds no personal data and no secrets. Create it with `twwa_state.py init --repo .`; init copies `templates/state/` and never overwrites an existing file.

## Layout

| Path | Content | Written by |
|---|---|---|
| `config.json` | decisions, caps, thresholds, connectors (below) | init, operator |
| `business.json` | canonical facts: the single source for NAP, schema and listings; `null` = unknown, never used in copy | onboarding, operator |
| `keywords.json` | `clusters: [{id, queries[], intent, priority, target_page, town, service, volume?, target?}]` | teardown, plan |
| `prompts.json`, `competitors.json`, `backlog.json`, `offsite.json`, `reviews.json` | lists with `schema_version` | their skills |
| `evidence/inbox/` | raw monthly project reports (text plus photo file names) | operator |
| `evidence/projects/<yyyy-mm>-<slug>.json` | normalised Projekt-Kurzbericht | `evidence.py intake` |
| `evidence/facts.json` | `facts: [{id, claim, value, unit, kind, town, pages, entities, source_url, source_date, verified_on, confirmed_by, subsidy}]` | `evidence.py add-fact` |
| `teardowns/<date>/` | SERP teardown per query plus `summary.json` | `serp_teardown.py` |
| `actions.jsonl` | append-only events; current state = fold of events | `twwa_actions.py` |
| `approvals/<id>.json` | `{action_id, records: [{role, by, at, channel, evidence, content_hash, git_head, preview_url, artifacts}]}` | `twwa_actions.py approve` |
| `drafts/<id>/` | Markdown drafts with provenance markers | writer agent |
| `snapshots/<yyyy-mm-dd>/<source>.json` | normalised data pulls: `gsc`, `bing`, `gbp`, `psi`, `vercel`, `site`, `regression-baseline`, `regression`, `form-probe`, `keyword-volume`, `grid`, `ai-panel`, `leads` | each connector |
| `reports/`, `proposals/` | German Markdown for the owner | report, propose `--as-proposal` |
| `leads.jsonl`, `spend.jsonl` | lead records without personal data; paid-API ledger | leads, spend |
| `out/` | exports and approval packets; git-ignored; the only place for HTML | packet, report |
| `STOP` | kill switch: nothing ships, nothing spends | `twwa_actions.py stop` |

Tier-guard compatibility (`twwa_state.py doctor`, exit 1 on a violation): no `.html` outside `out/`; no folder named `pages`, `app` or `routes`; no line that begins with the tier guard's approval marker; `out/` git-ignored.

## Library entry points (`scripts/twwa_lib`)

- `state.find_state(start)`, `require_state(args)`, `load_config(state)` (defaults merged), `load_json`, `save_json` (atomic), `append_jsonl`, `read_jsonl`, `stop_requested`, `snapshot_dir(state, date)`, `latest_snapshot(state, source, before)` returns the newest snapshot path or `None`; `load_latest_snapshot` returns its parsed content with `_date` and `_path`.
- `state.today()` honours `TWWA_TODAY=yyyy-mm-dd` (tests and replays).
- `cli.finding(...)` validates the finding schema: `id` dotted lowercase, `area`, `severity` P1 to P3 or info, `status` verified (evidence required), hypothesis or not_checked, `priority_group` 1 to 8.
- `http.fetch` refuses private addresses unless `allow_private`; `http.use_fixture(path)` answers from a file.

## `config.json` keys

| Key | Default | Meaning |
|---|---|---|
| `tier`, `scope_file`, `tier_guard` | detected | website tier; unknown is treated as premium |
| `site.url`, `site.default_branch`, `site.money_pages`, `site.preview_hosts`, `site.dist_dir`, `site.build_command` | from detection, `["/"]` | audit and ship targets |
| `exclusivity.offered` | `false` | `conflicts` only warns |
| `guarantee.mode` | `"none"` | guarantee wording is linted out |
| `approval.owner_channel`, `approval.twwa_channel` | `"message"`, `"branch_review"` | how approvals are given |
| `call_tracking.mode` | `"none"` | `"static"` possible; no DNI |
| `vercel.custom_events`, `vercel.analytics_plus` | `false` | Hobby-compatible lead counting |
| `gbp.mode`, `gbp.writes`, `gbp.pacing_hours` | `"auto"`, `"approved"`, `48` | GBP connector |
| `providers.prefer`, `providers.disabled` | `{}`, `[]` | provider layer |
| `spend.monthly_cap_usd` | `0` | paid calls off until set |
| `legal.signoff`, `legal.review_request_electronic`, `legal.referrer_capture` | `false` | legal switches |
| `owner_input.monthly_project_report` | `true` | weekly loop flags a missing report |
| `outreach.send_mode` | `"draft_only"` | nothing is sent |
| `ai_bots.training` | `"no_change"` | training-bot rules untouched |
| `paid_ads.mode` | `"mention_only"` | no campaign work |
| `data.pii` | `"never"` | no personal data in state |
| `autopilot.level` | `"off"` | `technical`, `approved` |
| `language.client`, `language.internal` | `"de"`, `"auto"` | |
| `caps.*` | proposals 5, table-stakes slots 2, target queries 15, AI prompts 40, runs 3, grid 7, grid keywords 10, crawl pages 25, competitor pages 8, page cooldown 14 days | |
| `thresholds.gates.*` | section 10 numbers | page gates |
| `thresholds.teardown.*` | section 10a numbers and weights | teardown |
| `thresholds.regression.*` | performance 90, CLS 0.05, LCP 2500 ms | regression guard |
| `thresholds.measure.*`, `thresholds.alerts.*` | GSC lag 3 days, 50 and 100 impressions; position drop 3, crawled-not-indexed 20% | measurement |
| `thresholds.overrides` | `[]` | every changed threshold with `{key, from, to, reason, by, on}` |
| `connectors.*` | GSC property, Bing site, GBP location, PSI strategy, Vercel ids, IndexNow key file and endpoint | |

There are no pricing or packaging keys; `twwa_state.py validate` rejects them.
