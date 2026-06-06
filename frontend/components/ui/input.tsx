import type { InputHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
};

export function Input({ className, id, label, ...props }: InputProps) {
  return (
    <label className="grid gap-2 text-sm text-slate-700" htmlFor={id}>
      <span className="font-medium">{label}</span>
      <input
        id={id}
        className={cn(
          "h-11 rounded-lg border border-slate-300 bg-white px-3 text-slate-950 shadow-sm outline-none transition placeholder:text-slate-400 hover:border-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500",
          className,
        )}
        {...props}
      />
    </label>
  );
}
