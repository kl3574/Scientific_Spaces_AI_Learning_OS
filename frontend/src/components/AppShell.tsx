"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { KeyboardEvent as ReactKeyboardEvent, ReactNode } from "react";
import { useEffect, useRef, useState } from "react";

import { GlobalSearchDialog } from "@/components/GlobalSearchDialog";
import { PrimaryNav } from "@/components/PrimaryNav";
import { resolveWorkspaceLocation } from "@/lib/navigation";

export function AppShell({ children }: Readonly<{ children: ReactNode }>) {
  const pathname = usePathname();
  const [hydrated, setHydrated] = useState(false);
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement | null>(null);
  const drawerRef = useRef<HTMLDivElement | null>(null);
  const searchReturnFocusRef = useRef<HTMLElement | null>(null);
  const location = hydrated
    ? resolveWorkspaceLocation(pathname)
    : { id: "unknown" as const, label: "Workspace", trail: ["Workspace"] };

  useEffect(() => {
    setHydrated(true);
  }, []);

  useEffect(() => {
    setNavigationOpen(false);
    setSearchOpen(false);
  }, [pathname]);

  useEffect(() => {
    function handleGlobalShortcut(event: globalThis.KeyboardEvent) {
      const target = event.target;
      const editable =
        target instanceof HTMLElement &&
        (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName));
      const commandShortcut = (event.metaKey || event.ctrlKey) && event.key.toLocaleLowerCase() === "k";
      const slashShortcut =
        event.key === "/" && !event.metaKey && !event.ctrlKey && !event.altKey && !editable;
      if (!commandShortcut && !slashShortcut) {
        return;
      }
      event.preventDefault();
      if (searchOpen) {
        return;
      }
      searchReturnFocusRef.current =
        document.activeElement instanceof HTMLElement ? document.activeElement : null;
      setNavigationOpen(false);
      setSearchOpen(true);
    }

    window.addEventListener("keydown", handleGlobalShortcut);
    return () => window.removeEventListener("keydown", handleGlobalShortcut);
  }, [searchOpen]);

  useEffect(() => {
    if (!navigationOpen) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    const focusFrame = window.requestAnimationFrame(() => {
      drawerRef.current?.querySelector<HTMLElement>("[data-drawer-autofocus]")?.focus();
    });
    document.body.style.overflow = "hidden";

    return () => {
      window.cancelAnimationFrame(focusFrame);
      document.body.style.overflow = previousOverflow;
    };
  }, [navigationOpen]);

  function closeNavigation(restoreFocus: boolean) {
    setNavigationOpen(false);
    if (restoreFocus) {
      window.requestAnimationFrame(() => menuButtonRef.current?.focus());
    }
  }

  function handleDrawerKeyDown(event: ReactKeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      closeNavigation(true);
      return;
    }
    if (event.key !== "Tab") {
      return;
    }

    const focusable = Array.from(
      drawerRef.current?.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
      ) ?? [],
    );
    if (focusable.length === 0) {
      return;
    }

    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function openSearch(trigger: HTMLElement | null) {
    searchReturnFocusRef.current = trigger;
    setNavigationOpen(false);
    setSearchOpen(true);
  }

  function closeSearch(restoreFocus: boolean) {
    setSearchOpen(false);
    if (restoreFocus) {
      window.requestAnimationFrame(() => searchReturnFocusRef.current?.focus());
    }
  }

  return (
    <div
      className="min-h-screen bg-slate-50 text-slate-950 lg:grid lg:grid-cols-[15rem_minmax(0,1fr)]"
      data-hydrated={hydrated ? "true" : "false"}
      data-testid="application-shell"
      data-workspace={hydrated ? location.id : "pending"}
    >
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>

      <aside className="hidden h-screen border-r border-slate-200 bg-white lg:sticky lg:top-0 lg:flex lg:flex-col">
        <div className="border-b border-slate-200 px-5 py-5">
          <Brand />
        </div>
        <div className="px-3 pt-4">
          <SearchTrigger
            testId="global-search-trigger-desktop"
            onOpen={(trigger) => openSearch(trigger)}
          />
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-3 py-4">
          <PrimaryNav activePathname={hydrated ? pathname : null} />
        </div>
        <div className="border-t border-slate-200 px-5 py-4 text-xs text-slate-500">
          Scientific learning workspace
        </div>
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur lg:hidden">
          <div className="flex min-h-16 items-center justify-between gap-2 px-4 py-2.5">
            <Brand compact currentLabel={location.label} />
            <div className="flex shrink-0 items-center gap-2">
              <SearchTrigger
                compact
                testId="global-search-trigger-mobile"
                onOpen={(trigger) => openSearch(trigger)}
              />
              <button
                ref={menuButtonRef}
                aria-controls="mobile-primary-navigation"
                aria-expanded={navigationOpen}
                aria-label="Open navigation"
                className="min-h-11 rounded-md border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-800 hover:border-slate-500 hover:bg-slate-50"
                type="button"
                onClick={() => setNavigationOpen(true)}
              >
                Menu
              </button>
            </div>
          </div>
        </header>

        {navigationOpen ? (
          <div className="fixed inset-0 z-50 lg:hidden" data-testid="mobile-navigation">
            <button
              aria-label="Close navigation overlay"
              className="absolute inset-0 bg-slate-950/40"
              type="button"
              onClick={() => closeNavigation(true)}
            />
            <div
              ref={drawerRef}
              aria-label="Application navigation"
              aria-modal="true"
              className="absolute inset-y-0 right-0 flex w-[min(20rem,calc(100%-3rem))] flex-col border-l border-slate-200 bg-white shadow-xl"
              id="mobile-primary-navigation"
              role="dialog"
              onKeyDown={handleDrawerKeyDown}
            >
              <div className="flex min-h-16 items-center justify-between gap-3 border-b border-slate-200 px-4">
                <p className="text-sm font-semibold text-slate-950">Navigation</p>
                <button
                  aria-label="Close navigation"
                  className="min-h-11 rounded-md border border-slate-300 px-3 text-sm font-semibold text-slate-700 hover:border-slate-500 hover:bg-slate-50"
                  data-drawer-autofocus
                  type="button"
                  onClick={() => closeNavigation(true)}
                >
                  Close
                </button>
              </div>
              <div className="min-h-0 flex-1 overflow-y-auto px-3 py-5">
                <PrimaryNav
                  activePathname={hydrated ? pathname : null}
                  variant="drawer"
                  onNavigate={() => closeNavigation(false)}
                />
              </div>
            </div>
          </div>
        ) : null}

        <GlobalSearchDialog open={searchOpen} onClose={closeSearch} />

        <p aria-atomic="true" aria-live="polite" className="sr-only">
          Current workspace: {location.label}
        </p>

        <div
          className="hidden border-b border-slate-200 bg-white px-6 py-2.5 lg:sticky lg:top-0 lg:z-30 lg:block"
          data-testid="workspace-context"
        >
          <nav aria-label="Breadcrumb">
            <ol className="flex min-w-0 items-center gap-2 text-xs font-medium text-slate-500">
              {location.trail.map((label, index) => {
                const current = index === location.trail.length - 1;
                return (
                  <li key={`${label}-${index}`} className="flex min-w-0 items-center gap-2">
                    {index > 0 ? <span aria-hidden="true" className="text-slate-300">/</span> : null}
                    <span
                      aria-current={current ? "page" : undefined}
                      className={current ? "truncate font-semibold text-slate-800" : "truncate"}
                    >
                      {label}
                    </span>
                  </li>
                );
              })}
            </ol>
          </nav>
        </div>

        <main id="main-content" className="mx-auto w-full min-w-0 max-w-7xl px-4 py-5 sm:px-6 sm:py-7">
          {children}
        </main>
      </div>
    </div>
  );
}

