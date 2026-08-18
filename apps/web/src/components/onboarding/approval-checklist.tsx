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

  return (
    <section className="text-card-foreground" aria-labelledby="approval-checklist-title">
      <div className="flex items-start justify-between gap-3 border-b pb-4">
        <div>
          <div className="dossier-label">Final authority</div>
          <h3 id="approval-checklist-title" className="mt-1 text-[15px] font-semibold">
            Release checklist
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
        <div className="mt-5 border border-dashed p-4 text-sm leading-6 text-muted-foreground">
          Checklist appears after the policy draft is generated.
        </div>
      ) : (
        <div className="pt-5">
          {incompleteBlockers.length > 0 && (
            <div className="border border-[var(--warning-border)] bg-[var(--warning-soft)] p-3 text-xs leading-5 text-[var(--warning)]">
              {incompleteBlockers.length} blocking checklist items remain.
            </div>
          )}
          <div className="mt-4 border-t">
            {items.map((item, index) => (
              <label
                key={item.id}
                className="grid cursor-pointer grid-cols-[32px_20px_minmax(0,1fr)_auto] items-start gap-3 border-b py-4 text-sm hover:bg-[var(--workspace)]"
              >
                <span className="dossier-label mt-0.5 text-[var(--cobalt)]">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <Checkbox
                  checked={item.checked}
                  disabled={updatingItemId === item.id}
                  onCheckedChange={(value) =>
                    void onUpdateItem(item.id, Boolean(value))
                  }
                  aria-label={item.label}
                />
                <span className="grid gap-1">
                  <span className="font-semibold leading-5">{item.label}</span>
                  <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    {item.blocks_release ? (
                      <>
                        <LockKeyhole className="size-3" />
                        Blocks release until checked
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="size-3" />
                        Review note
                      </>
                    )}
                  </span>
                </span>
                {updatingItemId === item.id && (
                  <Loader2 className="mt-0.5 size-4 animate-spin text-muted-foreground" />
                )}
              </label>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
