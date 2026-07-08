import Link from "next/link";
import type { ReactNode } from "react";

export function ReaderShell({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-5 py-4">
          <Link href="/" className="text-sm font-semibold tracking-normal text-slate-950">
            Scientific Spaces AI Learning OS
          </Link>
          <nav className="flex items-center gap-2 text-sm">
            <Link className="rounded border border-slate-200 px-3 py-2 hover:bg-slate-50" href="/">
              Dashboard
            </Link>
            <Link className="rounded border border-slate-200 px-3 py-2 hover:bg-slate-50" href="/articles">
              Articles
            </Link>
            <Link className="rounded border border-slate-200 px-3 py-2 hover:bg-slate-50" href="/zotero">
              Zotero
            </Link>
          </nav>
        </div>
      </header>
      <div className="mx-auto w-full max-w-6xl px-5 py-6">{children}</div>
    </main>
  );
}
