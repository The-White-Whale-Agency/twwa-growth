# 04 · Tooling layer: MCP servers, tool plugins, process skills, scheduling, plugin authoring

Inventory date 2026-11-16. Claude Code 2.1.325 (`~/.local/bin/claude --version`).

## 1. Scope

| Read | Version / licence |
|---|---|
| `~/.claude.json` `mcpServers`: only key names and auth type were read, no values | n/a |
| Vercel plugin `~/.claude/plugins/cache/claude-plugins-official/vercel/0.50.0` (skills, `.mcp.json`, `hooks/`, `CLAUDE.md`, bundled Agent SDK 0.2.70 `sdk.d.ts`) | 0.50.0, Apache-2.0 |
| chrome-devtools-mcp `…/chrome-devtools-plugins/chrome-devtools-mcp/1.12.0` (README, `docs/tool-reference.md`, skills) | 1.12.0 |
| exa `…/claude-plugins-official/exa/3.4.1` | 3.4.1 |
| superpowers `…/superpowers/7.0.2/skills` | 7.0.2, MIT |
| mattpocock-skills `…/mattpocock-skills/1.3.1` | 1.3.1, MIT |
| gstack skills in `~/.claude/skills/*` (symlinks into `~/.claude/skills/gstack`) | gstack, SKILL.md generated from templates |
| ai-builder-club `…/ai-builder-club/skills/0.1.0`; creative plugins (plugin.json descriptions only) | various |
| Claude Code changelog `~/.claude/cache/changelog.md` (10,690 lines); `claude plugin --help`, `validate --help`, `details --help`, `init --help`, `marketplace --help`, `claude --help`; `claude plugin details superpowers@claude-plugins-official` | 2.1.325 |
| Vercel MCP tool schemas for `request_promote`, `request_rollback`, `create_deployment`, `add_route`, `stage_redirects`, `aggregate_events`, `web_fetch_vercel_url`, `list_event_types` (schemas loaded, nothing called) | live |

Skipped: the small-business plugin (Gmail, Calendar, Drive) and the claude.ai connectors have no local files. I classified them from their tool names in this session only, so they are marked as such. I did not call any MCP tool.

## 2. Per source table

Safety: **RO** = read-only; **D** = writes drafts or private objects; **L** = writes live.

### A. Global MCP servers (`~/.claude.json`)

| Tool | Verified function | Phases | Use | Safety | Auth / cost |
|---|---|---|---|---|---|
| context7 | Library docs over HTTP (`mcp.context7.com/mcp`) | dev of the plugin only | ignore at runtime | RO | Bearer header in config |
| github | GitHub MCP over HTTP (`api.githubcopilot.com/mcp`) | P3 | call | **L** (`merge_pull_request`, `push_files`, `create_or_update_file`, `delete_file`, `delete_repository` all appear in the tool list) | `headersHelper` script runs `gh auth token`. The token scopes are those of the local gh login (unverified) |
| shadcn | `npx shadcn@latest mcp` component registry | none | ignore | RO | none |
| earshot | Local Python audio analysis (`EARSHOT_THREADS` env) | none | ignore | RO | local |

### B. Connectors, plugin MCPs, built-ins

