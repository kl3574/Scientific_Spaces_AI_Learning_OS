import React from "react";

import { installBootstrapHydrationWorkaround } from "@/lib/bootstrapHydration";

type NextWindow = Window & {
  next?: {
    appDir?: boolean;
    version?: string;
  };
};

type NextSelf = typeof self & {
  __next_s?: unknown[];
};

installBootstrapHydrationWorkaround({
  documentElementId: document.documentElement.id,
  globalState: globalThis as unknown as Record<PropertyKey, unknown>,
  nextRuntime: (window as NextWindow).next,
  nodeEnv: process.env.NODE_ENV,
  pendingScriptCount: (self as NextSelf).__next_s?.length ?? 0,
  reactRuntime: React,
  scheduleMicrotask: queueMicrotask,
});
