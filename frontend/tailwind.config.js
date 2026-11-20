/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        canvas: '#120a1f',                    // deep violet-black base
        surface: 'rgba(255,255,255,0.05)',    // glass panels
        raised: 'rgba(32,18,48,0.88)',        // menus and dropdowns
        line: 'rgba(255,255,255,0.12)',       // glass borders
        ink: '#f3eefa',
        mute: '#b3a7c7',
        // "gold" is now a soft rose accent (kept the name so no other file changes)
        gold: { DEFAULT: '#f0a6c0', soft: '#f7c6d8', dim: '#b4607f' },
      },
      fontFamily: {
        serif: ['Georgia', 'Cambria', '"Times New Roman"', 'serif'],
      },
      boxShadow: {
        soft: '0 8px 32px rgba(10,4,24,0.45)',
      },
    },
  },
  plugins: [],
}