import Link from "next/link";

const PROBLEMS = [
  "LeetCode-style screens miss architecture, debugging, and engineering judgment.",
  "AI makes basic take-homes and final-answer scoring less trustworthy.",
  "Hiring teams need evidence of how candidates reason, verify, and communicate.",
];

const SOLUTIONS = [
  "Realistic, executable repository scenarios matched to the selected stack.",
  "Test runs, code changes, AI prompts, and validation behavior captured together.",
  "Multi-agent review distilled into interviewer-ready evidence and follow-up questions.",
];

const WORKFLOW_STEPS = [
  {
    number: "01",
    title: "Configure the interview",
    description: "Select the role, stack, difficulty, scenario type, duration, and allowed AI mode.",
  },
  {
    number: "02",
    title: "Observe real engineering work",
    description: "The candidate solves a realistic repo task with code, tests, notes, and an AI copilot.",
  },
  {
    number: "03",
    title: "Review structured evidence",
    description: "Nexterview evaluates code, tests, prompts, debugging, communication, and verification discipline.",
  },
];

const FEATURES = [
  {
    label: "EX",
    title: "Real executable scenarios",
    description: "Multi-file projects with stack-matched structure, seed data, bugs, feature requests, and runnable checks.",
  },
  {
    label: "AI",
    title: "AI copilot included",
    description: "Candidates use AI as they would at work while every prompt and response becomes part of the evidence.",
  },
  {
    label: "MR",
    title: "Multi-agent review",
    description: "Independent reviewers assess correctness, architecture, debugging, security, communication, and risk.",
  },
  {
    label: "PQ",
    title: "Prompting skill analysis",
    description: "See whether candidates provide context, test hypotheses, challenge suggestions, and ask useful follow-ups.",
  },
  {
    label: "TV",
    title: "Test-based validation",
    description: "Visible checks and stored run history show whether the candidate verified changes before submitting.",
  },
  {
    label: "SR",
    title: "Candidate session replay",
    description: "Review code diffs, AI conversation, telemetry, notes, tests, and the final explanation in one place.",
  },
];

function BrandMark() {
  return (
    <span className="flex shrink-0 items-center gap-2.5">
      <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-950 text-sm font-bold text-white shadow-sm">
        N
      </span>
      <span className="text-lg font-semibold tracking-tight text-slate-950">Nexterview</span>
    </span>
  );
}

