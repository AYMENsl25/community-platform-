import type { ComponentPropsWithRef } from "react";

export function SkipLink({ className, ...props }: ComponentPropsWithRef<"a">) {
  const classes = ["tq-skip-link", className].filter(Boolean).join(" ");
  return <a className={classes} {...props} />;
}
