"use client";

import { useEffect, useState } from "react";

import { ProtectedRoute } from "@/components/auth/protected-route";
import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { getDashboard } from "@/lib/api";
import type { DashboardResponse } from "@/lib/types";

function DashboardContent() {
  const { logout, token, user } = useAuth();
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      return;
    }

    getDashboard(token)
      .then(setDashboard)
      .catch(() => setError("Unable to load dashboard."));
  }, [token]);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/95">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
          <div>
            <p className="text-sm text-slate-400">Nexterview</p>
            <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          </div>
          <Button variant="secondary" onClick={logout}>
            Log out
          </Button>
        </div>
      </header>
      <section className="mx-auto grid max-w-6xl gap-6 px-6 py-8 lg:grid-cols-[280px_1fr]">
        <aside className="rounded-md border border-slate-800 bg-slate-900/60 p-5">
          <div className="mb-5">
            <p className="text-sm text-slate-400">Signed in as</p>
            <p className="mt-1 font-medium">{user?.full_name}</p>
            <p className="mt-1 text-sm text-slate-400">{user?.email}</p>
          </div>
          <span className="rounded-full bg-cyan-400/10 px-3 py-1 text-sm font-medium text-cyan-200">{user?.role}</span>
        </aside>
        <div className="grid gap-6">
          <section className="rounded-md border border-slate-800 bg-slate-900/60 p-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h2 className="text-xl font-semibold">Organization access</h2>
                <p className="mt-2 text-sm leading-6 text-slate-400">
                  Your authenticated session is authorized against backend role guards.
                </p>
              </div>
              <span className="w-fit rounded-full bg-emerald-400/10 px-3 py-1 text-sm text-emerald-300">Protected</span>
            </div>
            {error ? <p className="mt-4 rounded-md border border-red-900/70 bg-red-950/50 px-3 py-2 text-sm text-red-200">{error}</p> : null}
            <div className="mt-6 grid gap-3">
              {(dashboard?.organizations ?? user?.organizations ?? []).map((membership) => (
                <div
                  className="flex flex-col gap-2 rounded-md border border-slate-800 bg-slate-950 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
                  key={membership.organization.id}
                >
                  <div>
                    <p className="font-medium">{membership.organization.name}</p>
                    <p className="text-sm text-slate-500">{membership.organization.slug}</p>
                  </div>
                  <span className="w-fit rounded-full border border-slate-700 px-3 py-1 text-sm text-slate-300">{membership.role}</span>
                </div>
              ))}
            </div>
          </section>
          <section className="rounded-md border border-slate-800 bg-slate-900/60 p-6">
            <h2 className="text-xl font-semibold">Auth foundation</h2>
            <div className="mt-5 grid gap-3 md:grid-cols-3">
              {["Registered user", "JWT verified", "RBAC enabled"].map((label) => (
                <div className="rounded-md border border-slate-800 bg-slate-950 p-4" key={label}>
                  <p className="text-sm text-slate-400">{label}</p>
                  <p className="mt-2 text-2xl font-semibold text-cyan-200">Active</p>
                </div>
              ))}
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
