import { useEffect, useMemo, useState } from "react"
import { Loader2, Save, ShieldAlert } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import type { FieldStatus, PolicyField, TutorPolicy } from "@/lib/api"
import { cn } from "@/lib/utils"

type PolicyReviewProps = {
  policy: TutorPolicy | null
  updatingFieldId: string | null
  onUpdateField: (
    fieldId: string,
    value: string | string[] | Record<string, unknown>,
    status: FieldStatus,
  ) => Promise<void>
}

type PolicyGroup = {
  title: string
  fields: PolicyField[]
}

const STATUS_OPTIONS: Array<{ value: FieldStatus; label: string }> = [
  { value: "resolved", label: "Resolved" },
  { value: "needs_review", label: "Review" },
  { value: "blocks_release", label: "Blocker" },
]

export function PolicyReview({
  policy,
  updatingFieldId,
  onUpdateField,
}: PolicyReviewProps) {
  const groups = useMemo<PolicyGroup[]>(
    () =>
      policy
        ? [
            { title: "Safety & Compliance", fields: policy.safety_compliance },
            { title: "Pedagogy", fields: policy.pedagogy },
            { title: "Professor Review", fields: policy.professor_review },
          ]
        : [],
    [policy],
  )
  const [drafts, setDrafts] = useState<Record<string, string>>({})

  useEffect(() => {
    if (!policy) {
      setDrafts({})
      return
    }

    setDrafts((current) => {
      const next = { ...current }

      for (const field of groups.flatMap((group) => group.fields)) {
        if (!(field.id in next)) {
          next[field.id] = fieldValueToText(field.value)
        }
      }

      return next
    })
  }, [groups, policy])

  return (
    <section className="rounded-lg border bg-card p-4 text-card-foreground">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">Tutor Policy</h2>
          <p className="text-xs text-muted-foreground">
            Editable fields generated from the instructor interview.
          </p>
        </div>
        <ReleaseBadge status={policy?.release_status ?? "draft"} />
      </div>

      {!policy ? (
        <div className="rounded-lg border border-dashed p-3 text-sm text-muted-foreground">
          Complete the interview to generate policy fields.
        </div>
      ) : (
        <div className="space-y-4">
          {groups.map((group) => (
            <div key={group.title} className="space-y-2">
              <h3 className="text-xs font-semibold uppercase tracking-normal text-muted-foreground">
                {group.title}
              </h3>
              {group.fields.map((field) => (
                <FieldEditor
                  key={field.id}
                  field={field}
                  draft={drafts[field.id] ?? fieldValueToText(field.value)}
                  isSaving={updatingFieldId === field.id}
                  onDraftChange={(value) =>
                    setDrafts((current) => ({
                      ...current,
                      [field.id]: value,
                    }))
                  }
                  onSave={(status) =>
                    onUpdateField(
                      field.id,
                      textToFieldValue(field.value, drafts[field.id] ?? ""),
                      status,
                    )
                  }
                />
              ))}
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function FieldEditor({
  field,
  draft,
  isSaving,
  onDraftChange,
  onSave,
}: {
  field: PolicyField
  draft: string
  isSaving: boolean
  onDraftChange: (value: string) => void
  onSave: (status: FieldStatus) => Promise<void>
}) {
  return (
    <div className="rounded-lg border bg-background p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="text-sm font-medium">{field.label}</div>
          <StatusLabel status={field.status} />
        </div>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => void onSave(field.status)}
          disabled={isSaving}
        >
          {isSaving ? (
            <Loader2 data-icon="inline-start" className="animate-spin" />
          ) : (
            <Save data-icon="inline-start" />
          )}
          Save
        </Button>
      </div>

      <Textarea
        value={draft}
        onChange={(event) => onDraftChange(event.target.value)}
        className="min-h-20 resize-y text-sm"
        aria-label={`${field.label} value`}
      />

      <div className="mt-2 flex flex-wrap gap-2">
        {STATUS_OPTIONS.map((option) => (
          <Button
            key={option.value}
            type="button"
            size="sm"
            variant={field.status === option.value ? "default" : "outline"}
            onClick={() => void onSave(option.value)}
            disabled={isSaving}
          >
            {option.label}
          </Button>
        ))}
      </div>

      {(field.warning || field.safe_default) && (
        <div className="mt-3 space-y-2 text-xs">
          {field.warning && (
            <p className="flex gap-2 rounded-md border border-amber-200 bg-amber-50 p-2 text-amber-800">
              <ShieldAlert className="mt-0.5 size-3.5 shrink-0" />
              {field.warning}
            </p>
          )}
          {field.safe_default && (
            <p className="rounded-md border border-sky-200 bg-sky-50 p-2 text-sky-800">
              Safe default: {field.safe_default}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

function ReleaseBadge({ status }: { status: string }) {
  return (
    <Badge
      variant={status === "approved" ? "default" : "outline"}
      className={cn(status === "blocked" && "border-red-200 text-red-700")}
    >
      {status.replace("_", " ")}
    </Badge>
  )
}

function StatusLabel({ status }: { status: FieldStatus }) {
  return (
    <div
      className={cn(
        "mt-0.5 text-xs font-medium",
        status === "resolved" && "text-emerald-700",
        status === "needs_review" && "text-amber-700",
        status === "blocks_release" && "text-red-700",
      )}
    >
      {status.replace("_", " ")}
    </div>
  )
}

function fieldValueToText(
  value: string | string[] | Record<string, unknown>,
): string {
  if (Array.isArray(value)) {
    return value.join("\n")
  }
  if (typeof value === "object") {
    return JSON.stringify(value, null, 2)
  }
  return value
}

function textToFieldValue(
  originalValue: string | string[] | Record<string, unknown>,
  draft: string,
): string | string[] | Record<string, unknown> {
  if (Array.isArray(originalValue)) {
    return draft
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
  }

  if (typeof originalValue === "object") {
    try {
      const parsed = JSON.parse(draft) as Record<string, unknown>
      return parsed
    } catch {
      return originalValue
    }
  }

  return draft
}
