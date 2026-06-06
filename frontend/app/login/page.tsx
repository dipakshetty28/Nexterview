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
      description="Manage realistic engineering interviews and review the evidence behind every candidate decision."
      eyebrow="Interviewer workspace"
      title="Continue your hiring workflow."
    >
      <div className="mx-auto w-full max-w-md">
        <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">Log in</p>
        <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">Access your organization</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Use your interviewer or admin account. Candidates should return through their interview invite.
        </p>

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
            <p aria-live="polite" className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm leading-6 text-rose-700" role="alert">
              {error}
            </p>
          ) : null}
          <Button aria-busy={isSubmitting} className="w-full" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Signing in..." : "Log in"}
          </Button>
        </form>

        <div className="mt-6 border-t border-slate-200 pt-5">
          <p className="text-sm text-slate-600">
          New organization?{" "}
            <Link href="/register" className="font-semibold text-blue-700 hover:text-blue-900">
              Create an admin account
            </Link>
          </p>
        </div>
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
