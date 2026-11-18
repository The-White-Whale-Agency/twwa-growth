// twwa-growth sitemap settings for @astrojs/sitemap.
// Usage in astro.config.mjs:
//   import sitemap from '@astrojs/sitemap';
//   import { sitemapOptions } from './sitemap.config.mjs';
//   export default defineConfig({ site: 'https://www.musterbetrieb.example', integrations: [sitemap(sitemapOptions)] });
//
// - filter: only indexable canonical URLs (no thank-you, internal, legal-noindex or 404 pages)
// - lastmod: the last git commit date of the page's source file, never the build time
import { execFileSync } from 'node:child_process';
import { existsSync } from 'node:fs';

// Paths that must never appear in the sitemap. Add every page that renders noindex.
const EXCLUDE = [/\/404\/?$/, /\/danke\/?$/, /\/intern(\/|$)/, /\?/];

function sourceFor(pathname) {
  const clean = pathname.replace(/\/+$/, '') || '/index';
  const stem = clean === '/index' || clean === '' ? 'index' : clean.replace(/^\//, '');
  for (const ext of ['.astro', '.md', '.mdx']) {
    for (const cand of [`src/pages/${stem}${ext}`, `src/pages/${stem}/index${ext}`]) {
      if (existsSync(cand)) return cand;
    }
  }
  return null;
}

function gitDate(file) {
  try {
    const out = execFileSync('git', ['log', '-1', '--format=%cI', '--', file], { encoding: 'utf8' }).trim();
    return out || undefined;
  } catch {
    return undefined;
  }
}

export const sitemapOptions = {
  filter: (page) => !EXCLUDE.some((re) => re.test(page)),
  serialize(item) {
    const file = sourceFor(new URL(item.url).pathname);
    const lastmod = file ? gitDate(file) : undefined;
    // Without a reliable date, omit lastmod instead of stamping the build time.
    if (lastmod) item.lastmod = lastmod;
    else delete item.lastmod;
    delete item.changefreq;
    delete item.priority;
    return item;
  },
};
