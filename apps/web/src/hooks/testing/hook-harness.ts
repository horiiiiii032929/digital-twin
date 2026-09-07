// Minimal deterministic React-hook adapter for deferred-request tests in Vitest's
// Node environment. Exercises hook logic; does not claim browser/DOM coverage.
export function createHookHarness() {
  let slots: unknown[] = [], cursor = 0
  let effects: Array<() => void> = []
  const same = (a: unknown[] | undefined, b: unknown[] | undefined) =>
    Boolean(a && b && a.length === b.length && a.every((x, i) => Object.is(x, b[i])))
  return {
    react: {
      useState(initial: unknown) {
        const i = cursor++
        if (!(i in slots)) slots[i] = typeof initial === 'function' ? initial() : initial
        return [slots[i], (value: unknown) => { slots[i] = typeof value === 'function' ? value(slots[i]) : value }]
      },
      useRef(initial: unknown) {
        const i = cursor++
        if (!(i in slots)) slots[i] = { current: initial }
        return slots[i]
      },
      useCallback(callback: unknown, deps: unknown[]) {
        const i = cursor++, old = slots[i] as { value: unknown; deps: unknown[] } | undefined
        if (!old || !same(old.deps, deps)) slots[i] = { value: callback, deps }
        return (slots[i] as { value: unknown }).value
      },
      useEffect(callback: () => void | (() => void), deps: unknown[]) {
        const i = cursor++, old = slots[i] as { deps: unknown[]; cleanup?: () => void } | undefined
        if (!old || !same(old.deps, deps)) effects.push(() => {
          old?.cleanup?.()
          slots[i] = { deps, cleanup: callback() }
        })
      },
    },
    render<T>(hook: () => T): T { cursor = 0; const value = hook(); const pending = effects; effects = []; pending.forEach(effect => effect()); return value },
    reset() { slots = []; effects = []; cursor = 0 },
  }
}
export function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason: unknown) => void
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
