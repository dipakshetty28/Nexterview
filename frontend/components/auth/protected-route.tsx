"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "@/components/auth/auth-provider";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isLoading, user } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [isLoading, pathname, router, user]);

  if (isLoading || !user) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-slate-300">
        <div className="h-10 w-10 rounded-full border-2 border-slate-800 border-t-cyan-400" aria-label="Loading" />
      </main>
    );
  }

  return <>{children}</>;
}
