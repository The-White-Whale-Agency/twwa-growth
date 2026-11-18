---
name: twwa-pages
description: Use when a TWWA client needs a new service, service-and-town, cost or case-study page, a refresh of an existing page, or when monthly project reports from the client must be turned into evidence for pages. Every page passes gates A to H before it can be approved.
---

# twwa-pages

Pages exist because the teardown shows winners have them and the client has real evidence for them, never to a count.

If `${CLAUDE_PLUGIN_ROOT}` is empty, the plugin root is two directories above this file. Scripts: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py"` (written below as `<name>.py`). Every script has `--help`; exit 3 = credentials missing (use the fallback it names), exit 4 = blocked by STOP, cap, approval, spend or scope (report it, never work around it).

1. Intake: every monthly project report `evidence.py intake <file>` (format: `templates/de/projekt-kurzbericht.md`). Missing fields become one German question to the owner.
2. Choose: from the backlog item (`new_page` or `page_refresh`) and the teardown winners' page type. Load `references/page-types.md`. On a one-page tier (premium) there are no new pages: strengthen the landing section and write the scope proposal.
3. Evidence: `evidence.py for-page --town <Ort> --service <id>` must show ≥ 3 items, ≥ 1 first-party. Not enough evidence = an owner data request ("wartet auf erstes Projekt mit Fotos in Nachbarstadt"), not a thinner page.
4. Draft: subagent `twwa-writer-de` with the brief and evidence paths. Every factual sentence carries `[[p:...]]`, `[[f:...]]` or `[[b:...]]`.
5. Gates: `evidence.py provenance <draft>`, `style_lint_de.py --gate <draft>`, `legal_lint.py text <draft>`, `page_gates.py run --page <draft> --action <id>`. Then subagent `twwa-quality-reviewer` (cold read, cannot edit). A script failure is never overruled.
6. Hand to skill `twwa-ship`. New templates start as a pilot of 3–5 pages; the ramp gate limits volume.
