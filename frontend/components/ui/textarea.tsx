import type { TextareaHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label: string;
};

export function Textarea({ className, id, label, ...props }: TextareaProps) {
  return (
    <label className="grid gap-2 text-sm text-slate-200" htmlFor={id}>
      <span>{label}</span>
      <textarea
        id={id}
        className={cn(
          "min-h-32 rounded-md border border-slate-700 bg-slate-950 px-3 py-3 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20",
          className,
        )}
        {...props}
      />
    </label>
  );
}
