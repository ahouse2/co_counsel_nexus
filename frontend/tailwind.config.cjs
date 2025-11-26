/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                halo: {
                    bg: '#000000',
                    card: '#0a0a0a',
                    border: '#1a1a1a',
                    text: '#e5e7eb',
                    muted: '#9ca3af',
                    cyan: '#00f0ff',
                    'cyan-dim': 'rgba(0, 240, 255, 0.1)',
                    'cyan-glow': 'rgba(0, 240, 255, 0.5)',
                }
            },
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
                mono: ['JetBrains Mono', 'monospace'],
            },
            animation: {
                'spin-slow': 'spin 20s linear infinite',
                'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
            }
        },
    },
    plugins: [],
}
