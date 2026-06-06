import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        app: {
          bg: "rgb(var(--app-bg) / <alpha-value>)",
          card: "rgb(var(--card-bg) / <alpha-value>)",
          elevated: "rgb(var(--card-elevated) / <alpha-value>)",
          border: "rgb(var(--border-color) / <alpha-value>)",
          ink: "rgb(var(--text-primary) / <alpha-value>)",
          muted: "rgb(var(--text-muted) / <alpha-value>)",
          subtle: "rgb(var(--text-subtle) / <alpha-value>)",
        },
        accent: {
          DEFAULT: "rgb(var(--accent-primary) / <alpha-value>)",
          soft: "rgb(var(--accent-soft) / <alpha-value>)",
          ink: "rgb(var(--accent-ink) / <alpha-value>)",
        },
        status: {
          success: "rgb(var(--success) / <alpha-value>)",
          warning: "rgb(var(--warning) / <alpha-value>)",
          danger: "rgb(var(--danger) / <alpha-value>)",
          info: "rgb(var(--info) / <alpha-value>)",
        },
      },
      borderRadius: {
        card: "var(--radius-card)",
      },
      boxShadow: {
        panel: "var(--shadow-panel)",
        elevated: "var(--shadow-elevated)",
        focus: "0 0 0 3px rgb(var(--focus-ring) / 0.32)",
      },
    },
  },
  plugins: [],
};

export default config;
