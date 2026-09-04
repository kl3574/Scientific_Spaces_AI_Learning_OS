import assert from "node:assert/strict";
import test from "node:test";

import {
  BOOTSTRAP_HYDRATION_PATCH_KEY,
  SUPPORTED_BOOTSTRAP_NEXT_VERSION,
  SUPPORTED_BOOTSTRAP_REACT_VERSION,
  installBootstrapHydrationWorkaround,
} from "../src/lib/bootstrapHydration";

function matchingOptions() {
  const calls: string[] = [];
  const microtasks: Array<() => void> = [];
  const originalTransition = (scope: () => void) => {
    calls.push("transition");
    scope();
  };
  const reactRuntime = {
    startTransition: originalTransition,
    version: SUPPORTED_BOOTSTRAP_REACT_VERSION,
  };
  const globalState: Record<PropertyKey, unknown> = {};

  return {
    calls,
    globalState,
    microtasks,
    options: {
      documentElementId: "",
      globalState,
      nextRuntime: { appDir: true, version: SUPPORTED_BOOTSTRAP_NEXT_VERSION },
      nodeEnv: "production",
      pendingScriptCount: 0,
      reactRuntime,
      scheduleMicrotask: (callback: () => void) => microtasks.push(callback),
    },
    originalTransition,
    reactRuntime,
  };
}

test("bootstrap hydration runs outside a transition and restores the runtime", () => {
  const fixture = matchingOptions();
  const originalDescriptor = Object.getOwnPropertyDescriptor(
    fixture.reactRuntime,
    "startTransition",
  );
  assert.equal(installBootstrapHydrationWorkaround(fixture.options), "installed");
  const capturedTransition = fixture.reactRuntime.startTransition;

  capturedTransition(() => fixture.calls.push("hydrate"));

  assert.deepEqual(fixture.calls, ["hydrate"]);
  assert.equal(fixture.reactRuntime.startTransition, fixture.originalTransition);
  assert.deepEqual(
    Object.getOwnPropertyDescriptor(fixture.reactRuntime, "startTransition"),
    originalDescriptor,
  );
  assert.equal(fixture.globalState[BOOTSTRAP_HYDRATION_PATCH_KEY], true);

  capturedTransition(() => fixture.calls.push("navigate"));
  assert.deepEqual(fixture.calls, ["hydrate", "transition", "navigate"]);
});

test("an unconsumed patch expires before a later application transition", () => {
  const fixture = matchingOptions();
  installBootstrapHydrationWorkaround(fixture.options);
  const capturedTransition = fixture.reactRuntime.startTransition;

  assert.equal(fixture.microtasks.length, 1);
  fixture.microtasks[0]();
  capturedTransition(() => fixture.calls.push("later"));

  assert.equal(fixture.reactRuntime.startTransition, fixture.originalTransition);
  assert.deepEqual(fixture.calls, ["transition", "later"]);
});

test("unsupported or unsafe bootstrap contexts fail open", () => {
  const variants = [
    { nodeEnv: "development" },
    { documentElementId: "__next_error__" },
    { pendingScriptCount: 1 },
    { nextRuntime: { appDir: true, version: "15.5.22" } },
    { reactRuntime: { startTransition: () => undefined, version: "19.2.0" } },
  ];

  for (const variant of variants) {
    const fixture = matchingOptions();
    const options = { ...fixture.options, ...variant };
    const initialTransition = options.reactRuntime.startTransition;
    assert.equal(installBootstrapHydrationWorkaround(options), "skipped");
    assert.equal(options.reactRuntime.startTransition, initialTransition);
    assert.equal(fixture.globalState[BOOTSTRAP_HYDRATION_PATCH_KEY], undefined);
  }
});

test("duplicate installation and a non-writable runtime fail open", () => {
  const duplicate = matchingOptions();
  duplicate.globalState[BOOTSTRAP_HYDRATION_PATCH_KEY] = true;
  assert.equal(installBootstrapHydrationWorkaround(duplicate.options), "skipped");
  assert.equal(
    duplicate.reactRuntime.startTransition,
    duplicate.originalTransition,
  );

  const immutable = matchingOptions();
  Object.defineProperty(immutable.reactRuntime, "startTransition", {
    configurable: false,
    enumerable: true,
    value: immutable.originalTransition,
    writable: false,
  });
  assert.equal(installBootstrapHydrationWorkaround(immutable.options), "skipped");
  assert.equal(
    immutable.reactRuntime.startTransition,
    immutable.originalTransition,
  );
  assert.equal(immutable.globalState[BOOTSTRAP_HYDRATION_PATCH_KEY], undefined);
});
