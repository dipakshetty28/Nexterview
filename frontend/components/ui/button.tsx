import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "icon";
};

const variants = {
  primary: "border border-blue-700 bg-blue-600 text-white shadow-sm shadow-blue-900/15 hover:bg-blue-700",
  secondary: "border border-slate-300 bg-white text-slate-800 shadow-sm hover:border-slate-400 hover:bg-slate-50",
  ghost: "text-slate-700 hover:bg-slate-100 hover:text-slate-950",
  danger: "border border-rose-600 bg-rose-600 text-white shadow-sm shadow-rose-900/15 hover:bg-rose-700",
  icon: "border border-slate-300 bg-white text-slate-700 shadow-sm hover:border-slate-400 hover:bg-slate-50",
};

export function Button({
  className,
  variant = "primary",
  children,
  disabled,
  "aria-busy": ariaBusy,
  ...props
}: ButtonProps) {
  const isBusy = ariaBusy === true || ariaBusy === "true";

  return (
    <button
      className={cn(
        "inline-flex h-11 items-center justify-center rounded-lg px-4 text-sm font-semibold outline-none transition disabled:cursor-not-allowed disabled:opacity-55",
        variant === "icon" && "h-10 w-10 px-0",
        variants[variant],
        className,
      )}
      aria-busy={ariaBusy}
      disabled={disabled}
      {...props}
    >
      {isBusy ? <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" /> : null}
      {children}
    </button>
  );
}
