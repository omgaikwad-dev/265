/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#006699',
          dark: '#004d73',
          light: '#0088cc',
          50: '#f0f7fb',
          100: '#e0eff7',
          500: '#006699',
          600: '#005580',
          700: '#004466',
        },
        secondary: {
          DEFAULT: '#EAF4FA',
          hover: '#d8eaf5',
        },
        surface: '#FFFFFF',
        background: '#F5F8FC',
        textMain: '#172B4D',
        success: '#16865B',
        warning: '#D99124',
        danger: '#D64545',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      boxShadow: {
        subtle: '0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.1)',
        card: '0 4px 6px -1px rgba(0, 102, 153, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.04)',
        elevated: '0 10px 15px -3px rgba(0, 102, 153, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.03)',
      }
    },
  },
  plugins: [],
}
