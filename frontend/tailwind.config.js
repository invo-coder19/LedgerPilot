/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // LedgerPilot brand palette — deep navy + electric blue
        brand: {
          50:  '#eef4ff',
          100: '#dce9fe',
          200: '#b9d3fd',
          300: '#85b3fb',
          400: '#4b89f7',
          500: '#2563eb',  // primary
          600: '#1d4ed8',
          700: '#1e40af',
          800: '#1e3a8a',
          900: '#1e3358',
          950: '#172554',
        },
        surface: {
          DEFAULT: '#0f172a',
          card:    '#1e293b',
          border:  '#334155',
          hover:   '#263550',
        },
        // Semantic colours
        success: '#22c55e',
        warning: '#f59e0b',
        danger:  '#ef4444',
        info:    '#38bdf8',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      borderRadius: {
        'xl': '0.75rem',
        '2xl': '1rem',
      },
      boxShadow: {
        card: '0 1px 3px 0 rgb(0 0 0 / 0.4), 0 1px 2px -1px rgb(0 0 0 / 0.4)',
        'card-hover': '0 4px 12px 0 rgb(0 0 0 / 0.4)',
      },
    },
  },
  plugins: [],
}
