export const BOOTSTRAP_HYDRATION_PATCH_KEY = Symbol.for(
  "scientific-spaces.bootstrap-hydration-workaround",
);

export const SUPPORTED_BOOTSTRAP_NEXT_VERSION = "15.5.21";
export const SUPPORTED_BOOTSTRAP_REACT_VERSION = "19.2.0-canary-0bdb9206-20250818";

// Next 15.5.21 starts App Router hydration inside a transition. Its bundled
// React canary can yield with a stale hydration cursor, so only that exact
// bootstrap call is taken out of transition context; every later call delegates.

type TransitionScope = () => void;
type StartTransition = (scope: TransitionScope) => void;

type ReactRuntime = {
  startTransition: StartTransition;
  version?: string;
};

type NextRuntime = {
  appDir?: boolean;
  version?: string;
};

export type BootstrapHydrationWorkaroundOptions = {
  documentElementId: string;
  globalState: Record<PropertyKey, unknown>;
  nextRuntime: NextRuntime | undefined;
  nodeEnv: string | undefined;
  pendingScriptCount: number;
  reactRuntime: ReactRuntime;
  scheduleMicrotask: (callback: () => void) => void;
};

export function installBootstrapHydrationWorkaround({
  documentElementId,
  globalState,
  nextRuntime,
  nodeEnv,
  pendingScriptCount,
  reactRuntime,
  scheduleMicrotask,
}: BootstrapHydrationWorkaroundOptions): "installed" | "skipped" {
  if (
    nodeEnv !== "production" ||
    documentElementId === "__next_error__" ||
    pendingScriptCount > 0 ||
    nextRuntime?.appDir !== true ||
    nextRuntime.version !== SUPPORTED_BOOTSTRAP_NEXT_VERSION ||
    reactRuntime.version !== SUPPORTED_BOOTSTRAP_REACT_VERSION ||
    globalState[BOOTSTRAP_HYDRATION_PATCH_KEY]
  ) {
    return "skipped";
  }

  const descriptor = Object.getOwnPropertyDescriptor(
    reactRuntime,
    "startTransition",
  );
  if (
    !descriptor ||
    descriptor.writable !== true ||
    typeof descriptor.value !== "function"
  ) {
    return "skipped";
  }

  const startTransitionDescriptor = descriptor;
  const startTransition = startTransitionDescriptor.value as StartTransition;
  let consumed = false;
  let bootstrapTransition: StartTransition;

  function restore() {
    const current = Object.getOwnPropertyDescriptor(reactRuntime, "startTransition");
    if (current?.value === bootstrapTransition) {
      Object.defineProperty(reactRuntime, "startTransition", startTransitionDescriptor);
    }
  }

  bootstrapTransition = (scope) => {
    if (consumed) {
      return Reflect.apply(startTransition, reactRuntime, [scope]);
    }
    consumed = true;
    restore();
    scope();
  };

  try {
    Object.defineProperty(reactRuntime, "startTransition", {
      ...startTransitionDescriptor,
      value: bootstrapTransition,
    });
  } catch {
    return "skipped";
  }

  globalState[BOOTSTRAP_HYDRATION_PATCH_KEY] = true;
  scheduleMicrotask(() => {
    if (!consumed) {
      consumed = true;
      restore();
    }
  });
  return "installed";
}
