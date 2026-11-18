---
name: twwa-gbp
description: Use when working with Google Business Profiles of TWWA or its clients: reading performance, reviews, posts and photos, auditing a profile against the map-pack winners, checking suspension risk, setting up API access, or writing a review reply, post or info edit through the API after approval.
---

# twwa-gbp

Covers TWWA's own profile and every client profile where the signed-in Google user is owner or manager.

If `${CLAUDE_PLUGIN_ROOT}` is empty, the plugin root is two directories above this file. Scripts: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py"` (written below as `<name>.py`). Every script has `--help`; exit 3 = credentials missing (use the fallback it names), exit 4 = blocked by STOP, cap, approval, spend or scope (report it, never work around it).

## Setup (once)

Load `references/gbp-api-setup.md`. Then `gbp.py auth --client-secrets <file>` and `gbp.py locations`. Put each client's `locations/<id>` into its `business.json` (`gbp.location`). Until API access is approved (quota shows 0), use `gbp.py template` and `gbp.py snapshot --from-file`.

## Read and audit

1. `gbp.py snapshot` (one client) or `gbp.py snapshot --all` (agency overview).
2. `gbp.py audit` (fields vs business.json and the pack winners from the latest teardown) and `gbp.py lint` (suspension risk). Load `references/suspension.md` before suggesting any identity change.
3. Turn findings into actions: `gbp_content_edit` (services, hours, description, secondary categories, attributes), `gbp_identity_edit` (primary category, primary phone, website link: both approvals, one per 48 h), `gbp_post` (conversion only, never as a ranking lever), `review_reply`.

## Write (approved actions only)

- Review reply: draft in `drafts/<id>/reply.txt`, `reviews.py reply-lint`, approvals, then `gbp.py reply --action <id> --account ... --location ... --review-id ... --text-file ...` (dry run) and `--execute`.
- Post: localPost JSON in `drafts/<id>/post.json` (German, `languageCode: de`), `legal_lint.py text`, then `gbp.py post ... --execute`.
- Info edit: `gbp.py update --location ... --mask <fields> --body-file ...`. Name, address and pin are refused by the script: those are R3, a human edits them in the profile.
- Every write: `twwa_actions.py verify` passes, pacing ok (`gbp.py pacing`), re-read confirms. Unattended runs never write.
