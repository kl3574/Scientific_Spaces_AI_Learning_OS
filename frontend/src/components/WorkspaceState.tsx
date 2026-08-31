import type { ReactNode } from "react";

type WorkspaceStateTone = "loading" | "empty" | "error" | "unavailable";

const toneClasses: Record<WorkspaceStateTone, string> = {
  loading: "border-slate-300 bg-white text-slate-700",
  empty: "border-slate-300 bg-white text-slate-700",
  error: "border-red-300 bg-red-50 text-red-900",
  unavailable: "border-amber-300 bg-amber-50 text-amber-950",
};

export function WorkspaceState({
  tone,
  title,
  detail,
  action,
  testId,
}: Readonly<{
  tone: WorkspaceStateTone;
  title: string;
  detail?: string | null;
  action?: ReactNode;
  testId?: string;
}>) {
  const isError = tone === "error";

  return (
    <section
      aria-live={isError ? "assertive" : "polite"}
      className={`border-y px-1 py-4 ${toneClasses[tone]}`}
      data-testid={testId}
      role={isError ? "alert" : "status"}
    >
      <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="text-sm font-semibold">{title}</p>
          {detail ? <p className="mt-1 break-words text-sm leading-6 opacity-80">{detail}</p> : null}
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
    </section>
  );
}
