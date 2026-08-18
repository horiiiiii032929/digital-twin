import { useState } from "react"
import {
  AlertTriangle,
  Check,
  ChevronDown,
  FileSearch,
  Loader2,
  MessageSquareText,
  Plus,
  X,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Textarea } from "@/components/ui/textarea"
import type {
  PreviewCase,
  PreviewDecisionValue,
  PromptTag,
  SourceLabel,
} from "@/lib/api/types"
import { cn } from "@/lib/utils"

type PreviewComparisonProps = {
  previewCases: PreviewCase[]
  updatingPreviewId: string | null
  isAddingCustomPreview: boolean
  onPreviewDecision: (
    previewCaseId: string,
    decision: PreviewDecisionValue,
    reason?: string,
  ) => Promise<void>
  onAddCustomPreview: (prompt: string, tag: PromptTag) => Promise<boolean>
}

const PROMPT_TAGS: Array<{ value: PromptTag; label: string }> = [
  { value: "source_grounding", label: "Source grounding" },
  { value: "academic_integrity", label: "Academic integrity" },
  { value: "misconception", label: "Misconception" },
  { value: "teaching_behavior", label: "Teaching behavior" },
  { value: "tone", label: "Tone" },
  { value: "other", label: "Other" },
]

export function PreviewComparison({
  previewCases,
  updatingPreviewId,
  isAddingCustomPreview,
  onPreviewDecision,
  onAddCustomPreview,
}: PreviewComparisonProps) {
  const [reasonByCase, setReasonByCase] = useState<Record<string, string>>({})
  const [customPrompt, setCustomPrompt] = useState("")
  const [customTag, setCustomTag] = useState<PromptTag>("teaching_behavior")
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null)
  const [customPromptOpen, setCustomPromptOpen] = useState(false)
  const fallbackCase =
    previewCases.find((preview) => preview.decision === "pending") ??
    previewCases[0]
  const selectedPreview =
    previewCases.find((preview) => preview.id === selectedCaseId) ?? fallbackCase
  const selectedIndex = selectedPreview
    ? previewCases.findIndex((preview) => preview.id === selectedPreview.id)
    : -1
  const acceptedCount = previewCases.filter(
    (preview) => preview.decision === "accepted",
  ).length
  const rejectedCount = previewCases.filter(
    (preview) => preview.decision === "rejected",
  ).length
  const pendingCount = previewCases.length - acceptedCount - rejectedCount

  const addCustom = async () => {
    const prompt = customPrompt.trim()
    if (!prompt || isAddingCustomPreview) {
      return
    }
    if (!(await onAddCustomPreview(prompt, customTag))) {
      return
    }
    setCustomPrompt("")
    setCustomTag("teaching_behavior")
  }

  return (
    <section className="text-card-foreground" aria-labelledby="preview-evidence-title">
      <div className="flex items-start justify-between gap-3 border-b pb-5 pr-11">
        <div>
          <h3 id="preview-evidence-title" className="text-lg font-semibold tracking-[-0.02em]">
            Preview
          </h3>
          <p className="mt-1 text-sm leading-5 text-muted-foreground">
            Compare tutor behavior, inspect its sources, and record your decision.
          </p>
        </div>
        <Badge variant="outline" className="status-badge">
          {previewCases.length} cases
        </Badge>
      </div>

      {previewCases.length === 0 ? (
        <div className="mt-5 rounded-xl border border-dashed p-5 text-sm leading-6 text-muted-foreground">
          Preview cases appear after draft policy generation.
        </div>
      ) : (
        <div className="flex flex-col gap-4 pt-5">
          <div
            className="flex flex-wrap gap-x-4 gap-y-1 rounded-lg bg-[var(--shell)] px-3 py-2.5 text-xs font-medium"
            aria-label={`${acceptedCount} accepted, ${pendingCount} pending, ${rejectedCount} rejected`}
          >
            <span className="text-[var(--success)]">{acceptedCount} accepted</span>
            <span className="text-[var(--warning)]">{pendingCount} pending</span>
            <span className="text-[var(--destructive-ink)]">{rejectedCount} rejected</span>
          </div>

          <nav aria-label="Preview case queue">
            <ol className="overflow-hidden rounded-xl border">
              {previewCases.map((preview, index) => (
                <li key={preview.id} className="border-b last:border-b-0">
                  <button
                    type="button"
                    className={cn(
                      "flex min-h-12 w-full items-center gap-3 px-3 py-2.5 text-left outline-none hover:bg-[var(--shell)] focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring/30",
                      selectedPreview?.id === preview.id && "bg-[var(--accent-soft)]",
                    )}
                    aria-current={selectedPreview?.id === preview.id ? "true" : undefined}
                    aria-label={`Open preview case ${index + 1}: ${formatTag(preview.tag)}, ${preview.decision}`}
                    onClick={() => setSelectedCaseId(preview.id)}
                  >
                    <span className="flex size-7 shrink-0 items-center justify-center rounded-lg border bg-white text-xs font-semibold">
                      {index + 1}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold">
                        {formatTag(preview.tag)}
                      </span>
                      <span className="block truncate text-xs text-muted-foreground">
                        {preview.prompt}
                      </span>
                    </span>
                    <DecisionBadge decision={preview.decision} />
                  </button>
                </li>
              ))}
            </ol>
          </nav>

          {selectedPreview ? (
            <PreviewCard
              key={selectedPreview.id}
              preview={selectedPreview}
              index={selectedIndex + 1}
              reason={reasonByCase[selectedPreview.id] ?? ""}
              isSaving={updatingPreviewId === selectedPreview.id}
              onReasonChange={(reason) =>
                setReasonByCase((current) => ({
                  ...current,
                  [selectedPreview.id]: reason,
                }))
              }
              onDecision={onPreviewDecision}
            />
          ) : null}
        </div>
      )}

      <Collapsible
        open={customPromptOpen}
        onOpenChange={setCustomPromptOpen}
        className="mt-5 overflow-hidden rounded-xl border bg-[var(--shell)]"
      >
        <CollapsibleTrigger className="flex min-h-12 w-full items-center justify-between gap-3 px-4 py-3 text-left text-sm font-semibold outline-none hover:bg-[var(--subtle)] focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring/30">
          <span>
            Add a custom test
            <span className="mt-0.5 block text-xs font-normal text-muted-foreground">
              Optional professor-authored preview case
            </span>
          </span>
          <Plus
            className={cn(
              "size-4 shrink-0 transition-transform",
              customPromptOpen && "rotate-45",
            )}
            aria-hidden="true"
          />
        </CollapsibleTrigger>
        <CollapsibleContent className="border-t p-4">
          <div className="grid gap-3">
            <Textarea
              value={customPrompt}
              onChange={(event) => setCustomPrompt(event.target.value)}
              className="min-h-20 bg-white text-sm"
              placeholder="Write a prompt to test before approval..."
              aria-label="Custom preview prompt"
            />
            <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
              <select
                value={customTag}
                onChange={(event) => setCustomTag(event.target.value as PromptTag)}
                className="h-10 min-w-0 rounded-lg border bg-white px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/25"
                aria-label="Custom prompt tag"
              >
                {PROMPT_TAGS.map((tag) => (
                  <option key={tag.value} value={tag.value}>
                    {tag.label}
                  </option>
                ))}
              </select>
              <Button
                type="button"
                size="sm"
                onClick={() => void addCustom()}
                disabled={!customPrompt.trim() || isAddingCustomPreview}
              >
                {isAddingCustomPreview ? (
                  <Loader2 data-icon="inline-start" className="animate-spin" />
                ) : (
                  <Plus data-icon="inline-start" />
                )}
                Add prompt
              </Button>
            </div>
          </div>
        </CollapsibleContent>
      </Collapsible>
    </section>
  )
}

