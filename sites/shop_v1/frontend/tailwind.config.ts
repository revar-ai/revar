/* SPDX-License-Identifier: Apache-2.0 */
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f5f3ff",
          100: "#ede9fe",
          500: "#7c3aed",
          600: "#6d28d9",
          700: "#5b21b6",
          900: "#3c1361",
        },
      },
    },
  },
  plugins: [],
};

export default config;
