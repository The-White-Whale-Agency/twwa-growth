---
name: twwa-offsite
description: Use when a TWWA client needs core citations, membership or manufacturer partner listings, local press, or mentions on sources that AI answers cite, or when NAP data across listings is inconsistent. Produces drafts and a tracker only.
---

# twwa-offsite

If `${CLAUDE_PLUGIN_ROOT}` is empty, the plugin root is two directories above this file. Scripts: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py"` (written below as `<name>.py`). Every script has `--help`; exit 3 = credentials missing (use the fallback it names), exit 4 = blocked by STOP, cap, approval, spend or scope (report it, never work around it).

1. `offsite.py plan`: tier-1 gaps (Google, Bing Places, Apple Business Connect, Das Örtliche, Gelbe Seiten, Das Telefonbuch), then sources the AI engines cite where competitors appear, then real memberships (Innung, Handwerkskammer, Kammer, Verband), manufacturer partner finders, local press for real news.
2. Each entry uses exactly the data in `business.json` (NAP). After it is live: `offsite.py track <id> --status live --url ...`, then `entity_check.py run`.
3. Pitches and press notes are German drafts under `drafts/<id>/`; `offsite.py lint <file>` must pass. Load `references/outreach-law-de.md`, then decide who sends:
   - the client from his own mailbox (always possible), or
   - TWWA on the client's behalf (`outreach.send_mode: "twwa_sends"` plus a recorded written mandate in `outreach.mandate`).
   Before every send: `offsite.py send-check --relationship member|partner|invited|press|listing|cold --channel email|form|phone|letter|portal --sender client|twwa --file <draft>`. Exit 4 = not allowed via that channel (cold contacts get a letter or a call, never an e-mail). A person sends; the plugin never does. Log it with `offsite.py track <id> --status submitted`.
4. Banned: link exchanges, paid links without rel=sponsored, blog networks, self-published "best of" lists naming the client, mass directory submissions.
