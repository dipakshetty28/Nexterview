"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import type { UserRole } from "@/lib/types";

type NavItem = {
  label: string;
  href: string;
  roles: UserRole[];
};

const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", roles: ["ADMIN", "INTERVIEWER"] },
  { label: "Interviews", href: "/interviews", roles: ["ADMIN", "INTERVIEWER"] },
  { label: "Results", href: "/results", roles: ["ADMIN", "INTERVIEWER"] },
  { label: "Calibration", href: "/calibration", roles: ["ADMIN", "INTERVIEWER"] },
];

function initials(name?: string | null): string {
  if (!name) {
    return "NT";
  }
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function isActive(pathname: string, href: string): boolean {
  if (href === "/dashboard") {
    return pathname === href;
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { logout, user } = useAuth();
  const organization = user?.organizations[0]?.organization;
  const navItems = NAV_ITEMS.filter((item) => user && item.roles.includes(user.role));

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="flex min-h-screen">
        <aside className="hidden w-72 shrink-0 border-r border-slate-800 bg-slate-950/95 px-4 py-5 lg:block">
          <div className="rounded-md border border-slate-800 bg-slate-900/60 p-4">
            <Link className="text-sm font-semibold text-cyan-300 outline-none hover:text-cyan-200 focus-visible:ring-2 focus-visible:ring-cyan-400/60" href="/dashboard">
              Nexterview
            </Link>
            <p className="mt-3 text-xs uppercase tracking-wide text-slate-500">Organization</p>
            <p className="mt-1 truncate text-sm font-medium text-slate-100">{organization?.name ?? "Workspace"}</p>
          </div>

          <nav aria-label="Primary navigation" className="mt-5 grid gap-1">
            {navItems.map((item) => (
              <Link
                className={cn(
                  "rounded-md px-3 py-2.5 text-sm font-medium outline-none transition focus-visible:ring-2 focus-visible:ring-cyan-400/60",
                  item.href && isActive(pathname, item.href)
                    ? "bg-cyan-400 text-slate-950"
                    : "text-slate-300 hover:bg-slate-900 hover:text-white",
                )}
                href={item.href}
                key={item.label}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </aside>

        <section className="min-w-0 flex-1">
          <header className="sticky top-0 z-20 border-b border-slate-800 bg-slate-950/95 backdrop-blur">
            <div className="flex flex-col gap-3 px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between">
              <div className="min-w-0">
                <p className="text-xs uppercase tracking-wide text-slate-500">Nexterview</p>
                <p className="mt-1 truncate text-sm font-medium text-slate-200">
                  {organization?.name ?? "Organization workspace"}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <nav aria-label="Mobile navigation" className="flex flex-wrap gap-1 lg:hidden">
                  {navItems
                    .filter((item) => item.href)
                    .map((item) => (
                      <Link
                        className={cn(
                          "rounded-md px-3 py-2 text-xs font-medium outline-none transition focus-visible:ring-2 focus-visible:ring-cyan-400/60",
                          isActive(pathname, item.href)
                            ? "bg-cyan-400 text-slate-950"
                            : "border border-slate-800 text-slate-300 hover:border-slate-600",
                        )}
                        href={item.href}
                        key={item.label}
                      >
                        {item.label}
                      </Link>
                    ))}
                </nav>

                <details className="relative">
                  <summary className="flex cursor-pointer list-none items-center gap-3 rounded-md border border-slate-800 bg-slate-900 px-3 py-2 outline-none transition hover:border-slate-600 focus-visible:ring-2 focus-visible:ring-cyan-400/60">
                    <span className="flex h-8 w-8 items-center justify-center rounded-md bg-cyan-400 text-xs font-bold text-slate-950">
                      {initials(user?.full_name)}
                    </span>
                    <span className="hidden min-w-0 text-left sm:block">
                      <span className="block truncate text-sm font-medium text-slate-100">{user?.full_name}</span>
                      <span className="block text-xs text-slate-500">{user?.role}</span>
                    </span>
                  </summary>
                  <div className="absolute right-0 mt-2 w-72 rounded-md border border-slate-800 bg-slate-900 p-3 shadow-2xl shadow-slate-950">
                    <p className="truncate text-sm font-medium text-slate-100">{user?.full_name}</p>
                    <p className="mt-1 truncate text-xs text-slate-400">{user?.email}</p>
                    <Button className="mt-3 w-full" onClick={logout} type="button" variant="secondary">
                      Log out
                    </Button>
                  </div>
                </details>
              </div>
            </div>
          </header>

          <div className="px-4 py-6 sm:px-6 lg:px-8">{children}</div>
        </section>
      </div>
    </main>
  );
}
