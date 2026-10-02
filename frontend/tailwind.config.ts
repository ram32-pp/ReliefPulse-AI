import type { Config } from "tailwindcss";
import defaultTheme from "tailwindcss/defaultTheme";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-geist-sans)', ...defaultTheme.fontFamily.sans],
        mono: ['var(--font-geist-mono)', ...defaultTheme.fontFamily.mono],
        urdu: ['var(--font-urdu)', ...defaultTheme.fontFamily.serif],
      },
      colors: {
        'deep-navy': '#0A0F1C', // Darker background
        'warm-white': '#FFFFFF', // Keeping white for text
        'pulse-red': '#DC2626', // High-contrast critical red
        'pulse-red-glow': '#EF4444', // Intense pulse glow
        'relief-green': '#16A34A', // High-contrast safe relief green
        'amber-alert': '#FF9100', // Neon amber
        'slate-grey': '#8A99AC', 
        'sky-blue': '#00B0FF',
        'glass-panel': 'rgba(255, 255, 255, 0.05)',
        'glass-panel-hover': 'rgba(255, 255, 255, 0.1)',
        'glass-border': 'rgba(255, 255, 255, 0.1)',
      },
      backgroundImage: {
        'radial-dark': 'radial-gradient(circle at top, #141E34 0%, #0A0F1C 100%)',
        'glass-gradient': 'linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.02) 100%)',
      },
      keyframes: {
        pulseHeartbeat: {
          '0%, 100%': { transform: 'scale(1)', opacity: '1', boxShadow: '0 0 20px rgba(255,42,76,0.6), inset 0 0 20px rgba(255,255,255,0.2)' },
          '50%': { transform: 'scale(1.05)', opacity: '0.9', boxShadow: '0 0 50px rgba(255,42,76,0.9), inset 0 0 30px rgba(255,255,255,0.4)' },
        },
        ripple: {
          '0%': { transform: 'scale(0.8)', opacity: '1' },
          '100%': { transform: 'scale(2.5)', opacity: '0' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-5px)' },
        }
      },
      animation: {
        'heartbeat': 'pulseHeartbeat 2s infinite ease-in-out',
        'ripple-fast': 'ripple 1.5s cubic-bezier(0, 0, 0.2, 1) infinite',
        'ripple-slow': 'ripple 2.5s cubic-bezier(0, 0, 0.2, 1) infinite',
        'floating': 'float 4s ease-in-out infinite',
      }
    },
  },
  plugins: [],
};

export default config;
