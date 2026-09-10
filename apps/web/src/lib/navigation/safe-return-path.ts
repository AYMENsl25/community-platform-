const ALLOWED_RETURN_PATH =
  /^\/(?:$|explore(?:[/?#]|$)|events\/[0-9a-f-]+(?:[?#]|$)|clubs\/[a-z0-9-]+(?:[?#]|$)|overview(?:[?#]|$)|organizer\/(?:overview|clubs|events)(?:[/?#]|$)|admin\/(?:review|audit|operations)(?:[/?#]|$))/i;

export function safeReturnPath(value: string | undefined): string {
  if (!value || value.startsWith("//") || value.includes("\\")) return "/";
  if (/[\u0000-\u001f\u007f]/.test(value) || !ALLOWED_RETURN_PATH.test(value))
    return "/";
  try {
    const parsed = new URL(value, "https://talaqi.invalid");
    if (parsed.origin !== "https://talaqi.invalid") return "/";
    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    return "/";
  }
}
