import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          base: "#0A0A0B",
          surface: "#111113",
          elevated: "#18181B",
        },
        cargo: {
          accent: "#10B981",
          "accent-dim": "#059669",
          "accent-muted": "#064E3B",
        },
        border: "#27272A",
        muted: "#71717A",
        text: {
          primary: "#FAFAFA",
          secondary: "#A1A1AA",
        },
        risk: {
          low: "#10B981",
          medium: "#F59E0B",
          high: "#EF4444",
          critical: "#DC2626",
        },
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "DM Mono", "monospace"],
      },
      borderRadius: {
        DEFAULT: "4px",
        sm: "2px",
        md: "4px",
        lg: "4px",
        xl: "4px",
        "2xl": "4px",
        full: "9999px",
      },
      boxShadow: {
        none: "none",
      },
    },
  },
  plugins: [],
};
export default config;
