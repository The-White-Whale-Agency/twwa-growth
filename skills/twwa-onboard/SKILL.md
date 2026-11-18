---
name: twwa-onboard
description: Use when a TWWA client repo has no .twwa-growth state folder yet, or when business facts, access to Search Console, Bing, the Business Profile or Vercel, or the client's tier need to be set up before any growth work.
---

# twwa-onboard

If `${CLAUDE_PLUGIN_ROOT}` is empty, the plugin root is two directories above this file. Scripts: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py"` (written below as `<name>.py`). Every script has `--help`; exit 3 = credentials missing (use the fallback it names), exit 4 = blocked by STOP, cap, approval, spend or scope (report it, never work around it).

## Steps

1. `twwa_state.py detect --repo .` then `twwa_state.py init` (idempotent) and `twwa_state.py doctor`.
2. Fill `.twwa-growth/business.json` from the repo (site data, schema, Impressum) and the live Impressum. Every unknown stays `null`; nothing unknown is ever written into copy, schema or reports. Load `../../references/state-and-config.md` for the fields.
3. Tier: `twwa_state.py scope`. Unknown tier is treated as premium with a finding for TWWA.
4. Connectors, in this order, each with its fallback:
   - Search Console: add the property to the Google user or service account; `gsc.py sites`; else CSV export.
   - Bing Webmaster: import the site from Search Console, set `BING_WEBMASTER_API_KEY`, `bing_wmt.py sitemap --feed <sitemap> --execute`.
   - IndexNow: `indexnow.py key --write` (key file in `public/`, ships with the next deploy).
   - Business Profile: `gbp.py locations`; set `business.gbp.location`; else `gbp.py template`. API access steps: skill `twwa-gbp` reference `gbp-api-setup.md`.
   - Vercel: `VERCEL_TOKEN` plus project and team id in config; analytics via MCP export.
   - Data providers: `providers.py list`; set `spend.monthly_cap_usd` only when the owner agreed.
5. Baselines: `gsc.py snapshot`, `gbp.py snapshot`, `regression_guard.py baseline`, `ai_panel.py generate --write`.
6. Owner questions (German) into the repo's `clients-questions/`: missing facts, service area with drive times and jobs per town, prices if they want them shown, memberships and partner programmes, consent wording sign-off. Mention the monthly project report format (`templates/de/projekt-kurzbericht.md`).
7. Then run mode `check` and hand over what is set up, what is missing, and who must act.
