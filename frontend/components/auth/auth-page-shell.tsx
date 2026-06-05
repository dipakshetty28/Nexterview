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
    <main className="min-h-screen bg-slate-950 px-6 py-8 text-slate-100">
      <section className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl items-center gap-8 lg:grid-cols-[minmax(0,1fr)_460px]">
        <div className="rounded-md border border-slate-800 bg-slate-900/50 p-6 lg:p-8">
          <Link href="/" className="text-lg font-semibold text-cyan-300 hover:text-cyan-200">
            Nexterview
          </Link>
          <p className="mt-10 text-sm font-semibold uppercase text-cyan-300">{eyebrow}</p>
          <h1 className="mt-4 max-w-2xl text-4xl font-semibold sm:text-5xl">{title}</h1>
          <p className="mt-5 max-w-2xl text-base leading-8 text-slate-300">{description}</p>

          <div className="mt-8 grid gap-3">
            {AUTH_POINTS.map((point) => (
              <div className="rounded-md border border-slate-800 bg-slate-950/70 px-4 py-3 text-sm leading-6 text-slate-300" key={point}>
                {point}
              </div>
            ))}
          </div>
        </div>

        <section className="rounded-md border border-slate-800 bg-slate-900/80 p-6 shadow-2xl shadow-slate-950">
          {children}
        </section>
      </section>
    </main>
  );
}
