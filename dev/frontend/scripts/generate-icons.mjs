#!/usr/bin/env node
/**
 * Phase 5 -- generates favicon/PWA icon PNGs from the SA-prepared
 * `public/logo-mark.png` (400x400, transparent, mark only). Never
 * regenerate from `MyPillSafe_Logo.png` (the original source asset --
 * keep it untouched and unreferenced in code) or `logo.png` (the full
 * wordmark lockup -- wrong aspect ratio for a square icon).
 *
 * Outputs (written to public/, uncommitted like every other Phase 5 file):
 *   favicon-32.png        32x32,   transparent
 *   apple-touch-icon.png  180x180, transparent
 *   pwa-192.png           192x192, transparent
 *   pwa-512.png           512x512, transparent
 *   pwa-maskable-512.png  512x512, mark scaled to ~78% centered on WHITE
 *                          (#FFFFFF) -- the maskable safe zone. The mark's
 *                          linework is navy, so per the Builder Briefing's
 *                          dark-surface rule it must sit on white here,
 *                          never navy.
 *
 * Run with: node scripts/generate-icons.mjs  (or `npm run generate-icons`)
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PUBLIC_DIR = path.resolve(__dirname, '../public');
const SOURCE = path.join(PUBLIC_DIR, 'logo-mark.png');

const PLAIN_TARGETS = [
  { file: 'favicon-32.png', size: 32 },
  { file: 'apple-touch-icon.png', size: 180 },
  { file: 'pwa-192.png', size: 192 },
  { file: 'pwa-512.png', size: 512 },
];

async function generatePlain({ file, size }) {
  const outPath = path.join(PUBLIC_DIR, file);
  await sharp(SOURCE)
    .resize(size, size, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } })
    .png()
    .toFile(outPath);
  console.log(`  wrote ${file} (${size}x${size}, transparent)`);
}

async function generateMaskable() {
  const size = 512;
  const markSize = Math.round(size * 0.78);
  const outPath = path.join(PUBLIC_DIR, 'pwa-maskable-512.png');

  const mark = await sharp(SOURCE)
    .resize(markSize, markSize, { fit: 'contain', background: { r: 255, g: 255, b: 255, alpha: 0 } })
    .toBuffer();

  const offset = Math.round((size - markSize) / 2);

  await sharp({
    create: {
      width: size,
      height: size,
      channels: 4,
      // White, not navy -- the mark's linework is navy (Builder Briefing
      // dark-surface rule: navy-on-navy is unreadable).
      background: { r: 255, g: 255, b: 255, alpha: 1 },
    },
  })
    .composite([{ input: mark, left: offset, top: offset }])
    .png()
    .toFile(outPath);

  console.log('  wrote pwa-maskable-512.png (512x512, mark @78% centered on white)');
}

async function main() {
  console.log(`Generating icons from ${SOURCE}`);
  for (const target of PLAIN_TARGETS) {
    await generatePlain(target);
  }
  await generateMaskable();
  console.log('Done.');
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
