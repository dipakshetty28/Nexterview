import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/cn";

type Tone = "neutral" | "success" | "warning" | "danger" | "info";
type CardPadding = "sm" | "md" | "lg";
type ActionVariant = "primary" | "secondary" | "ghost" | "danger";

const badgeTones: Record<Tone, string> = {
  neutral: "border-slate-200 bg-slate-100 text-slate-700",
  success: "border-emerald-200 bg-emerald-50 text-emerald-700",
  warning: "border-amber-200 bg-amber-50 text-amber-800",
  danger: "border-rose-200 bg-rose-50 text-rose-700",
  info: "border-sky-200 bg-sky-50 text-sky-700",
};

const metricTone: Record<Tone, string> = {
  neutral: "text-slate-950",
  success: "text-emerald-700",
  warning: "text-amber-700",
  danger: "text-rose-700",
  info: "text-blue-700",
};

const cardPadding: Record<CardPadding, string> = {
  sm: "p-4",
  md: "p-5",
  lg: "p-6",
};

const actionVariants: Record<ActionVariant, string> = {
  primary: "border-blue-700 bg-blue-600 text-white shadow-sm shadow-blue-900/15 hover:bg-blue-700",
  secondary: "border-slate-300 bg-white text-slate-800 shadow-sm hover:border-slate-400 hover:bg-slate-50",
  ghost: "border-transparent bg-transparent text-slate-700 hover:bg-slate-100 hover:text-slate-950",
  danger: "border-rose-600 bg-rose-600 text-white shadow-sm shadow-rose-900/15 hover:bg-rose-700",
};

export function statusTone(status: string | null | undefined): Tone {
  const normalized = (status ?? "").toLowerCase().replace(/\s+/g, "_");
  if (["ready", "active", "reviewed", "passed", "complete", "completed", "approved"].includes(normalized)) {
    return "success";
  }
  if (["submitted", "pending", "started", "review_in_progress", "used"].includes(normalized)) {
    return "warning";
  }
  if (["failed", "error", "deleted", "rejected", "timeout", "tests_failed", "review_failed", "expired", "revoked"].includes(normalized)) {
    return "danger";
  }
  if (["invited", "generated", "scenario_generated", "running", "ready_for_review"].includes(normalized)) {
    return "info";
  }
  return "neutral";
}

function formatStatusLabel(label: string): string {
  return label
    .split(":")
    .map((segment) =>
      segment
        .trim()
        .replace(/[_-]+/g, " ")
        .toLowerCase()
        .replace(/\b\w/g, (letter) => letter.toUpperCase()),
    )
    .join(": ");
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "Not available";
  }
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "Not available";
  }
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}

