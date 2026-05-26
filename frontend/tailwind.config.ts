import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        kawn: {
          orange: "#FF6B00",
          black: "#0B0B0B",
          charcoal: "#141414",
          mist: "#1F1F1F",
        },
      },
      boxShadow: {
        glow: "0 0 40px rgba(255, 107, 0, 0.25)",
      },
    },
  },
  plugins: [],
};

export default config;
