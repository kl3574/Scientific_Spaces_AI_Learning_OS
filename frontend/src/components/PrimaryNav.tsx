"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navigationItems = [
  { href: "/", label: "Dashboard" },
  { href: "/articles", label: "Articles" },
  { href: "/zotero", label: "Zotero" },
  { href: "/graph", label: "Graph" },
  { href: "/tutor", label: "Tutor" },
];

export function PrimaryNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="Primary" className="grid w-full grid-cols-5 gap-1 sm:flex sm:w-auto sm:items-center sm:gap-1.5">
      {navigationItems.map((item) => {
        const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            aria-current={active ? "page" : undefined}
            className={
              active
                ? "min-w-0 rounded border border-emerald-700 bg-emerald-700 px-1.5 py-2 text-center text-[11px] font-semibold text-white sm:px-3 sm:text-sm"
                : "min-w-0 rounded border border-transparent px-1.5 py-2 text-center text-[11px] font-medium text-slate-600 hover:border-slate-200 hover:bg-white hover:text-slate-950 sm:px-3 sm:text-sm"
            }
            href={item.href}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
