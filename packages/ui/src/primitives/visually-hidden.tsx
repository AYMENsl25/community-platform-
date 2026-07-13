import type { ComponentPropsWithRef } from "react";

export function VisuallyHidden({
  className,
  ...props
}: ComponentPropsWithRef<"span">) {
  const classes = ["tq-visually-hidden", className].filter(Boolean).join(" ");
  return <span className={classes} {...props} />;
}
