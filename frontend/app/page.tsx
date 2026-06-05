import Link from "next/link";

const WORKFLOW_STEPS = [
  {
    title: "Create a role-specific interview",
    description: "Choose stack, difficulty, interview type, duration, and the AI mode candidates may use.",
  },
  {
    title: "Run a realistic workspace session",
    description: "Candidates debug or build in a cloud IDE with task context, code, tests, notes, and AI copilot support.",
  },
  {
    title: "Review structured evidence",
    description: "Agent reviews combine code, tests, telemetry, prompts, transcript, and final explanation into a hiring signal.",
  },
];

const FEATURES = [
  "AI assistance allowed, validation and judgment evaluated",
  "Realistic debugging, full-stack, refactoring, API, frontend, and AI engineering tasks",
  "Prompt quality and AI usage analysis for every submitted session",
  "Multi-agent review across correctness, architecture, debugging, communication, and risk",
  "Evidence-based recommendation with score breakdown and session artifacts",
  "Role-aware dashboards for interviewers and admins",
];

const USERS = [
  {
    title: "Hiring teams",
    description: "Replace trivia screens with work samples that reflect modern engineering practice.",
  },
  {
    title: "Engineering leaders",
    description: "See how candidates reason, validate AI output, handle ambiguity, and communicate tradeoffs.",
  },
  {
    title: "Candidates",
    description: "Use AI as you would on the job, then show your debugging discipline and engineering judgment.",
  },
];