| Tool | Verified function | Phases | Use | Safety | Auth / cost |
|---|---|---|---|---|---|
| Exa `web_search_exa`, `web_search_advanced_exa`, `web_fetch_exa`; skills `exa:search` (deep research), `exa:exa-agent` (multi-step research, lists; Similarweb is among its data providers) | Web search and fetch | P1 competitor discovery, P6 citation/press prospects, P7 cited-domain lookups, P11 | call | RO | The hosted MCP works anonymously with rate limits. OAuth or an API key raises them, and Exa Agent needs auth (README l.113, 128). Price not verified |
| Vercel `aggregate_events`, `count_events`, `aggregate_pageviews`, `count_pageviews` | Custom events and pageviews by date range. Breakdown by `eventName`, `requestPath`, `referrerHostname`, `utm*` and `eventData/<prop>`; production only by default | P1 tracking check, P8, P10 | call | RO | OAuth (`mcp.vercel.com`). Custom events need Pro (dossier 10) |
| Vercel `list_event_types` | "user-facing event types". Not clear whether these are account events or analytics events | P8 | verify first | RO | OAuth |
| Vercel `get_runtime_errors`, `get_runtime_logs`, `list_deployments`, `get_deployment`, `list_deployment_events`, `get_observability_schema`, `create_observability_query` | Deploy state, build and runtime logs, observability queries | P3 live verification, P9 health (5xx on `api/contact`, bot 4xx) | call | RO (I did not check whether `create_observability_query` persists the query) | OAuth. Custom Metrics querying needs Observability Plus (`custom-metrics` SKILL l.140) |
| Vercel `web_fetch_vercel_url`, `get_access_to_vercel_url` | Fetches a protected deployment. It **creates or reuses a 23 h share link** | P3 preview checks | call | D (side effect: share link) | OAuth |
| Vercel `get_project`, `list_projects`, `list_project_domains`, `get_domain_config`, `list_project_routes`, `list_bulk_redirects`, `filter_project_envs` | Project, domain, route, redirect and env inventory | P0, P1 | call | RO (no env decryption unless asked, per server instructions) | OAuth |
| Vercel `add_route`, `stage_redirects`, `restore_redirects`, `create_project_env`, `create_deployment`, `request_promote`, `request_rollback` | `add_route` and `stage_redirects` stage a new version. Staged redirects go live only via `update_bulk_redirect_version`. `create_deployment` can target `production`. `request_promote` re-points production without a rebuild. `request_rollback` moves production back | P3 | call only behind gates; prefer git (`vercel.json`) | **L** | OAuth |
| Vercel `search_vercel_documentation`, `list_billing_charges` | Docs; billing lines | dev; P10 cost line | ignore / optional | RO | OAuth |
| Vercel plugin skills: `vercel-functions`, `env-vars`, `deployments-cicd`, `custom-metrics`, `cdn-caching`, `routing-middleware`, `vercel-cli`, `verification`, `vercel-firewall`, `vercel-storage`, `access-protected-vercel-deployment` | Vercel how-to. `custom-metrics` covers numeric metrics. It points conversions to Web Analytics custom events (l.152) | P3, P8 | distil (a few facts) | n/a | n/a |
| User skills `deploy-to-vercel`, `vercel-cli-with-tokens`, `vercel-optimize` | Preview-by-default deploy, which asks before pushing. Token-based CLI: its step A prints the token with `printenv`. Cost/performance audit where Astro support is "limited" | P3, P9 | ignore (`vercel-cli-with-tokens`: secret exposure); distil the "preview unless asked" rule | L | Vercel CLI |
| chrome-devtools-mcp: `lighthouse_audit`, `performance_*`, `navigate_page`, `new_page`, `emulate`, `resize_page`, `take_snapshot`, `take_screenshot`, `list/get_network_request`, `list_console_messages`, `evaluate_script`, `fill_form`, `click`; skills `debug-optimize-lcp`, `a11y-debugging`, `cookie-debugging`, `chrome-devtools` | `lighthouse_audit` covers a11y, SEO, best practices and agentic browsing, and **excludes performance**. Use performance traces for LCP (tool-reference l.433) | P1 site check, P3 live verification (headers, `track` request fired, CTA visible), P11 | call | RO, except `fill_form`/`click`, which are **L** (a real form submit triggers a Resend email) | `npx chrome-devtools-mcp@1.12.0`. Usage statistics go to Google by default (`--no-usage-statistics`). Trace URLs go to CrUX (`--no-performance-crux`) |
| GitHub MCP `create_branch`, `create_pull_request`, `pull_request_read`, `list_commits`, `get_file_contents`, `issue_write`, `push_files`, `create_or_update_file`, `merge_pull_request` | Branch, PR and merge without a local clone | P3, P9 (owner request as an issue) | call; fallback `git` + `gh` | RO / L | gh token |
| Gmail (small-business): `create_draft`, `search_threads`, `get_thread`, labels; also `trash_*`, `mark_*_spam` | Drafts only. **No send tool** in this session's list | P5 review-request drafts, P6 pitches, P9 owner message | call (drafts) | D; L for trash, spam and labels | Google OAuth (connector) |
| Calendar `create_event`, `update_event`, `delete_event`, `list_events`, `suggest_time` | Events | P9 reminders (Projekt-Kurzbericht, recheck dates) | optional | **L** (whether invites are e-mailed is unverified) | Google OAuth |
| Drive `search_files`, `read_file_content`, `download_file_content`, `create_file`, `copy_file` | Files. No delete tool listed | P0 owner photos and price lists, P10 report export | optional | RO / L | Google OAuth |
| Claude Docs connector | Living shared docs | P10 monthly report as a shared doc | optional | D (private until shared) | claude.ai |
| Auth stubs (Ahrefs, Similarweb, Supermetrics, Klaviyo, Apollo, Clay, Canva, Slack, Notion, Zapier, Stripe…) | Only `authenticate` / `complete_authentication` tools are exposed | see §4 | ignore unless connected | n/a | vendor plan |
| Figma, Higgsfield, Motion, shadcn, earshot | Design, video and audio tools | none | ignore | Higgsfield/Figma L | n/a |
| Shopify (small-business) | Store ops incl. `theme_publish`, `graphql_mutation`, `create-discount` | none (clients are Astro) | ignore + deny | **L** | n/a |
| claude-mem `mcp__plugin_claude-mem_*` | Cross-session memory | none | ignore: state must live in `growth/` (dossier 11 §4, stale notes) | D | local |
| `WebFetch`, `WebSearch`, `Bash` | Fetch, search, scripts | all (fallback layer) | call | RO / L (Bash) | built-in |
| `Artifact` | Private HTML page on claude.ai; can carry shared state/db per capability | P2/P3 owner approval page, P10 report | optional | D (private by default) | claude.ai login |
| `claude-in-chrome` | Drives the user's own Chrome sessions | none | ignore (logged-in sessions, unscoped) | L | extension |
| `schedule`, `loop` | Cloud cron routines; in-session interval | P9 | call (`schedule`) | L (runs unattended) | claude.ai |
| `code-review`, `security-review`, `dataviz` | Diff review; security review; chart method | P3 plugin dev; P10 grid/trend charts | optional / distil dataviz | RO | built-in |

