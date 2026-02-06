import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Cores do logo Iconsai
        'logo-gray': '#D1D5DB',
        'logo-red': '#EF4444',
        'logo-orange': '#F97316',
        // Fundos escuros recomendados
        'bg-dark': '#0a0e1a',
        'bg-darker': '#0f1629',
        'bg-purple': '#1a1a2e',
      },
    },
  },
  plugins: [],
}

export default config
