"use client";

import { useEffect, useState } from "react";

import { cn } from "@/lib/cn";

type CoachMarkTone = "light" | "dark";
type CoachMarkArrow = "top" | "right" | "bottom" | "left" | "none";

const STORAGE_PREFIX = "nexterview.coachMark.";

const arrowClasses: Record<Exclude<CoachMarkArrow, "none">, string> = {
  top: "-top-1.5 left-8 border-l border-t",
  right: "-right-1.5 top-5 border-r border-t",
  bottom: "-bottom-1.5 left-8 border-b border-r",
  left: "-left-1.5 top-5 border-b border-l",
};

export function CoachMark({
  id,
  title,
  description,
  arrow = "none",
  tone = "light",
  className,
}: {
  id: string;
  title: string;
  description: string;
  arrow?: CoachMarkArrow;
  tone?: CoachMarkTone;
  className?: string;
}) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    try {
      setIsVisible(window.localStorage.getItem(`${STORAGE_PREFIX}${id}`) !== "dismissed");
    } catch {
      setIsVisible(true);
    }
  }, [id]);

  function dismiss() {
    setIsVisible(false);
    try {
      window.localStorage.setItem(`${STORAGE_PREFIX}${id}`, "dismissed");
    } catch {
      // Dismissal still applies for the current page when storage is unavailable.
    }
  }

  if (!isVisible) {
    return null;
  }

  const isDark = tone === "dark";

  return (
    <aside
      aria-label={`${title} guidance`}
      className={cn(
        "relative flex items-start gap-3 rounded-lg border px-3 py-2.5 shadow-sm",
        isDark
          ? "border-blue-800/80 bg-blue-950/65 text-blue-50"
          : "border-blue-200 bg-blue-50/95 text-slate-800",
        className,
      )}
    >
      {arrow !== "none" ? (
        <span
          aria-hidden="true"
          className={cn(
            "absolute h-3 w-3 rotate-45",
            isDark ? "border-blue-800/80 bg-blue-950" : "border-blue-200 bg-blue-50",
            arrowClasses[arrow],
          )}
        />
      ) : null}
      <span
        aria-hidden="true"
        className={cn(
          "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[10px] font-bold",
          isDark ? "border-blue-700 bg-blue-900 text-blue-100" : "border-blue-200 bg-white text-blue-700",
        )}
      >
        i
      </span>
      <div className="min-w-0 flex-1">
        <p className={cn("text-xs font-semibold", isDark ? "text-blue-100" : "text-slate-900")}>{title}</p>
        <p className={cn("mt-0.5 text-xs leading-5", isDark ? "text-blue-200" : "text-slate-600")}>{description}</p>
      </div>
      <button
        aria-label={`Dismiss ${title} guidance`}
        className={cn(
          "flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-xs font-bold transition",
          isDark ? "text-blue-300 hover:bg-blue-900 hover:text-white" : "text-slate-500 hover:bg-white hover:text-slate-900",
        )}
        onClick={dismiss}
        type="button"
      >
        x
      </button>
    </aside>
  );
}
