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
      description="Create the organization workspace your team will use to configure interviews, invite candidates, and review evidence."
      eyebrow="Organization workspace"
      title="Build interviews around real engineering work."
    >
      <div className="mx-auto w-full max-w-md">
        <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">Create account</p>
        <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">Set up your workspace</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          This account becomes the first administrator for your organization.
        </p>

        <form className="mt-7 grid gap-4" onSubmit={handleSubmit}>
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
          <p className="-mt-2 text-xs leading-5 text-slate-500">Use 12 to 72 characters for the administrator password.</p>
          {error ? (
            <p aria-live="polite" className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm leading-6 text-rose-700" role="alert">
              {error}
            </p>
          ) : null}
          <Button aria-busy={isSubmitting} className="mt-1 w-full" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Creating account..." : "Create account"}
          </Button>
        </form>

        <div className="mt-6 border-t border-slate-200 pt-5">
          <p className="text-sm text-slate-600">
            Already registered?{" "}
            <Link href="/login" className="font-semibold text-blue-700 hover:text-blue-900">
              Log in to your workspace
            </Link>
          </p>
        </div>
      </div>
    </AuthPageShell>
  );
}