function PreviewCard({
  preview,
  index,
  reason,
  isSaving,
  onReasonChange,
  onDecision,
}: {
  preview: PreviewCase
  index: number
  reason: string
  isSaving: boolean
  onReasonChange: (reason: string) => void
  onDecision: (
    previewCaseId: string,
    decision: PreviewDecisionValue,
    reason?: string,
  ) => Promise<void>
}) {
  return (
    <article className="rounded-xl border p-4">
      <div className="grid grid-cols-[32px_minmax(0,1fr)] gap-3">
        <span className="flex size-8 items-center justify-center rounded-lg bg-[var(--accent-soft)] text-xs font-semibold text-[var(--accent-strong)]">
          {index}
        </span>
        <div>
          <div className="flex gap-2 text-sm font-semibold leading-6">
            <MessageSquareText className="mt-1 size-4 shrink-0 text-[var(--accent-strong)]" />
            <span>{preview.prompt}</span>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Badge variant="secondary">{formatTag(preview.tag)}</Badge>
            <DecisionBadge decision={preview.decision} />
            <Badge variant="outline">policy v{preview.policy_version}</Badge>
            {preview.generated_at && (
              <span className="text-xs text-muted-foreground">
                {new Date(preview.generated_at).toLocaleString()}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="mt-4 sm:ml-11">
        <ResponseBlock
          label="Configured response"
          body={preview.configured_response}
          tone="configured"
        />

      {preview.source_audit.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {preview.source_audit.map((source) => (
            <Badge
              key={`${preview.id}-${source.source_title}`}
              variant="outline"
              className={cn(labelTone(source.source_label))}
            >
              {source.source_label}
            </Badge>
          ))}
        </div>
      )}

      {preview.warnings.length > 0 && (
        <div className="mt-3 flex flex-col gap-1 rounded-lg bg-[var(--warning-soft)] p-3 text-xs leading-5 text-[var(--warning)]">
          {preview.warnings.map((warning) => (
            <div key={warning} className="flex gap-2">
              <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
              {warning}
            </div>
          ))}
        </div>
      )}

      <div className="mt-4 grid gap-2">
        <Collapsible>
          <CollapsibleTrigger
            className="flex min-h-10 w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm font-semibold outline-none hover:bg-[var(--shell)] focus-visible:ring-2 focus-visible:ring-ring/30"
            aria-label={`Show generic comparison for preview case ${index}`}
          >
            Generic comparison
            <ChevronDown className="size-4" />
          </CollapsibleTrigger>
          <CollapsibleContent className="pt-3">
            <ResponseBlock
              label="Generic response"
              body={preview.generic_response}
              tone="muted"
            />
          </CollapsibleContent>
        </Collapsible>

        <Collapsible>
          <CollapsibleTrigger
            className="flex min-h-10 w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm font-semibold outline-none hover:bg-[var(--shell)] focus-visible:ring-2 focus-visible:ring-ring/30"
            aria-label={`Show source audit for preview case ${index}`}
          >
            Source audit
            <FileSearch className="size-4" />
          </CollapsibleTrigger>
          <CollapsibleContent className="pt-3">
            <div className="overflow-hidden rounded-lg border">
              {preview.source_audit.map((source) => (
                <div
                  key={`${preview.id}-${source.url}`}
                  className="border-b bg-[var(--shell)] p-3 text-xs last:border-b-0"
                >
                  <div className="font-medium">{source.source_title}</div>
                  <div className="mt-1 break-words text-muted-foreground">
                    {source.url}
                  </div>
                  <div className="mt-2 grid gap-1">
                    <span>Type: {source.source_type}</span>
                    <span>Label: {source.source_label}</span>
                    <span>Supports: {source.supports}</span>
                    <span>Conflict: {source.conflict_status}</span>
                    <span>Selected: {source.selection_reason}</span>
                  </div>
                </div>
              ))}
            </div>
          </CollapsibleContent>
        </Collapsible>
      </div>

      <div className="mt-4 grid gap-3 rounded-lg bg-[var(--shell)] p-3">
        <label htmlFor={`decision-reason-${preview.id}`} className="text-xs font-medium text-muted-foreground">
          Case {index} decision reason (optional)
        </label>
        <input
          id={`decision-reason-${preview.id}`}
          value={reason}
          onChange={(event) => onReasonChange(event.target.value)}
          placeholder="Optional decision reason"
          className="h-10 rounded-lg border bg-white px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/25"
        />
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            variant={preview.decision === "accepted" ? "default" : "outline"}
            aria-pressed={preview.decision === "accepted"}
            aria-label={`Accept preview case ${index}`}
            disabled={isSaving}
            onClick={() => void onDecision(preview.id, "accepted", reason)}
          >
            {isSaving ? (
              <Loader2 data-icon="inline-start" className="animate-spin" />
            ) : (
              <Check data-icon="inline-start" />
            )}
            Accept
          </Button>
          <Button
            type="button"
            size="sm"
            variant={preview.decision === "rejected" ? "default" : "outline"}
            aria-pressed={preview.decision === "rejected"}
            aria-label={`Reject preview case ${index}`}
            disabled={isSaving}
            onClick={() => void onDecision(preview.id, "rejected", reason)}
          >
            <X data-icon="inline-start" />
            Reject
          </Button>
        </div>
      </div>
      </div>
    </article>
  )
}

function ResponseBlock({
  label,
  body,
  tone,
}: {
  label: string
  body: string
  tone: "muted" | "configured"
}) {
  return (
    <div
      className={
        tone === "configured"
          ? "rounded-lg bg-[var(--accent-soft)] p-4"
          : "rounded-lg bg-[var(--shell)] p-4"
      }
    >
      <div className="mb-1 text-xs font-medium text-muted-foreground">
        {label}
      </div>
      <p className="whitespace-pre-line text-sm leading-6">{body}</p>
    </div>
  )
}

function DecisionBadge({ decision }: { decision: PreviewDecisionValue }) {
  return (
    <Badge
      variant="outline"
      className={cn(
        "status-badge",
        decision === "accepted" && "status-badge-success",
        decision === "pending" && "status-badge-warning",
        decision === "rejected" && "status-badge-danger",
      )}
    >
      {decision}
    </Badge>
  )
}

function formatTag(tag: PromptTag): string {
  return tag.replaceAll("_", " ")
}

function labelTone(label: SourceLabel): string {
  if (label === "course-approved") {
    return "border-[var(--success-border)] bg-[var(--success-soft)] text-[var(--success)]"
  }
  if (label === "system-suggested-trusted") {
    return "border-[var(--accent-border)] bg-[var(--accent-soft)] text-[var(--accent-strong)]"
  }
  if (label === "professor-approved-external") {
    return "border-[var(--success-border)] bg-[var(--success-soft)] text-[var(--success)]"
  }
  return "border-[var(--warning-border)] bg-[var(--warning-soft)] text-[var(--warning)]"
}
