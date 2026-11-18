# Indexing: sitemap, robots.txt, AI crawlers, Bing, IndexNow

## Sitemap

- Only indexable, canonical URLs with status 200. No noindex pages, no redirects, no 404, no thank-you or internal pages.
- `lastmod` from the last real change of the page (git date of the source file), never the build time. Identical dates on every URL are a finding; Google ignores `lastmod` that is not consistently accurate.
- Served as XML. Named in robots.txt with an absolute `Sitemap:` line.
- Template: `templates/site/sitemap.config.mjs` for `@astrojs/sitemap` (filter plus git-based `lastmod`).

## robots.txt

- A 5xx on robots.txt makes Google treat the site as blocked: P1.
- Search crawlers (Googlebot, Bingbot) and search or answer crawlers (OAI-SearchBot, ChatGPT-User, PerplexityBot, Claude-SearchBot, Claude-User, Applebot) must not be blocked. A block is a finding.
- Training crawlers (GPTBot, Google-Extended, CCBot, ClaudeBot, Applebot-Extended and others) are a client decision in `config.ai_bots.training`. The audit reports their rules and does not judge them.
- `Disallow: /api/` is fine; the form handler has nothing to index.

## Google

- Sitemap plus internal links plus Search Console. URL Inspection (2,000 a day per property) shows index status and the canonical Google chose; `regression_guard.py run` reads it from the latest GSC snapshot.
- The Indexing API is for job postings and livestreams only. Never use it for normal pages.

## Bing

Bing feeds ChatGPT search and Copilot. Onboarding verifies the site in Bing Webmaster (import from Search Console), submits the sitemap and installs the IndexNow key. The weekly loop checks that money pages are in Bing's index.

## IndexNow

- Key file `public/<key>.txt` (8 to 128 characters of letters, digits, hyphen) containing only the key: `indexnow.py key --write`.
- After every production change and its live verification: `indexnow.py submit --action <id>` (dry run), then `--execute`. Submit removed URLs too.
- 403 means the key file is not served; 422 means a URL is on another host.
- Google does not use IndexNow. It shortens the time until other engines see a change; it is not a ranking lever.
