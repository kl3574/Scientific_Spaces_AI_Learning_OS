(() => {
  "use strict";

  const targetId = "article:attention-basics";
  const expectedVersion = "19.2.0-canary-0bdb9206-20250818";
  const events = [];
  const renderers = [];
  const identities = new WeakMap();
  const flags = { capture_error: false, overflow: false, coverage_incomplete: false, error: "none" };
  let nextIdentity = 1;
  let commitCount = 0;

  function fail(error, overflow = false) {
    flags.capture_error = true;
    flags.coverage_incomplete = true;
    flags.overflow ||= overflow;
    if (flags.error === "none") flags.error = error;
  }

  function identity(object, alternate = null) {
    if (!object || typeof object !== "object") throw new Error();
    let id = identities.get(object) || (alternate && identities.get(alternate));
    if (!id) id = nextIdentity++;
    identities.set(object, id);
    if (alternate && typeof alternate === "object") identities.set(alternate, id);
    return id;
  }

  function push(event) {
    if (events.length >= 512) {
      fail("event_budget", true);
      return;
    }
    events.push(event);
  }

  function hooksOf(fiber) {
    const hooks = [];
    const seen = new Set();
    for (let hook = fiber.memoizedState; hook; hook = hook.next) {
      if (seen.has(hook)) {
        fail("hook_cycle");
        return null;
      }
      if (hooks.length >= 128) {
        fail("hook_budget", true);
        return null;
      }
      seen.add(hook);
      hooks.push(hook);
    }
    return hooks;
  }

  function effectBelongs(fiber, wanted) {
    const last = fiber.updateQueue?.lastEffect;
    if (!last?.next) return false;
    const first = last.next;
    const seen = new Set();
    let effect = first;
    let found = false;
    while (effect) {
      if (seen.has(effect)) {
        if (effect !== first) fail("effect_cycle");
        return effect === first && found;
      }
      if (seen.size >= 64) {
        fail("effect_budget", true);
        return false;
      }
      seen.add(effect);
      found ||= effect === wanted;
      effect = effect.next;
    }
    return false;
  }

  function passive(effect, deps) {
    return effect && (effect.tag & 8) !== 0 && Array.isArray(effect.deps) &&
      effect.deps.length === deps.length && deps.every((item, index) => Object.is(item, effect.deps[index]));
  }

  function inspectTarget(host, ancestors) {
    const candidates = [];
    for (const fiber of ancestors) {
      if (fiber.memoizedProps?.id !== targetId || !fiber.memoizedState) continue;
      const hooks = hooksOf(fiber);
      if (!hooks || flags.capture_error) return null;
      for (let index = 0; index < hooks.length; index++) {
        if (hooks[index].memoizedState !== host.ref || !host.ref || host.ref.current !== host.stateNode) continue;
        const nearby = hooks.slice(index, index + 8).map((hook) => hook.memoizedState);
        if (nearby.length !== 8) continue;
        const effect = nearby[5];
        if (nearby[2]?.current !== "right" || nearby[3]?.current !== "left" || nearby[4]?.current !== "knowledge") continue;
        if (!effect || (effect.tag & 8) === 0 || !Array.isArray(effect.deps) || effect.deps.length !== 2) continue;
        if (typeof effect.deps[0] !== "boolean" || ![undefined, false, true].includes(effect.deps[1])) continue;
        if (!passive(nearby[6], []) || !passive(nearby[7], [targetId, "knowledge", "right", "left"])) continue;
        if (!effectBelongs(fiber, effect) || flags.capture_error) continue;
        candidates.push({ fiber, effect });
      }
    }
    if (flags.capture_error) return null;
    if (candidates.length !== 1) {
      fail(candidates.length ? "ambiguous_selector" : "missing_selector");
      return null;
    }
    const { fiber, effect } = candidates[0];
    return {
      wrapper: identity(host.stateNode),
      fiber: identity(fiber, fiber.alternate),
      initialized: effect.deps[0],
      hidden: effect.deps[1] === undefined ? "undefined" : effect.deps[1] ? "true" : "false",
      selected: host.memoizedProps.className.split(/\s+/).includes("selected"),
    };
  }

  function capture(renderer, root) {
    commitCount++;
    if (flags.capture_error) return;
    if (!Number.isInteger(renderer) || renderer < 1 || renderer > renderers.length) {
      fail("missing_renderer");
      return;
    }
    if (!root?.current) {
      fail("missing_root");
      return;
    }
    const stack = [{ fiber: root.current, ancestors: [] }];
    const seen = new Set();
    const targets = [];
    while (stack.length) {
      const { fiber, ancestors } = stack.pop();
      if (!fiber || seen.has(fiber)) {
        fail("fiber_cycle");
        return;
      }
      if (seen.size >= 4096 || ancestors.length > 128) {
        fail("fiber_budget", true);
        return;
      }
      seen.add(fiber);
      const props = fiber.memoizedProps;
      if (fiber.tag === 5 && props?.["data-id"] === targetId && props["data-testid"] === `rf__node-${targetId}` &&
          typeof props.className === "string" && props.className.split(/\s+/).includes("react-flow__node") &&
          ancestors.some((ancestor) => ancestor.memoizedProps?.["data-testid"] === "graph-visualization")) {
        targets.push({ host: fiber, ancestors });
      }
      if (fiber.sibling) stack.push({ fiber: fiber.sibling, ancestors });
      if (fiber.child) stack.push({ fiber: fiber.child, ancestors: [...ancestors, fiber] });
    }
    if (targets.length > 1) {
      fail("ambiguous_target");
      return;
    }
    const sample = targets.length ? inspectTarget(targets[0].host, targets[0].ancestors) : null;
    if (flags.capture_error) return;
    const time = performance.now();
    if (!Number.isFinite(time)) {
      fail("invalid_clock");
      return;
    }
    push({ sequence: commitCount, time, renderer, root: identity(root), present: sample !== null, ...(sample || {}) });
  }

  window.__scientificGraphProbe = Object.freeze({
    snapshot: () => ({
      schema_version: 1,
      ...flags,
      commit_count: commitCount,
      renderers: renderers.map((renderer) => ({ ...renderer })),
      events: events.map((event) => ({ ...event })),
    }),
  });
  if ("__REACT_DEVTOOLS_GLOBAL_HOOK__" in window) {
    fail("existing_hook");
    return;
  }
  window.__REACT_DEVTOOLS_GLOBAL_HOOK__ = {
    supportsFiber: true,
    inject(renderer) {
      try {
        if (renderers.length >= 4) {
          fail("renderer_budget", true);
          return 0;
        }
        const valid = renderer?.version === expectedVersion && renderer.reconcilerVersion === expectedVersion &&
          renderer.rendererPackageName === "react-dom" && renderer.bundleType === 0;
        const id = renderers.length + 1;
        renderers.push({ id, version: valid ? expectedVersion : "unrecognized", package: valid ? "react-dom" : "unrecognized" });
        if (!valid) fail("renderer_metadata");
        return id;
      } catch {
        fail("capture_exception");
        return 0;
      }
    },
    onCommitFiberRoot(renderer, root) {
      try {
        capture(renderer, root);
      } catch {
        fail("capture_exception");
      }
    },
  };
})();
