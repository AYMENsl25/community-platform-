import type { ComponentPropsWithRef } from "react";

type ButtonProps = ComponentPropsWithRef<"button"> & {
  variant?: "primary" | "secondary" | "quiet";
};

export function Button({
  className,
  variant = "primary",
  type = "button",
  ...props
}: ButtonProps) {
  const classes = ["tq-button", `tq-button--${variant}`, className]
    .filter(Boolean)
    .join(" ");

  return <button className={classes} type={type} {...props} />;
}
