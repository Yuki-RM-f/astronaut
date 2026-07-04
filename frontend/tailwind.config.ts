import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./src/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: "#172026",
        mist: "#f5f7f4",
        pine: "#0f766e",
        clay: "#b45309",
        memoryCream: "#fff7ec",
        memoryPaper: "#fff3df",
        memoryWarm: "#ffe4ca",
        memorySun: "#f59e5b",
        memoryAccent: "#e76f3c",
        memoryAccentDark: "#c9552d",
        memoryText: "#3b241b",
        memoryLine: "#e8c9aa",
        memoryGlow: "#ffd7a8"
      },
      boxShadow: {
        soft: "0 14px 36px rgba(96, 47, 22, 0.10)",
        warm: "0 20px 50px rgba(194, 91, 42, 0.24)",
        memory: "0 28px 80px rgba(67, 35, 18, 0.18)"
      },
      fontFamily: {
        serif: [
          "Noto Serif SC",
          "Songti SC",
          "STSong",
          "SimSun",
          "ui-serif",
          "Georgia",
          "serif"
        ]
      }
    }
  },
  plugins: []
};

export default config;
