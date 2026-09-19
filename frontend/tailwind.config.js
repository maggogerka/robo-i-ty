/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#142536",
        navy: "#073b5c",
        teal: "#05a89d",
        mist: "#edf7f6"
      },
      fontFamily: { sans: ["Inter", "Segoe UI", "Arial", "sans-serif"] },
      boxShadow: { card: "0 18px 50px rgba(17, 45, 65, 0.08)" }
    }
  },
  plugins: []
};

