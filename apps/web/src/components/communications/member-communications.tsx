"use client";

import { useEffect, useState } from "react";
import { translate, type LocaleCode } from "@talaqi/translations";
import { Card } from "@talaqi/ui";

import type { PublishedContent } from "@/lib/api/organizer-client";

export function MemberCommunications({
  kind,
  resourceId,
  locale,
}: {
  kind: "club" | "event";
  resourceId: string;
  locale: LocaleCode;
}) {
  const [items, setItems] = useState<PublishedContent[]>([]);

  useEffect(() => {
    let active = true;
    const resource = kind === "club" ? "clubs" : "events";
    const suffix = kind === "club" ? "announcements" : "updates";
    void fetch(`/api/organizer/api/v1/${resource}/${resourceId}/${suffix}`, {
      cache: "no-store",
      credentials: "include",
    })
      .then(async (response) => (response.ok ? response.json() : { items: [] }))
      .then((page: { items: PublishedContent[] }) => {
        if (active) setItems(page.items);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [kind, resourceId]);

  if (items.length === 0) return null;
  return (
    <Card aria-labelledby={`${kind}-member-communications`}>
      <h2 id={`${kind}-member-communications`}>
        {translate(
          locale,
          kind === "club"
            ? "communications.club.title"
            : "communications.event.title",
        )}
      </h2>
      <ul>
        {items.map((item) => (
          <li key={item.id}>
            <strong>{item.title}</strong>
            <p>{item.body}</p>
          </li>
        ))}
      </ul>
    </Card>
  );
}
