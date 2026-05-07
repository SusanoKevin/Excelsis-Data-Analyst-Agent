/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        navy:    '#1a3c5e',
        success: '#00a86b',
        warning: '#f5a623',
        danger:  '#e74c3c',
        accent:  '#3498db',
        surface: '#1e293b',
        border:  '#334155',
      },
    },
  },
  plugins: [],
}
