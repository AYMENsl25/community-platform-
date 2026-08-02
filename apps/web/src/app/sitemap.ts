import type { MetadataRoute } from "next";
import { LOCALE_CODES } from "@talaqi/translations";
import { createPublicClient } from "@/lib/api/public-client";

export const revalidate = 300;

function publicUrl(path: string): string {
  return new URL(
    path,
    process.env.WEB_PUBLIC_URL ?? "http://localhost:3000",
  ).toString();
}

function languages(path: string): Record<string, string> {
  return Object.fromEntries(
    LOCALE_CODES.map((locale) => [
      locale,
      publicUrl(`${path}?locale=${locale}`),
    ]),
  );
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const client = createPublicClient({
    baseUrl: process.env.API_PUBLIC_URL ?? "http://localhost:8000",
  });
  const [events, clubs] = await Promise.all([
    client.listEvents({ limit: 50 }),
    client.listClubs({ limit: 50 }),
  ]);
  const entries: MetadataRoute.Sitemap = [
    {
      url: publicUrl("/"),
      changeFrequency: "daily",
      priority: 1,
      alternates: { languages: languages("/") },
    },
    {
      url: publicUrl("/explore"),
      changeFrequency: "hourly",
      priority: 0.9,
      alternates: { languages: languages("/explore") },
    },
  ];
  if (events.ok)
    entries.push(
      ...events.data.items.map((event) => ({
        url: publicUrl(`/events/${event.id}`),
        changeFrequency: "daily" as const,
        priority: 0.8,
        alternates: { languages: languages(`/events/${event.id}`) },
      })),
    );
  if (clubs.ok)
    entries.push(
      ...clubs.data.items.map((club) => ({
        url: publicUrl(`/clubs/${club.slug}`),
        changeFrequency: "weekly" as const,
        priority: 0.7,
        alternates: { languages: languages(`/clubs/${club.slug}`) },
      })),
    );
  return entries;
}