### C. Engineering-process skills

| Skill | Verified function | Use for twwa-growth |
|---|---|---|
| superpowers `writing-skills` + `references/` | Skills built TDD-style: run a baseline failure scenario, then write the skill. Description = "Use when…" triggers only, never a workflow summary. Match the form of guidance to the type of failure. `name` ≤64 chars, `description` ≤1024, body <500 lines, third person (`anthropic-best-practices.md` l.149–241). Words: <150 for getting-started, <500 for other skills (`discovery.md` l.131–133) | distil (authoring rules) |
| `verification-before-completion` | No claim of success without fresh command output | distil: live verification step |
| `subagent-driven-development` | Fresh implementer subagent per task, then a spec-and-quality review per task and a whole-branch review at the end | distil for building the plugin |
| `dispatching-parallel-agents` | Parallel agents only for independent tasks | distil: P1 audits in parallel |
| `systematic-debugging` | Four phases; no fix before root cause | distil (P9 incident triage) |
| `test-driven-development` | Red-green-refactor | distil for gate scripts |
| `using-git-worktrees` | Prefer native worktree tools, git fallback | ignore at runtime (one branch per action is enough) |
| `finishing-a-development-branch` | Choose merge locally / PR / keep / discard; tests on merged result | distil the "verify after merge" step |
| `requesting-code-review` | Review BASE_SHA..HEAD_SHA with a reviewer subagent | distil for approval hash (diff range) |
| mattpocock `writing-for-agents` | Model-invoked skills keep a description. User-invoked skills (`disable-model-invocation: true`) cost no context. A router skill lists the user-invoked ones | distil: `/twwa-*` = user-invoked + one router |
| `tdd`, `pr`, `code-review` (two axes: standards vs spec), `research` (primary sources to a Markdown file), `grilling` | Engineering helpers | distil `code-review` two-axis idea for the reviewer; rest ignore |
| gstack `ship` | Bumps VERSION/CHANGELOG, pushes, opens PR | ignore (wrong for client repos) |
| `land-and-deploy`, `setup-deploy` | Merges the PR from `/ship` with a readiness gate, then verifies the deploy. GitHub only. `setup-deploy` writes deploy config to CLAUDE.md | ignore; distil "read server state after any merge error" |
| `canary` | Watches the live site for 1–30 min after deploy (default 10) via the Aside browser; screenshots, console errors vs baseline | ignore (Aside = real browser); distil the baseline/compare idea |
| `benchmark` | Live `performance.getEntries()` with a baseline | ignore; use chrome-devtools traces |
| `browse`, `scrape`, `qa`, `qa-only` | Drive the user's real signed-in browser (Aside); `qa` fixes, `qa-only` reports | ignore |
| `review` | Pre-landing PR review | optional for TWWA engineers |
| `careful`, `guard`, `freeze` | PreToolUse hooks declared in SKILL.md frontmatter. `freeze` returns deny and **fails closed** on its own errors | distil the hook pattern (§3) |
| `health`, `investigate`, `retro`, `learn`, `document-release` | Code quality dashboard; debugging with scope lock; git retro; learnings store; docs audit | ignore |
| `make-pdf` | Markdown to PDF via gstack binary (`gstack/make-pdf/dist/pdf`) | optional P10 PDF export; fallback HTML/Artifact |
| ai-builder-club `new-loop` / `verifier-setup` / `setup-codebase-harness` | File-based loop scaffold with one test run / repo verification harness (dev-local, playwright) / full agent harness | ignore / distil "one-command verify" / ignore |
| hyperframes, genjutsu, flick, bang-motion, scroll-world, motionsites, lemolab, brag | Video, motion, landing-page generators | ignore |
| last30days | Social/forum research | ignore (US/social sources) |
| social-media-skills `graphic-designer` | LinkedIn graphics as HTML/CSS or AI image prompt | optional: HTML/CSS path could render GBP post images or a review QR card; otherwise ignore |