function ProductPreview() {
  return (
    <section
      aria-label="Illustrative Nexterview product preview"
      className="relative mx-auto w-full min-w-0 max-w-7xl overflow-hidden px-4 pb-16 pt-4 sm:px-6 lg:px-8"
      id="sample-result"
    >
      <div className="absolute inset-x-20 bottom-8 top-20 rounded-[2rem] bg-blue-100/60 blur-3xl" />
      <div className="relative grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1.7fr)_minmax(290px,0.65fr)] lg:items-start">
        <div className="min-w-0 max-w-full overflow-hidden rounded-card border border-slate-800 bg-slate-950 shadow-elevated">
          <div className="flex flex-col gap-3 border-b border-slate-800 bg-slate-900/90 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex gap-1.5" aria-hidden="true">
                <span className="h-2.5 w-2.5 rounded-full bg-rose-400" />
                <span className="h-2.5 w-2.5 rounded-full bg-amber-400" />
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
              </div>
              <span className="text-xs font-medium text-slate-400">Candidate workspace</span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-slate-700 bg-slate-800 px-2.5 py-1 text-[11px] font-medium text-slate-300">
                Pair Programmer Mode
              </span>
              <span className="rounded-full border border-emerald-800 bg-emerald-950/70 px-2.5 py-1 text-[11px] font-semibold text-emerald-200">
                Session active
              </span>
            </div>
          </div>

          <div className="grid min-h-[430px] min-w-0 md:grid-cols-[210px_minmax(0,1fr)]">
            <aside className="border-b border-slate-800 bg-slate-900/50 p-4 md:border-b-0 md:border-r">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Project</p>
              <div className="mt-4 grid gap-1 font-mono text-xs text-slate-400">
                <span className="rounded bg-slate-800/80 px-2 py-2 text-slate-200">app/</span>
                <span className="px-4 py-1.5">main.py</span>
                <span className="rounded bg-blue-950/70 px-4 py-2 text-blue-200">services/orders.py</span>
                <span className="px-4 py-1.5">data/orders.json</span>
                <span className="rounded bg-slate-800/80 px-2 py-2 text-slate-200">tests/</span>
                <span className="px-4 py-1.5">test_orders.py</span>
              </div>
              <div className="mt-6 border-t border-slate-800 pt-4">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Task</p>
                <p className="mt-2 text-sm font-medium leading-5 text-slate-200">Fix order totals and add status filtering.</p>
              </div>
            </aside>

            <div className="grid min-w-0 grid-rows-[auto_1fr_auto]">
              <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/40 px-4 py-3">
                <span className="font-mono text-xs text-blue-200">app/services/orders.py</span>
                <span className="text-[11px] text-slate-500">Python</span>
              </div>
              <pre className="max-w-full overflow-hidden p-5 font-mono text-xs leading-6 text-slate-300 sm:text-[13px]">
                <code>
                  <span className="text-fuchsia-300">def</span> <span className="text-blue-300">calculate_total</span>
                  <span className="text-slate-400">(order):</span>
                  {"\n"}
                  <span className="text-slate-500">    # Quantity must be applied per line item</span>
                  {"\n"}
                  <span className="text-fuchsia-300">    return</span> <span className="text-slate-300">sum(</span>
                  {"\n"}
                  <span className="text-slate-300">        item[</span><span className="text-amber-200">"unit_price"</span>
                  <span className="text-slate-300">] * item[</span><span className="text-amber-200">"quantity"</span>
                  <span className="text-slate-300">]</span>
                  {"\n"}
                  <span className="text-fuchsia-300">        for</span> <span className="text-slate-300">item </span>
                  <span className="text-fuchsia-300">in</span> <span className="text-slate-300">order[</span>
                  <span className="text-amber-200">"items"</span><span className="text-slate-300">]</span>
                  {"\n"}
                  <span className="text-slate-300">    )</span>
                </code>
              </pre>
              <div className="grid gap-2 border-t border-slate-800 bg-slate-900/55 p-4 sm:grid-cols-[1fr_auto] sm:items-center">
                <div>
                  <p className="text-xs font-semibold text-emerald-300">7 checks passed</p>
                  <p className="mt-1 font-mono text-[11px] text-slate-500">python -m pytest</p>
                </div>
                <span className="w-fit rounded-full border border-emerald-800 bg-emerald-950/60 px-3 py-1 text-xs font-medium text-emerald-200">
                  Validated
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="grid min-w-0 gap-4 lg:pt-10">
          <article className="rounded-card border border-white/90 bg-white p-5 shadow-elevated">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">AI copilot</p>
                <h3 className="mt-1 text-base font-semibold text-slate-950">Context-aware guidance</h3>
              </div>
              <span className="rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-[11px] font-semibold text-blue-700">
                High context
              </span>
            </div>
            <div className="mt-4 grid gap-3 text-sm leading-6">
              <div className="ml-6 rounded-lg border border-blue-100 bg-blue-50 p-3 text-slate-700">
                The total ignores quantity. I would fix that first, then add a focused regression test.
              </div>
              <div className="mr-6 rounded-lg border border-slate-200 bg-slate-50 p-3 text-slate-700">
                Compare that hypothesis against the seed orders and identify the smallest safe change.
              </div>
            </div>
          </article>

          <article className="rounded-card border border-white/90 bg-white p-5 shadow-elevated">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Illustrative result</p>
                <h3 className="mt-1 text-base font-semibold text-slate-950">Agent review</h3>
              </div>
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-center">
                <p className="text-2xl font-semibold text-emerald-700">84</p>
                <p className="text-[10px] font-semibold uppercase text-emerald-700">Strong</p>
              </div>
            </div>
            <div className="mt-4 grid gap-2">
              {[
                ["Correctness", "91"],
                ["Debugging", "86"],
                ["AI usage", "82"],
                ["Communication", "77"],
              ].map(([label, value]) => (
                <div className="grid grid-cols-[1fr_auto] items-center gap-3 rounded-lg bg-slate-50 px-3 py-2" key={label}>
                  <span className="text-xs font-medium text-slate-600">{label}</span>
                  <span className="text-xs font-semibold text-slate-950">{value}</span>
                </div>
              ))}
            </div>
          </article>
        </div>
      </div>
    </section>
  );
}

