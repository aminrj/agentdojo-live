/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Slightly warm dark palette to complement the terracotta accent
        ink:    '#0d0b0a',   // warm near-black (body bg)
        canvas: '#141210',   // warm dark card bg
        line:   '#262018',   // warm dark border
        // Molntek brand accent — terracotta
        accent: '#c8553d',
        'accent-dark': '#9e3f2c',
        warn:   '#e8a44a',   // warm amber (hint text)
      },
      fontFamily: {
        // Molntek brand serif for display headings
        display: ['var(--font-display)', 'Georgia', 'serif'],
        // JetBrains Mono for all code and monospace
        mono: ['var(--font-mono)', 'ui-monospace', 'Menlo', 'monospace'],
        // System sans for body
        sans: ['ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