## 3. Rules worth distilling

1. **Gates as hooks fail open unless built to fail closed.** If a hook exits non-zero without decision JSON, Claude Code treats it as non-blocking (`gstack/freeze/bin/check-freeze.sh` l.16–19). Our hook therefore traps errors and still emits `deny`. Scripts in the ship path remain the main gate; hooks are a backstop (dossier 11).
2. The decision must be nested in `hookSpecificOutput`, because a top-level `permissionDecision` is ignored (`check-careful.sh` l.9–10).
3. **Skill descriptions are triggers only** (superpowers `writing-skills` l.93–98). All `/twwa-*` skills are user-invoked (`disable-model-invocation: true`), with one router description (mattpocock SKILL-MECHANICS).
4. **Preview first; production only on explicit request** (`deploy-to-vercel` l.11). Use `promote` on the validated preview rather than a new prod build, which keeps "approve the exact version" true (`deployments-cicd` l.96–110).
5. Never pass a Vercel token as a CLI flag (`vercel-cli-with-tokens` l.57). Never `printenv` it.
6. Lighthouse budgets: `lighthouse_audit` has no performance score. Use `performance_start_trace` plus `debug-optimize-lcp`, or the Lighthouse CLI in CI.
7. Run chrome-devtools-mcp with `--no-usage-statistics --no-performance-crux --isolated` for client audits (README l.35–45, l.174).

## 4. Scripts, data access, D1 to D7