export function PageHeader({
  title,
  eyebrow,
  description,
  actions,
  meta,
}: {
  title: string;
  eyebrow?: string;
  description?: string;
  actions?: ReactNode;
  meta?: ReactNode;
}) {
  return (
    <header className="relative overflow-hidden rounded-card border border-white/80 bg-white/80 p-5 shadow-panel backdrop-blur lg:p-6">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-blue-600 via-sky-400 to-slate-200" />
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div className="min-w-0">
        {eyebrow ? <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">{eyebrow}</p> : null}
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-slate-950">{title}</h1>
        {meta ? <div className="mt-3 flex flex-wrap items-center gap-2">{meta}</div> : null}
        {description ? <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{description}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap gap-2">{actions}</div> : null}
      </div>
    </header>
  );
}

export function StatusBadge({ label, tone = "neutral" }: { label: string; tone?: Tone }) {
  return (
    <span className={cn("inline-flex h-7 items-center rounded-full border px-2.5 text-xs font-semibold", badgeTones[tone])}>
      {formatStatusLabel(label)}
    </span>
  );
}

export function AppCard({
  children,
  className,
  padding = "md",
}: {
  children: ReactNode;
  className?: string;
  padding?: CardPadding;
}) {
  return (
    <section className={cn("rounded-card border border-white/80 bg-white shadow-panel", cardPadding[padding], className)}>
      {children}
    </section>
  );
}

export function ElevatedCard({
  children,
  className,
  padding = "lg",
}: {
  children: ReactNode;
  className?: string;
  padding?: CardPadding;
}) {
  return (
    <section
      className={cn(
        "rounded-card border border-slate-200/80 bg-white/95 shadow-elevated backdrop-blur",
        cardPadding[padding],
        className,
      )}
    >
      {children}
    </section>
  );
}

export function SoftPanel({
  children,
  className,
  padding = "md",
}: {
  children: ReactNode;
  className?: string;
  padding?: CardPadding;
}) {
  return (
    <section className={cn("rounded-card border border-slate-200 bg-slate-50/90", cardPadding[padding], className)}>
      {children}
    </section>
  );
}

export function SectionHeader({
  title,
  description,
  aside,
}: {
  title: string;
  description?: string;
  aside?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h2 className="text-lg font-semibold text-slate-950">{title}</h2>
        {description ? <p className="mt-1 text-sm leading-6 text-slate-600">{description}</p> : null}
      </div>
      {aside ? <div className="shrink-0">{aside}</div> : null}
    </div>
  );
}

export function MetricCard({
  label,
  value,
  description,
  tone = "neutral",
  icon,
}: {
  label: string;
  value: string | number;
  description?: string;
  tone?: Tone;
  icon?: ReactNode;
}) {
  return (
    <section className="relative min-h-36 overflow-hidden rounded-card border border-white/80 bg-white p-5 shadow-panel">
      <div className={cn("absolute inset-x-0 top-0 h-1", tone === "neutral" ? "bg-slate-200" : badgeTones[tone].split(" ")[1])} />
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
          <p className={cn("mt-3 text-3xl font-semibold tracking-tight", metricTone[tone])}>{value}</p>
        </div>
        {icon ? (
          <span
            aria-hidden="true"
            className={cn(
              "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border text-xs font-bold",
              badgeTones[tone],
            )}
          >
            {icon}
          </span>
        ) : null}
      </div>
      {description ? <p className="mt-3 text-sm leading-5 text-slate-600">{description}</p> : null}
    </section>
  );
}

export const StatCard = MetricCard;

export function EmptyState({
  title,
  description,
  actionHref,
  actionLabel,
  action,
  embedded = false,
}: {
  title: string;
  description: string;
  actionHref?: string;
  actionLabel?: string;
  action?: ReactNode;
  embedded?: boolean;
}) {
  return (
    <section
      className={cn(
        "p-6 text-center",
        !embedded && "rounded-card border border-dashed border-slate-300 bg-white/75 shadow-sm",
      )}
    >
      <div className="mx-auto mb-4 h-10 w-10 rounded-full border border-blue-100 bg-blue-50 shadow-inner" />
      <h2 className="text-base font-semibold text-slate-950">{title}</h2>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-600">{description}</p>
      {actionHref && actionLabel ? (
        <Link
          className="mt-4 inline-flex h-10 items-center justify-center rounded-lg border border-blue-700 bg-blue-600 px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
          href={actionHref}
        >
          {actionLabel}
        </Link>
      ) : null}
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </section>
  );
}

function sanitizeUiMessage(message: string): string {
  return message
    .replace(/\b(OPENAI_API_KEY|GITHUB_TOKEN|JWT_SECRET|DATABASE_URL|REDIS_URL)\s*=\s*[^\s]+/gi, "$1=[redacted]")
    .replace(/\b(postgresql|postgres|redis):\/\/[^\s)]+/gi, "$1://[redacted]")
    .replace(/\bsk-[A-Za-z0-9_-]{16,}/g, "sk-[redacted]")
    .replace(/Traceback \(most recent call last\):[\s\S]*?(?=\n\n|$)/g, "Technical details hidden.");
}

export function LoadingSkeleton({ label = "Loading workspace", rows = 3 }: { label?: string; rows?: number }) {
  return (
    <div className="rounded-card border border-white/80 bg-white p-5 shadow-panel" role="status" aria-live="polite">
      <div className="flex items-center gap-3">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-blue-600" />
        <span className="text-sm font-medium text-slate-700">{label}</span>
      </div>
      <div className="mt-5 grid gap-3">
        {Array.from({ length: rows }).map((_, index) => (
          <div className="grid gap-2" key={index}>
            <div className="h-3 w-1/3 animate-pulse rounded bg-slate-200" />
            <div className="h-10 animate-pulse rounded-lg bg-slate-100" />
          </div>
        ))}
      </div>
    </div>
  );
}

export const LoadingState = LoadingSkeleton;

export function ErrorState({ message }: { message: string }) {
  return (
    <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm leading-6 text-rose-700">
      {sanitizeUiMessage(message)}
    </p>
  );
}

export function InfoTooltip({ content, label = "More information" }: { content: string; label?: string }) {
  return (
    <span className="group relative inline-flex align-middle">
      <span
        aria-label={label}
        role="note"
        tabIndex={0}
        className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-slate-300 bg-white text-[11px] font-bold text-slate-600 shadow-sm transition hover:border-blue-300 hover:text-blue-700"
      >
        i
      </span>
      <span
        className="pointer-events-none absolute bottom-full left-1/2 z-30 mb-2 w-64 -translate-x-1/2 rounded-lg border border-slate-200 bg-slate-950 px-3 py-2 text-xs font-normal leading-5 text-white opacity-0 shadow-elevated transition group-focus-within:opacity-100 group-hover:opacity-100"
        role="tooltip"
      >
        {content}
      </span>
    </span>
  );
}

export function FloatingHint({
  title,
  children,
  tone = "info",
  className,
}: {
  title: string;
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <aside className={cn("rounded-card border bg-white/90 p-4 text-sm shadow-panel", badgeTones[tone], className)}>
      <p className="font-semibold">{title}</p>
      <div className="mt-1 leading-6">{children}</div>
    </aside>
  );
}

export function ActionButton({
  href,
  children,
  variant = "primary",
  className,
  disabled,
  "aria-busy": ariaBusy,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  href?: string;
  variant?: ActionVariant;
}) {
  const classes = cn(
    "inline-flex h-10 items-center justify-center rounded-lg border px-4 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-55",
    actionVariants[variant],
    className,
  );
  const isBusy = ariaBusy === true || ariaBusy === "true";

  if (href) {
    return (
      <Link className={classes} href={href}>
        {children}
      </Link>
    );
  }

  return (
    <button aria-busy={ariaBusy} className={classes} disabled={disabled} {...props}>
      {isBusy ? <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" /> : null}
      {children}
    </button>
  );
}

export function FormSection({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-card border border-slate-200 bg-slate-50/90 p-4">
      <div>
        <h2 className="text-sm font-semibold text-slate-950">{title}</h2>
        {description ? <p className="mt-1 text-sm leading-6 text-slate-600">{description}</p> : null}
      </div>
      <div className="mt-4 grid gap-4">{children}</div>
    </section>
  );
}
