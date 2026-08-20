import { useEffect, useMemo, useRef, useState } from "react"
import { ChevronDown, Loader2, Save, ShieldAlert } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import type { FieldStatus, PolicyField, TutorPolicy } from "@/lib/api/types"
import { mergePolicyDrafts, type FieldDraft } from "@/lib/onboarding/policy-drafts"
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
  const allFields = useMemo(
    () => groups.flatMap((group) => group.fields),
    [groups],
  )
  const statusCounts = useMemo(
    () => ({
      resolved: allFields.filter((field) => field.status === "resolved").length,
      needsReview: allFields.filter((field) => field.status === "needs_review").length,
      blockers: allFields.filter((field) => field.status === "blocks_release").length,
    }),
    [allFields],
  )
  const [drafts, setDrafts] = useState<Record<string, FieldDraft>>({})
  const serverDrafts = useRef<Record<string, FieldDraft>>({})
  const [expandedFieldId, setExpandedFieldId] = useState<string | null>(null)

  useEffect(() => {
    if (!policy) {
      setDrafts({})
      serverDrafts.current = {}
      setExpandedFieldId(null)
      return
    }

    const nextServerDrafts = Object.fromEntries(
      allFields.map((field) => [
          field.id,
          {
            status: field.status,
            value: fieldValueToText(field.value),
          },
        ]),
    )
    setDrafts((current) =>
      mergePolicyDrafts(current, serverDrafts.current, nextServerDrafts),
    )
    serverDrafts.current = nextServerDrafts
    setExpandedFieldId((current) => {
      if (current && allFields.some((field) => field.id === current)) {
        return current
      }
      return (
        allFields.find((field) => field.status === "blocks_release")?.id ??
        allFields.find((field) => field.status === "needs_review")?.id ??
        allFields[0]?.id ??
        null
      )
    })
  }, [allFields, policy])

  return (
    <section className="p-5 text-card-foreground sm:p-6" aria-labelledby="policy-review-title">
      <div className="flex items-start justify-between gap-3 border-b pb-5 pr-11">
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
          <div
            className="flex flex-wrap gap-x-4 gap-y-1 rounded-lg bg-[var(--shell)] px-3 py-2.5 text-xs font-medium"
            aria-label={`${statusCounts.resolved} resolved, ${statusCounts.needsReview} need review, ${statusCounts.blockers} block release`}
          >
            <span className="text-[var(--success)]">
              {statusCounts.resolved} resolved
            </span>
            <span className="text-[var(--warning)]">
              {statusCounts.needsReview} to review
            </span>
            <span className="text-[var(--destructive-ink)]">
              {statusCounts.blockers} blocking
            </span>
          </div>

          <p className="text-xs leading-5 text-muted-foreground">
            Open one field at a time. Saving a field records both its value and
            release status.
          </p>

          {groups.map((group) => (
            <section key={group.title} className="overflow-hidden rounded-xl border">
              <div className="flex items-center justify-between gap-3 bg-[var(--shell)] px-4 py-3">
                <h4 className="text-sm font-semibold">{group.title}</h4>
                <span className="text-xs tabular-nums text-muted-foreground">
                  {group.fields.filter((field) => field.status !== "resolved").length} open
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
                    expanded={expandedFieldId === field.id}
                    isSaving={updatingFieldId === field.id}
                    onToggle={() =>
                      setExpandedFieldId((current) =>
                        current === field.id ? null : field.id,
                      )
                    }
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
  expanded,
  isSaving,
  onToggle,
  onDraftChange,
  onSave,
}: {
  field: PolicyField
  draft: FieldDraft
  expanded: boolean
  isSaving: boolean
  onToggle: () => void
  onDraftChange: (draft: FieldDraft) => void
  onSave: () => Promise<void>
}) {
  const isStructuredValue =
    typeof field.value === "object" && !Array.isArray(field.value)
  const [structuredEditorOpen, setStructuredEditorOpen] = useState(false)
  const structuredValueIsValid =
    !isStructuredValue || isValidStructuredValue(draft.value)
  const editorId = `policy-field-${field.id}`

  return (
    <article className="border-t first:border-t-0">
      <button
        type="button"
        className="flex min-h-14 w-full items-center justify-between gap-3 px-4 py-3 text-left outline-none hover:bg-[var(--shell)] focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring/30"
        aria-expanded={expanded}
        aria-controls={editorId}
        onClick={onToggle}
      >
        <span className="min-w-0">
          <span className="block text-sm font-semibold leading-5">{field.label}</span>
          <StatusLabel status={field.status} />
        </span>
        <ChevronDown
          className={cn(
            "size-4 shrink-0 text-muted-foreground transition-transform",
            expanded && "rotate-180",
          )}
          aria-hidden="true"
        />
      </button>

      {expanded ? (
        <div id={editorId} className="min-w-0 border-t bg-[var(--shell)] p-4">
          {isStructuredValue ? (
            <div className="rounded-lg border bg-white px-3 py-2.5">
              <p className="text-sm leading-5 text-foreground">
                {summarizeStructuredValue(draft.value)}
              </p>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="mt-1 -ml-2 h-7 px-2 text-xs text-muted-foreground"
                aria-expanded={structuredEditorOpen}
                aria-label={`${structuredEditorOpen ? "Close" : "Edit"} ${field.label} JSON`}
                onClick={() => setStructuredEditorOpen((open) => !open)}
              >
                {structuredEditorOpen ? "Close JSON" : "Edit JSON"}
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

          <div className="mt-3 grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2">
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
              aria-label={`Save ${field.label}`}
            >
              {isSaving ? (
                <Loader2 data-icon="inline-start" className="animate-spin" />
              ) : (
                <Save data-icon="inline-start" />
              )}
              Save
            </Button>
          </div>

          {field.warning || field.safe_default ? (
            <div className="mt-3 flex flex-col gap-2">
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
    <span
      className={cn(
        "mt-0.5 block text-xs font-medium",
        status === "resolved" && "text-[var(--success)]",
        status === "needs_review" && "text-[var(--warning)]",
        status === "blocks_release" && "text-[var(--destructive-ink)]",
      )}
    >
      {status.replace("_", " ")}
    </span>
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