function InsightColumn({
  eyebrow,
  title,
  items,
  tone,
}: {
  eyebrow: string;
  title: string;
  items: string[];
  tone: "slate" | "blue";
}) {
  const accentClass = tone === "blue" ? "bg-blue-600 text-white" : "bg-slate-950 text-white";
  return (
    <article className="rounded-card border border-white/80 bg-white p-6 shadow-panel">
      <span className={`inline-flex h-8 items-center rounded-lg px-3 text-xs font-semibold uppercase tracking-wide ${accentClass}`}>
        {eyebrow}
      </span>
      <h3 className="mt-5 text-2xl font-semibold tracking-tight text-slate-950">{title}</h3>
      <ul className="mt-5 grid gap-3">
        {items.map((item) => (
          <li className="grid grid-cols-[20px_1fr] gap-3 text-sm leading-6 text-slate-600" key={item}>
            <span className="mt-1 flex h-5 w-5 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-[10px] font-bold text-slate-600">
              +
            </span>
            {item}
          </li>
        ))}
      </ul>
    </article>
  );
}

export default function Home() {
  return (
    <main className="min-h-screen w-full max-w-full overflow-x-hidden bg-slate-100 text-slate-950">
      <nav className="border-b border-white/80 bg-white/80 backdrop-blur-xl">
        <div className="mx-auto flex min-w-0 max-w-7xl items-center justify-between gap-3 px-4 py-4 sm:px-6 lg:px-8">
          <Link aria-label="Nexterview home" className="min-w-0" href="/">
            <BrandMark />
          </Link>
          <div className="flex shrink-0 items-center gap-1 sm:gap-2">
            <Link className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 hover:text-slate-950" href="/login">
              Log in
            </Link>
            <Link
              className="rounded-lg border border-blue-700 bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 sm:px-4"
              href="/register"
            >
              <span className="sm:hidden">Create</span>
              <span className="hidden sm:inline">Create interview</span>
            </Link>
          </div>
        </div>
      </nav>

      <section className="relative border-b border-white/80 bg-white/60 px-4 pb-8 pt-16 sm:px-6 sm:pt-20 lg:px-8">
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(148,163,184,0.12)_1px,transparent_1px),linear-gradient(90deg,rgba(148,163,184,0.12)_1px,transparent_1px)] bg-[size:42px_42px] [mask-image:linear-gradient(to_bottom,black,transparent_80%)]" />
        <div className="relative mx-auto min-w-0 max-w-5xl text-center">
          <p className="mx-auto w-fit rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-sm font-semibold text-blue-700">
            AI-native engineering interviews
          </p>
          <h1 className="mx-auto mt-6 max-w-4xl text-4xl font-semibold tracking-tight text-slate-950 sm:text-6xl lg:text-7xl">
            Evaluate engineers for the AI era.
          </h1>
          <p className="mx-auto mt-6 max-w-3xl text-lg leading-8 text-slate-600 sm:text-xl">
            Run realistic coding, debugging, and full-stack interviews where AI is allowed, and engineering judgment is measured.
          </p>
          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <Link
              className="inline-flex h-12 items-center justify-center rounded-lg border border-blue-700 bg-blue-600 px-6 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
              href="/login"
            >
              Start interviewer demo
            </Link>
            <Link
              className="inline-flex h-12 items-center justify-center rounded-lg border border-slate-300 bg-white px-6 text-sm font-semibold text-slate-800 shadow-sm transition hover:border-slate-400 hover:bg-slate-50"
              href="#sample-result"
            >
              View sample result
            </Link>
          </div>
          <div className="mx-auto mt-8 flex max-w-3xl flex-wrap justify-center gap-x-6 gap-y-2 text-sm text-slate-600">
            <span>Real repositories</span>
            <span>AI usage evidence</span>
            <span>Test-based validation</span>
            <span>Structured hiring signal</span>
          </div>
        </div>
      </section>

      <ProductPreview />

      <section className="border-y border-white/80 bg-white/65 px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="max-w-3xl">
            <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">From final answers to real evidence</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
              Modern engineering interviews should measure the work behind the answer.
            </h2>
          </div>
          <div className="mt-8 grid gap-5 lg:grid-cols-2">
            <InsightColumn eyebrow="The problem" items={PROBLEMS} title="Traditional screens hide the signals that matter." tone="slate" />
            <InsightColumn eyebrow="The solution" items={SOLUTIONS} title="Nexterview makes engineering behavior reviewable." tone="blue" />
          </div>
        </div>
      </section>

      <section className="px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="grid gap-8 lg:grid-cols-[0.75fr_1.25fr] lg:items-end">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">How it works</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
                A practical interview flow from setup to decision.
              </h2>
            </div>
            <p className="max-w-2xl text-base leading-8 text-slate-600 lg:justify-self-end">
              Interviewers configure the signal they need. Candidates work in a realistic environment. Reviewers get a concise,
              evidence-backed result.
            </p>
          </div>
          <div className="mt-8 grid gap-4 lg:grid-cols-3">
            {WORKFLOW_STEPS.map((step) => (
              <article className="rounded-card border border-white/80 bg-white p-6 shadow-panel" key={step.number}>
                <span className="font-mono text-sm font-semibold text-blue-700">{step.number}</span>
                <h3 className="mt-6 text-xl font-semibold text-slate-950">{step.title}</h3>
                <p className="mt-3 text-sm leading-6 text-slate-600">{step.description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="border-y border-white/80 bg-white/65 px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="max-w-3xl">
            <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">One evidence system</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
              Everything an interviewer needs to understand how the candidate worked.
            </h2>
          </div>
          <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {FEATURES.map((feature) => (
              <article className="rounded-card border border-white/90 bg-white p-5 shadow-panel" key={feature.title}>
                <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-blue-100 bg-blue-50 font-mono text-xs font-bold text-blue-700">
                  {feature.label}
                </span>
                <h3 className="mt-5 text-lg font-semibold text-slate-950">{feature.title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">{feature.description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 rounded-card border border-slate-800 bg-slate-950 p-7 shadow-elevated sm:p-10 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-2xl">
            <p className="text-sm font-semibold uppercase tracking-wide text-blue-300">See the complete hiring signal</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white">Run an interview built for modern engineering work.</h2>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              Create a role-specific task, let candidates use AI openly, and review the evidence behind the solution.
            </p>
          </div>
          <div className="flex shrink-0 flex-col gap-3 sm:flex-row">
            <Link
              className="inline-flex h-11 items-center justify-center rounded-lg border border-blue-500 bg-blue-500 px-5 text-sm font-semibold text-white transition hover:bg-blue-400"
              href="/register"
            >
              Create interview
            </Link>
            <Link
              className="inline-flex h-11 items-center justify-center rounded-lg border border-slate-700 bg-slate-900 px-5 text-sm font-semibold text-slate-100 transition hover:border-slate-600 hover:bg-slate-800"
              href="/login"
            >
              Open workspace
            </Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-white/80 bg-white/70 px-4 py-7 sm:px-6 lg:px-8">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
          <BrandMark />
          <p>Evidence-based engineering interviews for teams hiring in the AI era.</p>
        </div>
      </footer>
    </main>
  );
}