**Ahrefs** (if connected): competitor backlinks and referring domains for P6, keyword volumes for P4 demand. Without it: Bing `GetUrlLinks`/`GetLinkCounts`, Exa searches for mentions, DataForSEO volumes (dossier 10). **Similarweb**: traffic estimates for competitors and prospects in P11. Coverage of small German local sites is unverified and probably thin. Without it: GSC and Vercel for the client, no traffic claims about competitors.

**D1 Plugin layout.** `.claude-plugin/plugin.json` in 29 manifests: `name` and `description` 29, `author` 28, `version` 27, `license` 26, `repository`/`homepage` 25, `keywords` 21, `skills` (array of dirs) 5, `mcpServers` inline 2 (exa, chrome-devtools), `displayName` 2, `commands`/`agents` arrays 1 (vercel), `userConfig` 1, `$schema` 1. Skills are auto-discovered from `skills/<name>/SKILL.md` when `skills` is absent (brag: no list, has `skills/brag`). Agents `agents/*.md` frontmatter in use: `name`, `description` 74/74, `tools` (comma string) 57, `maxTurns` 43, `model` (e.g. `sonnet`) 22, `effort` 1. `commands/*.md` used by vercel. `hooks/hooks.json` = `{"hooks":{"<Event>":[{"matcher":"Edit|Write","hooks":[{"type":"command","command":"node","args":["${CLAUDE_PLUGIN_ROOT}/…","${tool_input.file_path}"],"timeout":30}]}]}}`. `async`, `shell`, `statusMessage` and `powershell` also appear (claude-seo, claude-mem, superpowers). Events: 21 in `HOOK_EVENTS` (PreToolUse, PostToolUse, SessionStart, Stop, …; SDK `sdk.d.ts` l.397). `.mcp.json` = `{"mcpServers":{"vercel":{"type":"http","url":"…"}}}`. Validate with `claude plugin validate --strict` and `--profile directory`. Scaffold with `claude plugin init --with skills agents hooks`.

**D2 Invocation.** Both forms work. The namespaced form is `/plugin:skill` (vercel README l.160 `/vercel:nextjs`; hyperframes README l.51), and session skill lists show `brag:brag`, `vercel:deploy`. The bare name has worked since 2.1.265 ("a plugin skill is now found by its bare name"), and since 2.1.269 the Skill tool names the full form when a bare name is unique. brag README uses `/brag`. Confidence high. Collisions are real: gstack `/review` vs mattpocock `code-review`. Keep a `twwa-` prefix so `/twwa-weekly` stays unique, and document `/twwa-growth:twwa-weekly` as the canonical form.

**D3 SKILL.md frontmatter** (counts across 1,665 local SKILL.md files). `name`/`description` 1,665. `metadata` 360 (vercel puts `filePattern`/`bashPattern` there for its own hook). `allowed-tools` 124 (YAML list allowed since 2.1.0). `argument-hint` 100 (since 1.0.54). `user-invocable` 63 (`false` hides it from the slash menu, 2.1.0). `disable-model-invocation` 33 (the model cannot call it and is told to ask the user, 2.1.222). `hooks` 12 (gstack). Not found in any local SKILL.md, verified from the changelog only: `effort` (2.1.80), `context: fork` (2.1.0; background by default since 2.1.218, opt out with `background: false`), `disallowed-tools` (2.1.152). `model` and `agent` were not verified from any source. The misspelled `user-invokable` (32 files) is probably ignored (unverified).

**D4 Paths.** `${CLAUDE_PLUGIN_ROOT}` appears in 33 SKILL.md files and `${CLAUDE_SKILL_DIR}` in 44 (added per changelog: "skills to reference their own directory"). `${CLAUDE_PLUGIN_DATA}` is persistent state that survives updates. Examples: (1) `"${CLAUDE_PLUGIN_ROOT}/scripts/claude-seo" run render_page.py <URL> --mode auto` (claude-seo `seo-sxo` l.43); (2) `python3 "${CLAUDE_SKILL_DIR}/scripts/run.py" google_auth --check --json` with `CLAUDE_BLOG_RUNTIME_DIR='${CLAUDE_PLUGIN_DATA}/…'` (claude-blog `blog-google` l.82–83); (3) hook `node "${CLAUDE_PLUGIN_ROOT}/hooks/session-start-profiler.mjs"` (vercel hooks.json). gstack notes that early skill bash runs before `CLAUDE_SKILL_DIR` exists and anchors on `$HOME` instead (`investigate` l.505). Quote the variable, because `validate` warns on unquoted shell use.

