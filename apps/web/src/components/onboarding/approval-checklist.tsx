import { useMemo } from "react"
import { CheckCircle2, Loader2, LockKeyhole } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import type { ApprovalItem } from "@/lib/api/types"

type ApprovalChecklistProps = {
  items: ApprovalItem[]
  releaseStatus: string
  updatingItemId: string | null
  onUpdateItem: (itemId: string, checked: boolean) => Promise<void>
}

export function ApprovalChecklist({
  items,
  releaseStatus,
  updatingItemId,
  onUpdateItem,
}: ApprovalChecklistProps) {
  const incompleteBlockers = useMemo(
    () => items.filter((item) => item.blocks_release && !item.checked),
    [items],
  )
  const pendingItems = useMemo(
    () => items.filter((item) => !item.checked),
    [items],
  )
  const completedItems = useMemo(
    () => items.filter((item) => item.checked),
    [items],
  )

  return (
    <section className="p-5 text-card-foreground sm:p-6" aria-labelledby="approval-checklist-title">
      <div className="flex items-start justify-between gap-3 border-b pb-5 pr-11">
        <div>
          <h3 id="approval-checklist-title" className="text-lg font-semibold tracking-[-0.02em]">
            Approval
          </h3>
          <p className="mt-1 text-sm leading-5 text-muted-foreground">
            Local professor review checklist for the draft release gate.
          </p>
        </div>
        <Badge
          variant="outline"
          className={
            releaseStatus === "approved"
              ? "status-badge status-badge-success"
              : "status-badge status-badge-warning"
          }
        >
          {releaseStatus === "approved" ? "approved" : "draft only"}
        </Badge>
      </div>

      {items.length === 0 ? (
          <div className="mt-5 rounded-xl border border-dashed p-5 text-sm leading-6 text-muted-foreground">
          Checklist appears after the policy draft is generated.
        </div>
      ) : (
        <div className="pt-5">
          <div
            className="flex flex-wrap gap-x-4 gap-y-1 rounded-lg bg-[var(--shell)] px-3 py-2.5 text-xs font-medium"
            aria-label={`${completedItems.length} of ${items.length} approval checks complete`}
          >
            <span className="text-[var(--success)]">
              {completedItems.length} complete
            </span>
            <span className="text-[var(--warning)]">
              {pendingItems.length} remaining
            </span>
          </div>

          {incompleteBlockers.length > 0 && (
            <div className="mt-3 rounded-lg bg-[var(--warning-soft)] p-3 text-xs leading-5 text-[var(--warning)]">
              {incompleteBlockers.length} blocking checklist items remain.
            </div>
          )}
          {pendingItems.length > 0 ? (
            <div className="mt-4 overflow-hidden rounded-xl border">
              {pendingItems.map((item) => (
                <ChecklistRow
                  key={item.id}
                  item={item}
                  isUpdating={updatingItemId === item.id}
                  onUpdateItem={onUpdateItem}
                />
              ))}
            </div>
          ) : (
            <p className="mt-4 rounded-lg bg-[var(--success-soft)] p-3 text-sm leading-5 text-[var(--success)]">
              Every local approval check is complete.
            </p>
          )}

          {completedItems.length > 0 ? (
            <details className="mt-4 overflow-hidden rounded-xl border">
              <summary className="min-h-11 cursor-pointer list-none px-4 py-3 text-sm font-semibold outline-none hover:bg-[var(--shell)] focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring/30 [&::-webkit-details-marker]:hidden">
                Show completed checks ({completedItems.length})
              </summary>
              <div className="border-t bg-[var(--shell)]">
                {completedItems.map((item) => (
                  <ChecklistRow
                    key={item.id}
                    item={item}
                    isUpdating={updatingItemId === item.id}
                    onUpdateItem={onUpdateItem}
                  />
                ))}
              </div>
            </details>
          ) : null}
        </div>
      )}
    </section>
  )
}

function ChecklistRow({
  item,
  isUpdating,
  onUpdateItem,
}: {
  item: ApprovalItem
  isUpdating: boolean
  onUpdateItem: (itemId: string, checked: boolean) => Promise<void>
}) {
  return (
    <label className="grid cursor-pointer grid-cols-[20px_minmax(0,1fr)_16px] items-start gap-3 border-b p-4 text-sm last:border-b-0 hover:bg-[var(--shell)]">
      <Checkbox
        checked={item.checked}
        disabled={isUpdating}
        onCheckedChange={(value) => void onUpdateItem(item.id, Boolean(value))}
        aria-label={`Mark ${item.label} ${item.checked ? "incomplete" : "complete"}`}
      />
      <span className="grid gap-1">
        <span className="font-semibold leading-5">{item.label}</span>
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
          {item.blocks_release ? (
            <>
              <LockKeyhole className="size-3" aria-hidden="true" />
              Blocks release until checked
            </>
          ) : (
            <>
              <CheckCircle2 className="size-3" aria-hidden="true" />
              Review note
            </>
          )}
        </span>
      </span>
      {isUpdating ? (
        <Loader2
          className="mt-0.5 size-4 animate-spin text-muted-foreground"
          aria-hidden="true"
        />
      ) : null}
    </label>
  )
}
