"use client";

import { WorkspaceState } from "@/components/WorkspaceState";

export default function ErrorBoundary({
  error,
  reset,
}: Readonly<{
  error: Error & { digest?: string };
  reset: () => void;
}>) {
  return (
    <WorkspaceState
      action={
        <button
          className="rounded-md bg-red-800 px-3 py-2 text-sm font-semibold text-white hover:bg-red-900"
          type="button"
          onClick={reset}
        >
          Retry
        </button>
      }
      detail={error.message || "An unexpected route error occurred."}
      testId="route-error-state"
      title="This workspace could not be loaded"
      tone="error"
    />
  );
}
