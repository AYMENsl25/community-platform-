/* eslint-disable @next/next/no-img-element -- the optimizer cache can outlive
 * event eligibility; this route keeps the revocation-aware cache boundary. */

import "./discovery.css";

const demoCovers: Record<string, string> = {
  "33333333-3333-4333-8333-333333333301": "/demo/events/pottery-workshop.webp",
  "33333333-3333-4333-8333-333333333302": "/demo/events/balat-photo-walk.webp",
  "33333333-3333-4333-8333-333333333303": "/demo/events/algiers-sketchbook-cafe.webp",
  "33333333-3333-4333-8333-333333333304": "/demo/events/bosphorus-yoga.webp",
};

export function CanonicalCover({
  mediaId,
  alt,
}: {
  mediaId: string | null;
  alt: string;
}) {
  const source = mediaId
    ? `/api/media/${encodeURIComponent(mediaId)}`
    : process.env.NODE_ENV === "development"
      ? "/demo/community-gathering.png"
      : null;
  if (!source) return null;
  return (
    <img
      className="tq-discovery-cover"
      src={source}
      alt={alt}
      width={1200}
      height={675}
      loading="lazy"
      decoding="async"
    />
  );
}
