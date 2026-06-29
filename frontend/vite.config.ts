import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/auth": "http://127.0.0.1:8000",
      "/me": "http://127.0.0.1:8000",
      "/documents": "http://127.0.0.1:8000",
      "/chat": "http://127.0.0.1:8000",
      "/search": "http://127.0.0.1:8000",
      "/ws": {
        target: "ws://127.0.0.1:8000",
        ws: true
      }
    }
  }
});