function ProductPreview() {
  return (
    <div className="mx-auto mt-10 max-w-5xl overflow-hidden rounded-md border border-slate-800 bg-slate-950 shadow-2xl shadow-slate-950">
      <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/80 px-4 py-3">
        <div>
          <p className="text-xs font-semibold uppercase text-cyan-300">Live candidate session</p>
          <p className="mt-1 text-sm text-slate-300">Backend debugging / Pair Programmer Mode</p>
        </div>
        <span className="rounded-md border border-emerald-800 bg-emerald-950/60 px-3 py-1 text-xs text-emerald-200">
          Evidence captured
        </span>
      </div>
      <div className="grid min-h-[360px] lg:grid-cols-[0.9fr_1.35fr_0.95fr]">
        <section className="border-b border-slate-800 p-4 lg:border-b-0 lg:border-r">
          <p className="text-xs font-semibold uppercase text-slate-500">Task brief</p>
          <h2 className="mt-3 text-lg font-semibold text-slate-100">Fix duplicate payment retries</h2>
          <p className="mt-3 text-sm leading-6 text-slate-400">
            Investigate retry logs, preserve idempotency, update the service path, and validate the visible regression checks.
          </p>
          <div className="mt-5 grid gap-2 text-xs text-slate-300">
            {["Business impact", "Visible requirements", "Bug report", "Expected deliverables"].map((item) => (
              <div className="rounded-md border border-slate-800 bg-slate-900/50 px-3 py-2" key={item}>
                {item}
              </div>
            ))}
          </div>
        </section>
        <section className="border-b border-slate-800 p-4 lg:border-b-0 lg:border-r">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase text-slate-500">Code and checks</p>
            <span className="font-mono text-xs text-slate-500">orders.py</span>
          </div>
          <pre className="mt-3 overflow-hidden rounded-md border border-slate-800 bg-slate-950 p-4 font-mono text-xs leading-6 text-slate-300">
            <code>{`def process_payment(event):
    key = event.payment_id
    if was_processed(key):
        return existing_receipt(key)
    return charge_provider(event, key)`}</code>
          </pre>
          <div className="mt-4 rounded-md border border-emerald-900/70 bg-emerald-950/30 px-3 py-2 text-sm text-emerald-200">
            5 passed / 0 failed
          </div>
        </section>
        <section className="p-4">
          <p className="text-xs font-semibold uppercase text-slate-500">AI usage review</p>
          <div className="mt-3 grid gap-3">
            <div className="rounded-md border border-cyan-900/60 bg-cyan-950/30 p-3">
              <p className="text-sm text-cyan-100">Prompt quality</p>
              <p className="mt-1 text-xs leading-5 text-slate-400">Specific question with logs, hypothesis, and suspected code path.</p>
            </div>
            <div className="rounded-md border border-amber-900/60 bg-amber-950/20 p-3">
              <p className="text-sm text-amber-100">Risk signal</p>
              <p className="mt-1 text-xs leading-5 text-slate-400">Candidate verified the AI suggestion before final submit.</p>
            </div>
            <div className="rounded-md border border-slate-800 bg-slate-900/50 p-3">
              <p className="text-sm text-slate-100">Recommendation</p>
              <p className="mt-1 text-xl font-semibold text-emerald-300">Lean Hire</p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <Link href="/" className="text-lg font-semibold">
          Nexterview
        </Link>
        <div className="flex items-center gap-2">
          <Link className="rounded-md px-3 py-2 text-sm text-slate-300 hover:bg-slate-900 hover:text-white" href="/login">
            Log in
          </Link>
          <Link className="rounded-md bg-cyan-400 px-3 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-300" href="/register">
            Create account
          </Link>
        </div>
      </nav>

      <section className="border-y border-slate-800 bg-slate-900/30 px-6 py-16">
        <div className="mx-auto max-w-6xl text-center">
          <p className="mx-auto w-fit rounded-md border border-cyan-800 bg-cyan-950/50 px-3 py-1 text-sm text-cyan-200">
            AI-era engineering evaluation
          </p>
          <h1 className="mx-auto mt-6 max-w-4xl text-4xl font-semibold sm:text-6xl">Nexterview</h1>
          <p className="mx-auto mt-5 max-w-3xl text-lg leading-8 text-slate-300">
            Evaluate realistic engineering work where AI is allowed, but judgment, validation, debugging discipline,
            and communication decide the signal.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link className="rounded-md bg-cyan-400 px-5 py-3 text-sm font-medium text-slate-950 hover:bg-cyan-300" href="/register">
              Start an organization
            </Link>
            <Link className="rounded-md border border-slate-700 px-5 py-3 text-sm font-medium text-slate-100 hover:border-slate-500" href="/login">
              Open dashboard
            </Link>
          </div>
          <ProductPreview />
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-8 px-6 py-14 lg:grid-cols-[0.8fr_1.2fr]">
        <div>
          <p className="text-sm font-semibold uppercase text-cyan-300">Problem</p>
          <h2 className="mt-3 text-3xl font-semibold">Coding screens have not caught up with AI-assisted work.</h2>
        </div>
        <p className="text-base leading-8 text-slate-300">
          Modern engineers use AI, tests, logs, docs, and code review to solve real problems. Nexterview turns that
          workflow into structured evidence: what candidates asked, what they changed, how they validated it, and how
          well they explained the result.
        </p>
      </section>

      <section className="border-y border-slate-800 bg-slate-900/30 px-6 py-14">
        <div className="mx-auto max-w-6xl">
          <p className="text-sm font-semibold uppercase text-cyan-300">How it works</p>
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {WORKFLOW_STEPS.map((step, index) => (
              <section className="rounded-md border border-slate-800 bg-slate-950 p-5" key={step.title}>
                <span className="font-mono text-sm text-cyan-300">0{index + 1}</span>
                <h3 className="mt-4 text-lg font-semibold">{step.title}</h3>
                <p className="mt-3 text-sm leading-6 text-slate-400">{step.description}</p>
              </section>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-14">
        <div className="grid gap-8 lg:grid-cols-[0.75fr_1.25fr]">
          <div>
            <p className="text-sm font-semibold uppercase text-cyan-300">Key features</p>
            <h2 className="mt-3 text-3xl font-semibold">A full hiring signal from code, AI usage, and validation evidence.</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {FEATURES.map((feature) => (
              <div className="rounded-md border border-slate-800 bg-slate-900/60 p-4 text-sm leading-6 text-slate-300" key={feature}>
                {feature}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t border-slate-800 px-6 py-14">
        <div className="mx-auto max-w-6xl">
          <p className="text-sm font-semibold uppercase text-cyan-300">Built for</p>
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {USERS.map((user) => (
              <section className="rounded-md border border-slate-800 bg-slate-900/60 p-5" key={user.title}>
                <h3 className="text-lg font-semibold">{user.title}</h3>
                <p className="mt-3 text-sm leading-6 text-slate-400">{user.description}</p>
              </section>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t border-slate-800 bg-slate-900/40 px-6 py-12">
        <div className="mx-auto flex max-w-6xl flex-col gap-5 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-2xl font-semibold">Ready to evaluate AI-era engineering skill?</h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              Create an organization, generate a realistic task, and review the evidence from a candidate session.
            </p>
          </div>
          <Link className="w-fit rounded-md bg-cyan-400 px-5 py-3 text-sm font-medium text-slate-950 hover:bg-cyan-300" href="/register">
            Create account
          </Link>
        </div>
      </section>
    </main>
  );
}
