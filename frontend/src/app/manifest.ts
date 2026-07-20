import type { MetadataRoute } from "next";

// PWA web app manifest (Stage 8 baseline). Served at /manifest.webmanifest.
// Installable app only — no push, no offline product. background/theme match the
// brand dark (globals.css --background). Icons are real PNGs in /public/icons.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "FINARODA",
    short_name: "FINARODA",
    description: "Decision-support for crypto swing trading. Analysis, not advice.",
    start_url: "/scan",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#0b0d12",
    theme_color: "#0b0d12",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
