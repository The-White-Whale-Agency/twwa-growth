---
name: twwa-report
description: Use at month end, or when the owner of a TWWA client asks what the work brought, to write the one-page German report led by qualified Anfragen.
---

# twwa-report

If `${CLAUDE_PLUGIN_ROOT}` is empty, the plugin root is two directories above this file. Scripts: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py"` (written below as `<name>.py`). Every script has `--help`; exit 3 = credentials missing (use the fallback it names), exit 4 = blocked by STOP, cap, approval, spend or scope (report it, never work around it).

1. Data younger than the month end: skill `twwa-measure` step 1 if stale. If no lead number exists, ask the owner for the count of Anfragen this month, or mark it "nicht erfasst". Never estimate.
2. `leads.py qualify`, then `report.py build --month <yyyy-mm>`. The script refuses wording that fails the legal lint (guarantees, superlatives).
3. Read it once as the owner would: one page, plain German, leads first, then visibility, done, effect, next, one request. Manual AI samples are labelled "Stichprobe".
4. Hand over `reports/<yyyy-mm>.md` with a short message text for e-mail or WhatsApp.
