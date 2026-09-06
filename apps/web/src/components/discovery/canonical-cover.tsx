/* eslint-disable @next/next/no-img-element -- the optimizer cache can outlive
 * event eligibility; this route keeps the revocation-aware cache boundary. */

import "./discovery.css";

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
