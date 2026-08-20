import type { FieldStatus } from "@/lib/api/types"

export type FieldDraft = {
  status: FieldStatus
  value: string
}

export function mergePolicyDrafts(
  current: Record<string, FieldDraft>,
  previousServer: Record<string, FieldDraft>,
  nextServer: Record<string, FieldDraft>,
): Record<string, FieldDraft> {
  return Object.fromEntries(
    Object.entries(nextServer).map(([fieldId, nextServerDraft]) => {
      const currentDraft = current[fieldId]
      const previousServerDraft = previousServer[fieldId]
      const isDirty =
        currentDraft !== undefined &&
        previousServerDraft !== undefined &&
        (currentDraft.status !== previousServerDraft.status ||
          currentDraft.value !== previousServerDraft.value)
      return [fieldId, isDirty ? currentDraft : nextServerDraft]
    }),
  )
}
