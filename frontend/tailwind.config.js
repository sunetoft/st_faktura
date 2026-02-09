/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#141414",
        paper: "#f7f2e7",
        accent: "#d94f3d",
        lake: "#1b6e6b",
        sand: "#ffe8c2",
        mist: "#d6f1ef",
      },
      boxShadow: {
        soft: "0 10px 30px rgba(20, 20, 20, 0.12)",
      },
      fontFamily: {
        serif: ["\"EB Garamond\"", "Garamond", "Times New Roman", "serif"],
        sans: ["\"Space Grotesk\"", "\"Helvetica Neue\"", "Arial", "sans-serif"],
      },
    },
  },
  plugins: [],
}
