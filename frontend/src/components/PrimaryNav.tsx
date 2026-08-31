"use client";

import Link from "next/link";

import { PRIMARY_NAVIGATION, isNavigationItemActive } from "@/lib/navigation";

export function PrimaryNav({
  activePathname,
  variant = "rail",
  onNavigate,
}: Readonly<{
  activePathname: string | null;
  variant?: "rail" | "drawer";
  onNavigate?: () => void;
}>) {
  return (
    <nav aria-label="Primary" className="w-full" data-variant={variant}>
      <ul className="grid gap-1.5">
        {PRIMARY_NAVIGATION.map((item) => {
          const active = activePathname !== null && isNavigationItemActive(activePathname, item);
          return (
            <li key={item.href}>
              <Link
                aria-current={active ? "page" : undefined}
                className={
                  active
                    ? "flex min-h-11 items-center gap-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-sm font-semibold text-emerald-950"
                    : "flex min-h-11 items-center gap-3 rounded-md border border-transparent px-3 py-2.5 text-sm font-medium text-slate-600 hover:border-slate-200 hover:bg-slate-50 hover:text-slate-950"
                }
                data-testid={`primary-nav-${item.id}`}
                href={item.href}
                onClick={onNavigate}
              >
                <span
                  aria-hidden="true"
                  className={`h-2 w-2 shrink-0 rounded-sm ${active ? "bg-emerald-600" : "bg-slate-300"}`}
                />
                <span>{item.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
