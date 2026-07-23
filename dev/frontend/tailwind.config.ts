import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Phase 5 (PathoIntern palette adoption) -- bare brand tokens.
        // teal is the ACCENT value (kept as a 50-900 scale below, derived
        // from this exact hex at 500, so every pre-existing `teal-*`
        // utility class across the app re-themes to the new brand accent
        // without a file-by-file rewrite); navy is the new PRIMARY anchor
        // colour for headers/hero/nav; coral/burnt/light are secondary
        // accents. Never used on a decision-bearing surface (success/
        // warning/danger below are FROZEN and byte-identical -- Phase 3).
        // Phase 6 design decision (PisaPillsafeFindings.md §2/§7): app CHROME
        // (Navbar + BottomTabBar) carries this navy anchor; CONTENT SURFACES
        // (page backgrounds, cards) stay neutral slate by design, not by
        // accident.
        navy: '#1E3A5F',
        coral: '#D64045',
        burnt: '#E76F51',
        light: '#E8EEF2',
        // Teal accent scale, re-derived from #2A9D8F (was #0EA5A0-based) --
        // 500 is the exact brand accent value. Every existing `bg-teal-600`/
        // `text-teal-700`/`border-teal-300`/etc usage across dashboard, auth,
        // and admin pages picks up the new palette automatically.
        teal: {
          50:  '#E9F7F5',
          100: '#C7EBE6',
          200: '#93D6CC',
          300: '#5FC0B2',
          400: '#3BAC9C',
          500: '#2A9D8F',
          600: '#23847A',
          700: '#1C6B63',
          800: '#15514C',
          900: '#0E3835',
        },
        // Remapped to navy (was #0F6E56 green) -- restyles every pre-existing
        // `bg-primary`/`text-primary` usage globally.
        primary: { DEFAULT: '#1E3A5F', light: '#E8EEF2', dark: '#162B47' },
        surface: { DEFAULT: '#FFFFFF', secondary: '#F8F9FA', tertiary: '#F0F4F8' },
        border: { DEFAULT: '#E2E8F0', strong: '#CBD5E0' },
        text: { primary: '#1A202C', secondary: '#4A5568', muted: '#718096' },
        // FROZEN, byte-identical (Phase 3 decision colour semantics --
        // verify=green / abstain=amber / reject=red -- never restyle these).
        success: { bg: '#F0FDF4', text: '#166534', border: '#BBF7D0' },
        warning: { bg: '#FFFBEB', text: '#92400E', border: '#FDE68A' },
        danger: { bg: '#FEF2F2', text: '#991B1B', border: '#FECACA' },
        morning: '#FEF9C3',
        afternoon: '#FEF3C7',
        // Phase 6 palette sweep: these two were literal blue-family hex values
        // (#EFF6FF / #F5F3FF, Tailwind's stock blue-50/violet-50) left over
        // from before the Phase 5 navy/teal system -- currently only consumed
        // by the (unused) TIME_SLOT_PAGE_WASH export in lib/timeOfDay.ts, but
        // fixed here too so no on-brand token silently carries an off-brand
        // hex value. evening now matches the rose family used by
        // schedule-badge-evening; night matches the `light` background token.
        evening: '#FFF1F2',
        night: '#E8EEF2',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        // Auth brand panel + public hero -- navy version (Phase 5).
        'brand-hero':
          'linear-gradient(135deg, #162B47 0%, #1E3A5F 55%, #2A9D8F 140%)',
      },
      animation: {
        'fade-in': 'fadeIn 0.4s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
};

export default config;
