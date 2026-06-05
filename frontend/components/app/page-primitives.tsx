import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type Tone = "neutral" | "success" | "warning" | "danger" | "info";

const badgeTones: Record<Tone, string> = {
  neutral: "border-slate-700 bg-slate-900 text-slate-200",
  success: "border-emerald-800 bg-emerald-950/60 text-emerald-200",
  warning: "border-amber-800 bg-amber-950/60 text-amber-200",
  danger: "border-red-800 bg-red-950/60 text-red-200",
  info: "border-cyan-800 bg-cyan-950/60 text-cyan-200",
};

export function statusTone(status: string | null | undefined): Tone {
  const normalized = (status ?? "").toLowerCase();
  if (["ready", "active", "reviewed", "passed", "complete", "completed", "ready_for_review"].includes(normalized)) {
    return "success";
  }
  if (["submitted", "pending", "started", "draft", "review_in_progress", "used"].includes(normalized)) {
    return "warning";
  }
  if (["failed", "error", "deleted", "rejected", "timeout", "tests_failed", "review_failed", "expired", "revoked"].includes(normalized)) {
    return "danger";
  }
  if (["invited", "generated", "running"].includes(normalized)) {
    return "info";
  }
  return "neutral";
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
}: {
  title: string;
  eyebrow?: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div className="min-w-0">
        {eyebrow ? <p className="text-xs font-semibold uppercase tracking-wide text-cyan-300">{eyebrow}</p> : null}
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-50">{title}</h1>
        {description ? <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">{description}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap gap-2">{actions}</div> : null}
    </header>
  );
}

export function StatusBadge({ label, tone = "neutral" }: { label: string; tone?: Tone }) {
  return (
    <span className={cn("inline-flex h-7 items-center rounded-md border px-2.5 text-xs font-medium", badgeTones[tone])}>
      {label}
    </span>
  );
}

export function StatCard({
  label,
  value,
  description,
  tone = "neutral",
}: {
  label: string;
  value: string | number;
  description?: string;
  tone?: Tone;
}) {
  return (
    <section className="rounded-md border border-slate-800 bg-slate-900/70 p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className={cn("mt-2 text-2xl font-semibold text-slate-50", tone === "success" && "text-emerald-300", tone === "warning" && "text-amber-300", tone === "danger" && "text-red-300", tone === "info" && "text-cyan-300")}>
        {value}
      </p>
      {description ? <p className="mt-2 text-sm leading-5 text-slate-500">{description}</p> : null}
    </section>
  );
}

export function EmptyState({
  title,
  description,
  actionHref,
  actionLabel,
}: {
  title: string;
  description: string;
  actionHref?: string;
  actionLabel?: string;
}) {
  return (
    <section className="rounded-md border border-dashed border-slate-700 bg-slate-900/50 p-6 text-center">
      <h2 className="text-base font-semibold text-slate-100">{title}</h2>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-400">{description}</p>
      {actionHref && actionLabel ? (
        <Link
          className="mt-4 inline-flex h-10 items-center justify-center rounded-md bg-cyan-400 px-4 text-sm font-medium text-slate-950 transition hover:bg-cyan-300"
          href={actionHref}
        >
          {actionLabel}
        </Link>
      ) : null}
    </section>
  );
}

export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="rounded-md border border-slate-800 bg-slate-900/70 p-5 text-sm text-slate-300">
      {label}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <p className="rounded-md border border-red-900/70 bg-red-950/50 px-3 py-2 text-sm text-red-200">
      {message}
    </p>
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
    <section className="rounded-md border border-slate-800 bg-slate-950/60 p-4">
      <div>
        <h2 className="text-sm font-semibold text-slate-100">{title}</h2>
        {description ? <p className="mt-1 text-sm leading-6 text-slate-500">{description}</p> : null}
      </div>
      <div className="mt-4 grid gap-4">{children}</div>
    </section>
  );
}
