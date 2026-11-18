# Astro and Vercel: URL rules the audit enforces

## One slash policy, everywhere

| Setting | No trailing slash (TWWA default) | Trailing slash |
|---|---|---|
| `astro.config` `trailingSlash` | `'never'` | `'always'` |
| `astro.config` `build.format` | `'file'` | `'directory'` |
| `vercel.json` `trailingSlash` | `false` | `true` |
| `vercel.json` `cleanUrls` | `true` (else `/seite` does not resolve to `seite.html`) | `true` |

A mismatch produces a 308 on every internal link (`tech.slash.policy_mismatch`, `tech.links.redirect_hop`). Internal links, canonicals, sitemap entries and redirect targets must already be in the final form. `site` must be set in `astro.config`; without it there are no absolute canonicals and no correct sitemap.

## Canonical

- One `<link rel="canonical">` per indexable page, absolute, on the production host, no query string, normalised to the slash policy. `templates/site/components/SeoHead.astro` builds it from `Astro.site` and the path.
- UTM links from the Google profile must canonicalise to the clean URL; the query never reaches the canonical.
- A canonical to another page is allowed only on purpose; the audit marks it as a hypothesis when the target exists and as P2 when it does not.
- www and apex: one host. The other redirects with 308 at Vercel Domains.

## Redirects

- `vercel.json` `redirects` with `permanent: true` (308). Literal sources are checked against the build: target exists, anchor exists, no chain, no loop.
- Relaunch: list every old URL (GSC pages with impressions, old sitemap, linked URLs), map each to the closest new page, never everything to the home page. `site_audit.py redirects --old-urls <file> --from-gsc` reports old URLs that end in a 404.
- Bulk lists (`bulkRedirectsPath`) are for large migrations; no wildcards there.

## Preview hosts

- `*.vercel.app` previews are served with `X-Robots-Tag: noindex` by Vercel.
- A custom preview domain (for example `staging.example.de`) needs an explicit header rule scoped by host: `templates/site/vercel.preview-noindex.json`. List such hosts in `config.site.preview_hosts`; the audit checks the rule (dist) or the live header.

## 404

`src/pages/404.astro` becomes `404.html`, which Vercel serves with status 404. It should carry navigation, phone and a link home, and `noindex`. `site_audit.py live` probes a random path and flags a soft 404.

## Images and first screen

- Hero image: `loading="eager"`, `fetchpriority="high"`, width and height set. Everything below the first screen lazy.
- Remote Google Fonts are a finding (IP transfer to Google, slower); self-host under `public/fonts/`.
- Map embeds only behind a click (two-click solution).

## Fix order

Configuration first (site, slash policy, cleanUrls), then canonicals, then internal links and redirects, then sitemap. Each step is a separate `tech_fix` action unless the changes are one commit that cannot be split.
