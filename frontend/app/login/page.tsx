"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";

import { LoadingState } from "@/components/app/page-primitives";
import { AuthPageShell } from "@/components/auth/auth-page-shell";
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
      setError(caughtError instanceof ApiError ? caughtError.message : "Unable to log in. Check your email and password.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthPageShell
      description="Open your hiring workspace to manage interviews, review evidence, and track candidate outcomes."
      eyebrow="Secure hiring workspace"
      title="Welcome back."
    >
      <div>
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">Log in</p>
          <h2 className="mt-2 text-3xl font-semibold text-slate-950">Access your organization</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Use the account assigned to your role. Candidate sessions continue from invite links.
          </p>
        </div>
        <form className="mt-7 grid gap-5" onSubmit={handleSubmit}>
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
          {error ? (
            <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm leading-6 text-rose-700">
              {error}
            </p>
          ) : null}
          <Button aria-busy={isSubmitting} type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Signing in..." : "Log in"}
          </Button>
        </form>
        <p className="mt-6 text-sm text-slate-600">
          New organization?{" "}
          <Link href="/register" className="font-medium text-blue-700 hover:text-blue-900">
            Create account
          </Link>
        </p>
      </div>
    </AuthPageShell>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <main className="app-page-bg flex min-h-screen items-center justify-center px-6 text-slate-700">
          <div className="w-full max-w-md">
            <LoadingState label="Preparing login" rows={2} />
          </div>
        </main>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
