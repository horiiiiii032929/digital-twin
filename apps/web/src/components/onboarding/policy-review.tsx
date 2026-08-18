import { useEffect, useMemo, useState } from "react"
import { ChevronDown, Loader2, Save, ShieldAlert } from "lucide-react"

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

type FieldDraft = {
  status: FieldStatus
  value: string
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
  const [drafts, setDrafts] = useState<Record<string, FieldDraft>>({})

  useEffect(() => {
    if (!policy) {
      setDrafts({})
      return
    }

    setDrafts((current) => {
      const next = { ...current }

      for (const field of groups.flatMap((group) => group.fields)) {
        if (!(field.id in next)) {
          next[field.id] = {
            status: field.status,
            value: fieldValueToText(field.value),
          }
        }
      }

      return next
    })
  }, [groups, policy])

  return (
    <section className="p-5 text-card-foreground sm:p-6" aria-labelledby="policy-review-title">
      <div className="flex items-start justify-between gap-3 border-b pb-5">
        <div>
          <h3 id="policy-review-title" className="text-lg font-semibold tracking-[-0.02em]">
            Tutor policy
          </h3>
          <p className="mt-1 text-sm leading-5 text-muted-foreground">
            Review the guidance generated from your interview.
          </p>
        </div>
        <ReleaseBadge status={policy?.release_status ?? "draft"} />
      </div>

      {!policy ? (
        <div className="mt-5 rounded-xl border border-dashed p-5 text-sm leading-6 text-muted-foreground">
          Complete the interview to generate policy fields.
        </div>
      ) : (
        <div className="flex flex-col gap-5 pt-5">
          {groups.map((group) => (
            <section key={group.title} className="overflow-hidden rounded-xl border">
              <div className="flex items-center justify-between gap-3 bg-[var(--shell)] px-4 py-3">
                <h4 className="text-sm font-semibold">{group.title}</h4>
                <span className="text-xs tabular-nums text-muted-foreground">
                  {group.fields.length} field{group.fields.length === 1 ? "" : "s"}
                </span>
              </div>
              <div>
                {group.fields.map((field) => (
                  <FieldEditor
                    key={field.id}
                    field={field}
                    draft={drafts[field.id] ?? {
                      status: field.status,
                      value: fieldValueToText(field.value),
                    }}
                    isSaving={updatingFieldId === field.id}
                    onDraftChange={(draft) =>
                      setDrafts((current) => ({
                        ...current,
                        [field.id]: draft,
                      }))
                    }
                    onSave={() =>
                      onUpdateField(
                        field.id,
                        textToFieldValue(
                          field.value,
                          drafts[field.id]?.value ?? fieldValueToText(field.value),
                        ),
                        drafts[field.id]?.status ?? field.status,
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
  draft: FieldDraft
  isSaving: boolean
  onDraftChange: (draft: FieldDraft) => void
  onSave: () => Promise<void>
}) {
  const isStructuredValue =
    typeof field.value === "object" && !Array.isArray(field.value)
  const [structuredEditorOpen, setStructuredEditorOpen] = useState(false)
  const structuredValueIsValid =
    !isStructuredValue || isValidStructuredValue(draft.value)

  return (
    <article className="grid gap-3 border-t p-4 first:border-t-0 sm:grid-cols-[minmax(140px,0.72fr)_minmax(220px,1.28fr)]">
      <div>
        <div className="text-sm font-semibold leading-5">{field.label}</div>
        <StatusLabel status={field.status} />
      </div>
      <div className="min-w-0">
        {isStructuredValue ? (
          <div className="rounded-lg border bg-[var(--shell)] px-3 py-2.5">
            <p className="text-sm leading-5 text-foreground">
              {summarizeStructuredValue(draft.value)}
            </p>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="mt-1 -ml-2 h-7 px-2 text-xs text-muted-foreground"
              aria-expanded={structuredEditorOpen}
              onClick={() => setStructuredEditorOpen((open) => !open)}
            >
              Edit JSON
              <ChevronDown
                data-icon="inline-end"
                className={cn(
                  "transition-transform",
                  structuredEditorOpen && "rotate-180",
                )}
              />
            </Button>
          </div>
        ) : null}

        {!isStructuredValue || structuredEditorOpen ? (
          <Textarea
            value={draft.value}
            onChange={(event) =>
              onDraftChange({ ...draft, value: event.target.value })
            }
            className={cn(
              "h-20 min-h-20 resize-y text-sm leading-5",
              isStructuredValue && "mt-2 font-mono text-xs",
            )}
            aria-label={`${field.label} value`}
            aria-invalid={!structuredValueIsValid}
          />
        ) : null}

        {isStructuredValue && !structuredValueIsValid ? (
          <p className="mt-2 text-xs font-medium text-[var(--destructive-ink)]">
            Enter a valid JSON object before saving.
          </p>
        ) : null}

        <div className="mt-2 flex items-center gap-2">
          <div className="relative min-w-0 flex-1">
            <select
              value={draft.status}
              onChange={(event) =>
                onDraftChange({
                  ...draft,
                  status: event.target.value as FieldStatus,
                })
              }
              aria-label={`${field.label} status`}
              disabled={isSaving}
              className="h-9 w-full appearance-none rounded-lg border bg-white px-3 pr-8 text-xs font-medium outline-none focus-visible:border-[var(--accent-border)] focus-visible:ring-2 focus-visible:ring-[var(--accent-soft)]"
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <ChevronDown
              className="pointer-events-none absolute right-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
          </div>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => void onSave()}
            disabled={isSaving || !structuredValueIsValid}
          >
            {isSaving ? (
              <Loader2 data-icon="inline-start" className="animate-spin" />
            ) : (
              <Save data-icon="inline-start" />
            )}
            Save
          </Button>
        </div>
      </div>

      {(field.warning || field.safe_default) ? (
        <div className="flex flex-col gap-2 sm:col-start-2">
          {field.warning ? (
            <p className="flex gap-2 rounded-lg bg-[var(--warning-soft)] p-3 text-xs leading-5 text-[var(--warning)]">
              <ShieldAlert className="mt-0.5 size-3.5 shrink-0" />
              {field.warning}
            </p>
          ) : null}
          {field.safe_default ? (
            <p className="rounded-lg bg-[var(--accent-soft)] p-3 text-xs leading-5 text-[var(--accent-foreground)]">
              Safe default: {field.safe_default}
            </p>
          ) : null}
        </div>
      ) : null}
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

function summarizeStructuredValue(value: string): string {
  try {
    const parsed = JSON.parse(value) as Record<string, unknown>
    const current = parsed.source_strictness
    const recommended = parsed.recommended_value

    if (typeof current === "string" && current !== "unresolved") {
      return `Current: ${current.replaceAll("_", " ")}`
    }
    if (typeof recommended === "string") {
      return `Not confirmed · Recommended: ${recommended.replaceAll("_", " ")}`
    }
  } catch {
    return "Invalid JSON · Open the editor to correct it"
  }

  return "Structured policy value"
}

function isValidStructuredValue(value: string): boolean {
  try {
    const parsed = JSON.parse(value)
    return Boolean(parsed) && typeof parsed === "object" && !Array.isArray(parsed)
  } catch {
    return false
  }
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
