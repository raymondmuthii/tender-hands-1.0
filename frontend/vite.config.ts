/**
 * Vite configuration for TanStack Start application
 *
 * Plugins configured:
 * - TanStack Start: SSR framework with file-based routing
 * - React: Fast Refresh and JSX transform
 * - TailwindCSS v4: Utility-first styling with lightning-fast compilation
 * - TypeScript paths: resolves @/ alias to src/ directory
 * - Nitro: production server bundler (targets Cloudflare by default)
 *
 * Dev proxy:
 * - All /api/* requests are forwarded to the Flask backend (VITE_API_URL or localhost:5000)
 */
import { defineConfig, loadEnv } from "vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import tsconfigPaths from "vite-tsconfig-paths";
import { nitro } from "nitro/vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backendUrl = env['VITE_API_URL'] || 'http://localhost:5000';

  return {
    plugins: [
      tsconfigPaths(),
      tanstackStart({
        server: {
          entry: "server",
        },
      }),
      react(),
      tailwindcss(),
      nitro(),
    ],

    server: {
      proxy: {
        // Forward all /api/* calls to Flask in development
        "/api": {
          target: backendUrl,
          changeOrigin: true,
        },
      },
    },
  };
});
