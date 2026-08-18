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
  onAddCustomPreview: (prompt: string, tag: PromptTag) => Promise<void>
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

  const addCustom = async () => {
    const prompt = customPrompt.trim()
    if (!prompt || isAddingCustomPreview) {
      return
    }
    await onAddCustomPreview(prompt, customTag)
    setCustomPrompt("")
    setCustomTag("teaching_behavior")
  }

  return (
    <section className="text-card-foreground" aria-labelledby="preview-evidence-title">
      <div className="flex items-start justify-between gap-3 border-b pb-4">
        <div>
          <div className="dossier-label">Comparison record</div>
          <h3 id="preview-evidence-title" className="mt-1 text-[15px] font-semibold">
            Required preview cases
          </h3>
          <p className="mt-1 text-sm leading-5 text-muted-foreground">
            Configured tutor responses, source audit, and professor decisions.
          </p>
        </div>
        <Badge variant="outline" className="status-badge">
          {previewCases.length} cases
        </Badge>
      </div>

      {previewCases.length === 0 ? (
        <div className="mt-5 border border-dashed p-4 text-sm leading-6 text-muted-foreground">
          Preview cases appear after draft policy generation.
        </div>
      ) : (
        <div className="divide-y">
          {previewCases.map((preview, index) => (
            <PreviewCard
              key={preview.id}
              preview={preview}
              index={index + 1}
              reason={reasonByCase[preview.id] ?? ""}
              isSaving={updatingPreviewId === preview.id}
              onReasonChange={(reason) =>
                setReasonByCase((current) => ({
                  ...current,
                  [preview.id]: reason,
                }))
              }
              onDecision={onPreviewDecision}
            />
          ))}
        </div>
      )}

      <section className="mt-5 border-t pt-5" aria-labelledby="custom-preview-title">
        <div className="dossier-label">Additional evidence</div>
        <h3 id="custom-preview-title" className="mt-1 text-sm font-semibold">
          Professor custom prompt
        </h3>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          Add a tagged case that must be reviewed before approval.
        </p>
        <div className="mt-3 grid gap-3">
          <Textarea
            value={customPrompt}
            onChange={(event) => setCustomPrompt(event.target.value)}
            className="min-h-20 text-sm"
            placeholder="Write a prompt to test before approval..."
            aria-label="Custom preview prompt"
          />
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={customTag}
              onChange={(event) => setCustomTag(event.target.value as PromptTag)}
              className="h-10 rounded-md border bg-white px-3 text-sm outline-none focus-visible:border-[var(--cobalt)] focus-visible:ring-2 focus-visible:ring-ring/25"
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
      </section>
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
    <article className="py-5">
      <div className="grid grid-cols-[36px_minmax(0,1fr)] gap-3">
        <span className="dossier-label mt-0.5 text-[var(--cobalt)]">
          P-{String(index).padStart(2, "0")}
        </span>
        <div>
          <div className="flex gap-2 text-sm font-semibold leading-6">
            <MessageSquareText className="mt-1 size-4 shrink-0 text-[var(--cobalt)]" />
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

      <div className="mt-4 sm:ml-12">
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
        <div className="mt-3 space-y-1 border border-[var(--warning-border)] bg-[var(--warning-soft)] p-3 text-xs leading-5 text-[var(--warning)]">
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
          <CollapsibleTrigger className="flex min-h-10 w-full items-center justify-between border-y px-3 py-2 text-left text-sm font-semibold hover:bg-[var(--workspace)] focus-visible:outline-2 focus-visible:outline-[var(--cobalt)]">
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
          <CollapsibleTrigger className="flex min-h-10 w-full items-center justify-between border-y px-3 py-2 text-left text-sm font-semibold hover:bg-[var(--workspace)] focus-visible:outline-2 focus-visible:outline-[var(--cobalt)]">
            Source audit
            <FileSearch className="size-4" />
          </CollapsibleTrigger>
          <CollapsibleContent className="pt-3">
            <div className="border-t">
              {preview.source_audit.map((source) => (
                <div
                  key={`${preview.id}-${source.url}`}
                  className="border-b bg-[var(--workspace)] p-3 text-xs"
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

      <div className="mt-4 grid gap-3 border-t bg-[var(--workspace)] p-3">
        <label htmlFor={`decision-reason-${preview.id}`} className="dossier-label">
          Decision reason <span className="normal-case tracking-normal">(optional)</span>
        </label>
        <input
          id={`decision-reason-${preview.id}`}
          value={reason}
          onChange={(event) => onReasonChange(event.target.value)}
          placeholder="Optional decision reason"
          className="h-10 rounded-md border bg-white px-3 text-sm outline-none focus-visible:border-[var(--cobalt)] focus-visible:ring-2 focus-visible:ring-ring/25"
        />
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            variant={preview.decision === "accepted" ? "default" : "outline"}
            aria-pressed={preview.decision === "accepted"}
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
          ? "border-l-2 border-[var(--cobalt)] bg-[var(--cobalt-soft)] p-4"
          : "border-l-2 border-[var(--rule-strong)] bg-[var(--workspace)] p-4"
      }
    >
      <div className="dossier-label mb-1">
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
    return "border-[#b9cdfb] bg-[var(--cobalt-soft)] text-[var(--cobalt)]"
  }
  if (label === "professor-approved-external") {
    return "border-[var(--success-border)] bg-[var(--success-soft)] text-[var(--success)]"
  }
  return "border-[var(--warning-border)] bg-[var(--warning-soft)] text-[var(--warning)]"
}
