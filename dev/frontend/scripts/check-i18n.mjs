#!/usr/bin/env node
/**
 * i18n guard -- two independent checks, one exit code.
 *
 *   1. KEY PARITY   en.json and fr.json must expose exactly the same key
 *                   paths, and any array must be the same length in both.
 *                   Catches the classic drift where a key is added to one
 *                   locale and the other silently falls back to English.
 *
 *   2. HARDCODED COPY   No user-visible literal may sit in a .tsx file.
 *                   Catches the gap this script was written for: whole
 *                   pages that were never wired to i18n at all, which key
 *                   parity cannot see because the strings were never keys.
 *
 * Run: `npm run check:i18n` (exit 0 = clean, 1 = findings).
 *
 * WHY A SCRIPT AND NOT AN ESLINT RULE: this project has no eslint install
 * and no frontend test runner. Adding a linter, a config and a plugin chain
 * to enforce one rule was more risk than the rule is worth, so the check is
 * a zero-dependency node script instead. It is intentionally conservative:
 * it would rather miss an odd literal than cry wolf on every build.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, relative, sep } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = join(ROOT, 'src');
const LOCALES = join(SRC, 'i18n', 'locales');

const problems = [];

/* ── 1. Key parity ─────────────────────────────────────────────────── */

/** Flattens to "a.b.c" paths; arrays become one path plus a length marker. */
function paths(node, prefix = '', out = new Map()) {
  if (Array.isArray(node)) {
    out.set(prefix, `array[${node.length}]`);
    return out;
  }
  if (node && typeof node === 'object') {
    for (const [k, v] of Object.entries(node)) {
      paths(v, prefix ? `${prefix}.${k}` : k, out);
    }
    return out;
  }
  out.set(prefix, 'leaf');
  return out;
}

const en = JSON.parse(readFileSync(join(LOCALES, 'en.json'), 'utf8'));
const fr = JSON.parse(readFileSync(join(LOCALES, 'fr.json'), 'utf8'));
const enPaths = paths(en);
const frPaths = paths(fr);

for (const [p, kind] of enPaths) {
  if (!frPaths.has(p)) problems.push(`[key-parity] missing in fr.json: ${p}`);
  else if (frPaths.get(p) !== kind) {
    problems.push(`[key-parity] shape differs at ${p}: en=${kind} fr=${frPaths.get(p)}`);
  }
}
for (const p of frPaths.keys()) {
  if (!enPaths.has(p)) problems.push(`[key-parity] missing in en.json: ${p}`);
}

/* ── 2. Hardcoded user-visible copy ────────────────────────────────── */

// Files with no user-facing copy by construction: bootstrap, routing tables,
// and unstyled UI primitives that render only their children.
const EXEMPT_FILES = new Set(
  [
    'main.tsx',
    'App.tsx',
    'router/index.tsx',
    'components/ui/Button.tsx',
    'components/ui/Card.tsx',
    'components/ui/Input.tsx',
    'components/ui/Alert.tsx',
    'components/ui/SectionHeader.tsx',
    'components/ui/StatCard.tsx',
    'components/ui/LoadingSkeleton.tsx',
    'components/ui/PasswordField.tsx',
    'components/ui/Logo.tsx',
    'components/layout/PublicLayout.tsx',
    'components/layout/AppShell.tsx',
  ].map((p) => p.split('/').join(sep)),
);

// Literals that are correct in every locale and must never be translated:
// language endonyms, the brand, proper nouns, and bibliographic titles.
const EXEMPT_TEXT = new Set([
  'English',
  'Français',
  'العربية',
  'Español',
  'தமிழ்',
  'MyPillSafe',
  'PillSafe',
  'ML', // technical abbreviation on the admin-only dashboard
  'Muthuraj Jayakumar',
  'Sumanth Reddy',
  'Lohith Reddy',
  'Ali Ozdemir',
  'Abdullah Mohammed',
  'documentation/evaluation/rx_parsing/',
  'NLM Pill Image Recognition Challenge (2016)',
  'ePillID (Usuyama et al., 2020)',
  'GO-PILL (2025)',
  'CIHI — Drug Use Among Seniors in Canada',
]);

function walk(dir, acc = []) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) walk(full, acc);
    else if (entry.endsWith('.tsx')) acc.push(full);
  }
  return acc;
}

/** A candidate is user-visible copy if it reads like a word, not like code. */
function looksLikeCopy(text) {
  const s = text.trim();
  if (s.length < 2) return false;
  if (EXEMPT_TEXT.has(s)) return false;
  if (!/[A-Za-z]{2}/.test(s)) return false; // needs real letters
  if (/^[a-z][a-zA-Z0-9]*$/.test(s)) return false; // bare identifier: `slot`, `onClose`
  if (/[{}()[\]=;`$]|=>|&&|\|\|/.test(s)) return false; // code, not prose
  if (/^\d/.test(s)) return false; // "404", "01"
  return true;
}

for (const file of walk(SRC)) {
  const rel = relative(SRC, file);
  if (EXEMPT_FILES.has(rel)) continue;
  const source = readFileSync(file, 'utf8');

  // Strip comments so explanatory prose in a /* */ block is not "copy".
  const code = source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

  // (a) JSX text nodes: >  some words  <
  // The lookbehind rejects `=>`, so an arrow function returning a generic
  // (`=> Promise<void>`) is not mistaken for the JSX text " Promise ".
  for (const m of code.matchAll(/(?<![=-])>([^<>{}]+)</g)) {
    if (looksLikeCopy(m[1])) {
      problems.push(`[hardcoded] ${rel}: JSX text "${m[1].trim().replace(/\s+/g, ' ').slice(0, 60)}"`);
    }
  }

  // (b) Literal strings in props that render to the user.
  const PROPS = /(?:aria-label|placeholder|title|label|description|message|alt)\s*=\s*"([^"]+)"/g;
  for (const m of code.matchAll(PROPS)) {
    if (looksLikeCopy(m[1])) {
      problems.push(`[hardcoded] ${rel}: prop text "${m[1].slice(0, 60)}"`);
    }
  }
}

/* ── Report ────────────────────────────────────────────────────────── */

if (problems.length > 0) {
  console.error(`i18n check FAILED -- ${problems.length} problem(s):\n`);
  for (const p of problems) console.error(`  ${p}`);
  console.error('\nEvery user-visible string belongs in src/i18n/locales/{en,fr}.json.');
  process.exit(1);
}

console.log(`i18n check passed: ${enPaths.size} keys in EN/FR lockstep, no hardcoded copy found.`);
