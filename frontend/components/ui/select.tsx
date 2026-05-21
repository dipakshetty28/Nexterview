import type { SelectHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
};

export function Select({ children, className, id, label, ...props }: SelectProps) {
  return (
    <label className="grid gap-2 text-sm text-slate-200" htmlFor={id}>
      <span>{label}</span>
      <select
        id={id}
        className={cn(
          "h-11 rounded-md border border-slate-700 bg-slate-950 px-3 text-slate-100 outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20",
          className,
        )}
        {...props}
      >
        {children}
      </select>
    </label>
  );
}
