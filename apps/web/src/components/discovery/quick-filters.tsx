import type { components } from "@talaqi/api-client";
import {
  translate,
  type LocaleCode,
  type TranslationKey,
} from "@talaqi/translations";

type Metadata = components["schemas"]["DiscoveryMetadataResponse"];
type Values = Record<string, string | undefined>;

function href(values: Values, key: string, value: string): string {
  const params = new URLSearchParams();
  for (const [name, current] of Object.entries(values)) {
    if (name !== "cursor" && current) params.set(name, current);
  }
  if (params.get(key) === value) params.delete(key);
  else params.set(key, value);
  const query = params.toString();
  return query ? `/explore?${query}` : "/explore";
}

export function QuickFilters({
  locale,
  metadata,
  values,
}: {
  locale: LocaleCode;
  metadata: Metadata;
  values: Values;
}) {
  const categoryName = (item: Metadata["categories"][number]) => {
    const fallback = String(item.slug ?? "")
      .replaceAll("-", " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
    const localized = item.name_key
      ? translate(locale, item.name_key as TranslationKey)
      : "";
    return localized || fallback;
  };
  return (
    <nav
      aria-label={translate(locale, "filters.title")}
      className="tq-quick-filters"
    >
      <a
        aria-current={values.price === "free" ? "true" : undefined}
        href={href(values, "price", "free")}
      >
        {translate(locale, "filters.free")}
      </a>
      {metadata.categories
        .filter((category) => category.slug && categoryName(category))
        .slice(0, 6)
        .map((category) => (
          <a
            aria-current={
              values.category === category.slug ? "true" : undefined
            }
            href={href(values, "category", category.slug ?? "")}
            key={category.slug}
          >
            {categoryName(category)}
          </a>
        ))}
    </nav>
  );
}
