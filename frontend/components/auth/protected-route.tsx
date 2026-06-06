"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "@/components/auth/auth-provider";
import { LoadingState } from "@/components/app/page-primitives";

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
      <main className="app-page-bg flex min-h-screen items-center justify-center px-6 text-slate-700">
        <div className="w-full max-w-md">
          <LoadingState label="Preparing secure workspace" rows={2} />
        </div>
      </main>
    );
  }

  return <>{children}</>;
}
