// Scope protected-request failures to the authentication state that issued them.
let revision = 0
const listeners = new Set<() => void>()
export function sessionRevision() { return revision }
export function advanceSessionRevision() { revision += 1 }
export function onSessionExpired(listener: () => void) {
  listeners.add(listener)
  return () => { listeners.delete(listener) }
}
export function reportSessionExpired(requestRevision: number) {
  if (requestRevision !== revision) return
  advanceSessionRevision()
  listeners.forEach(listener => listener())
}