**D5 Marketplace.** Minimal working single-plugin repos (brag, flick): `.claude-plugin/marketplace.json` = `{"name":"<mkt>","owner":{"name":"…"},"plugins":[{"name":"<plugin>","source":"./","description":"…"}]}` next to `.claude-plugin/plugin.json`. READMEs install with `/plugin marketplace add <owner>/<repo>` then `/plugin install <plugin>@<mkt>`, and `known_marketplaces.json` records `{"source":"github","repo":"…"}`. Other source forms: `{"source":"url","url":"…git","sha":"…"}`, `git-subdir`, and `strict: true` (superpowers-marketplace). Since 2.1.292 `claude plugin install --marketplace <source>` does both steps. Names that cannot be installed now fail validation (2.1.283).

**D6 PreToolUse.** Stdin JSON: `session_id`, `transcript_path`, `cwd`, `permission_mode`, `agent_id`/`agent_type` (subagent), `hook_event_name`, `tool_name`, `tool_input`, `tool_use_id` (`sdk.d.ts` l.99–110, 1248–1253). There are two ways to block: exit 2 with the reason on stderr (`block-dangerous-git.sh`), or exit 0 with `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny"|"ask","permissionDecisionReason":"…"}}` (hyperframes `.claude/settings.json`; gstack). `updatedInput` and `additionalContext` are also allowed. A non-zero exit other than 2, or a crash without JSON, is **non-blocking** (freeze l.16–19). The tool hook timeout default is 10 min (2.1.3), overridable per hook. Behaviour on timeout is not documented as blocking: treat it as fail-open (unverified beyond the 2.1.210 and 2.1.304 fixes). `--bare` **skips plugin and settings hooks** (`claude --help`).

**D7 Scheduling.** Cloud `/schedule` routines run in Anthropic's cloud on a repo with a GitHub trigger. They load the plugins enabled on the claude.ai account (2.1.314). **MCP servers configured in Claude Code cannot be attached**, only claude.ai connectors (2.1.251). Routines default to a few minutes past the hour (2.1.283). A run that fails partway may be re-run from the start an hour later, so writes must be idempotent (2.1.302). A run skips and retries for 72 h if GitHub is disconnected (2.1.274). Concurrent cloud session limits apply (2.1.302). **Since 2.1.325, scheduled tasks and `/loop` ask before running a skill that declares `allowed-tools` or hooks**, so `Skill(twwa-weekly)` must be in `permissions.allow`. `/loop` self-paced waits max 1 h and lives in the session only. Local alternative: launchd/cron runs `cd <client-repo> && claude -p "/twwa-weekly" --permission-mode dontAsk --allowed-tools … --max-budget-usd 2 --output-format json --no-session-persistence`, which keeps local MCP, gh and keychain. Do not use `--bare` (it skips our guard hooks). The cron minimum interval for cloud routines is not verified.

## 5. Contradictions with the dossier

| Claim | Dossier | Verdict |
|---|---|---|
| Vercel plugin `.mcp.json` note says the MCP is "Read-only in initial release" | 10 §1 treats the MCP as read and write | The tool list has live writers (`request_promote`, `create_deployment`, `add_route`). The note is stale, so the dossier is right |
| Lighthouse budget "Performance ≥ 90" via tooling | 07 §5 | `lighthouse_audit` excludes performance. Need a trace or the Lighthouse CLI |
| Weekly loop as a cloud routine with all integrations | 11 §5 | Cloud routines cannot attach local MCP servers (github, context7). Use connectors or plain scripts with env secrets |
| "Hook that errors/times out doesn't block" | 11 §1 | Confirmed (freeze comments) |

