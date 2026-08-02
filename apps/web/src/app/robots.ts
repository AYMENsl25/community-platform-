import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  const baseUrl = (
    process.env.WEB_PUBLIC_URL ?? "http://localhost:3000"
  ).replace(/\/$/, "");
  return {
    rules: {
      userAgent: "*",
      allow: ["/", "/api/media/"],
      disallow: ["/admin/", "/organizer/", "/api/"],
    },
    sitemap: `${baseUrl}/sitemap.xml`,
  };
}
