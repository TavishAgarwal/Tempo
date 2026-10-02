/** Theme reads only design tokens from src/styles/tokens.css. */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: ["class", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)", surface: "var(--surface)", raised: "var(--raised)", rule: "var(--rule)", border: "var(--border)", text: "var(--text)",
        muted: "var(--text-muted)", primary: "var(--primary)", success: "var(--success)",
        warning: "var(--warning)", danger: "var(--danger)",
      },
      borderRadius: { DEFAULT: "2px", sm: "1px", md: "2px", lg: "2px", xl: "2px", "2xl": "3px", full: "9999px" },
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"], mono: ["JetBrains Mono", "ui-monospace", "monospace"] },
      fontSize: { xs: "12px", sm: "14px", base: "16px", xl: "20px", "3xl": "28px" },
    },
  },
};
