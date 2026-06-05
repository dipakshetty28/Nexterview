"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { AuthPageShell } from "@/components/auth/auth-page-shell";
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
      setError(caughtError instanceof ApiError ? caughtError.message : "Unable to create account. Review the fields and try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthPageShell
      description="Create the organization workspace your interviewers will use to generate tasks, invite candidates, and review evidence."
      eyebrow="Organization setup"
      title="Start evaluating modern engineering work."
    >
      <div>
        <div>
          <p className="text-sm font-semibold uppercase text-cyan-300">Create account</p>
          <h2 className="mt-2 text-3xl font-semibold">Set up your workspace</h2>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            This creates the first admin account for your organization.
          </p>
        </div>
        <form className="mt-7 grid gap-5" onSubmit={handleSubmit}>
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
            label="Work email"
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
          {error ? (
            <p className="rounded-md border border-red-900/70 bg-red-950/50 px-3 py-2 text-sm leading-6 text-red-200">
              {error}
            </p>
          ) : null}
          <Button aria-busy={isSubmitting} type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Creating account..." : "Create account"}
          </Button>
        </form>
        <p className="mt-6 text-sm text-slate-400">
          Already registered?{" "}
          <Link href="/login" className="font-medium text-cyan-300 hover:text-cyan-200">
            Log in
          </Link>
        </p>
      </div>
    </AuthPageShell>
  );
}
