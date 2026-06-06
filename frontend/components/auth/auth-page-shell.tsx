import Link from "next/link";
import type { ReactNode } from "react";

const AUTH_POINTS = [
  "AI-assisted work is allowed and visible in the evidence trail.",
  "Tasks include realistic code, bug reports, validation checks, and final explanations.",
  "Interviewers see code quality, prompt quality, AI usage, telemetry, and recommendation signals.",
];

export function AuthPageShell({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <main className="app-page-bg min-h-screen px-6 py-8 text-slate-950">
      <section className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl items-center gap-8 lg:grid-cols-[minmax(0,1fr)_460px]">
        <div className="relative overflow-hidden rounded-card border border-white/80 bg-white/80 p-6 shadow-panel backdrop-blur lg:p-8">
          <div className="pointer-events-none absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-blue-600 via-sky-400 to-slate-200" />
          <Link href="/" className="text-lg font-semibold text-blue-700 hover:text-blue-900">
            Nexterview
          </Link>
          <p className="mt-10 text-sm font-semibold uppercase tracking-wide text-blue-700">{eyebrow}</p>
          <h1 className="mt-4 max-w-2xl text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">{title}</h1>
          <p className="mt-5 max-w-2xl text-base leading-8 text-slate-600">{description}</p>

          <div className="mt-8 grid gap-3">
            {AUTH_POINTS.map((point) => (
              <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm leading-6 text-slate-700 shadow-sm" key={point}>
                {point}
              </div>
            ))}
          </div>
        </div>

        <section className="rounded-card border border-white/80 bg-white p-6 shadow-elevated">
          {children}
        </section>
      </section>
    </main>
  );
}
