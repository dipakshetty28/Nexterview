import Link from "next/link";
import type { ReactNode } from "react";

const AUTH_POINTS = [
  {
    label: "Real work",
    description: "Executable repository tasks matched to role and stack.",
  },
  {
    label: "Open AI use",
    description: "Candidates can use the copilot while judgment and validation are measured.",
  },
  {
    label: "Reviewable evidence",
    description: "Code, tests, prompts, telemetry, and explanations stay connected.",
  },
];

function BrandMark() {
  return (
    <span className="flex items-center gap-2.5">
      <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-950 text-sm font-bold text-white shadow-sm">
        N
      </span>
      <span className="text-lg font-semibold tracking-tight text-slate-950">Nexterview</span>
    </span>
  );
}

function ProductSignalPreview() {
  return (
    <div className="mt-8 overflow-hidden rounded-card border border-slate-700 bg-slate-950 shadow-elevated">
      <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-blue-300">Evaluation workspace</p>
          <p className="mt-1 text-sm font-medium text-slate-200">Senior Backend Engineer</p>
        </div>
        <span className="rounded-full border border-emerald-800 bg-emerald-950/60 px-2.5 py-1 text-[11px] font-semibold text-emerald-200">
          Reviewed
        </span>
      </div>
      <div className="grid gap-3 p-4 sm:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-4">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-slate-300">Evidence captured</span>
            <span className="text-slate-500">Complete</span>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2">
            {["Code changes", "Test history", "AI transcript", "Final notes"].map((item) => (
              <span className="rounded-md border border-slate-800 bg-slate-950 px-2 py-2 text-[11px] text-slate-400" key={item}>
                {item}
              </span>
            ))}
          </div>
        </div>
        <div className="rounded-lg border border-blue-900 bg-blue-950/50 p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-blue-300">Review signal</p>
          <p className="mt-3 text-3xl font-semibold text-white">84</p>
          <p className="mt-1 text-xs text-blue-200">Strong engineering evidence</p>
          <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-slate-800">
            <div className="h-full w-[84%] rounded-full bg-blue-400" />
          </div>
        </div>
      </div>
    </div>
  );
}

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
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="border-b border-white/80 bg-white/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
          <Link aria-label="Nexterview home" href="/">
            <BrandMark />
          </Link>
          <Link className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-100 hover:text-slate-950" href="/">
            Back to overview
          </Link>
        </div>
      </header>

      <section className="relative px-4 py-8 sm:px-6 sm:py-12">
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(148,163,184,0.1)_1px,transparent_1px),linear-gradient(90deg,rgba(148,163,184,0.1)_1px,transparent_1px)] bg-[size:42px_42px] [mask-image:linear-gradient(to_bottom,black,transparent_72%)]" />
        <div className="relative mx-auto grid max-w-6xl gap-6 lg:grid-cols-[minmax(0,1.05fr)_minmax(420px,0.95fr)] lg:items-stretch">
          <section className="order-2 rounded-card border border-white/80 bg-white/75 p-6 shadow-panel backdrop-blur sm:p-8 lg:order-1">
            <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">{eyebrow}</p>
            <h1 className="mt-4 max-w-xl text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">{title}</h1>
            <p className="mt-5 max-w-xl text-base leading-7 text-slate-600">{description}</p>

            <div className="mt-7 grid gap-3 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
              {AUTH_POINTS.map((point) => (
                <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm" key={point.label}>
                  <span className="flex h-7 w-7 items-center justify-center rounded-md border border-blue-100 bg-blue-50 text-xs font-bold text-blue-700">
                    +
                  </span>
                  <h2 className="mt-3 text-sm font-semibold text-slate-950">{point.label}</h2>
                  <p className="mt-1 text-xs leading-5 text-slate-600">{point.description}</p>
                </div>
              ))}
            </div>

            <ProductSignalPreview />
          </section>

          <section className="order-1 flex rounded-card border border-white/90 bg-white p-6 shadow-elevated sm:p-8 lg:order-2">
            <div className="my-auto w-full">{children}</div>
          </section>
        </div>
      </section>
    </main>
  );
}
