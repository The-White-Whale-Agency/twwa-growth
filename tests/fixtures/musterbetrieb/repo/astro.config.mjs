import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://www.musterbetrieb.example',
  output: 'static',
  trailingSlash: 'never',
  build: { format: 'file', inlineStylesheets: 'auto' },
});
