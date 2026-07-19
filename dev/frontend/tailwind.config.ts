import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Keep teal palette — primary brand color
        teal: {
          50:  '#E6FAFA',
          100: '#C0F0EE',
          200: '#81E1DC',
          300: '#42D2CA',
          400: '#1CC3BA',
          500: '#0EA5A0',
          600: '#0B8A86',
          700: '#09706C',
          800: '#065553',
          900: '#033B39',
        },
        // PILLSAFE_BUILD.md Priority 2 design tokens
        primary: { DEFAULT: '#0F6E56', light: '#E6F4F1', dark: '#0A5240' },
        surface: { DEFAULT: '#FFFFFF', secondary: '#F8F9FA', tertiary: '#F0F4F8' },
        border: { DEFAULT: '#E2E8F0', strong: '#CBD5E0' },
        text: { primary: '#1A202C', secondary: '#4A5568', muted: '#718096' },
        success: { bg: '#F0FDF4', text: '#166534', border: '#BBF7D0' },
        warning: { bg: '#FFFBEB', text: '#92400E', border: '#FDE68A' },
        danger: { bg: '#FEF2F2', text: '#991B1B', border: '#FECACA' },
        morning: '#FEF9C3',
        afternoon: '#FEF3C7',
        evening: '#EFF6FF',
        night: '#F5F3FF',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        // Auth brand panel — soft teal gradient (replaces old dark navy)
        'brand-hero':
          'linear-gradient(135deg, #09706C 0%, #0B8A86 50%, #0EA5A0 100%)',
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
