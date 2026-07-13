import type { ComponentPropsWithRef } from "react";

type StackProps = ComponentPropsWithRef<"div"> & {
  gap?: "small" | "medium" | "large";
};

export function Stack({ className, gap = "medium", ...props }: StackProps) {
  const classes = ["tq-stack", className].filter(Boolean).join(" ");
  return <div className={classes} data-gap={gap} {...props} />;
}
