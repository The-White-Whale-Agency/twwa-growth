---
name: twwa-leads
description: Use when a TWWA client's inquiries must be counted and attributed without cookies, when the contact form, call or WhatsApp links need tracking, when the form pipeline must be tested, or when leads need qualifying before the monthly report.
---

# twwa-leads

If `${CLAUDE_PLUGIN_ROOT}` is empty, the plugin root is two directories above this file. Scripts: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py"` (written below as `<name>.py`). Every script has `--help`; exit 3 = credentials missing (use the fallback it names), exit 4 = blocked by STOP, cap, approval, spend or scope (report it, never work around it).

1. Form handler: compare the repo's `api/contact.js` with `templates/site/api/contact-attribution.js`. The pattern adds a "Wie haben Sie uns gefunden?" select, the landing page, and a probe short-circuit (`_twwa_probe`), and tags the notification subject (`[Anfrage | Quelle | Seite]`). No personal data leaves the handler beyond the e-mail to the owner. Ship it as a `tracking_fix` (premium allows changes to the existing handler).
2. Clicks: `tel:`, `wa.me` and `mailto:` links get Vercel custom events only when `vercel.custom_events` is true (Pro). Otherwise calls are counted from GBP performance and the owner's monthly count.
3. Record: `leads.py add` per inquiry (operator, from tagged notifications) or `leads.py import-events <jsonl>`; `leads.py qualify`; outcomes with `leads.py outcome <id> won|lost`.
4. Test: `leads.py probe <https://client/api/contact>` (dry run), `--execute` only on the client's own domain. Failure is P1.
5. Monthly: `leads.py summary --month <yyyy-mm>` feeds the report.
