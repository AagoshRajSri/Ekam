import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f5f7ff',
          100: '#ebf0fe',
          200: '#d6e0fd',
          300: '#b3c7fc',
          400: '#8ba7f9',
          500: '#6383f6',
          600: '#4763eb',
          700: '#344ad5',
          800: '#2c3eb0',
          900: '#28378c',
        },
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { transform: 'scale(1)', opacity: '0.8', filter: 'blur(20px)' },
          '50%': { transform: 'scale(1.15)', opacity: '1', filter: 'blur(30px)' },
        },
        speakingWave: {
          '0%, 100%': { transform: 'scale(1)', boxShadow: '0 0 30px rgba(99, 131, 246, 0.6)' },
          '50%': { transform: 'scale(1.08)', boxShadow: '0 0 60px rgba(139, 92, 246, 0.8)' },
        },
      },
      animation: {
        'pulse-glow': 'pulseGlow 3s ease-in-out infinite',
        'speaking-wave': 'speakingWave 1.2s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};

export default config;

