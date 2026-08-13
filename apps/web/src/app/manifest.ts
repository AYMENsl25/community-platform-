import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Talaqi",
    short_name: "Talaqi",
    description: "Discover communities and events with Talaqi.",
    start_url: "/",
    display: "standalone",
    background_color: "#fffaf4",
    theme_color: "#166b5c",
    icons: [
      {
        src: "/brand/talaqi-pwa-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/brand/talaqi-pwa-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "maskable",
      },
      {
        src: "/brand/talaqi-pwa-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/brand/talaqi-pwa-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
