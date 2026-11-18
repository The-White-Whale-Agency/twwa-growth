# 11 · Automation, agents, KPIs and realistic timelines

Confidence legend: [P] primary · [S] secondary · [V] vendor claim · [I] inference/recommendation.

## 1. How practitioners run SEO with Claude Code / agents (2026)

Patterns that recur across practitioner write-ups [S, 2026: waseemnasir, khamsouk, odiseo, bigguyonstuff, dev.to failure-mode posts, seoshouts]:
- **Per-client context file** (CLAUDE.md, lean ~100 lines) + targeted reference files; large context causes rules from early files to be underweighted.
- **Skills (slash commands) per role** (strategist, writer, SEO, CRO) and **subagents** for independent parallel tasks (keyword research ∥ competitor analysis ∥ technical audit); dependencies run sequentially (research → brief → article).
- **Read-only auditors**: a reviewer that can edit "quietly fixes what it found".
- **Plan mode before multi-file changes**; approved plan = written scope.
- **Hard gates in code, not prose**: "Documented. Not enforced." A five-agent sign-off documented in CLAUDE.md was bypassed because the publisher regenerated content; fix = a script that must exit 0 before publish. Hooks (PreToolUse) for hard stops; but a hook that errors/times out doesn't block by default.
- **Idempotency**: a publisher calling create unconditionally made duplicates; fix = lookup by slug/ID, update-in-place, daily divergence audit.
- **Echo/stale-doc risk**: agents reading their own earlier docs treat them as truth; rule "measure before you read" — live system (API, HTTP, git) wins over docs.
- **Independence**: a subagent asked to "review independently" shares context and agrees; use a fresh headless process with paths and checks only.
- **Loops need limits**: step, time and spend caps + a circuit-breaker file.
- **Verification**: every finding cites URL/line/data point; unverified = "Hypothese"; spot-check 3–5 findings per run; diff vs last run (fixed issue shouldn't reappear).
- **Scheduling options**: cloud routines (`/schedule`, fresh repo clone, runs with laptop off), desktop scheduled tasks (local files/MCP), `/loop` for in-session polling [S, seoshouts 2026-11].
- **Drafts only for anything customer-facing** (AI replied to a lead before approval → rule: replies are drafts) [S].
- Approval = **state transition** recording who approved which version; content change after approval invalidates it [S, odiseo].

## 2. Recommended architecture for `twwa-growth` [I]

```
/twwa-growth (entry)  →  check → plan → (approval) → implement → verify → measure → schedule weekly
   ├─ /twwa-check        read-only: tech, GBP, citations, reviews, AI panel, CRO, tracking
   ├─ /twwa-plan         ranked action list with hypotheses, windows, effort, risk
   ├─ /twwa-ship         implements approved actions on a branch → Vercel preview → PR
   ├─ /twwa-gbp          GBP audit + drafts (posts, replies, services) → approval → API publish
   ├─ /twwa-reviews      review engine assets, velocity targets, reply drafts
   ├─ /twwa-pages        page pipeline with gates A–H (06)
   ├─ /twwa-ai-visibility prompt panel runs + cited-source analysis
   ├─ /twwa-offsite      opportunities + pitch drafts
   ├─ /twwa-measure      data pull + per-action verdicts
   ├─ /twwa-report       monthly German owner report
   └─ /twwa-weekly       scheduled loop (cloud routine)
Subagents (read-only unless noted): auditor-tech, auditor-local, researcher-keywords, researcher-competitors,
  writer-de (write, drafts only), reviewer-quality (fresh process, gates), analyst-measure, legal-linter.
Hard gates (scripts, exit codes): seo-checks (07), page-gates (06), legal-lint (03: UWG/Impressum/§5b), approval-check (hash match).
```

### Approval model
- States: `proposed → approved(v_hash, by, at) → shipped(commit, deploy_id) → measured(verdict) → kept|reverted`.
- Approval channel: PR on GitHub (TWWA approves technical/content), owner approval for content claims/prices/photos/GBP/reviews via a simple review page or e-mail summary with Ja/Nein links (owner time budget ≤ 10 min/month, Klano promises ~5) [P Klano; I].
- Default autopilot: nothing. Allowed-without-owner (TWWA-approved only): technical fixes that don't change visible claims (redirect fixes, canonical, image compression, schema/NAP sync, internal links).
- Revert: `git revert` of the action commit + redeploy; record verdict.

### Budget/safety caps per run [I]
- Max N new pages proposed per week (Gate G), max 1 GBP identity edit per 48 h, max 10 GBP API edits/min (hard API limit) [P], token budget per client run, API spend cap (DataForSEO balance alert), circuit-breaker file `growth/STOP`.

## 3. What moves when — realistic timelines (for judging actions in the weekly loop)

| Action | First observable signal | Typical evaluation window | Evidence |
|---|---|---|---|
| Technical fix (indexing, canonical, redirects) | Recrawl days; GSC changes in 1–3 weeks | 7–28 days | Klano: "Technik-Fixes 7 bis 28 Tage" [V/P] |
| Title/meta rewrite on ranking page | CTR change once recrawled | 14–28 days (compare equal-length windows) | [I] |
| New page (service/town/cost) | Indexed days–weeks; impressions 2–8 weeks | 28–90 days | Klano: "neue Artikel typisch nach 2 bis 8 Wochen" [V]; local organic slower in competitive towns [I] |
| GBP primary category change | Hours–2 days; judge at 48 h, settle 1–2 weeks; may trigger re-verification | 2–14 days | [S] LSF, Sterling Sky 2025-12, NinjaJump |
| GBP secondary categories/services | Days (wait ~4 days before measuring) | 7–14 days | [V] GMB Everywhere test |
| Hours/"open now" fixes | Immediate effect on time-of-search visibility | 7 days | [P] Whitespark factor #5 |
| Reviews velocity | Rankings respond over weeks; stopping reviews for ~18 days preceded a drop in one case | 30–90 days | [S] Joy Hawkins 2025 |
| Citations (core) | Little ranking impact within a month (Whitespark 100-citation test) | 60–120 days; mostly AI/consistency value | [P] Whitespark 2021 |
| Links/PR | Weeks–months | 60–180 days | [I] |
| Robots change for OAI-SearchBot | ~24 h | 7 days | [S] OpenAI via Klano |
| AI mention rate | Weeks after underlying changes; high variance | ≥4 weekly points | [S] SparkToro, BrightLocal |
| Spam-update recovery | Months | until next core update | [S] Google via secondary |
| Seasonal pages | Must be live 6–10 weeks before peak | YoY comparison | [I] |

### KPI hierarchy
- North star: qualified Anfragen/month (and won jobs/value when owner reports).
- Leading (weekly): non-brand impressions & clicks (GSC, `brandedClassification`), money-page positions, geo-grid SoLV/ATRP, GBP calls/website clicks/directions, review count last 30/90 days vs competitor median, AI mention rate, indexed share of sitemap.
- Health: deploy success, form pipeline success, CWV budgets, index coverage, NAP/schema drift, robots/noindex regressions.

### Weekly loop algorithm [I]
1. **Measure first** (live data, not docs): pull GSC, GBP Performance, grid (if due), AI panel (if due), Vercel events, lead records, deploy status.
2. **Health checks**: any P1 (form broken, noindex on money page, prod deploy failing, GBP suspended) → alert immediately, propose fix, stop other work.
3. **Evaluate open actions** whose window ended: compute deltas vs baseline and vs control pages; label win/neutral/loss/inconclusive; propose revert for losses.
4. **Detect opportunities**: striking-distance (pos 4–15, impressions ≥ threshold), CTR outliers (CTR < 50% of expected for position), new queries without dedicated page (cluster), pages failing Gate H, review velocity below target, competitors' new reviews/categories, AI cited sources where client absent, seasonal calendar triggers, Förder source changes.
5. **Rank** by expected leads × confidence ÷ effort; respect caps; produce ≤ 5 proposals with hypothesis + window.
6. **Request owner inputs** (photos, prices, approvals) in one short German message.
7. **Write snapshot + log**; diff vs last week; no "new" issue that was fixed (verify deploy).
8. Monthly: generate report (09 §4); quarterly: re-plan, prune, refresh prompt panel and competitor set.

## 4. What fails in practice (and the countermeasure)
| Failure | Countermeasure |
|---|---|
| Gate described in prompt, bypassed by agent | Gate = script with exit code in the ship path |
| Duplicate pages/posts on retries | Idempotent publish keyed by slug/ID; reconcile before create |
| Agent trusts its own stale notes | Live-measure-first rule; snapshots dated; docs never override APIs |
| Confident but wrong findings | Evidence field required; spot-check sample; second data source for keyword claims |
| Over-production of pages | Gates A–H, weekly caps, pilot batches |
| AI-sounding German copy | Style linter + human approval; regional vocabulary; owner facts |
| Silent tracking breakage after redesign | Synthetic form test each run |
| Small-data overclaiming | Report confidence; aggregate; leading indicators |
| GBP suspension from rapid edits | Edit pacing, linter, never change name/address via automation |
| Legal exposure (reviews, Impressum, claims) | legal-lint + human sign-off for legal-relevant changes |

## 5. Implications for the plugin [I]
- The entry skill must be resumable (state in `growth/`), idempotent, and evidence-first.
- Ship scripts, not prose, for every gate; use hooks only as an extra guard.
- Run the weekly loop as a scheduled cloud routine per client repo with spend caps and a STOP file; human approval remains the only path to production content changes.
