import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Dossier Core Palette
        pine: {
          DEFAULT: '#2E3A2F',
          light: '#3D4D3E',
          dark: '#1F2720',
        },
        sage: {
          DEFAULT: '#6B7F5B',
          light: '#839971',
          dark: '#546447',
        },
        khaki: {
          DEFAULT: '#D9C9B2',
          light: '#E5D9C7',
          dark: '#C7B49B',
        },
        terracotta: {
          DEFAULT: '#C96F4F',
          light: '#D78466',
          // Darkened from #B15A3B: the original only cleared 4.42:1 on cream
          // and 2.95:1 on khaki (fails WCAG AA 4.5:1 for normal text in both
          // cases, since StampBadge/error text renders at 9-11px). This shade
          // holds 6.9:1 on cream and 4.6:1 on khaki.
          dark: '#84432C',
        },
        cream: {
          DEFAULT: '#F8F6EE',
          light: '#FCFBF6',
          dark: '#EFECE0',
        },
        // Evidentiary / Tactical Accents (from CLAUDE.md)
        dossier: {
          ground: '#0F172A',
          surface: '#1E293B',
          border: '#334155',
          amber: '#F59E0B',
          crimson: '#EF4444',
          cyan: '#06B6D4',
          readout: '#F8FAFC',
          muted: '#94A3B8',
          // Palette references
          pine: '#2E3A2F',
          sage: '#6B7F5B',
          khaki: '#D9C9B2',
          terracotta: '#C96F4F',
          cream: '#F8F6EE',
        },
      },
      fontFamily: {
        display: ['Fraunces', 'Georgia', 'serif'],
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          'Helvetica',
          'Arial',
          'sans-serif',
        ],
        mono: [
          '"JetBrains Mono"',
          '"IBM Plex Mono"',
          'ui-monospace',
          'SFMono-Regular',
          'Menlo',
          'Monaco',
          'Consolas',
          'monospace',
        ],
      },
      boxShadow: {
        'paper-sm': '0 1px 2px rgba(46, 58, 47, 0.08), 0 1px 3px rgba(46, 58, 47, 0.06)',
        paper:
          '0 1px 2px rgba(46, 58, 47, 0.08), 0 4px 8px rgba(46, 58, 47, 0.08), 0 12px 24px rgba(46, 58, 47, 0.08)',
        'paper-raised':
          '0 2px 4px rgba(46, 58, 47, 0.08), 0 8px 16px rgba(46, 58, 47, 0.1), 0 20px 36px rgba(46, 58, 47, 0.12)',
        'paper-inset':
          'inset 0 2px 4px rgba(46, 58, 47, 0.12), inset 0 1px 2px rgba(46, 58, 47, 0.08)',
        'paper-inset-focus':
          'inset 0 2px 5px rgba(46, 58, 47, 0.18), inset 0 1px 3px rgba(46, 58, 47, 0.12)',
        stamp: '0 0 0 1px rgba(201, 111, 79, 0.4), inset 0 0 4px rgba(201, 111, 79, 0.15)',
        'stamp-sage':
          '0 0 0 1px rgba(107, 127, 91, 0.4), inset 0 0 4px rgba(107, 127, 91, 0.15)',
      },
    },
  },
  plugins: [],
} satisfies Config;
