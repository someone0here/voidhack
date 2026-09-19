import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        dossier: {
          ground: '#0F172A',
          surface: '#1E293B',
          border: '#334155',
          amber: '#F59E0B',
          crimson: '#EF4444',
          cyan: '#06B6D4',
          readout: '#F8FAFC',
          muted: '#94A3B8',
        },
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          'Helvetica',
          'Arial',
          'sans-serif',
        ],
        mono: [
          'ui-monospace',
          'SFMono-Regular',
          'Menlo',
          'Monaco',
          'Consolas',
          'monospace',
        ],
      },
    },
  },
  plugins: [],
} satisfies Config;
