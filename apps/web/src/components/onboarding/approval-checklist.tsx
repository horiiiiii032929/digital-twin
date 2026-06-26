import { useEffect, useMemo, useState } from "react"
import { CheckCircle2, LockKeyhole } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import type { ApprovalItem } from "@/lib/api"

type ApprovalChecklistProps = {
  items: ApprovalItem[]
}

export function ApprovalChecklist({ items }: ApprovalChecklistProps) {
  const [checked, setChecked] = useState<Record<string, boolean>>({})

  useEffect(() => {
    setChecked(
      Object.fromEntries(items.map((item) => [item.id, item.checked])) as Record<
        string,
        boolean
      >,
    )
  }, [items])

  const incompleteBlockers = useMemo(
    () => items.filter((item) => item.blocks_release && !checked[item.id]),
    [checked, items],
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
        <Badge variant={incompleteBlockers.length === 0 ? "default" : "outline"}>
          {incompleteBlockers.length === 0 ? "ready" : "draft only"}
        </Badge>
      </div>

      {items.length === 0 ? (
        <div className="rounded-lg border border-dashed p-3 text-sm text-muted-foreground">
          Checklist appears after the policy draft is generated.
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <label
              key={item.id}
              className="flex cursor-pointer items-start gap-3 rounded-lg border bg-background p-3 text-sm"
            >
              <Checkbox
                checked={Boolean(checked[item.id])}
                onCheckedChange={(value) =>
                  setChecked((current) => ({
                    ...current,
                    [item.id]: Boolean(value),
                  }))
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
            </label>
          ))}
        </div>
      )}
    </section>
  )
}