## 6. Harmful or banned for our use

- `fill_form`/`click` on a production contact form sends real leads. Synthetic tests run only on preview, or use a `X-TWWA-Test` header that `api/contact.js` drops before Resend.
- `claude-in-chrome`, gstack `browse`/`scrape`/`canary` drive real signed-in browsers. Client data could leak, and sessions could be used to post reviews or listings.
- `vercel-cli-with-tokens` prints the token.
- Shopify `theme_publish`, Higgsfield publishing: no use for us, and they write live.

### Risks and guards

| Live writer | Guard in `twwa-growth` |
|---|---|
| Vercel `request_promote`, `create_deployment` (target production), `request_rollback` | PreToolUse deny unless `growth/approvals/<id>.json` hash equals the deployment's commit SHA and `growth/STOP` is absent. Rollback is allowed only from `/twwa-ship --revert` |
| Vercel `add_route`, `stage_redirects`, `update_bulk_redirect_version`, `restore_redirects`, `create_project_env`, `edit_project_env` | Deny by default; redirects go via `vercel.json` in git (reviewable, revertible) |
| GitHub `merge_pull_request`, `push_files`, `create_or_update_file`, `delete_*` | Deny `merge` unless the approval hash matches the PR head SHA and gate scripts exited 0. Deny pushes to the default branch |
| Gmail `create_draft`; `trash_*`, `mark_*_spam`, labels | Drafts allowed (no send tool exists); deny trash/spam/label tools |
| Calendar `create_event`/`update_event`/`delete_event` | Ask; only on TWWA calendar |
| Drive `create_file`/`copy_file` | Ask; TWWA folder only |
| Shopify, Higgsfield, Figma writes | Deny via `disallowed-tools` in every `/twwa-*` skill |
| `web_fetch_vercel_url` share link | Allowed for previews only; log the link |

## 7. Optional integrations (if available, use X for Y; otherwise Z)

1. Vercel `aggregate_events` for form/tel/WhatsApp counts by source; otherwise a REST script on `/v1/query/web-analytics/events/aggregate` with a Vercel token.
2. Vercel `list_deployments` + `get_runtime_errors` for health; otherwise `vercel ls`/`vercel logs`, or `curl -I` on the live site.
3. Vercel `web_fetch_vercel_url` for protected preview checks; otherwise `vercel curl` (`access-protected-vercel-deployment`), or set preview protection to public with `x-robots-tag: noindex`.
4. chrome-devtools `performance_*` + `emulate` for the LCP/CWV check; otherwise the Lighthouse CLI or PSI API script.
5. chrome-devtools `list_network_requests` to confirm the `track` call and `x-robots-tag`; otherwise `curl -I` and a server-side event check.
6. GitHub MCP `create_pull_request` for the approval PR; otherwise `git push` + `gh pr create`.
7. Exa `web_search_exa` for cited-domain and press prospects; otherwise `WebSearch` + `WebFetch`.
8. Gmail `create_draft` for owner request and pitch drafts; otherwise a Markdown draft in `growth/outbox/`.
9. `Artifact` for the owner Ja/Nein approval page and the monthly report; otherwise an e-mail summary + `reports/YYYY-MM.md` (PDF via `make-pdf` if installed).
10. `schedule` for `/twwa-weekly` per client repo; otherwise launchd + `claude -p` with `--max-budget-usd`.

## 8. Gaps

- No installed tool reads GSC, GBP, Bing Webmaster, IndexNow or DataForSEO. All need our own scripts with env/keychain secrets.
- No Resend delivery-status tool.
- No German citation or review data source.
- No approval-hash or action-log tooling: we must build it.
- The cloud cron minimum interval, Exa pricing, GitHub token scopes, whether Calendar sends invites, and `list_event_types` semantics are unverified.
- `model`/`agent` SKILL.md fields are unverified.
