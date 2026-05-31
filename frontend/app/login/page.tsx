"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";

import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login({ email, password });
      router.push(searchParams.get("next") ?? "/dashboard");
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : "Unable to log in.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen bg-slate-950 px-6 py-10 text-slate-100 lg:grid-cols-[1fr_480px]">
      <section className="hidden items-end border-r border-slate-800 pr-10 lg:flex">
        <div className="max-w-xl pb-10">
          <Link href="/" className="text-lg font-semibold">
            Nexterview
          </Link>
          <h1 className="mt-8 text-5xl font-semibold tracking-tight">Welcome back.</h1>
          <p className="mt-4 text-lg leading-8 text-slate-300">
            Continue from your organization dashboard with a verified account and role-aware access.
          </p>
        </div>
      </section>
      <section className="mx-auto flex w-full max-w-md flex-col justify-center">
        <Link href="/" className="mb-10 text-lg font-semibold lg:hidden">
          Nexterview
        </Link>
        <div>
          <h2 className="text-3xl font-semibold tracking-tight">Log in</h2>
          <p className="mt-2 text-sm text-slate-400">Use your organization account.</p>
        </div>
        <form className="mt-8 grid gap-5" onSubmit={handleSubmit}>
          <Input
            id="email"
            label="Email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
          <Input
            id="password"
            label="Password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          {error ? <p className="rounded-md border border-red-900/70 bg-red-950/50 px-3 py-2 text-sm text-red-200">{error}</p> : null}
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Logging in..." : "Log in"}
          </Button>
        </form>
        <p className="mt-6 text-sm text-slate-400">
          New organization?{" "}
          <Link href="/register" className="font-medium text-cyan-300 hover:text-cyan-200">
            Register
          </Link>
        </p>
      </section>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-slate-300">
          <div className="h-10 w-10 rounded-full border-2 border-slate-800 border-t-cyan-400" aria-label="Loading" />
        </main>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
