import type { ComponentPropsWithRef } from "react";

export function Container({
  className,
  ...props
}: ComponentPropsWithRef<"div">) {
  const classes = ["tq-container", className].filter(Boolean).join(" ");
  return <div className={classes} {...props} />;
}
