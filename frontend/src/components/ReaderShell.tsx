import Link from "next/link";
import type { ReactNode } from "react";

import { PrimaryNav } from "@/components/PrimaryNav";

export function ReaderShell({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-slate-50/95 backdrop-blur">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-start gap-2 px-5 py-3 sm:flex-row sm:items-center sm:justify-between">
          <Link href="/" className="flex items-center gap-2 text-sm font-semibold text-slate-950">
            <span aria-hidden="true" className="h-2.5 w-2.5 bg-amber-500" />
            <span>Scientific Spaces AI Learning OS</span>
          </Link>
          <PrimaryNav />
        </div>
      </header>
      <main id="main-content" className="mx-auto w-full max-w-6xl px-5 py-6">
        {children}
      </main>
    </div>
  );
}
