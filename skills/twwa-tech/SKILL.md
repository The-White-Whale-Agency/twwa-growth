---
name: twwa-tech
description: Use when a client or prospect site on Astro and Vercel needs a technical SEO audit or a technical fix, such as canonical or trailing-slash problems, redirects, sitemap or robots.txt, AI crawler access, JSON-LD and NAP drift against business.json, internal links, images, preview hosts that can be indexed, or IndexNow setup.
---

# twwa-tech

Technical audit and fixers for Astro static sites on Vercel. The audit is read-only. Every fix becomes an action that ships through `twwa-ship`; this skill never merges or deploys.

If `${CLAUDE_PLUGIN_ROOT}` is empty, the plugin root is two directories above this file.

## Inputs

- A client repo with `.twwa-growth/` (client mode), or only a URL (prospect mode: facts are inferred from the Impressum and marked as inferred).
- Optional: a fresh build in `dist/` (`npm run build`).

## Steps

1. Detect the setup and confirm the state folder is healthy:
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/twwa_state.py" detect --repo .`
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/twwa_state.py" doctor` (stop and fix on exit 1).
2. Audit the build: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/site_audit.py" dist dist --write-snapshot --json`.
   Live data wins over the build: also run `site_audit.py live <site url>` (25 pages by default, robots.txt respected, GET only). For a prospect, run only `live` and write results to `./twwa-checks/<domain>/`, never into a client repo.
3. Check structured data against `business.json`: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/schema_gen.py" validate dist`. Load `references/schema.md` before changing any JSON-LD.
4. Check redirects: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/site_audit.py" redirects --repo . --from-gsc` (add `--live <url>` after a deploy). Load `references/astro-vercel.md` for slash policy, `cleanUrls`, preview hosts and relaunch mapping.
5. Check the link graph: `site_audit.py linkgraph dist`. Money pages need at least 3 internal inlinks and no links through redirects.
6. Check indexing basics: robots.txt and AI bot findings come from step 2; IndexNow with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/indexnow.py" check`. Load `references/indexing.md` for Bing, IndexNow and the AI crawler policy.
7. Turn findings into actions. Group related findings into one action (one action per fix, not per page). For each:
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/twwa_actions.py" propose --type tech_fix --title-de "<German title>" --findings <finding id> --pages <path> --hypothesis "<if X then Y because Z>"`.
   Use `robots_policy` for robots.txt changes and `tracking_fix` for form or source-field fixes. Exit 4 means a cap, STOP or scope block: report it, do not work around it.
8. Hand the approved action to `twwa-ship`.

## Decisions

- P1 findings (noindex on a money page, robots blocking search bots, broken form handler, unreachable Impressum) go first, ahead of any teardown-driven work.
- Findings with status `hypothesis` never lead a report and never justify a change alone; collect evidence first.
- Training crawlers: report only. Change their rules only when `config.ai_bots.training` says so.
- `llms.txt` and special AI files are not a lever. Schema is for entity clarity, not for rich results that no longer exist (FAQ, HowTo).
- Changes to Impressum, Datenschutz or consent text are R3: write the finding and stop. See `../../references/legal-de.md`.

## Outputs

- `snapshots/<date>/site.json` with findings (section 4.3 schema) and pages.
- Proposed actions in `actions.jsonl`.
- For fixes: template files from `templates/site/` (`components/SeoHead.astro`, `components/LocalBusinessSchema.astro`, `components/ServiceSchema.astro`, `public/robots.txt`, `sitemap.config.mjs`, `vercel.preview-noindex.json`, `indexnow-notes.md`) copied by `twwa-ship` on the action branch.

## Stop conditions

- `STOP` exists in the state folder.
- `twwa_state.py doctor` fails.
- No build and no live site reachable: report "nicht geprüft" for the affected areas instead of guessing.

## Optional integrations

| If available | Use it for | Otherwise |
|---|---|---|
| chrome-devtools performance tools | lab Core Web Vitals on home and one service page | `psi.py run` (keyless at low volume) |
| Vercel MCP deployments and runtime errors | production deploy health, 5xx on `api/contact` | `site_audit.py live` status codes |
| Search Console data (`gsc.py`) | index status and Google-chosen canonicals | report as "nicht geprüft" |

## References

- `references/astro-vercel.md`: slash policy, canonicals, redirects, preview hosts, 404 (step 2 and 4).
- `references/schema.md`: subtype choice, required fields, what not to mark up (step 3).
- `references/indexing.md`: sitemap rules, robots and AI bots, Bing, IndexNow (step 6).
- Shared: `../../references/state-and-config.md`, `../../references/safety.md`.
