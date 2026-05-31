"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();
  const [fullName, setFullName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await register({
        email,
        password,
        full_name: fullName,
        organization_name: organizationName,
      });
      router.push("/dashboard");
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : "Unable to register.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen bg-slate-950 px-6 py-10 text-slate-100 lg:grid-cols-[1fr_520px]">
      <section className="hidden items-end border-r border-slate-800 pr-10 lg:flex">
        <div className="max-w-xl pb-10">
          <Link href="/" className="text-lg font-semibold">
            Nexterview
          </Link>
          <h1 className="mt-8 text-5xl font-semibold tracking-tight">Create the first admin account.</h1>
          <p className="mt-4 text-lg leading-8 text-slate-300">
            Registration creates an organization, an ADMIN user, and the initial organization membership.
          </p>
        </div>
      </section>
      <section className="mx-auto flex w-full max-w-md flex-col justify-center">
        <Link href="/" className="mb-10 text-lg font-semibold lg:hidden">
          Nexterview
        </Link>
        <div>
          <h2 className="text-3xl font-semibold tracking-tight">Register</h2>
          <p className="mt-2 text-sm text-slate-400">Start with your organization owner account.</p>
        </div>
        <form className="mt-8 grid gap-5" onSubmit={handleSubmit}>
          <Input
            id="fullName"
            label="Full name"
            autoComplete="name"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            required
          />
          <Input
            id="organizationName"
            label="Organization"
            autoComplete="organization"
            value={organizationName}
            onChange={(event) => setOrganizationName(event.target.value)}
            required
          />
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
            autoComplete="new-password"
            minLength={12}
            maxLength={72}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          {error ? <p className="rounded-md border border-red-900/70 bg-red-950/50 px-3 py-2 text-sm text-red-200">{error}</p> : null}
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Creating account..." : "Create account"}
          </Button>
        </form>
        <p className="mt-6 text-sm text-slate-400">
          Already registered?{" "}
          <Link href="/login" className="font-medium text-cyan-300 hover:text-cyan-200">
            Log in
          </Link>
        </p>
      </section>
    </main>
  );
}
