---
name: twwa-reviews
description: Use when a TWWA client needs more, newer or better-answered Google reviews, when review request materials or a §5b UWG review notice are needed, or when a review reply draft must be checked, all within German law.
---

# twwa-reviews

If `${CLAUDE_PLUGIN_ROOT}` is empty, the plugin root is two directories above this file. Scripts: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py"` (written below as `<name>.py`). Every script has `--help`; exit 3 = credentials missing (use the fallback it names), exit 4 = blocked by STOP, cap, approval, spend or scope (report it, never work around it).

Load `references/review-law-de.md` before producing any text.

1. Target: `reviews.py target` (monthly velocity from the pack winners and the client's last 90 days).
2. Assets: `reviews.py assets --action <id>` writes the card, the in-person request and the §5b notice as drafts. They are marked for legal review while `legal.signoff` is false.
3. Electronic requests (e-mail, WhatsApp) only with recorded consent and `legal.review_request_electronic: true`: `reviews.py consent add --ref <Auftragsnummer> --channel ...`. The plugin never sends requests; the owner does.
4. Replies: draft per review (thank, specific, no personal data, no incentive; for criticism: factual, offer contact by phone), `reviews.py reply-lint <file>`, then the GBP write path in skill `twwa-gbp`.
5. Website: if reviews are shown, the §5b notice sits next to them (`legal_lint.py site` checks it).
