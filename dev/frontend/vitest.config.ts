import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

// Standalone from vite.config.ts on purpose (MPR1-T07) -- this project had no
// frontend test runner before this file (see scripts/check-i18n.mjs's own
// comment to that effect). Keeping the PWA/manifest-heavy vite.config.ts
// untouched avoids dragging vite-plugin-pwa's build-time asset generation
// into every test run; the `@` alias is duplicated here to match it.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
});
