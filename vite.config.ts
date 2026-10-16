/**
 * Vite configuration for TanStack Start application
 *
 * Plugins configured:
 * - TanStack Start: SSR framework with file-based routing
 * - React: Fast Refresh and JSX transform
 * - TailwindCSS v4: Utility-first styling with lightning-fast compilation
 * - TypeScript paths: resolves @/ alias to src/ directory
 * - Nitro: production server bundler (targets Cloudflare by default)
 */
import { defineConfig } from "vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import tsconfigPaths from "vite-tsconfig-paths";
import { nitro } from "nitro/vite";

export default defineConfig({
  plugins: [
    // TypeScript path resolution - must come first
    tsconfigPaths(),
    // TanStack Start - SSR and routing
    tanstackStart({
      server: {
        // Use custom server entry point (src/server.ts) for enhanced SSR error handling
        entry: "server",
      },
    }),
    // React with Fast Refresh
    react(),
    // TailwindCSS v4 - automatically processes @import "tailwindcss" in CSS
    tailwindcss(),
    // Nitro - bundles the server for production deployment
    // Targets Cloudflare by default; auto-detects Vercel/Netlify/etc via NITRO_PRESET
    nitro(),
  ],
});
