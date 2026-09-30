import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        swiss: {
          ink: "#0A120E",
          cream: "#F4F3EF",
          slate: "#64746B",
          glass: "rgba(244, 243, 239, 0.82)",
          glassDark: "rgba(10, 18, 14, 0.82)",
        },
      },
      borderRadius: {
        macos: "12px",
      },
    },
  },
  plugins: [],
};

export default config;