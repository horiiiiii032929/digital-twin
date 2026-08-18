import { useEffect, useMemo, useState } from "react"
import { Loader2, Save, ShieldAlert } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import type { FieldStatus, PolicyField, TutorPolicy } from "@/lib/api/types"
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
    <section className="text-card-foreground" aria-labelledby="policy-review-title">
      <div className="flex items-start justify-between gap-3 border-b pb-4">
        <div>
          <div className="dossier-label">Policy record</div>
          <h3 id="policy-review-title" className="mt-1 text-[15px] font-semibold">
            Generated tutor policy
          </h3>
          <p className="mt-1 text-sm leading-5 text-muted-foreground">
            Editable fields generated from the instructor interview.
          </p>
        </div>
        <ReleaseBadge status={policy?.release_status ?? "draft"} />
      </div>

      {!policy ? (
        <div className="mt-5 border border-dashed p-4 text-sm leading-6 text-muted-foreground">
          Complete the interview to generate policy fields.
        </div>
      ) : (
        <div className="divide-y">
          {groups.map((group) => (
            <section key={group.title} className="py-5 first:pt-5">
              <div className="mb-3 flex items-center justify-between gap-3">
                <h4 className="dossier-label text-[var(--ink)]">{group.title}</h4>
                <span className="text-xs tabular-nums text-muted-foreground">
                  {group.fields.length} field{group.fields.length === 1 ? "" : "s"}
                </span>
              </div>
              <div className="border-t">
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
            </section>
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
    <article className="border-b py-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold">{field.label}</div>
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
        className={cn(
          "min-h-24 resize-y text-sm leading-6",
          typeof field.value === "object" &&
            !Array.isArray(field.value) &&
            "font-mono text-xs",
        )}
        aria-label={`${field.label} value`}
      />

      <div className="mt-2 flex flex-wrap gap-2">
        {STATUS_OPTIONS.map((option) => (
          <Button
            key={option.value}
            type="button"
            size="sm"
            variant={field.status === option.value ? "default" : "outline"}
            aria-pressed={field.status === option.value}
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
            <p className="flex gap-2 border border-[var(--warning-border)] bg-[var(--warning-soft)] p-3 text-[var(--warning)]">
              <ShieldAlert className="mt-0.5 size-3.5 shrink-0" />
              {field.warning}
            </p>
          )}
          {field.safe_default && (
            <p className="border border-[#b9cdfb] bg-[var(--cobalt-soft)] p-3 text-[var(--cobalt)]">
              Safe default: {field.safe_default}
            </p>
          )}
        </div>
      )}
    </article>
  )
}

function ReleaseBadge({ status }: { status: string }) {
  return (
    <Badge
      variant="outline"
      className={cn(
        "status-badge",
        status === "approved" && "status-badge-success",
        status === "blocked" && "status-badge-danger",
        status === "draft" && "status-badge-warning",
      )}
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
        status === "resolved" && "text-[var(--success)]",
        status === "needs_review" && "text-[var(--warning)]",
        status === "blocks_release" && "text-[var(--destructive-ink)]",
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
