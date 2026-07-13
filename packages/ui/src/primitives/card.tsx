import type { ComponentPropsWithRef } from "react";

export function Card({
  className,
  ...props
}: ComponentPropsWithRef<"section">) {
  const classes = ["tq-card", className].filter(Boolean).join(" ");
  return <section className={classes} {...props} />;
}
