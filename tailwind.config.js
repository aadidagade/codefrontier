/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: '#080C14',
          subtle: '#0D1322',
          light: '#F8FAFC',
          'light-subtle': '#F1F5F9'
        },
        surface: {
          DEFAULT: '#0F172A',
          card: '#111A2E',
          elevated: '#17223B',
          hover: '#1D2A47',
          light: '#FFFFFF',
          'light-card': '#FFFFFF',
          'light-elevated': '#F8FAFC',
          'light-hover': '#F1F5F9',
        },
        border: {
          DEFAULT: '#1E293B',
          subtle: 'rgba(255, 255, 255, 0.08)',
          highlight: 'rgba(99, 102, 241, 0.3)',
          light: '#E2E8F0',
          'light-subtle': '#E2E8F0',
        },
        brand: {
          50: '#EEF2FF',
          100: '#E0E7FF',
          200: '#C7D2FE',
          300: '#A5B4FC',
          400: '#818CF8',
          500: '#6366F1', // Electric indigo
          600: '#4F46E5',
          700: '#4338CA',
          800: '#3730A3',
          900: '#312E81',
          accent: '#8B5CF6', // Electric violet
          cyan: '#06B6D4',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Menlo', 'monospace'],
      },
      boxShadow: {
        'subtle': '0 1px 2px 0 rgba(0, 0, 0, 0.25)',
        'card': '0 4px 20px -2px rgba(0, 0, 0, 0.35)',
        'glow': '0 0 25px -5px rgba(99, 102, 241, 0.25)',
        'glow-accent': '0 0 30px -5px rgba(139, 92, 246, 0.3)',
        'glow-cyan': '0 0 25px -5px rgba(6, 182, 212, 0.25)',
      },
      animation: {
        'pulse-subtle': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'shimmer': 'shimmer 2.5s infinite linear',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
    },
  },
  plugins: [],
}
