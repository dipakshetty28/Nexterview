import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          Nexterview
        </Link>
        <div className="flex items-center gap-2">
          <Link className="rounded-md px-3 py-2 text-sm text-slate-300 hover:bg-slate-900 hover:text-white" href="/login">
            Log in
          </Link>
          <Link className="rounded-md bg-cyan-400 px-3 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-300" href="/register">
            Register
          </Link>
        </div>
      </nav>
      <section className="mx-auto grid min-h-[calc(100vh-88px)] max-w-6xl items-center gap-10 px-6 py-12 lg:grid-cols-[1fr_440px]">
        <div>
          <p className="mb-4 w-fit rounded-full border border-slate-700 px-3 py-1 text-sm text-slate-300">
            AI-native engineering interviews
          </p>
          <h1 className="max-w-3xl text-4xl font-semibold tracking-tight sm:text-6xl">Evaluate how engineers work with AI.</h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
            Nexterview gives teams a production foundation for authenticated, organization-ready engineering
            evaluations built on FastAPI, PostgreSQL, Redis, and Next.js.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link className="rounded-md bg-cyan-400 px-4 py-3 text-sm font-medium text-slate-950 hover:bg-cyan-300" href="/register">
              Create organization
            </Link>
            <Link className="rounded-md border border-slate-700 px-4 py-3 text-sm font-medium text-slate-100 hover:border-slate-500" href="/login">
              Open dashboard
            </Link>
          </div>
        </div>
        <div className="rounded-md border border-slate-800 bg-slate-900/60 p-5 shadow-2xl shadow-cyan-950/20">
          <div className="mb-5 flex items-center justify-between border-b border-slate-800 pb-4">
            <div>
              <p className="text-sm text-slate-400">Auth status</p>
              <p className="text-xl font-semibold">Production foundation</p>
            </div>
            <span className="rounded-full bg-emerald-400/10 px-3 py-1 text-sm text-emerald-300">Ready</span>
          </div>
          <div className="grid gap-3">
            {["JWT access tokens", "Bcrypt password hashing", "Organization membership", "Role-based guards"].map((item) => (
              <div key={item} className="flex items-center justify-between rounded-md border border-slate-800 bg-slate-950 px-4 py-3">
                <span className="text-sm text-slate-300">{item}</span>
                <span className="h-2 w-2 rounded-full bg-cyan-300" />
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