function SearchTrigger({
  compact = false,
  testId,
  onOpen,
}: Readonly<{
  compact?: boolean;
  testId: string;
  onOpen: (trigger: HTMLButtonElement) => void;
}>) {
  return (
    <button
      aria-haspopup="dialog"
      aria-label="Open global search"
      className={`${compact ? "px-3" : "w-full px-3"} flex min-h-11 items-center rounded-md border border-slate-300 bg-white text-sm font-semibold text-slate-700 hover:border-slate-500 hover:bg-slate-50`}
      data-testid={testId}
      type="button"
      onClick={(event) => onOpen(event.currentTarget)}
    >
      <span>Search</span>
    </button>
  );
}

function Brand({ compact = false, currentLabel }: Readonly<{ compact?: boolean; currentLabel?: string }>) {
  return (
    <Link
      aria-label="Scientific Spaces AI Learning OS home"
      className="flex min-w-0 flex-1 items-center gap-3 text-slate-950"
      href="/"
    >
      <span
        aria-hidden="true"
        className={`${compact ? "h-8 w-8 text-[10px]" : "h-9 w-9 text-xs"} flex shrink-0 items-center justify-center rounded-md bg-amber-400 font-black text-slate-950`}
      >
        SS
      </span>
      <span className="min-w-0">
        <span className="block truncate text-sm font-bold">Scientific Spaces</span>
        <span className="block truncate text-xs text-slate-500">
          {compact && currentLabel ? currentLabel : "AI Learning OS"}
        </span>
      </span>
    </Link>
  );
}
