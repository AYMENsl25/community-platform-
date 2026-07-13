import type { ComponentPropsWithRef } from "react";

type ActionLinkProps = ComponentPropsWithRef<"a"> & {
  variant?: "primary" | "secondary" | "quiet";
};

export function ActionLink({
  className,
  variant = "primary",
  ...props
}: ActionLinkProps) {
  const classes = ["tq-action-link", `tq-action-link--${variant}`, className]
    .filter(Boolean)
    .join(" ");

  return <a className={classes} {...props} />;
}
