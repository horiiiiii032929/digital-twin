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
    <section className="rounded-lg border bg-card p-4 text-card-foreground">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">Approval Checklist</h2>
          <p className="text-xs text-muted-foreground">
            Local professor review checklist for the draft release gate.
          </p>
        </div>
        <Badge variant={releaseStatus === "approved" ? "default" : "outline"}>
          {releaseStatus === "approved" ? "approved" : "draft only"}
        </Badge>
      </div>

      {items.length === 0 ? (
        <div className="rounded-lg border border-dashed p-3 text-sm text-muted-foreground">
          Checklist appears after the policy draft is generated.
        </div>
      ) : (
        <div className="space-y-3">
          {incompleteBlockers.length > 0 && (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800">
              {incompleteBlockers.length} blocking checklist items remain.
            </div>
          )}
          <div className="space-y-3">
            {items.map((item) => (
              <label
                key={item.id}
                className="flex cursor-pointer items-start gap-3 rounded-lg border bg-background p-3 text-sm"
              >
                <Checkbox
                  checked={item.checked}
                  disabled={updatingItemId === item.id}
                  onCheckedChange={(value) =>
                    void onUpdateItem(item.id, Boolean(value))
                  }
                  aria-label={item.label}
                />
                <span className="grid gap-1">
                  <span className="font-medium">{item.label}</span>
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
                  <Loader2 className="ml-auto mt-0.5 size-4 animate-spin text-muted-foreground" />
                )}
              </label>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
