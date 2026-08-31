import Link from "next/link";

import { WorkspaceState } from "@/components/WorkspaceState";

export default function NotFound() {
  return (
    <WorkspaceState
      action={
        <div className="flex flex-wrap gap-2">
          <Link
            className="rounded-md bg-slate-950 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-800"
            href="/"
          >
            Dashboard
          </Link>
          <Link
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:border-slate-500"
            href="/articles"
          >
            Articles
          </Link>
        </div>
      }
      detail="The requested route is not part of this local learning workspace."
      testId="route-not-found-state"
      title="Page not found"
      tone="empty"
    />
  );
}
