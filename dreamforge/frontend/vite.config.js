import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Прокси на бэкенд в дев-режиме.
// allowedHosts разрешает открывать Vite через ngrok.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    allowedHosts: [
      "boring-magnolia-yearbook.ngrok-free.dev",
    ],
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/uploads": "http://127.0.0.1:8000",
    },
  },
});