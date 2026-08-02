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
  if (!mediaId) return null;
  return (
    <img
      className="tq-discovery-cover"
      src={`/api/media/${encodeURIComponent(mediaId)}`}
      alt={alt}
      width={1200}
      height={675}
      loading="lazy"
      decoding="async"
    />
  );
}
