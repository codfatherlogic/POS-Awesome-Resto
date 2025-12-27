export default {
  content: ["./src/**/*.{vue,js,ts,jsx,tsx,html}"],
  corePlugins: {
    preflight: false, // Disable Tailwind's CSS reset to prevent hiding Frappe's navbar/search
  },
  theme: {
    extend: {},
  },
  plugins: [],
};
