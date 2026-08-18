export type StudentRequestIdRuntime = {
  randomUUID?: (() => string) | null
  now?: () => number
  random?: () => number
}

export function createStudentRequestId(
  runtime: StudentRequestIdRuntime = {},
): string {
  const randomUUID =
    runtime.randomUUID === undefined
      ? globalThis.crypto?.randomUUID?.bind(globalThis.crypto)
      : runtime.randomUUID
  const uuid = randomUUID?.()
  if (uuid) return uuid

  const now = runtime.now ?? Date.now
  const random = runtime.random ?? Math.random
  return `student-request-${now()}-${random().toString(36).slice(2, 12)}`
}
