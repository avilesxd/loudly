import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://avilesxd.github.io/loudly',
  base: '/loudly',
  output: 'static',
  integrations: [sitemap()],
});
