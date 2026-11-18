---
name: twwa-ai-visibility
description: Use when checking whether ChatGPT, Gemini, Google AI Mode or Perplexity name or cite a TWWA client for local buyer questions, when measuring that over time, or when finding which cited sources the client is missing from.
---

# twwa-ai-visibility

Measures mention rates with intervals, never an "AI ranking position". Answers vary from run to run.

If `${CLAUDE_PLUGIN_ROOT}` is empty, the plugin root is two directories above this file. Scripts: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py"` (written below as `<name>.py`). Every script has `--help`; exit 3 = credentials missing (use the fallback it names), exit 4 = blocked by STOP, cap, approval, spend or scope (report it, never work around it).

1. `ai_panel.py generate --write` (≤ 40 German prompts: 40 % recommendation, 25 % need, 20 % cost and process, 15 % brand; location set per prompt). Edit prompts that sound unnatural.
2. `ai_panel.py run` (dry run, cost) then `--execute` under the spend cap; direct APIs are `ui_parity: false` and say so. Without API keys: collect answers by hand or with a browser tool and `ai_panel.py import <folder>` ("Stichprobe").
3. `ai_panel.py compare` (movement only when intervals separate or 4 runs trend), `ai_panel.py gaps` → skill `twwa-offsite`.
4. Levers that work: a dedicated service page with explicit facts (prices, area, process, proof), rating ≥ 4.3 with ≥ 20 reviews, presence on the directories and associations the engines cite, Bing indexing (`bing_wmt.py`, `indexnow.py`). Not a lever: llms.txt, extra schema, pages written to steer AI answers.
